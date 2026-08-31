.PHONY: help up down install setup-db load-data run run-open run-gui run-gui-open setup dev status logs clean test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start Docker services
	docker compose up -d

down: ## Stop Docker services
	docker compose down

install: ## Install all Python dependencies (incl. NiceGUI)
	pip install nicegui markdown requests streamlit neo4j groq sentence-transformers pandas psycopg2-binary pgvector python-dotenv streamlit-cookies-manager

setup-db: ## Create database tables
	docker exec -i aifinder-postgres psql -U aifinder -d aifinder < data/schema.sql
	docker exec -i aifinder-neo4j cypher-shell -u neo4j -p aifinder_pass < data/graph_schema.cypher

load-data: ## Load product data into DB
	python data/ingest.py
	python core/sync.py

run: ## Run Streamlit app
	streamlit run app.py --server.headless true

run-open: ## Run Streamlit app and open browser
	pkill -9 -f "streamlit run" 2>/dev/null; sleep 2
	streamlit run app.py --server.headless true --server.address 0.0.0.0 &
	sleep 3
	open http://localhost:8501

run-gui: ## Run NiceGUI app
	lsof -ti:8080 | xargs kill -9 2>/dev/null; pkill -9 -f "nicegui_app" 2>/dev/null; sleep 1
	python3 nicegui_app.py

run-gui-open: ## Run NiceGUI app and open browser
	lsof -ti:8080 | xargs kill -9 2>/dev/null; pkill -9 -f "nicegui_app" 2>/dev/null; sleep 1
	python3 nicegui_app.py &
	sleep 5
	open http://localhost:8080

setup: install up setup-db load-data ## 1) Install everything (deps + DB + data)

dev: setup run ## Full setup + run (Streamlit)

status: ## Show service status
	docker compose ps

logs: ## Show Docker logs
	docker compose logs -f

clean: ## Remove all data and containers
	docker compose down -v
	rm -rf __pycache__ data/__pycache__ core/__pycache__ pages/__pycache__

restart: down up ## Restart Docker services

psql: ## Connect to PostgreSQL
	docker exec -it aifinder-postgres psql -U aifinder -d aifinder

neo4j: ## Open Neo4j shell
	docker exec -it aifinder-neo4j cypher-shell -u neo4j -p aifinder_pass

reindex: ## Reindex database
	docker exec -i aifinder-postgres psql -U aifinder -d aifinder -c "REINDEX INDEX idx_products_embedding;"

test: ## Run all tests
	python3 tests/test_all.py

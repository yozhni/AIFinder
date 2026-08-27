.PHONY: help up down install setup-db load-data run setup dev status logs clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start Docker services
	docker compose up -d

down: ## Stop Docker services
	docker compose down

install: ## Install Python dependencies
	pip install -r requirements.txt

setup-db: ## Create database tables
	docker exec -i aifinder-postgres psql -U aifinder -d aifinder < data/schema.sql
	docker exec -i aifinder-neo4j cypher-shell -u neo4j -p aifinder_pass < data/graph_schema.cypher

load-data: ## Load product data
	python data/ingest.py
	python core/sync.py

run: ## Run Streamlit app
	streamlit run app.py

setup: install up setup-db load-data ## Full setup (install + db + data)

dev: setup run ## Full setup + run

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

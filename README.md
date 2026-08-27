# AIFinder

Sales chatbot that helps users find lab products, compare items, get recommendations, and mock-purchase.

## Features

- Natural language product search (semantic + SQL + graph traversal)
- Product comparison by name
- Context-aware recommendations via Neo4j graph
- 20-step conversation memory
- Mock e-commerce (cart, orders)
- Free at all stages

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Streamlit App                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Chat     │  │ Products │  │ Cart/Orders      │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
└───────┼──────────────┼─────────────────┼────────────┘
        │              │                 │
┌───────▼──────────────▼─────────────────▼────────────┐
│              core/search.py                          │
│         (PostgreSQL + Neo4j + Embeddings)            │
└───────┬──────────────┬─────────────────┬────────────┘
        │              │                 │
┌───────▼──────┐ ┌─────▼─────┐ ┌────────▼────────────┐
│ PostgreSQL   │ │   Neo4j   │ │ Local Embeddings    │
│ (products,   │ │  (graph   │ │ (MiniLM-L6-v2)      │
│  chat_hist)  │ │  rels)    │ │                     │
└──────────────┘ └───────────┘ └─────────────────────┘
        │              │
┌───────▼──────────────▼──────────────────────────────┐
│                    LLM Layer                         │
│  ┌─────────────────┐  ┌──────────────────────────┐  │
│  │ Groq (cloud)    │  │ Ollama (local fallback)  │  │
│  │ llama-3.1-8b    │  │ qwen2.5:3b               │  │
│  │ 560 tokens/sec  │  │ 80-120 tokens/sec        │  │
│  └─────────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker Desktop installed
- Python 3.10+
- (Optional) Groq API key for cloud LLM
- (Optional) Ollama for local LLM

### Python Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI framework |
| `neo4j` | Neo4j database driver |
| `groq` | Groq API client |
| `sentence-transformers` | Embedding model (MiniLM-L6-v2) |
| `pandas` | CSV data handling |
| `psycopg2-binary` | PostgreSQL driver |
| `pgvector` | Vector similarity search |
| `python-dotenv` | Environment variable loading |
| `streamlit-cookies-manager` | Browser cookie for session persistence |

Install all at once:
```bash
make install
```

### 1. Start Services

```bash
make up
```

Or manually:
```bash
docker compose up -d
```

### 2. Install Python Dependencies

```bash
make install
```

Or manually:
```bash
pip install -r requirements.txt
```

### 3. Setup Database

```bash
make setup-db
```

Or manually:
```bash
# Create tables in PostgreSQL
docker exec -i aifinder-postgres psql -U aifinder -d aifinder < data/schema.sql

# Create graph schema in Neo4j
docker exec -i aifinder-neo4j cypher-shell -u neo4j -p aifinder_pass < data/graph_schema.cypher
```

### 4. Load Data

```bash
make load-data
```

Or manually:
```bash
python data/ingest.py
python core/sync.py
```

### 5. Run App

```bash
make run
```

Or manually:
```bash
streamlit run app.py
```

### 6. Open in Browser

- **App**: http://localhost:8501
- **Neo4j Browser**: http://localhost:7474 (login: neo4j / aifinder_pass)

## Services

| Service | Port | URL | Login |
|---------|------|-----|-------|
| Streamlit App | 8501 | http://localhost:8501 | - |
| PostgreSQL | 5432 | localhost:5432 | aifinder / aifinder_pass |
| Neo4j Browser | 7474 | http://localhost:7474 | neo4j / aifinder_pass |
| Neo4j Bolt | 7687 | localhost:7687 | - |

## Make Commands

```bash
make help          # Show all commands
make up            # Start Docker services
make down          # Stop Docker services
make install       # Install Python dependencies
make setup-db      # Create database tables
make load-data     # Load product data
make run           # Run Streamlit app
make setup         # Full setup (install + up + setup-db + load-data)
make dev           # Full setup + run
make status        # Show service status
make logs          # Show Docker logs
make clean         # Remove all data and containers
```

## LLM Options

### Groq (Cloud) - Recommended

1. Get free API key at https://console.groq.com
2. Add to `.env`:
   ```
   GROQ_API_KEY=gsk_your_key_here
   ```
3. Model: `llama-3.1-8b-instant` (560 tokens/sec, free tier)

### Ollama (Local)

1. Install Ollama: https://ollama.com
2. Pull model: `ollama pull qwen2.5:3b`
3. App auto-detects Ollama as fallback

## Data

- **POC**: 500 products (test_data.csv)
- **Extended**: 10,000 products (test_data_10_000.csv)
- **Production**: 10M+ products

## Project Structure

```
AIFinder/
├── app.py                    # Main Streamlit entry point
├── pages/
│   ├── 1_Chat.py             # Chat interface
│   ├── 2_Products.py         # Product catalog
│   ├── 3_Cart.py             # Shopping cart
│   └── 4_Orders.py           # Order history
├── core/
│   ├── database.py           # PostgreSQL connection
│   ├── graph.py              # Neo4j connection
│   ├── embeddings.py         # Vector generation
│   ├── llm.py                # Groq/Ollama integration
│   ├── search.py             # Search orchestration
│   ├── sync.py               # PostgreSQL → Neo4j sync
│   └── tools.py              # LLM tool definitions
├── data/
│   ├── schema.sql            # PostgreSQL schema
│   ├── graph_schema.cypher   # Neo4j schema
│   ├── ingest.py             # Data ingestion
│   └── test_data.csv         # 500 products
├── docker-compose.yml        # Docker services
├── requirements.txt          # Python dependencies
├── Makefile                  # Build commands
├── .env.example              # API keys template
└── roadmap.md                # Implementation plan
```

## Pricing

| Phase | Components | Cost |
|-------|------------|------|
| POC | PostgreSQL + Neo4j + Groq + Local embeddings | $0 |
| Cloud | Streamlit Cloud + Groq free tier | $0 |
| Production | Paid tiers | $25-50/mo |

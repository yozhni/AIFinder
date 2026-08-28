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

### Hugging Face Token (Optional)

The embedding model (`all-MiniLM-L6-v2`) is downloaded from Hugging Face Hub on first run (~80MB). This works without a token, but you may see:

```
Warning: You are sending unauthenticated requests to the HF Hub
```

To remove this warning and get faster downloads:

1. Sign up at https://huggingface.co (free)
2. Go to Settings → Access Tokens → New token (Read role)
3. Add to `config.yaml`:
   ```yaml
   huggingface:
     token: hf_your_token_here
   ```

Without a token: model works fine, just slower downloads on first run.

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
pip install streamlit neo4j groq sentence-transformers pandas psycopg2-binary pgvector python-dotenv streamlit-cookies-manager
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

### Quick Start (One Command)

```bash
make run-open    # Starts app + opens browser
```

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

### Option 1: Ollama (Local) - Free

Completely free, runs on your machine, no internet required.

**Step 1: Install Ollama**
```bash
# macOS
brew install ollama

# Or download from https://ollama.com/download
```

**Step 2: Start Ollama**
```bash
ollama serve
```

**Step 3: Pull model**
```bash
ollama pull qwen2.5:3b
```

**Step 4: Configure**
Edit `config.yaml`:
```yaml
llm:
  provider: ollama
  ollama_model: qwen2.5:3b
```

**Models available:**
| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| qwen2.5:3b | 1.9 GB | 80-120 t/s | Good |
| qwen2.5:7b | 4.7 GB | 50-80 t/s | Better |
| llama3:8b | 4.7 GB | 50-80 t/s | Good |

### Option 2: Groq (Cloud) - Paid

Very fast inference, but costs money ($0.075-0.60 per 1M tokens).

**Step 1: Get API Key**
1. Go to https://console.groq.com
2. Sign up (free account)
3. Go to API Keys → Create Key
4. Copy the key

**Step 2: Configure**
Edit `config.yaml`:
```yaml
llm:
  provider: groq
  groq_model: openai/gpt-oss-20b

groq:
  api_key: gsk_your_key_here
```

**Available models:**
| Model | Speed | Price (per 1M tokens) |
|-------|-------|----------------------|
| openai/gpt-oss-20b | 1000 t/s | $0.075 in / $0.30 out |
| openai/gpt-oss-120b | 500 t/s | $0.15 in / $0.60 out |
| qwen/qwen3.6-27b | 500 t/s | $0.60 in / $3.00 out |

**Recommendation:** Start with Ollama (free). Switch to Groq only if you need faster responses.

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

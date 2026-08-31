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
│  │ Google (cloud) │  │ Ollama (local fallback)  │  │
│  │ llama-3.1-8b    │  │ qwen2.5:3b               │  │
│  │ 560 tokens/sec  │  │ 80-120 tokens/sec        │  │
│  └─────────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Quick Start
### 2 commands:

```bash
make setup           # 1) Install everything: deps + start Docker + create DB + load data
make run-gui-open    # 2) Run the app locally and open http://localhost:8080
```

### Prerequisites

- Docker Desktop installed
- Python 3.10+
- (Optional) Google AI API key for cloud LLM (see LLM Options)
- (Optional) Ollama for local LLM (see LLM Options)

### Python Dependencies

| Package | Purpose |
|---------|---------|
| `nicegui` | Web UI framework (primary frontend) |
| `streamlit` | Legacy web UI framework |
| `neo4j` | Neo4j database driver |
| `groq` | Groq API client |
| `sentence-transformers` | Embedding model (MiniLM-L6-v2) |
| `pandas` | CSV data handling |
| `psycopg2-binary` | PostgreSQL driver |
| `pgvector` | Vector similarity search |
| `python-dotenv` | Environment variable loading |

Install all at once:
```bash
make install
```

> The `make install` command installs the base packages. `nicegui` must be installed separately:
> ```bash
> pip install nicegui
> ```

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

**Option A: NiceGUI (primary, chat + catalog + cart in one UI)**
```bash
make run-gui-open    # Starts NiceGUI app + opens browser
```
Or manually:
```bash
python3 nicegui_app.py
```
App opens at **http://localhost:8080**

**Option B: Streamlit (legacy pages)**
```bash
make run
```
Or manually:
```bash
streamlit run app.py
```

### 6. Open in Browser


> **Recommended:** Use `make run-gui-open` for the current NiceGUI frontend (chatbot + products + cart + orders).

> **Prerequisite for chat:** if using Ollama, start it first with `ollama serve` then pull the model (`ollama pull qwen2.5:3b`).



**Step-by-step the same thing:**
```bash
make up            # start PostgreSQL + Neo4j containers
make install       # pip install all python deps (incl. nicegui)
make setup-db      # create tables in PostgreSQL + Neo4j
make load-data     # load product data into DB
make run-gui-open  # start NiceGUI app at http://localhost:8080
```

> **Prerequisite for chat:** start Ollama first, then pull the model:
> ```bash
> ollama serve &
> ollama pull qwen2.5:3b
> ```
> Or set a Google API key (see LLM Options below).

> If a previous instance is running, `make run-gui-open` kills old processes automatically.

## Services

| Service | Port | URL | Login |
|---------|------|-----|-------|
| NiceGUI App | 8080 | http://localhost:8080 | - |
| Streamlit App | 8501 | http://localhost:8501 | - |
| PostgreSQL | 5432 | localhost:5432 | aifinder / aifinder_pass |
| Neo4j Browser | 7474 | http://localhost:7474 | neo4j / aifinder_pass |
| Neo4j Bolt | 7687 | localhost:7687 | - |

## Make Commands

```bash
make help          # Show all commands
make setup         # 1) Install everything (deps + DB + data)
make run-gui-open  # 2) Run NiceGUI app + open browser
make up            # Start Docker services
make down          # Stop Docker services
make install       # Install all Python dependencies (incl. nicegui)
make setup-db      # Create database tables
make load-data     # Load product data into DB
make run           # Run Streamlit app (legacy)
make run-gui       # Run NiceGUI app
make run-open      # Run Streamlit app + open browser
make dev           # Full setup + run Streamlit
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

ollama:
  host: http://localhost:11434
  model: qwen2.5:3b
```

**Models available:**
| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| qwen2.5:3b | 1.9 GB | 80-120 t/s | Good |
| qwen2.5:7b | 4.7 GB | 50-80 t/s | Better |
| llama3:8b | 4.7 GB | 50-80 t/s | Good |

**Step 4 note:** the chat history cleanup config lives under `chat:`:
```yaml
chat:
  context_window_size: 20
  history_limit: 50      # max messages kept per session
  retention_days: 30     # delete inactive sessions after this many days
```

### Option 2: Google (Cloud) - Free tier

Free tier via Google AI Studio. Requires an API key.

**Step 1: Get API Key**
1. Go to https://aistudio.google.com/apikey
2. Create a key (free account)
3. Store it in `.env` as `GOOGLE_API_KEY` (file is gitignored):
   ```
   GOOGLE_API_KEY=AQ.your_key_here
   ```

**Step 2: Configure**
Edit `config.yaml`:
```yaml
llm:
  provider: google

google:
  model: auto
  api_key: ${GOOGLE_API_KEY}
```

**Recommendation:** Start with Ollama (free, offline). Switch to Google if you need faster/better responses without running a local model.

## Data

- **POC**: 500 products (test_data.csv)
- **Extended**: 10,000 products (test_data_10_000.csv)
- **Production**: 10M+ products

## Project Structure

```
AIFinder/
├── nicegui_app.py          # NiceGUI frontend (chat + catalog + cart + orders)
├── app.py                  # Main Streamlit entry point (legacy)
├── pages/
│   ├── 1_Chat.py           # Chat interface
│   ├── 2_Products.py       # Product catalog
│   ├── 3_Cart.py           # Shopping cart
│   └── 4_Orders.py         # Order history
├── core/
│   ├── database.py         # PostgreSQL connection
│   ├── graph.py            # Neo4j connection
│   ├── embeddings.py       # Vector generation
│   ├── llm.py              # Groq/Ollama integration
│   ├── search.py           # Search orchestration
│   ├── sync.py             # PostgreSQL → Neo4j sync
│   └── tools.py            # LLM tool definitions
├── data/
│   ├── schema.sql          # PostgreSQL schema
│   ├── graph_schema.cypher # Neo4j schema
│   ├── ingest.py           # Data ingestion
│   └── test_data.csv       # 500 products
├── static/                 # Images (main_page.png, microscope.png, placeholder.webp)
├── docker-compose.yml      # Docker services
├── Makefile                # Build commands
├── .env.example            # API keys template
└── roadmap.md              # Implementation plan
```

## Pricing

| Phase | Components | Cost |
|-------|------------|------|
| POC | PostgreSQL + Neo4j + Ollama (or Google free tier) + Local embeddings | $0 |
| Cloud | VPS/Railway + Ollama (or Google free tier) | $0-5/mo |
| Production | Paid tiers | $25-50/mo |

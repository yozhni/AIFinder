# AIFinder Implementation Roadmap

## Project Overview

**Goal**: Sales chatbot that helps users find lab products, compare items, get recommendations, and mock-purchase.

**Key Features**:
- Natural language product search (semantic + SQL + graph traversal)
- Product comparison by name
- Context-aware recommendations via Neo4j graph
- 20-step conversation memory
- Mock e-commerce (cart, orders)
- Free at all stages

---

## Project Structure

```
AIFinder/
├── app.py                          # Main Streamlit entry point
├── pages/
│   ├── 1_💬_Chat.py                # Chat interface (main sales bot)
│   ├── 2_📦_Products.py            # Product catalog browser
│   ├── 3_🛒_Cart.py                # Shopping cart (mock)
│   └── 4_📋_Orders.py              # Order history (mock)
├── core/
│   ├── __init__.py
│   ├── database.py                 # PostgreSQL connection & queries
│   ├── graph.py                    # Neo4j connection & graph queries
│   ├── embeddings.py               # Vector embedding generation
│   ├── llm.py                      # Groq/Ollama LLM integration
│   ├── search.py                   # Search orchestration (PostgreSQL + Neo4j)
│   ├── sync.py                     # PostgreSQL → Neo4j data sync
│   └── tools.py                    # LLM tool definitions
├── data/
│   ├── ingest.py                   # CSV → PostgreSQL ingestion script
│   ├── schema.sql                  # PostgreSQL schema
│   ├── graph_schema.cypher         # Neo4j graph schema
│   ├── generate_test_data.py       # Generate fake product data
│   └── testdata/
│       ├── test_data.csv           # 500 products (LC-0001 to LC-0500)
│       └── test_data_10_000.csv    # 10,000 products (LC-0001 to LC-10000)
├── tests/
│   └── test_all.py                 # Test suite
├── images/                         # Product images folder
├── config.py                       # YAML config loader
├── config.yaml                     # Centralized configuration
├── docker-compose.yml              # PostgreSQL + Neo4j containers
├── Makefile                        # Build commands
├── .env.example                    # API keys template
├── .gitignore                      # Git ignore rules
├── roadmap.md                      # Implementation plan
└── README.md                       # Full instructions
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Streamlit App                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ 💬 Chat  │  │ 📦 Products│  │ 🛒 Cart/Orders  │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │              │                 │             │
│  ┌────▼──────────────▼─────────────────▼─────────┐  │
│  │              core/search.py                    │  │
│  │         (orchestrates PostgreSQL + Neo4j)      │  │
│  └──┬─────────────────────┬──────────────────┬───┘  │
└─────┼─────────────────────┼──────────────────┼──────┘
      │                     │                  │
┌─────▼──────┐  ┌───────────▼──────────┐  ┌────▼────────────┐
│ PostgreSQL │  │        Neo4j         │  │ Local Embeddings│
│ - products │  │  - graph traversal   │  │ (MiniLM-L6-v2)  │
│ - chat     │  │  - workflows         │  │                 │
│ - cart     │  │  - compatibility     │  └─────────────────┘
│ - orders   │  │  - alternatives      │
│ - indexes  │  │  - no JOINs needed   │
└────────────┘  └──────────────────────┘
      │                     │
      └─────────┬───────────┘
                │
┌───────────────▼───────────────────────────────────────┐
│                    LLM Layer                          │
│  ┌─────────────────┐  ┌────────────────────────────┐  │
│  │ Groq (cloud)    │  │ Ollama (local fallback)    │  │
│  │ llama-3.1-8b    │  │ qwen2.5:3b                 │  │
│  │ 560 tokens/sec  │  │ 80-120 tokens/sec          │  │
│  │ Free tier       │  │ Free, 32K context           │  │
│  └─────────────────┘  └────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

---

## Data

| Stage | Rows | Product IDs |
|-------|------|-------------|
| **POC (test data)** | **500** | LC-0001 to LC-0500 |
| **Production** | **10M+** | TBD |

---

## LLM Selection

| Component | Model | Speed | Context | Cost |
|-----------|-------|-------|---------|------|
| **Groq (cloud)** | `llama-3.1-8b-instant` | **560 tokens/sec** | 131K | Free tier (6K tokens/min) |
| **Ollama (local)** | `qwen2.5:3b` | **80-120 tokens/sec** | 32K | Free |

**Why these models**:
- `llama-3.1-8b-instant`: Fastest on Groq (560 t/s), sufficient quality for sales assistant
- `qwen2.5:3b`: Small (1.9GB), 32K context (holds more history), fast, tool support, free license

---

## Speed Estimates

| Component | Time |
|-----------|------|
| Embedding generation (MiniLM-L6-v2) | ~50ms |
| PostgreSQL search (indexed) | ~20-50ms |
| Neo4j graph query (no JOINs) | ~20-50ms |
| LLM inference (Groq 560 t/s) | ~200-500ms |
| **Total per query** | **~300-650ms** |

With local Qwen2.5:3b (80-120 t/s): ~400-800ms per query.

---

## Phase 1: Setup (10 min)

### Step 1.1: Create project structure
- Create directories: `core/`, `pages/`, `data/`, `images/`

### Step 1.2: Create docker-compose.yml

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: aifinder
      POSTGRES_PASSWORD: aifinder_pass
      POSTGRES_DB: aifinder
    volumes:
      - pgdata:/var/lib/postgresql/data

  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"   # Browser UI
      - "7687:7687"   # Bolt protocol
    environment:
      NEO4J_AUTH: neo4j/aifinder_pass
      NEO4J_PLUGINS: '["graph-data-science"]'
    volumes:
      - neo4jdata:/data

volumes:
  pgdata:
  neo4jdata:
```

### Step 1.3: Create data/schema.sql
- Products table (30 columns)
- Chat history table
- Cart table
- Orders table
- All indexes (see Indexes section below)

### Step 1.4: Create data/graph_schema.cypher
- Neo4j node definitions
- Neo4j relationship definitions
- Indexes for Neo4j

### Step 1.5: Create requirements.txt
- streamlit
- neo4j (Python driver)
- groq
- sentence-transformers
- pandas
- python-dotenv
- psycopg2-binary
- pgvector

### Step 1.6: Create .env.example
- GROQ_API_KEY
- DATABASE_URL
- OLLAMA_HOST
- NEO4J_URI=bolt://localhost:7687
- NEO4J_USER=neo4j
- NEO4J_PASSWORD=aifinder_pass

---

## Phase 2: Core Database (20 min)

### Step 2.1: Create core/__init__.py
- Empty init file

### Step 2.2: Create core/database.py
- `get_connection()` - PostgreSQL connection pool
- `save_message(session_id, role, content)` - Save chat history
- `load_history(session_id, limit)` - Load last N messages
- `search_products(query, category, min_price, max_price, ...)` - SQL filter search
- `semantic_search(query_embedding, limit)` - Vector similarity search
- `get_product_by_name(product_name, brand)` - Name lookup
- `compare_products(product_name_1, product_name_2)` - Side-by-side comparison
- `add_to_cart(session_id, product_id, quantity)` - Add to cart
- `get_cart(session_id)` - View cart
- `add_product(data)` - CRUD: Create
- `update_product(product_id, data)` - CRUD: Update
- `delete_product(product_id)` - CRUD: Delete

### Step 2.3: Create core/graph.py
- `get_neo4j_driver()` - Neo4j connection
- `find_centrifuges_for_cell_harvest()` - Graph query for test 1
- `find_workflow_products(workflow_name)` - Graph query for test 2
- `search_products_by_name(name)` - Graph query for test 3
- `find_sterile_compatible(sterile, compatible_with)` - Graph query for test 4
- `compare_products_graph(name1, name2)` - Graph query for test 5
- `get_recommendations(context)` - Graph query for test 6
- `find_alternatives(product_id)` - Find alternative products
- `find_compatible_products(product_id)` - Find compatible products
- `find_products_in_workflow(workflow)` - Find all products in a workflow

### Step 2.4: Create core/embeddings.py
- Load all-MiniLM-L6-v2 model (384 dimensions)
- `generate_embedding(text)` → vector
- `batch_embed(texts)` → list of vectors

---

## Phase 3: Data Ingestion & Sync (20 min)

### Step 3.1: Create data/ingest.py
- Read CSV file (test_data.csv, 500 products)
- Parse all 26 columns
- Clean data:
  - Remove $ and , from price → float
  - Convert Yes/No → TRUE/FALSE for booleans
  - Handle NULL/empty values
- Generate embedding text from multiple fields:
  ```
  text = f"{product_name} {brand} {category} {application} 
          {use_case} {specifications} {used_for} {requires} 
          {alternative_to} {typical_user_question}"
  ```
- Call embedding model → vector [0.23, -0.45, ...] (384 dims)
- Insert into PostgreSQL with ALL columns + embedding
- Verify row count (500 products)

### Step 3.2: Create core/sync.py
- Sync products from PostgreSQL to Neo4j
- Create Product nodes from PostgreSQL rows
- Create Category, Application, UseCase, Workflow, Property nodes
- Create relationships from product data:
  - BELONGS_TO: product → category
  - HAS_APPLICATION: product → application
  - HAS_USE_CASE: product → use_case
  - HAS_PROPERTY: product → sterile, refrigerated, etc.
  - COMPATIBLE_WITH: derived from compatible_with column
  - ALTERNATIVE_TO: derived from alternative_to column
  - PART_OF_WORKFLOW: derived from application/use_case patterns
- Nightly cron job to rebuild relationships: `0 2 * * * python core/sync.py`

---

## Phase 4: Search & LLM (40 min)

### Step 4.1: Create core/search.py
- Orchestrates PostgreSQL and Neo4j searches
- `search_products()` - PostgreSQL SQL filters (category, price, brand, etc.)
- `semantic_search()` - PostgreSQL vector similarity (natural language queries)
- `graph_search()` - Neo4j graph traversal (workflow, compatibility, alternatives)
- `get_product_by_name()` - PostgreSQL name lookup (exact or partial match)
- `compare_products()` - PostgreSQL side-by-side comparison
- `get_recommendations()` - Neo4j graph-based recommendations
- `resolve_product_name()` - Handle multiple matches, ask for clarification

### Step 4.2: Create core/tools.py
- Define all 7 LLM tools:
  1. `search_products` - Search with SQL filters
  2. `semantic_search` - Natural language vector search
  3. `get_product_by_name` - Find by name
  4. `compare_products` - Compare two products
  5. `get_recommendations` - Graph-based recommendations
  6. `add_to_cart` - Add to cart
  7. `get_cart` - View cart

### Step 4.3: Create core/llm.py
- `get_llm_response(context, user_message)` - Main LLM function
- `build_context(session_id)` - Build chat history context (20 steps)
- `summarize_old_messages(messages)` - Token management
- `execute_tools(tool_calls)` - Tool execution
- Groq primary (llama-3.1-8b-instant, 560 t/s), Ollama fallback (qwen2.5:3b)
- System prompt (sales assistant persona)

---

## Phase 5: Streamlit App (50 min)

### Step 5.1: Create app.py
- Main entry point
- Navigation sidebar
- Session state initialization

### Step 5.2: Create pages/1_💬_Chat.py
- Chat interface
- Session ID management via browser cookie (streamlit-cookies-manager):
  - Generate UUID on first visit, save to cookie
  - Load same session_id on return visits
  - Cookie persists across tab close/reopen
  - Package: `pip install streamlit-cookies-manager`
- Message history display
- User input handling
- LLM response integration
- Tool result display
- Context persistence (20 steps back)
- Save/load from chat_history table

### Step 5.3: Create pages/2_📦_Products.py
- Product catalog grid
- Filters (category, brand, price range, etc.)
- Search functionality
- Product cards with images
- Add to cart buttons

### Step 5.4: Create pages/3_🛒_Cart.py
- Cart contents display
- Quantity update
- Remove items
- Checkout (mock)
- Order creation

### Step 5.5: Create pages/4_📋_Orders.py
- Order history display
- Order details
- Mock order creation

---

## Phase 6: Setup & Docs (15 min)

### Step 6.1: Create setup.sh
- Start Docker containers (PostgreSQL + Neo4j)
- pip install requirements
- Run PostgreSQL schema setup
- Run Neo4j graph schema setup
- Run data ingestion
- Run PostgreSQL → Neo4j sync
- Launch Streamlit app

### Step 6.2: Create README.md
- Project overview
- Setup instructions
- Testing guide
- Architecture diagram
- Pricing breakdown

---

## Phase 7: Testing (20 min)

### Step 7.1: Test data ingestion
- Verify 500 rows loaded in PostgreSQL
- Verify 500 Product nodes in Neo4j
- Check embeddings generated
- Verify all columns populated

### Step 7.2: Test chat scenarios

**Test 1**: "I need to harvest mammalian cells, what centrifuge I needed?"
- Expected: Neo4j graph query finds refrigerated centrifuges for cell harvest
```cypher
MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: "Equipment"})
MATCH (p)-[:HAS_APPLICATION]->(a:Application)
WHERE p.name CONTAINS "centrifuge" 
    AND p.refrigerated = true
    AND (a.name CONTAINS "cell" OR a.name CONTAINS "laboratory")
RETURN p.name, p.brand, p.price, p.specifications
ORDER BY p.price;
```

**Test 2**: "What equipment I need for recombinant protein expressing and purification"
- Expected: Neo4j graph traversal finds all products in protein purification workflow
```cypher
MATCH (w:Workflow)-[:REQUIRES]->(p:Product)
WHERE w.name CONTAINS "protein purification"
RETURN p.name, p.brand, p.price, p.category
```

**Test 3**: "Help to find pipettes"
- Expected: Search by name, handle not found gracefully
```cypher
MATCH (p:Product)
WHERE p.name CONTAINS "pipette"
RETURN p.name, p.brand, p.price;
```

**Test 4**: "Find sterile pipette tips that are compatible with Ergonomic pipettes"
- Expected: Neo4j filter + compatibility check (no JOINs)
```cypher
MATCH (p:Product)
WHERE p.name CONTAINS "pipette tips" AND p.sterile = true
OPTIONAL MATCH (p)-[:COMPATIBLE_WITH]->(compat:Product)
WHERE compat.name CONTAINS "ergonomic"
RETURN p.name, p.brand, p.price;
```

**Test 5**: "Compare the Size Exclusion Column and the Desalting Column"
- Expected: Name search → clarify if multiple matches → compare
```cypher
MATCH (p1:Product), (p2:Product)
WHERE p1.name CONTAINS "Size Exclusion Column" 
    AND p2.name CONTAINS "Desalting Column"
    AND p1.id < p2.id
RETURN p1, p2 LIMIT 1;
```

**Test 6**: "Recommend me.."
- Expected: Use conversation history + Neo4j graph for context-based recommendations
```cypher
// If previous context was "mammalian cell culture"
MATCH (p:Product)-[:HAS_APPLICATION]->(a:Application)
WHERE a.name CONTAINS "cell culture"
RETURN p.name, p.brand, p.price, p.specifications
ORDER BY p.price LIMIT 5;
```

### Step 7.3: Test chat history
- Send 20+ messages
- Verify context maintained
- Test page refresh persistence
- Test summarize older messages

### Step 7.4: Test CRUD
- Add product (PostgreSQL)
- Update product (PostgreSQL)
- Delete product (PostgreSQL)
- Verify sync to Neo4j

### Step 7.5: Test mock e-commerce
- Add to cart
- View cart
- Mock checkout
- View orders

---

## PostgreSQL Schema (30 Columns)

### Products Table
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE products (
    -- All CSV columns (26)
    id VARCHAR(10) PRIMARY KEY,
    category VARCHAR(100),
    product_name VARCHAR(200),
    brand VARCHAR(100),
    model_sku VARCHAR(50),
    specifications TEXT,
    volume_or_capacity VARCHAR(100),
    max_rcf_xg INTEGER,
    refrigerated BOOLEAN DEFAULT FALSE,
    sterile BOOLEAN DEFAULT FALSE,
    endotoxin_free BOOLEAN DEFAULT FALSE,
    application VARCHAR(200),
    use_case VARCHAR(200),
    compatible_with TEXT,
    used_for VARCHAR(200),
    requires TEXT,
    alternative_to TEXT,
    limitations_notes TEXT,
    typical_user_question TEXT,
    price_usd DECIMAL(10,2),
    verification_status VARCHAR(100),
    data_provenance VARCHAR(100),
    source_reference TEXT,
    url VARCHAR(500),
    discount DECIMAL(5,2),           -- Percentage, e.g., 15.5 = 15.5%
    is_deleted BOOLEAN DEFAULT FALSE,
    
    -- Generated columns (4)
    embedding vector(384),
    image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Chat History Table
```sql
CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,           -- 'user' or 'assistant'
    content TEXT NOT NULL,
    tool_calls JSONB,                    -- Optional: what tools were called
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chat_session ON chat_history(session_id, created_at DESC);
```

### Cart Table
```sql
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    product_id VARCHAR(10) REFERENCES products(id),
    quantity INTEGER DEFAULT 1,
    added_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cart_session ON cart_items(session_id);
```

### Orders Table
```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    total_amount DECIMAL(10,2),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id VARCHAR(10) REFERENCES products(id),
    quantity INTEGER,
    price_at_purchase DECIMAL(10,2)
);
```

---

## PostgreSQL Indexes

```sql
-- HIGH PRIORITY (most common queries)
CREATE INDEX idx_products_embedding ON products 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_price ON products(price_usd);

-- MEDIUM PRIORITY (frequent filters)
CREATE INDEX idx_products_refrigerated ON products(refrigerated);
CREATE INDEX idx_products_sterile ON products(sterile);

-- LOW PRIORITY (common search patterns)
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_products_application ON products(application);
CREATE INDEX idx_products_use_case ON products(use_case);
CREATE INDEX idx_products_product_name ON products(product_name);
```

---

## Neo4j Graph Schema

### Node Types
```cypher
// Product nodes (synced from PostgreSQL)
(:Product {
    id: "LC-0017",
    name: "Refrigerated Benchtop Centrifuge",
    brand: "CellForge",
    price: 2156.43,
    category: "Equipment",
    refrigerated: true,
    sterile: false,
    specifications: "Max 18,000 × g; capacity 12 × 15 mL",
    application: "General laboratory",
    use_case: "Cold sample centrifugation"
})

// Category nodes
(:Category {name: "Equipment"})
(:Category {name: "Chromatography"})
(:Category {name: "Reagents"})
(:Category {name: "Plasticware"})
(:Category {name: "Glassware"})
(:Category {name: "Cell Culture"})
(:Category {name: "Molecular Biology"})

// Application nodes
(:Application {name: "Protein purification"})
(:Application {name: "Cell culture"})
(:Application {name: "General laboratory"})
(:Application {name: "Biochemistry"})
(:Application {name: "Cloning"})
(:Application {name: "Sample preparation"})

// UseCase nodes
(:UseCase {name: "Protein polishing"})
(:UseCase {name: "Buffer exchange"})
(:UseCase {name: "Mammalian cell culture"})
(:UseCase {name: "Bacterial culture"})
(:UseCase {name: "Cold sample centrifugation"})
(:UseCase {name: "His-tag purification"})

// Workflow nodes
(:Workflow {name: "Recombinant protein expression"})
(:Workflow {name: "Recombinant protein purification"})
(:Workflow {name: "Cell harvesting"})
(:Workflow {name: "Buffer preparation"})

// Property nodes
(:Property {name: "sterile", value: true})
(:Property {name: "sterile", value: false})
(:Property {name: "refrigerated", value: true})
(:Property {name: "refrigerated", value: false})
(:Property {name: "endotoxin_free", value: true})
```

### Relationship Types
```cypher
(:Product)-[:BELONGS_TO]->(:Category)
(:Product)-[:HAS_APPLICATION]->(:Application)
(:Product)-[:HAS_USE_CASE]->(:UseCase)
(:Product)-[:HAS_PROPERTY]->(:Property)
(:Product)-[:COMPATIBLE_WITH]->(:Product)
(:Product)-[:ALTERNATIVE_TO]->(:Product)
(:Workflow)-[:REQUIRES]->(:Product)
(:Workflow)-[:USES_APPLICATION]->(:Application)
(:Application)-[:HAS_USE_CASE]->(:UseCase)
```

### Graph Relationship Derivation

1. **Workflow relationships**: Products sharing the same application/use_case are part of the same workflow
   - Example: Ni-IMAC Column + Imidazole both have application="protein purification"
   - → (:Ni-IMAC)-[:PART_OF_WORKFLOW]->(:ProteinPurification)<-[:PART_OF_WORKFLOW]-(:Imidazole)

2. **Compatibility relationships**: Derived from the compatible_with column
   - Example: Product with compatible_with="FPLC/low-pressure systems"
   - → (:Product)-[:COMPATIBLE_WITH]->(:FPLCSystem)

3. **Alternative relationships**: Derived from the alternative_to column
   - Example: Product with alternative_to="Other size exclusion column"
   - → (:Product)-[:ALTERNATIVE_TO]->(:SimilarProduct)

4. **Application relationships**: Products for the same application are connected through Application nodes

---

## Reindex Commands

### Manual REINDEX (after bulk import)
```bash
psql -U aifinder -d aifinder -c "REINDEX INDEX idx_products_embedding;"
```

### Nightly Cron Job (for 100K+ products)
```bash
# crontab -e
0 2 * * * psql -U aifinder -d aifinder -c "REINDEX INDEX idx_products_embedding;"
```

### Python Function
```python
def reindex():
    """Rebuild vector index for optimal performance."""
    db.execute("REINDEX INDEX idx_products_embedding;")
```

---

## Chat History & Context Management

### Requirement
- Remember at least **20 steps back** (20 user messages + 20 bot responses = 40 messages)
- Maintain conversation context across the session
- Persist history (survive page refresh)

### Context Window Strategy
```
┌─────────────────────────────────────────────────────┐
│  Context Window (max 6,000 tokens for Groq free)    │
├─────────────────────────────────────────────────────┤
│  [System Prompt]                  ~500 tokens       │
│  [Tool Definitions]               ~1,000 tokens     │
│  [Last 5 Messages - Full Detail]  ~1,500 tokens    │
│  [Messages 6-20 - Summary]        ~1,000 tokens    │
│  [Current User Message]           ~200 tokens       │
│  [Buffer for Response]            ~1,800 tokens     │
└─────────────────────────────────────────────────────┘
```

### Flow
1. User sends message
2. Save to DB (chat_history table) → Persistent
3. Keep in session_state (memory) → Fast access
4. When LLM needs context:
   - Load last 20 message pairs from DB
   - Check token count
   - If < 6,000 tokens → Send full history
   - If > 6,000 tokens → Summarize older messages
5. LLM generates response
6. Save bot response to DB

---

## Pricing

| Phase | Components | Monthly Cost |
|-------|------------|--------------|
| **POC (Local)** | PostgreSQL Docker + Neo4j Docker + Groq + Local LLM + Local embeddings | **$0** |
| **Cloud** | Streamlit Cloud + Groq free tier | **$0** |
| **Production (10K users)** | Paid tiers | **$25-50** |

---

## API Key Security

### Current Approach (POC)
API keys are stored in `config.yaml` (plain text). This is fine for local POC but NOT for production.

### Production Approach
For production, keys should be encrypted:

1. **Environment Variables** (recommended):
   - Store keys in OS environment variables
   - Never commit to git
   - Use `.env` file locally (add to .gitignore)

2. **Encryption at Rest**:
   - Use `cryptography` library to encrypt config.yaml
   - Store encryption key in environment variable
   - Decrypt on app startup

3. **Secret Management** (production):
   - AWS Secrets Manager
   - HashiCorp Vault
   - Docker Secrets

### Implementation Example

```python
# Encrypt config.yaml
from cryptography.fernet import Fernet

key = Fernet.generate_key()  # Store this securely
cipher = Fernet(key)

with open("config.yaml", "rb") as f:
    encrypted = cipher.encrypt(f.read())

with open("config.yaml.enc", "wb") as f:
    f.write(encrypted)

# Decrypt on startup
with open("config.yaml.enc", "rb") as f:
    decrypted = cipher.decrypt(f.read())
```

### TODO: Implement Before Public Release

- [ ] Move API keys to environment variables
- [ ] Add config.yaml to .gitignore
- [ ] Create config.example.yaml (without secrets)
- [ ] Implement encryption at rest for config.yaml
- [ ] Add secret validation on startup

---

## Tunable Parameters

| Parameter | Location | Default | Effect |
|-----------|----------|---------|--------|
| `similarity_threshold` | `search.py` | 0.7 | How similar products must be (0-1) |
| `max_results` | `search.py` | 10 | Number of results returned |
| `llm_temperature` | `llm.py` | 0.7 | Response creativity (0-1) |
| `embedding_model` | `embeddings.py` | all-MiniLM-L6-v2 | Switch between models |
| `index_lists` | `schema.sql` | 100 | IVFFlat accuracy vs speed |
| `context_window_size` | `llm.py` | 20 | Messages to keep in context |
| `groq_model` | `llm.py` | llama-3.1-8b-instant | Switch Groq model |
| `ollama_model` | `llm.py` | qwen2.5:3b | Switch Ollama model |

---

## Summary

| Phase | Steps | Time |
|-------|-------|------|
| 1. Setup | 6 | 10 min |
| 2. Core Database | 4 | 20 min |
| 3. Data Ingestion & Sync | 2 | 20 min |
| 4. Search & LLM | 3 | 40 min |
| 5. Streamlit App | 5 | 50 min |
| 6. Setup & Docs | 2 | 15 min |
| 7. Testing | 5 | 20 min |
| **Total** | **27** | **~3 hours** |

---

## Fixed Bugs & Changes

### NiceGUI Frontend (nicegui_app.py)

- [x] **Chatbot not answering** — Fixed async handler with `asyncio.to_thread()` instead of `asyncio.run()`
- [x] **Chatbot history lost on page switch** — Moved to PostgreSQL `chat_history` table (replaced JSON file / localStorage)
- [x] **Chatbot thinking animation** — Added "thinking..." label while LLM processes, disabled input during thinking
- [x] **Double submit prevention** — Input and button disabled while bot thinks, re-enabled after response
- [x] **Chat continues if user navigates away** — LLM call continues, response saved to server, UI updates only if page alive
- [x] **Product links 404** — Converted `/Products?product_id=X` to `/products/X` (single format, in config)
- [x] **Product search not working** — Replaced search with pagination (12 products/page, prev/next buttons)
- [x] **Cart buttons not working** — Added `ui.navigate.reload()` after clear/remove operations
- [x] **View/Add buttons different sizes** — Matched height (32px), padding, min-width exactly
- [x] **Button text auto-capitalized** — Added `text-transform: none !important` to override Quasar
- [x] **All buttons lowercase** — "view", "add", "clear", "checkout"
- [x] **Send button blue** — Forced grey with `.q-btn` selector and `!important`
- [x] **Grey lines removed** — `.q-splitter__before, .q-splitter__after { border: none !important; }`
- [x] **Product image too large** — Reduced from 400px to 250px max-width
- [x] **Add button too wide on product page** — Removed `width:100%`
- [x] **Welcome message persistence** — PostgreSQL storage, hidden if history exists
- [x] **Chatbot persistence across pages** — PostgreSQL `chat_history`, loaded on page init
- [x] **Common page template** — `page_template()` function for all pages (header, 65/35 split, chatbot, footer)

### Image Loading

- [x] **SSL certificate error** — Added SSL bypass for Cloudinary HEAD requests
- [x] **Images not loading** — Simplified to return Cloudinary URL directly (no HEAD check)
- [x] **Placeholder fallback** — Cloudinary → local → placeholder logic

### Streamlit Pages

- [x] **`on_error` not supported** — Removed from all `st.image()` calls
- [x] **Floating chat button** — Used `st.components.v1.html` iframe for fixed positioning
- [x] **Sidebar hidden** — CSS to hide hamburger menu and sidebar navigation
- [x] **`ui.query_params` not available** — Used JavaScript redirect for `/Products` route

### Configuration

- [x] **API key in config.yaml** — Moved to environment variable `${GOOGLE_API_KEY}`
- [x] **`.env` file created** — Contains actual keys, gitignored
- [x] **`.env.example` created** — Template without secrets
- [x] **Config env var resolution** — Added `_resolve_env_vars()` to config.py

### Design

- [x] **Background color** — `#D3D3D3` everywhere
- [x] **Text color** — `#555555` everywhere
- [x] **No grey lines** — Removed all borders from nav, splitter, copyright
- [x] **Copyright at bottom** — Fixed position, small font
- [x] **Navigation right-aligned** — Home, Products, Cart links
- [x] **Image rounded corners** — `border-radius: 12px`
- [x] **Chat input styling** — White background, rounded corners, grey border
- [x] **Chatbot on all pages** — Shared template with chatbot sidebar (35%)
- [x] **LLM prompt fixed** — Use `/products/LC-XXXX` format for links

### Deployment

- [x] **Makefile updated** — Added `run-gui` and `run-gui-open` commands
- [x] **Process cleanup** — Makefile kills old processes before starting
- [x] **Favicon** — microscope.png as browser tab icon
- [x] **Static files** — `app.add_static_files()` for images

### Database

- [x] **Friendly error messages** — "I couldn't find a product matching X. Would you try something else?"
- [x] **Session ID consistency** — Fixed session ID across all pages for cart persistence

### Chat Persistence, Scaling & Search (latest)

- [x] **Per-user session isolation** — `get_session_id()` uses `app.storage.user` (server-side cookie) instead of shared constant; verified isolated per browser + consistent across pages
- [x] **Question + "thinking" survive page switch** — User message saved synchronously + cache invalidated immediately, so the new page reads fresh history (no more disappearing/reappearing)
- [x] **Removed duplicate user-save** — `core/llm.py` saves only the assistant response; caller saves the user message
- [x] **Chatbot scroll-to-bottom** — New `scroll_chat_to_bottom()` with reliable `id="chat-msgs"`; scrolls on submit, thinking, response, page open, and pending-request append
- [x] **Pending request appends in place** — Replaced full page reload with append + scroll (case 7)
- [x] **Chat history → PostgreSQL** — Replaced JSON file with `chat_history` table (already existed)
- [x] **In-memory history cache** — `cached_load_history()` + `invalidate_history_cache()` (configurable `history_limit`)
- [x] **DB cleanup algorithm** — Per-session message cap on save, expired-history/cart cleanup on startup + daily timer (`retention_days`)
- [x] **Search improved (Option B + semantic fallback)** — `search_products` extracts volume spec (e.g. `50 mL`) with word-boundary match + falls back to `semantic_search`; fixes "50 mL tubes" returning 0 while "250 mL" no longer false-matches
- [x] **`.gitignore` cleanup** — Added `.nicegui/`, fixed `.env.env` → `.env` typo

---

## Online Hosting for ~$0 with a Free LLM

Host AIFinder online with minimal spend by using free tiers for the app host, database, and LLM.

### What the app actually needs at runtime (verified in code)

| Component | Required? | Notes |
|---|---|---|
| NiceGUI Python app (port 8080) | ✅ | `ui.run(host='0.0.0.0', port=8080)` in `nicegui_app.py:463` |
| PostgreSQL + **pgvector** | ✅ | products, chat history, cart, orders all in DB (`core/database.py`). Schema runs `CREATE EXTENSION IF NOT EXISTS vector` (`data/schema.sql:1`) |
| `sentence-transformers` + `all-MiniLM-L6-v2` | ✅ | Loaded at runtime (`core/embeddings.py`), ~80MB download, needs **≥2GB RAM** |
| LLM provider | ✅ | Code supports `google` (free tier) + `ollama` (local) |
| **Neo4j (graph)** | ✅ **Included** | For the full feature set (workflow/compatibility/alternative recommendations) the deployed app now uses the graph via `core/search.py` + `core/graph.py`. Host with **Neo4j AuraDB Free**. `core/llm.py` was wired to route `get_recommendations` and graph tools through the graph, falling back to SQL if the graph is unreachable. |

> ⚠️ **Important note:** `.env` says `LLM_PROVIDER=groq` with `GROQ_MODEL=...`, but **`core/llm.py` only implements `ollama` and `google`** (`llm.py:96-104`). The real switch is `config.yaml` → `llm.provider`, currently `ollama`. So for online hosting you set it to `google`.

---

### Hosting-platform comparison (to help you choose)

The app is a Python **NiceGUI** service (FastAPI/uvicorn under the hood) on port 8080, plus a **PostgreSQL + pgvector** database. The embedding model needs **≥2 GB RAM**. Evaluate the factors below.

| Platform | App host | RAM | Free tier | Cost for this app | Notes |
|---|---|---|---|---|---|
| **Hugging Face Spaces** | ✅ Docker SDK | **2 vCPU / 16 GB** | **Paid plan required to CREATE a Docker Space** (PRO $9/mo personal) | **~$9/mo** | ⚠️ Verified: Docker/Gradio Spaces need a paid plan; free personal accounts only get 2 Gradio **ZeroGPU** Spaces (not NiceGUI). CPU Basic hardware itself is $0/hr, but creating the Space is gated behind PRO/Team |
| **Google Cloud Run** | ✅ container | configurable (≥2 GB) | Generous free tier (2M requests/mo, scales to zero) | **$0** | Scales to zero, real custom domain; needs GCP account + a small credit card for setup; cold starts |
| **Railway** | ✅ container | configurable | Trial credit (~$5) then pay | ~$5/mo | Simple, one-click Postgres, but paid after trial |
| **Render** | ✅ web service | **512 MB on free** | Yes (web) | **$0 app, but OOM risk** | ⚠️ Free tier too small for `sentence-transformers`/torch; free DB is only a 30-day trial |
| **PythonAnywhere** | ✅ (Not NiceGUI-friendly) | free tier limited | Yes | $0 | ⚠️ Free tier is for WSGI apps / limited; not ideal for NiceGUI + external pgvector |
| **Koyeb** | ✅ container | configurable | Free tier | $0 | Free tier with limits; less turnkey |
| **Fly.io** | ✅ container | configurable | Small free allowance | ~$0–5/mo | Free allowances vary; pay-as-you-go for extras |

**Database hosts (free, pgvector built in or easy to enable):**

| Provider | Free tier | pgvector | Notes |
|---|---|---|---|
| **Neon** | 0.5 GB, serverless | ✅ built in | Great default; connection string with `?sslmode=require` |
| **Supabase** | 500 MB project | ✅ built in | Full Postgres + pgvector; nice dashboard |
| **Aiven** | small free plan | ✅ | Requires card for some plans |
| **Railway Postgres** | paid after trial | ✓ | Simpler if you use Railway for the app too |

**LLM hosts (free):**

| Provider | Model | Free tier | Code support today |
|---|---|---|---|
| **Google AI Studio → Gemini Flash** | `gemini-*-flash` | Generous (hundreds of req/day) | ✅ `provider: google` (**zero code changes**) |
| **Groq** | `llama-3.1-8b-instant` | Free, very fast (~560 t/s) | ❌ `groq` referenced in deps/.env but **not implemented** in `core/llm.py` |
| **Ollama** (hosted on a cheap VPS) | `qwen2.5:3b` | Free, offline, but you pay for the VPS | ✅ `provider: ollama` |

---

### Recommended plan (updated after verification)

> ⚠️ **Correction found while verifying against official docs:** Hugging Face **Docker Spaces are no longer free for personal accounts**. From HF Spaces overview: *"Gradio and Docker Spaces run on compute and require a paid plan to create: PRO for personal accounts, Team or Enterprise for organizations. Free personal accounts in good standing can still host up to 2 Gradio Spaces running on ZeroGPU."* Since AIFinder is a **NiceGUI** app (needs the **Docker** SDK, not Gradio), HF Spaces is **~$9/mo (PRO)**, not free. The true **$0** app host is **Google Cloud Run free tier**.
>
> Other verified facts: **Neon Free** = 100 CU-hrs + 0.5 GB storage per project, scale-to-zero after 5 min, **pgvector included**, no credit card, permanent. **Cloud Run free tier** (request-based) = 180,000 vCPU-seconds + 360,000 GiB-seconds + 2M requests/month, but **billing (a card) must be enabled**.

### Option A — Hugging Face Spaces + Neon + Gemini

**What it is:** Run the NiceGUI app as a HF **Docker Space**; Neon for PostgreSQL; Gemini Flash (free key) for the LLM.

**Verified facts:**
- CPU Basic hardware = 2 vCPU / 16 GB RAM, priced **$0/hr**, but **creating a Docker/Gradio Space requires a paid plan**: HF PRO **$9/mo** (personal) or Team **$20/user/mo**. Free accounts only get 2 Gradio **ZeroGPU** Spaces. *(Source: HF Spaces overview + pricing)*
- Free/CPU-Basic Spaces go to sleep when idle; outbound networking allowed on ports **80/443/8080** only.
- Neon Free: 100 CU-hrs, 0.5 GB, scale-to-zero, **pgvector included**, no card needed.
- Gemini Flash: free via an AI Studio API key (rate limits apply; verify current limits at ai.google.dev).

**Monthly cost (personal account):**

| Item | Cost |
|---|---|
| HF PRO (required to host a Docker Space) | $9/mo |
| Neon Free | $0 |
| Gemini Flash free tier | $0 |
| **Total** | **≈ $9/mo** |

**Step-by-step:**
1. Create a **Neon** project and copy the connection string (add `?sslmode=require`).
2. Load schema + data into Neon from your machine (which has the embedding model — skip Neo4j):
   ```bash
   export DATABASE_URL="postgresql://...?sslmode=require"
   psql "$DATABASE_URL" -f data/schema.sql
   python data/ingest.py
   ```
3. On HF, create a **Space** with SDK = **Docker** and `app_port: 8080` (requires PRO on a personal account). Add a `README.md` front-matter:
   ```yaml
   sdk: docker
   app_port: 8080
   ```
4. Add a `Dockerfile` that installs deps and runs `python3 nicegui_app.py`.
5. In **Settings → Secrets**, add `DATABASE_URL` and `GOOGLE_API_KEY` (and a `STORAGE_SECRET`). Set `config.yaml` → `llm.provider: google` and `database.url` to the Neon URL.
6. Push to the Space repo (`git push`) → auto-build and run at `https://<your-user>-<space>.hf.space`.

**Caveats:** not free for personal accounts (~$9/mo); sleeps when idle; custom domain requires paid; no persistent disk (data lives in Neon, so fine).

---

### Option B — Cloud Run (free tier) + Neon (Postgres) + AuraDB (Neo4j) + Gemini

**What it is:** Run the NiceGUI app in a container on **Cloud Run**, scale-to-zero; **Neon** for PostgreSQL/pgvector; **Neo4j AuraDB Free** for the graph; Gemini Flash for the LLM. **All features included** (SQL + semantic + graph-backed recommendations/workflow/compatibility), not just SQL.

**Verified facts:**
- Free tier (request-based): **180,000 vCPU-seconds + 360,000 GiB-seconds + 2M requests/month** (us-central1). *(Source: Cloud Run pricing)*
- Requires a Google Cloud project with **billing enabled** (a credit card) even to use the free tier; new accounts get $300 credit.
- Memory is configurable — set **~2 GiB** (the embedding model needs it). Scales to zero (no charge when idle); public `*.run.app` URL + custom domain support.
- Neon Free (0.5 GB, pgvector, scale-to-zero) + **Neo4j AuraDB Free** ($0, managed graph) as above.
- ⚠️ **WebSocket gotcha:** NiceGUI keeps a **WebSocket per open tab**. On Cloud Run request-based billing a held-open WebSocket counts the instance as "active" and bills vCPU+RAM for the whole time it is open. Roughly, one instance at 1 vCPU / 2 GiB open for ~50 hrs/month ≈ the free vCPU tier. Fine for a short demo / few users; heavy "always-on" idle tabs can exceed the free tier.

**Monthly cost:**

| Item | Cost |
|---|---|
| Cloud Run (within free tier) | $0 |
| Neon Free | $0 |
| **Neo4j AuraDB Free** | $0 |
| Gemini Flash free tier | $0 |
| **Total** | **≈ $0/mo** (card on file) |

**Detailed plan (step-by-step):**

**Prerequisites (one-time)**
- Docker Desktop installed (required, not optional).
- Google Cloud account with a project and **billing enabled** (card required even for the free tier; new accounts get $300 credit).
- `gcloud` CLI installed (`brew install google-cloud-sdk` or install from googlecloudsdk), then `gcloud auth login`.
- Python 3.10+ on your machine.
- Neon account + project (free, pgvector built in).
- **Neo4j AuraDB account + instance (Free tier)** → copy the Bolt URI + credentials.
- Google AI Studio API key (free, for Gemini Flash).

**Step 1 — Create the Neon database**
1. Go to https://neon.com → create a project (free tier).
2. In the SQL editor, run `CREATE EXTENSION IF NOT EXISTS vector;`.
3. Copy the connection string, e.g. `postgresql://user:pass@ep-xxx.aws.neon.tech/aifinder?sslmode=require`.

**Step 2 — Create the Neo4j AuraDB instance**
1. Go to https://console.neo4j.io → create a **Free** AuraDB instance.
2. Copy the **Bolt URI** (`neo4j+s://xxxx.databases.neo4j.io`), **user**, and **password**.

**Step 3 — Load schema + product data into Neon** (from your machine, which has the embedding model)
```bash
export DATABASE_URL="postgresql://user:pass@ep-xxx.aws.neon.tech/aifinder?sslmode=require"
psql "$DATABASE_URL" -f data/schema.sql          # creates tables
python data/ingest.py                            # generates embeddings, inserts products, builds pgvector indexes
```

**Step 4 — Build the Neo4j graph** (from your machine, pointing at AuraDB)
```bash
export NEO4J_URI="neo4j+s://xxxx.databases.neo4j.io"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"
make sync-graph        # = python core/sync.py  (Product nodes + BELONGS_TO/HAS_APPLICATION/HAS_USE_CASE/WORKFLOW/HAS_PROPERTY/ALTERNATIVE_TO)
```
> To rebuild clean later: `make clean-sync-graph` (= wipes `MATCH (n) DETACH DELETE n` then re-syncs via `scripts/rebuild_graph.py`).

**Step 5 — Get the Gemini API key**
1. Go to https://aistudio.google.com/apikey → create a free key.
2. Keep it secret; never commit it.

**Step 6 — Point config at Neon + AuraDB + Google** (`config.yaml`)
```yaml
database:
  url: postgresql://user:pass@ep-xxx.aws.neon.tech/aifinder?sslmode=require

llm:
  provider: google
  temperature: 0.7
  max_tokens: 2048
  system_prompt: | ...
```
The Google key is read from env via `${GOOGLE_API_KEY}` (`config.yaml` → `google.api_key`). `core/database.py` and `core/graph.py` now prefer the env vars `DATABASE_URL` / `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` (falling back to `config.yaml`) — so you don't have to edit config for each environment. Add a `storage_secret`:
```yaml
chat:
  storage_secret: aifinder_super_secret_key
```
Set local `.env` (gitignored):
```
DATABASE_URL=postgresql://user:pass@ep-xxx.aws.neon.tech/aifinder?sslmode=require
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
GOOGLE_API_KEY=your_key_here
```

**Step 7 — Small code change** (`nicegui_app.py:463`): Cloud Run injects `$PORT`; make the app honor it.
```python
import os  # already imported at top
ui.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), title='AIFinder',
       reload=False, favicon=FAVICON,
       storage_secret=get("chat", "storage_secret") or "aifinder_secret_key")
```

**Step 8 — Create `requirements.txt`** (created in repo; full project deps)
```
nicegui, markdown, requests, python-dotenv, psycopg2-binary, pgvector,
sentence-transformers, pandas, streamlit, streamlit-cookies-manager,
neo4j, groq
```
> The NiceGUI container needs `nicegui, requests, markdown, python-dotenv, psycopg2-binary, pgvector, sentence-transformers, pandas, neo4j` (the last is required because `core/llm.py` → `core/search.py` → `core/graph.py` imports the Neo4j driver). `streamlit` and `groq` are for legacy/optional paths. The `Dockerfile` installs this file.
> Note: `config.py` was updated to call `load_dotenv()`, and `core/database.py` / `core/graph.py` now prefer env vars (`DATABASE_URL`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`) over `config.yaml`, so they work both locally and on Cloud Run without editing config per environment.

**Step 9 — Create `Dockerfile`**
```dockerfile
FROM python:3.11-slim
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user . .
ENV HF_HOME=/home/user/.cache/huggingface \
    HF_HUB_ENABLE_HF_TRANSFER=0
EXPOSE 8080
CMD ["python3", "nicegui_app.py"]
```
> Optional hardening: pre-download the embedding model at build time so cold starts don't re-fetch `all-MiniLM-L6-v2` (add a `RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"` and pass `HF_TOKEN` as a build secret). Note this enlarges the image (~1-2 GB). Always set a user id 1000 (HF/container contract guidance).

**Step 8 — Create `.dockerignore`** (exclude secrets, git, data, caches)
```
.env
.git
.gitignore
*.csv
.nicegui/
__pycache__/
*.pyc
data/testdata/
docker-compose.yml
Makefile
roadmap.md
README.md
tests/
scripts/
```

**Step 10 — Build & test locally (REQUIRED before deploying)**
```bash
docker build -t aifinder .
docker run --rm -p 8080:8080 \
  -e PORT=8080 \
  -e DATABASE_URL='postgresql://user:pass@ep-xxx.aws.neon.tech/aifinder?sslmode=require' \
  -e NEO4J_URI='neo4j+s://xxxx.databases.neo4j.io' \
  -e NEO4J_USER='neo4j' \
  -e NEO4J_PASSWORD='your_password' \
  -e GOOGLE_API_KEY='your_key_here' \
  -e STORAGE_SECRET='aifinder_super_secret_key' \
  aifinder
open http://localhost:8080
```
Verify: page loads, chat responds via Gemini, product catalog loads, **graph-backed recommendations/workflow/compatibility answers work**, add-to-cart works. Then stop the container (`Ctrl-C`). If it fails, fix before pushing — this is the mandatory local test gate.

**Step 11 — Build & push to Cloud Run, then deploy**
```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT/aifinder
gcloud run deploy aifinder \
  --image gcr.io/YOUR_PROJECT/aifinder \
  --region us-central1 \
  --cpu 1 --memory 2Gi \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars DATABASE_URL='postgresql://user:pass@ep-xxx.aws.neon.tech/aifinder?sslmode=require',NEO4J_URI='neo4j+s://xxxx.databases.neo4j.io',NEO4J_USER='neo4j',NEO4J_PASSWORD='your_password',GOOGLE_API_KEY='your_key_here',STORAGE_SECRET='aifinder_super_secret_key'
```

**Step 12 — Verify live + optional domain**
1. Open the returned `https://aifinder-XXXX-uc.a.run.app`.
2. Re-test chat + catalog + cart + graph recommendations on the live URL.
3. Optional: map a custom domain under Cloud Run → "Custom domains".

**Costs at scale (context):** Cloud Run free tier = 180,000 vCPU-sec + 360,000 GiB-sec + 2M requests/mo. Within this, $0. Card on file only (no active charges for light use).

**Caveats:** Docker Desktop required for the local test gate; Google Cloud billing account/card required even for the free tier; WebSocket billing caveat (open idle tabs count as active time); cold starts (embedding model reloads on first request); small code change for `$PORT`; the Neo4j graph must be re-synced after data changes (`make sync-graph` / `make clean-sync-graph`).

---

### Which to choose

- **Cheapest with ALL features:** **Option B** (Cloud Run + Neon + AuraDB + Gemini) — needs a GCP account + card.
- **Quick demo without a card / already on HF PRO:** **Option A** (~$9/mo) — but note Option A also needs a Neo4j store (AuraDB Free) + `core/sync.py` to keep the graph.
- **Avoid for the app host:** Render free (512 MB RAM → OOM with `sentence-transformers`) and PythonAnywhere (NiceGUI + external pgvector not a good fit).

### Updated cost estimate

| Option | App | DB | Graph | LLM | Total |
|---|---|---|---|---|---|
| **A**: HF Spaces + Neon + AuraDB + Gemini (personal) | $9/mo (PRO) | $0 | $0 | $0 | **≈ $9/mo** |
| **B**: Cloud Run + Neon + AuraDB + Gemini | $0 (free tier) | $0 | $0 | $0 | **≈ $0/mo** (card on file) |
| Railway/Render (paid) + Neon + AuraDB | ~$5/mo | $0 | $0 | $0 | ~$5/mo |
| Production (paid, per README) | — | — | — | — | $25–50/mo |

---

### Gotchas (updated)

- **HF Docker Spaces are paid-only now** (verified). Free HF = only 2 Gradio **ZeroGPU** Spaces, which cannot host NiceGUI.
- **Cloud Run needs a billing account/card** even to use the free tier.
- **NiceGUI WebSockets on Cloud Run** can exceed the free tier if users leave tabs open — cap max instances / keep sessions short for a demo.
- `nicegui_app.py:463` reads `PORT` from env now (default 8080).
- **Neo4j AuraDB Free** pauses after inactivity and has limited capacity; **re-sync the graph** (`make clean-sync-graph`) after data updates. If the graph is unreachable, `get_recommendations` falls back to SQL automatically.
- Free-tier limits change often — re-verify Neon / AuraDB / Cloud Run / Gemini limits at deploy time.

---

### Neo4j AuraDB Free: auto-pause and keep-warm options (decide here)

**The problem:** AuraDB Free **auto-pauses after 72 hours of inactivity** (no writes/changes). Data is preserved, but it does **not** auto-resume — you must resume it manually from the console. If left paused **> 30 days it is deleted and all data lost**. Our deployed chatbot only **reads** the graph, so it will **not** keep the instance warm on its own. (If the graph is down, `get_recommendations` already falls back to SQL, so the chat keeps working.)

**Resume manually (when needed):** https://console.neo4j.io → paused instance → **⋯ → Resume** → wait for **Running**.

Choose one of the options below to avoid the pause.

| Option | Mechanism | Cost | Reliability | Effort |
|---|---|---|---|---|
| **1A. GitHub Actions cron** | daily write via neo4j driver | free | good (disabled after 60 days repo inactivity) | low |
| **1B. GCP Cloud Scheduler + Cloud Run Job** | daily write job | free (3 Scheduler jobs/mo) | best, all-GCP | medium |
| **1C. External cron → app endpoint** | HTTP ping triggers a write | free | ok | medium |
| **2. Aura API auto-resume** | resume after pause | free only if API access available (usually paid) | depends | medium |
| **3. Avoid pause entirely** | self-host Neo4j (VPS) or paid Aura | ~$5/mo VPS or $65/GB/mo Aura | best | medium |

#### Option 1A — GitHub Actions scheduled write (simplest)
Keep-warm query (resets the 72h timer):
```cypher
MERGE (k:KeepAlive {id: 1}) SET k.at = datetime()
```
1. Create `scripts/neo4j_keepalive.py`:
   ```python
   """Tiny write to Neo4j so AuraDB Free does not auto-pause after 72h."""
   import os, sys
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   from core.graph import execute_query

   def main():
       print("Neo4j keepalive OK:", execute_query(
           "MERGE (k:KeepAlive {id: 1}) SET k.at = datetime() RETURN k.at AS at"))

   if __name__ == "__main__":
       main()
   ```
2. Create `.github/workflows/neo4j-keepalive.yml`:
   ```yaml
   name: Neo4j Keepalive
   on:
     schedule:
       - cron: "0 6 * * *"   # daily 06:00 UTC
     workflow_dispatch:
   jobs:
     keepalive:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: "3.11"
         - run: pip install neo4j python-dotenv pyyaml
         - name: Write to Neo4j
           env:
             NEO4J_URI: ${{ secrets.NEO4J_URI }}
             NEO4J_USER: ${{ secrets.NEO4J_USER }}
             NEO4J_PASSWORD: ${{ secrets.NEO4J_PASSWORD }}
           run: python scripts/neo4j_keepalive.py
   ```
3. Add repo **Secrets** `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` (Settings → Secrets and variables → Actions).
4. Test: Actions → **Neo4j Keepalive** → **Run workflow**.

> Caveats: runs only on the default branch, cron may be delayed, and GitHub disables scheduled workflows after ~60 days of repo inactivity.

#### Option 1B — GCP Cloud Scheduler → Cloud Run Job (all-GCP, most reliable)
```bash
# 1) Create a job that runs the keepalive script using the app image
gcloud run jobs create neo4j-keepalive \
  --image gcr.io/YOUR_PROJECT/aifinder \
  --command python --args scripts/neo4j_keepalive.py \
  --region us-central1 \
  --set-env-vars NEO4J_URI='neo4j+s://...',NEO4J_USER='neo4j',NEO4J_PASSWORD='...'

# 2) Trigger it daily
gcloud scheduler jobs create http neo4j-keepalive-daily \
  --schedule "0 6 * * *" --time-zone "UTC" \
  --uri "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/YOUR_PROJECT/jobs/neo4j-keepalive:run" \
  --http-method POST \
  --oauth-service-account-email YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com

# 3) Test
gcloud run jobs execute neo4j-keepalive --region us-central1
```

#### Option 1C — External free cron → app endpoint
Add a protected `/api/keepalive` route in `nicegui_app.py` that runs the same `MERGE` write (guard with a secret token), then point **cron-job.org** / **UptimeRobot** at it daily. More moving parts than 1A/1B.

#### Option 2 — Auto-resume via the Aura REST API
Aura has a REST API that can resume an instance:
```
POST https://api.neo4j.io/v1beta5/instances/{instance_id}/resume   (OAuth 2.0)
```
Check **Aura console → Account/Integrations** for API credentials. These generally require a **paid tier**; on Free you usually can't automate the resume, so use option 1.

#### Option 3 — Avoid the pause entirely
- **Self-host Neo4j** in Docker on a small VPS (part of "Option C", ~$5/mo): no pause policy, you manage it.
- **Upgrade AuraDB** to Professional/Business Critical: no pause, but ~$65+/GB/mo.

**Recommendation:** for a free demo, **Option 1A** (simplest) or **1B** (most reliable). Keep SQL fallback enabled so the chat is unaffected when the graph pauses.

---

## Secret Management & Rotation

> Verified against Google Cloud Run "Configure secrets for services" and GitHub "Security hardening for GitHub Actions" docs. **Status: planned / to implement — test locally on Docker first.**

### Principles
- **Never** store secrets in tracked files (code, `config.yaml`, workflow YAML).
- One **source of truth per environment**, injected at runtime — not baked into the image.
- **Least privilege** (service accounts/roles scoped to what's needed).
- Prefer **short-lived credentials** (OIDC) over long-lived keys.
- **Rotate** periodically and immediately on exposure.

### Secret inventory
| Secret | Used by | Currently (bad) | Target store |
|---|---|---|---|
| `GOOGLE_API_KEY` | app LLM | `.env` + **git history** | Secret Manager (runtime), Actions secret (CI) |
| `DATABASE_URL` (Neon pw) | app | `.env` | Secret Manager |
| `NEO4J_URI/USER/PASSWORD` | app + keepalive | `.env` | Secret Manager / Actions secret |
| `STORAGE_SECRET` | NiceGUI sessions | unset | Secret Manager |
| `CLOUDINARY_API_KEY/SECRET` | upload scripts | **`config.yaml` (tracked!)** + `.env` | Secret Manager + env |
| `CLOUDINARY_CLOUD_NAME` | scripts etc. | `config.yaml` | not secret — env optional |

### Storage per environment

**a) Local dev → `.env` (gitignored).** Already wired (`config.py` calls `load_dotenv()`). Keep `.env.example` with placeholders only.

**b) Runtime on Cloud Run → GCP Secret Manager (Google's recommendation).**
```bash
gcloud services enable secretmanager.googleapis.com
printf '%s' "VALUE" | gcloud secrets create GOOGLE_API_KEY --data-file=-
# grant the Cloud Run runtime service account access
gcloud secrets add-iam-policy-binding GOOGLE_API_KEY \
  --member="serviceAccount:YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
# reference without plaintext
gcloud run deploy aifinder --image ... \
  --set-secrets GOOGLE_API_KEY=GOOGLE_API_KEY:latest,DATABASE_URL=DATABASE_URL:latest,NEO4J_PASSWORD=NEO4J_PASSWORD:latest,STORAGE_SECRET=STORAGE_SECRET:latest
```
> Env-var secrets are resolved at instance start → **pin a version** (e.g. `:3`) for deterministic rollouts, or **mount as a volume** to always fetch latest (better for rotation). Never use plain `--set-env-vars` for secrets in production (values visible in console).

**c) CI / automation on GitHub Actions → GitHub Actions Secrets.**
- `Settings → Secrets and variables → Actions` (repo or **Environment** secrets; environments can require reviewers).
- Reference `${{ secrets.NAME }}`; values never in the YAML; masked in logs.
- Harden: `permissions: contents: read` for `GITHUB_TOKEN`; pin third-party actions to a commit SHA; `::add-mask::` derived values.
- For deploy jobs prefer **OIDC → GCP Workload Identity Federation** (keyless) over a long-lived service-account key.

**d) Build time.** Dockerfile must not embed secrets (it doesn't — env is passed at runtime). If ever needed at build, use BuildKit `--mount=type=secret`, never `ARG`/`ENV`.

### Repo-side enforcement
- Move Cloudinary creds out of `config.yaml` → `${CLOUDINARY_API_KEY}` / `${CLOUDINARY_API_SECRET}` (`config.py` already resolves `${…}`).
- Keep `.env` in `.gitignore` (done); never stage it.
- Add a secret scanner: **gitleaks** pre-commit, or GitHub's built-in **secret scanning + push protection** (free on public repos — blocks commits containing secrets).
- Optional: fail-fast validation at startup for required secrets in production.

### Rotation
1. **Now (exposed):** revoke/rotate Gemini, Groq, Cloudinary.
2. Update new values in: local `.env`, GitHub Actions secrets, Secret Manager.
3. Re-deploy Cloud Run (new revision picks up the new secret version).
4. Schedule periodic rotation (e.g., quarterly).

### Incident response for what already leaked
- **Revoke/rotate first** (a public copy can't be un-seen).
- Remove from history: `git filter-repo --path .env --invert-paths` + force-push; strip secrets from `config.yaml` history if needed.
- Delete logs that printed a secret.
- Enable **secret scanning + push protection** to prevent recurrence.

### Is this the best approach? (comparison)
| Approach | Verdict for this stack |
|---|---|
| **`.env` (local) + Actions Secrets (CI) + Secret Manager (Cloud Run)** | ✅ **Recommended** — matches Google + GitHub guidance; nothing in the repo |
| Plain `--set-env-vars` only | ⚠️ Works; values visible in console; weaker than Secret Manager |
| Committing encrypted secrets (SOPS/age) | Viable; adds key-mgmt overhead; unnecessary here |
| Vault / AWS Secrets Manager | Overkill for a free demo |
| Hardcoding / committing | ❌ Never |

### Implementation checklist
- [ ] Rotate Gemini, Groq, Cloudinary keys
- [ ] `config.yaml`: Cloudinary → env vars; `.env.example` placeholders
- [ ] Create Secret Manager secrets + grant `secretmanager.secretAccessor`
- [ ] Deploy with `--set-secrets`
- [ ] Add GitHub Actions secrets (and OIDC for deploy if automating)
- [ ] Enable GitHub secret scanning + push protection
- [ ] (Optional) `git filter-repo` history purge
- [ ] (Optional) gitleaks pre-commit

### Test locally on Docker (before deploying)
Pass secrets at runtime (the image excludes `.env`). Simplest is to point at the **real** Neon/AuraDB/Gemini so the local test mirrors prod:
```bash
docker build -t aifinder .
docker run --rm -p 8080:8080 --env-file .env \
  -e DATABASE_URL='postgresql://...?sslmode=require' \
  -e NEO4J_URI='neo4j+s://...' -e NEO4J_USER='neo4j' -e NEO4J_PASSWORD='...' \
  -e GOOGLE_API_KEY='...' -e STORAGE_SECRET='...' \
  aifinder
open http://localhost:8080
```
- To test against **local** Postgres/Neo4j (docker-compose) instead, remember that inside the container `localhost` is the container itself — use `host.docker.internal:5432` / `:7687` (Docker Desktop) or put the app on the same compose network.
- Verify: chat answers via Gemini, catalog loads, cart works, and graph recommendations work.

---

## Smarter Helper Improvements (PLANNED — NOT IMPLEMENTED)

Goal: evolve AIFinder from a search-returning chatbot into a genuinely smart assistant.

**Priority legend**
- **P0 — Correctness (BUGS):** the app currently produces wrong answers (hallucinated products/links, non-DB data). Must fix before recommending any provider switch.
- **P1 — Make it smarter:** grounding infrastructure + better retrieval/graph/memory.
- **P2 — Enhancements:** nice-to-have features.

> **Context / why P0 exists:** the DB is only reachable through tools, and tools run **only if the model emits a tool call**. If the model answers with plain text, `core/llm.py:_process_response:228-229` returns that text verbatim — no query, no validation. This is model-dependent: Ollama's `qwen2.5:3b` called tools (looked correct); Gemini Flash answered directly → invented `LC-0002` ("MolecuLab Sterile Pipette") and echoed the system-prompt example (CellForge/ApexBio). Both bugs share this root cause.

---

### P0 — Correctness (BUGS)

> **Status: ✅ IMPLEMENTED** — `core/llm.py` (agent loop, `sanitize_links`, forced retrieval), `config.yaml` (`system_prompt` grounding rules + `max_tool_steps`), test: `tests/test_all.py::test_grounding`.

#### P0.1 — Force retrieval; never answer product questions from the model alone ✅
- **Problem:** `get_llm_response` → `_process_response` (`core/llm.py:219`): if `tool_calls` is empty (`:228`) it returns `content` (`:229`) with no DB access.
- **Fix:**
  - Always run a retrieval step for product intents: detect "no tool call" and **retry with tools forced**, or run a fallback query server-side.
  - Gemini: set `toolConfig.functionCallingConfig.mode = "ANY"` (or `"REQUIRED"`) for product queries in `_call_google` (`core/llm.py:152`). (Optionally add a no-op `answer_directly` tool + `ANY` so chit-chat still works.)
  - If still no products found → say so; **do not** let the model invent.
- **Files:** `core/llm.py` (`_call_google`, `get_llm_response`).
- **Test:** a product query must produce ≥1 tool call; assert `tool_calls` non-empty.

#### P0.2 — Ground & validate links/IDs/prices server-side ✅
- **Problem:** raw model text can contain `/products/LC-XXXX` that don't exist (seen: `LC-0002`).
- **Fix:**
  - After the final text is produced, scan for `/products/([A-Za-z0-9-]+)`, look each up (`core/database.get_product`); **drop/replace** unknown IDs.
  - Best: **don't let the model write links at all** — inject links from tool results server-side.
  - Validate any mentioned prices/specs against the DB (flag/strip mismatches).
- **Files:** `core/llm.py` → new `_sanitize_links(text, allowed_ids)` applied before returning/saving.
- **Test:** feed a reply containing `LC-0002` for a pipette query → link removed/replaced; a reply with a valid ID keeps it.

#### P0.3 — Remove the copyable example answer from the system prompt ✅
- **Problem:** `config.yaml` system prompt (~lines 130-142) contains a **full example answer** with real products/prices/links. The model parrots it (proven: reply matched it exactly, including the stale brand for `LC-0011`).
- **Fix:**
  - Replace the concrete example with a **format skeleton** using placeholders (no real names/prices/IDs), or drop it.
  - Add explicit rules: *"Never invent product names, IDs, prices, or links. Only mention products returned by tools. If you did not call a tool, call one before answering."*
- **Files:** `config.yaml` (`llm.system_prompt`).
- **Test:** golden reply must not contain the old example products unless returned by tools.

#### P0.4 — Reason over tool results (multi-step, LLM-composed answers) ✅
- **Problem:** `_process_response` returns `_format_tool_results` (`core/llm.py:241`) — the model never sees tool output, so grounding and natural phrasing can't coexist.
- **Fix (from the unified LLM plan):** after tools run, append the assistant tool-call turn + tool-result messages and **call the model again** so it composes the answer from **real data**; keep `_format_tool_results` only as a fallback. Add a `max_tool_steps` guard.
- **Files:** `core/llm.py` (agent loop; provider adapters if the pluggable refactor lands).
- **Test:** mock a tool-call turn then a final turn; assert final text is model-composed and all links came from DB results.

#### P0 — acceptance criteria
- Product questions always hit the DB (tool call observed).
- **Every** `/products/LC-XXXX` link in any reply exists in the DB; unknown IDs never reach the user.
- No reply contains product names/prices/links not present in tool results.
- Works identically on **ollama and google**.

---

### Preventing fake / hallucinated data (detailed measures)

1. **Retrieval-or-refuse:** no DB-backed products → no product claims ("I couldn't find any…" instead).
2. **Links generated/validated server-side** (P0.2) — model never authors links.
3. **Prices/specs injected from tool results**, not written by the model.
4. **Tool-arg validation:** reject unknown `product_id` in `add_to_cart`, `find_alternatives`, etc.; return an error to the model to self-correct.
5. **Prompt rules:** explicit "never invent IDs/prices/links; only use tool-returned products; if unsure, ask or call a tool."
6. **No copyable few-shot data:** keep examples as placeholders/skeletons (P0.3).
7. **Output post-validation:** scan final text for product IDs/prices; strip or regenerate on mismatch; log every violation.
8. **Groundedness tests/eval:** golden set asserting (a) every link exists, (b) every mentioned price/spec matches the DB, (c) product queries always call a tool.
9. **Observability:** log tool-call rate per query, and a "hallucination flag" when validation strips something.
10. **Prefer structured output:** have the model return product IDs only, then render names/prices/links server-side from the DB.

---

### P1 — Make it smarter

> **Status: ✅ IMPLEMENTED** — graph edges (`core/sync.py` + rebuild), hybrid retrieval/`find_by_spec`/query understanding (`core/database.py`), user profile (`core/llm.py`), kit/cart tools (`core/tools.py`). Test: `tests/test_all.py::test_p1`.

#### P1.1 — Finish and actually use the graph ✅
- `core/sync.py` creates `BELONGS_TO`, `HAS_APPLICATION`, `HAS_USE_CASE`, `HAS_PROPERTY`, `ALTERNATIVE_TO`, `Workflow-USES_APPLICATION` — but **never builds `COMPATIBLE_WITH`** and **never links `Workflow-REQUIRES-Product`**, though `core/graph.py:find_products_in_workflow` queries `:REQUIRES`. Build the missing edges; parse free-text `compatible_with`/`requires`; expose the graph tools; add multi-hop reasoning; keep `data/graph_schema.cypher` in sync.

#### P1.2 — Upgrade retrieval ✅
- **Hybrid search** (SQL + pgvector + graph) via **Reciprocal Rank Fusion** instead of the cascade in `core/database.py:search_products`.
- **Rerank** top-N with a cross-encoder.
- **Query understanding:** rewrite/expand, synonyms, normalize units; extract structured filters (RCF, capacity, sterile).
- Add a **`find_by_spec`** tool.

#### P1.3 — Memory & personalization ✅
- Persist a **user profile** (budget, lab type, recurring applications, preferred brands) keyed by `session_id`; use it in recommendations; summarize older turns into durable facts.

#### P1.4 — Agentic "kit builder" + cart intelligence ✅
- `build_kit(application/use_case, budget)` → graph traversal + compatibility → coherent cart with quantities + budget total.
- `check_cart_compatibility`, `suggest_missing_items(cart)`, `estimate_quote(cart)`.

---

### P2 — Enhancements

#### P2.1 — RAG over documents (datasheets, manuals, FAQs)
- Ingest PDFs → chunk → embed into Postgres/pgvector; answer spec/how-to questions with citations.

#### P2.2 — Better data & ontology
- Normalize/structured-ize free-text columns; add a small equipment ontology (categories, properties, units); clean duplicates; add verification/confidence.

#### P2.3 — UX that makes it feel smart
- "Why this product" explanations; side-by-side comparison view; proactive suggestion chips; saved searches / shareable links; streaming responses.

#### P2.4 — Evaluation, feedback, observability
- Thumbs up/down per answer; golden eval set (extend `tests/test_all.py`); tracing (Langfuse/OpenTelemetry); retrieval metrics (recall@k).

#### P2.5 — Performance & cost
- Cache embeddings and LLM responses; route (cheap model for lookups, stronger for planning); pre-warm the embedding model.

---

### Suggested sequence
1. **P0.1–P0.4** — grounding + forced retrieval + validated links + reason over tool results (kills both bugs)
2. **P1.1** — finish graph edges + expose graph tools
3. **P1.2** — hybrid retrieval + reranking
4. **P1.3–P1.4** — memory + kit builder
5. **P2** — RAG, data/ontology, UX, evals, perf

### Quick wins (small, high value)
- P0.2 link validation (stops wrong links immediately)
- P0.3 strip the example from the system prompt (stops parroting)
- Finish missing `COMPATIBLE_WITH` / `REQUIRES` edges
- Expose `resolve_product_name` as a clarifying tool
- Add `find_by_spec`

---

## Future Refactoring Ideas (NOT IMPLEMENTED — DON'T DO NOW)

> These ideas are recorded for later. The current single-file approach works and preserves all custom UI styles. Splitting risks breaking imports, CSS selectors, and session logic. Only do when the app grows or multiple devs work on it.

### Refactor: Split nicegui_app.py into modules

Current single file (~350 lines) mixes layout, pages, chat, and API. Proposed structure:

```
nicegui_app.py          # entry: ui.run(), API routes
frontend/
  __init__.py
  template.py           # page_template(), header, footer, CSS
  chatbot.py            # chat logic, send_msg, history load/render
  pages.py              # home, products, cart, product_detail content fns
```

**Benefits:** easier to read, isolated chatbot logic, design changes in one place, smaller diffs.

**Costs:** more files, complex import paths, risk of breaking the tightly-coupled CSS.

**Prerequisites before attempting:**
- [ ] Move shared constants (BG, TEXT, ACCENT) to a common module
- [ ] Extract `page_template()` into `frontend/template.py`
- [ ] Extract chat logic (`send_msg`, history) into `frontend/chatbot.py`
- [ ] Extract page content functions into `frontend/pages.py`
- [ ] Verify ALL CSS selectors still apply after split
- [ ] Verify session/cart persistence still works


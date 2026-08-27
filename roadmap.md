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
aifinder/
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
│   └── test_data.csv               # 500 products (LC-0001 to LC-0500)
├── images/                         # Product images folder
├── requirements.txt                # Python dependencies
├── .env.example                    # API keys template
├── docker-compose.yml              # PostgreSQL + Neo4j containers
├── setup.sh                        # One-click setup script
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

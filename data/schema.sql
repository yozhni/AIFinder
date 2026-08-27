CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE products (
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
    discount DECIMAL(5,2),
    is_deleted BOOLEAN DEFAULT FALSE,
    embedding vector(384),
    image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chat_session ON chat_history(session_id, created_at DESC);

CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    product_id VARCHAR(10) REFERENCES products(id),
    quantity INTEGER DEFAULT 1,
    added_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cart_session ON cart_items(session_id);

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

CREATE INDEX idx_products_embedding ON products
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_price ON products(price_usd);
CREATE INDEX idx_products_refrigerated ON products(refrigerated);
CREATE INDEX idx_products_sterile ON products(sterile);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_products_application ON products(application);
CREATE INDEX idx_products_use_case ON products(use_case);
CREATE INDEX idx_products_product_name ON products(product_name);

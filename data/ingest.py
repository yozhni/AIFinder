"""Data ingestion: CSV -> PostgreSQL with embeddings."""

import os
import sys
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get
from core.database import get_connection, execute_query
from core.embeddings import generate_embedding, build_embedding_text
from pgvector.psycopg2 import register_vector

# Load config
CSV_COLS = get("csv_columns")
EMBEDDING_FIELDS = get("embedding_fields")
EMBEDDING_DIM = get("embeddings", "dim")


def safe_str(val):
    """Convert to safe string."""
    if pd.isna(val):
        return ""
    return str(val).strip()


def clean_price(price_str):
    """Convert price string like '$1,620.24' to float."""
    if not price_str or pd.isna(price_str):
        return 0.0
    price_str = str(price_str).replace("$", "").replace(",", "").strip()
    try:
        return float(price_str)
    except ValueError:
        return 0.0


def clean_boolean(val):
    """Convert Yes/No/True/False to boolean."""
    if isinstance(val, bool):
        return val
    if pd.isna(val) or val == "":
        return False
    return str(val).strip().lower() in ("yes", "true", "1")


def clean_integer(val):
    """Convert to integer or return None."""
    if pd.isna(val) or val == "":
        return None
    try:
        return int(float(str(val).strip()))
    except ValueError:
        return None


def clean_decimal(val):
    """Convert to float or return None."""
    if pd.isna(val) or val == "":
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except ValueError:
        return None


def load_csv(csv_path):
    """Load CSV file into DataFrame."""
    print(f"Loading CSV: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8")
    print(f"  Loaded {len(df)} rows")
    return df


def insert_products(df):
    """Insert products into PostgreSQL with embeddings."""
    conn = get_connection()
    register_vector(conn)

    try:
        with conn.cursor() as cur:
            inserted = 0
            errors = 0

            for idx, row in df.iterrows():
                try:
                    product_id = row.get(CSV_COLS["product_id"], f"GEN-{idx:04d}")

                    # Build embedding text from config fields
                    product_data = {}
                    for field in EMBEDDING_FIELDS:
                        csv_col = CSV_COLS.get(field, field)
                        product_data[field] = row.get(csv_col, "")

                    # Generate embedding
                    embedding_text = build_embedding_text(product_data)
                    if not embedding_text.strip():
                        embedding = [0.0] * EMBEDDING_DIM
                    else:
                        embedding = generate_embedding(embedding_text)

                    # Parse typed fields
                    price = clean_price(row.get(CSV_COLS["price_usd"], 0))
                    refrigerated = clean_boolean(row.get(CSV_COLS["refrigerated"], False))
                    sterile = clean_boolean(row.get(CSV_COLS["sterile"], False))
                    endotoxin_free = clean_boolean(row.get(CSV_COLS["endotoxin_free"], False))
                    max_rcf = clean_integer(row.get(CSV_COLS["max_rcf_xg"]))
                    discount = clean_decimal(row.get(CSV_COLS["discount"]))

                    # Helper to get field value via config
                    def get_val(field):
                        csv_col = CSV_COLS.get(field, field)
                        return safe_str(row.get(csv_col))

                    cur.execute("""
                        INSERT INTO products (
                            id, category, product_name, brand, model_sku, specifications,
                            volume_or_capacity, max_rcf_xg, refrigerated, sterile, endotoxin_free,
                            application, use_case, compatible_with, used_for, requires,
                            alternative_to, limitations_notes, typical_user_question,
                            price_usd, verification_status, data_provenance, source_reference,
                            url, discount, is_deleted, embedding, image_url
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            category = EXCLUDED.category,
                            product_name = EXCLUDED.product_name,
                            brand = EXCLUDED.brand,
                            model_sku = EXCLUDED.model_sku,
                            specifications = EXCLUDED.specifications,
                            volume_or_capacity = EXCLUDED.volume_or_capacity,
                            max_rcf_xg = EXCLUDED.max_rcf_xg,
                            refrigerated = EXCLUDED.refrigerated,
                            sterile = EXCLUDED.sterile,
                            endotoxin_free = EXCLUDED.endotoxin_free,
                            application = EXCLUDED.application,
                            use_case = EXCLUDED.use_case,
                            compatible_with = EXCLUDED.compatible_with,
                            used_for = EXCLUDED.used_for,
                            requires = EXCLUDED.requires,
                            alternative_to = EXCLUDED.alternative_to,
                            limitations_notes = EXCLUDED.limitations_notes,
                            typical_user_question = EXCLUDED.typical_user_question,
                            price_usd = EXCLUDED.price_usd,
                            verification_status = EXCLUDED.verification_status,
                            data_provenance = EXCLUDED.data_provenance,
                            source_reference = EXCLUDED.source_reference,
                            url = EXCLUDED.url,
                            discount = EXCLUDED.discount,
                            embedding = EXCLUDED.embedding,
                            updated_at = NOW()
                    """, (
                        product_id,
                        get_val("category"),
                        get_val("product_name"),
                        get_val("brand"),
                        get_val("model_sku"),
                        get_val("specifications"),
                        get_val("volume_or_capacity"),
                        max_rcf, refrigerated, sterile, endotoxin_free,
                        get_val("application"),
                        get_val("use_case"),
                        get_val("compatible_with"),
                        get_val("used_for"),
                        get_val("requires"),
                        get_val("alternative_to"),
                        get_val("limitations_notes"),
                        get_val("typical_user_question"),
                        price,
                        get_val("verification_status"),
                        get_val("data_provenance"),
                        get_val("source_reference"),
                        get_val("url"),
                        discount, False, embedding, "",
                    ))

                    inserted += 1
                    if inserted % 100 == 0:
                        print(f"  Inserted {inserted} products...")
                        conn.commit()

                except Exception as e:
                    errors += 1
                    print(f"  Error inserting row {idx}: {e}")
                    conn.rollback()
                    continue

            conn.commit()
            print(f"\nDone: {inserted} products inserted/updated, {errors} errors")
            return inserted

    finally:
        conn.close()


def create_indexes():
    """Recreate indexes after bulk insert."""
    print("Rebuilding indexes...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("DROP INDEX IF EXISTS idx_products_embedding")
                cur.execute("""
                    CREATE INDEX idx_products_embedding ON products
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """)
            except Exception as e:
                print(f"  IVFFlat index warning: {e}")

            for idx_name, col in [
                ("idx_products_category", "category"),
                ("idx_products_price", "price_usd"),
                ("idx_products_refrigerated", "refrigerated"),
                ("idx_products_sterile", "sterile"),
                ("idx_products_brand", "brand"),
                ("idx_products_application", "application"),
                ("idx_products_use_case", "use_case"),
                ("idx_products_product_name", "product_name"),
            ]:
                try:
                    cur.execute(f"DROP INDEX IF EXISTS {idx_name}")
                    cur.execute(f"CREATE INDEX {idx_name} ON products({col})")
                except Exception as e:
                    print(f"  Index {idx_name} warning: {e}")

        conn.commit()
        print("  Indexes rebuilt")
    finally:
        conn.close()


def verify():
    """Verify ingestion."""
    count = execute_query("SELECT COUNT(*) as count FROM products")
    print(f"\nVerification: {count[0]['count']} products in database")


def main():
    """Main ingestion pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description="Ingest product data into PostgreSQL")
    parser.add_argument("--file", default=get("data", "source"), help="CSV file path")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    df = load_csv(args.file)
    inserted = insert_products(df)
    if inserted > 0:
        create_indexes()
    verify()
    print("\nIngestion complete!")


if __name__ == "__main__":
    main()

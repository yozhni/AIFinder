"""PostgreSQL database connection and operations."""

import os
import json
from datetime import datetime
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from pgvector.psycopg2 import register_vector

from config import get

DATABASE_URL = get("database", "url")

# Chat history cleanup config
HISTORY_LIMIT = get("chat", "history_limit") or 50
RETENTION_DAYS = get("chat", "retention_days") or 30


def get_connection():
    """Get PostgreSQL connection."""
    conn = psycopg2.connect(DATABASE_URL)
    register_vector(conn)
    return conn


def execute_query(query, params=None, fetch=True):
    """Execute a query and return results."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch and cur.description:
                return cur.fetchall()
            conn.commit()
            return None
    finally:
        conn.close()


# ============================================
# PRODUCT OPERATIONS
# ============================================

def get_product(product_id):
    """Get a single product by ID."""
    result = execute_query(
        "SELECT * FROM products WHERE id = %s AND is_deleted = FALSE",
        (product_id,)
    )
    return dict(result[0]) if result else None


import re
from core.embeddings import generate_embedding


def _extract_volume_spec(query):
    """Extract a measurable volume spec like '50 mL', '1.5 mL', '1 L' from query text."""
    if not query:
        return None
    m = re.search(r'\b(\d+(?:\.\d+)?)\s*(mL|ml|ML|µL|uL|L)\b', query)
    if not m:
        return None
    num = m.group(1)
    unit = m.group(2)
    # Normalize to 'N mL' / 'N L' form as stored in volume_or_capacity
    return f"{num} {unit}"


def search_products(query=None, category=None, brand=None, min_price=None,
                    max_price=None, refrigerated=None, sterile=None, limit=10):
    """Search products with SQL filters (keyword) + capacity spec match + semantic fallback."""
    conditions = ["is_deleted = FALSE"]
    params = []

    if query:
        conditions.append("(product_name ILIKE %s OR application ILIKE %s OR use_case ILIKE %s OR specifications ILIKE %s)")
        q = f"%{query}%"
        params.extend([q, q, q, q])

    if category:
        conditions.append("category = %s")
        params.append(category)

    if brand:
        conditions.append("brand ILIKE %s")
        params.append(f"%{brand}%")

    if min_price is not None:
        conditions.append("price_usd >= %s")
        params.append(min_price)

    if max_price is not None:
        conditions.append("price_usd <= %s")
        params.append(max_price)

    if refrigerated is not None:
        conditions.append("refrigerated = %s")
        params.append(refrigerated)

    if sterile is not None:
        conditions.append("sterile = %s")
        params.append(sterile)

    where_clause = " AND ".join(conditions)
    query_str = f"SELECT * FROM products WHERE {where_clause} ORDER BY price_usd LIMIT %s"
    params.append(limit)

    results = execute_query(query_str, tuple(params))
    products = [dict(r) for r in results] if results else []

    # Step 2: if keyword search found nothing, filter by extracted volume spec
    # (e.g. "50 mL tubes" -> capacity contains "50 mL")
    if not products and query:
        spec = _extract_volume_spec(query)
        if spec:
            spec_conditions = ["is_deleted = FALSE"]
            spec_params = []
            if category:
                spec_conditions.append("category = %s")
                spec_params.append(category)
            if brand:
                spec_conditions.append("brand ILIKE %s")
                spec_params.append(f"%{brand}%")
            if refrigerated is not None:
                spec_conditions.append("refrigerated = %s")
                spec_params.append(refrigerated)
            if sterile is not None:
                spec_conditions.append("sterile = %s")
                spec_params.append(sterile)
            # word-boundary match in volume_or_capacity to avoid '250 mL' matching '50 mL'
            spec_conditions.append(
                "(volume_or_capacity ~* %s OR specifications ~* %s)")
            # Require the number to be a standalone token (not part of '250')
            like_spec = r'(?<![0-9])' + re.escape(spec).replace(r'\ ', r'\s+')
            spec_params.extend([like_spec, like_spec])
            spec_where = " AND ".join(spec_conditions)
            spec_query = (f"SELECT * FROM products WHERE {spec_where} "
                          f"ORDER BY price_usd LIMIT %s")
            spec_params.append(limit)
            spec_results = execute_query(spec_query, tuple(spec_params))
            products = [dict(r) for r in spec_results] if spec_results else []

    # Step 3: semantic fallback if still nothing
    if not products and query:
        try:
            embedding = generate_embedding(query)
            products = semantic_search(query_embedding=embedding, limit=limit)
        except Exception:
            products = []

    return products


def get_product_by_name(product_name, brand=None):
    """Find products by name (exact or partial match)."""
    if brand:
        results = execute_query(
            "SELECT * FROM products WHERE product_name ILIKE %s AND brand ILIKE %s AND is_deleted = FALSE",
            (f"%{product_name}%", f"%{brand}%")
        )
    else:
        results = execute_query(
            "SELECT * FROM products WHERE product_name ILIKE %s AND is_deleted = FALSE",
            (f"%{product_name}%",)
        )
    return [dict(r) for r in results] if results else []


def compare_products(product_name_1, product_name_2, brand_1=None, brand_2=None):
    """Compare two products side by side."""
    results_1 = get_product_by_name(product_name_1, brand_1)
    results_2 = get_product_by_name(product_name_2, brand_2)

    if not results_1:
        return {"error": f"I couldn't find a product matching '{product_name_1}'. Would you try something else?"}
    if not results_2:
        return {"error": f"I couldn't find a product matching '{product_name_2}'. Would you try something else?"}

    return {
        "product_1": results_1[0],
        "product_2": results_2[0],
        "multiple_matches_1": len(results_1) > 1,
        "multiple_matches_2": len(results_2) > 1,
        "all_matches_1": results_1,
        "all_matches_2": results_2,
    }


def get_recommendations(product_id=None, use_case=None, limit=5):
    """Get product recommendations."""
    if product_id:
        product = get_product(product_id)
        if not product:
            return []
        results = execute_query(
            "SELECT * FROM products WHERE category = %s AND id != %s AND is_deleted = FALSE ORDER BY price_usd LIMIT %s",
            (product["category"], product_id, limit)
        )
    elif use_case:
        results = execute_query(
            "SELECT * FROM products WHERE use_case ILIKE %s AND is_deleted = FALSE ORDER BY price_usd LIMIT %s",
            (f"%{use_case}%", limit)
        )
    else:
        results = execute_query(
            "SELECT * FROM products WHERE is_deleted = FALSE ORDER BY price_usd LIMIT %s",
            (limit,)
        )
    return [dict(r) for r in results] if results else []


def add_product(data):
    """Insert a new product."""
    query = """
        INSERT INTO products (id, category, product_name, brand, model_sku, specifications,
            volume_or_capacity, max_rcf_xg, refrigerated, sterile, endotoxin_free,
            application, use_case, compatible_with, used_for, requires, alternative_to,
            limitations_notes, typical_user_question, price_usd, verification_status,
            data_provenance, source_reference, url, discount, is_deleted, embedding, image_url)
        VALUES (%(id)s, %(category)s, %(product_name)s, %(brand)s, %(model_sku)s, %(specifications)s,
            %(volume_or_capacity)s, %(max_rcf_xg)s, %(refrigerated)s, %(sterile)s, %(endotoxin_free)s,
            %(application)s, %(use_case)s, %(compatible_with)s, %(used_for)s, %(requires)s, %(alternative_to)s,
            %(limitations_notes)s, %(typical_user_question)s, %(price_usd)s, %(verification_status)s,
            %(data_provenance)s, %(source_reference)s, %(url)s, %(discount)s, %(is_deleted)s, %(embedding)s, %(image_url)s)
    """
    execute_query(query, data, fetch=False)


def update_product(product_id, data):
    """Update a product."""
    set_clauses = []
    params = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        params.append(value)
    set_clauses.append("updated_at = NOW()")
    params.append(product_id)

    query = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = %s"
    execute_query(query, tuple(params), fetch=False)


def delete_product(product_id):
    """Soft delete a product."""
    execute_query(
        "UPDATE products SET is_deleted = TRUE, updated_at = NOW() WHERE id = %s",
        (product_id,),
        fetch=False
    )


def get_categories():
    """Get all unique categories."""
    results = execute_query(
        "SELECT DISTINCT category FROM products WHERE is_deleted = FALSE ORDER BY category"
    )
    return [r["category"] for r in results] if results else []


def get_brands():
    """Get all unique brands."""
    results = execute_query(
        "SELECT DISTINCT brand FROM products WHERE is_deleted = FALSE ORDER BY brand"
    )
    return [r["brand"] for r in results] if results else []


def get_price_range():
    """Get min and max price."""
    result = execute_query(
        "SELECT MIN(price_usd) as min_price, MAX(price_usd) as max_price FROM products WHERE is_deleted = FALSE"
    )
    if result and result[0]["min_price"] is not None:
        return {"min": float(result[0]["min_price"]), "max": float(result[0]["max_price"])}
    return {"min": 0, "max": 10000}


def get_total_products():
    """Get total product count."""
    result = execute_query("SELECT COUNT(*) as count FROM products WHERE is_deleted = FALSE")
    return result[0]["count"] if result else 0


# ============================================
# SEMANTIC SEARCH
# ============================================

def semantic_search(query_embedding, limit=10):
    """Vector similarity search."""
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    results = execute_query(
        """SELECT *, 1 - (embedding <=> %s::vector) as similarity
           FROM products
           WHERE is_deleted = FALSE AND embedding IS NOT NULL
           ORDER BY embedding <=> %s::vector
           LIMIT %s""",
        (embedding_str, embedding_str, limit)
    )
    return [dict(r) for r in results] if results else []


# ============================================
# CHAT HISTORY
# ============================================

def save_message(session_id, role, content, tool_calls=None):
    """Save a message to chat history, then cap per-session history."""
    tool_calls_json = Json(tool_calls) if tool_calls else None
    execute_query(
        """INSERT INTO chat_history (session_id, role, content, tool_calls)
           VALUES (%s, %s, %s, %s)""",
        (session_id, role, content, tool_calls_json),
        fetch=False
    )
    # Cap: keep only the last HISTORY_LIMIT messages per session
    execute_query(
        """DELETE FROM chat_history
           WHERE id IN (
               SELECT id FROM chat_history
               WHERE session_id = %s
               ORDER BY created_at DESC
               OFFSET %s)""",
        (session_id, HISTORY_LIMIT),
        fetch=False
    )


def cleanup_expired_chat_history():
    """Delete chat history and abandoned carts inactive for RETENTION_DAYS."""
    # Expire old chat history (by last-message time)
    execute_query(
        "DELETE FROM chat_history WHERE created_at < NOW() - make_interval(days => %s)",
        (RETENTION_DAYS,),
        fetch=False
    )
    # Expire abandoned carts (by last-add time)
    execute_query(
        "DELETE FROM cart_items WHERE added_at < NOW() - make_interval(days => %s)",
        (RETENTION_DAYS,),
        fetch=False
    )


def load_history(session_id, limit=20):
    """Load last N message pairs from chat history."""
    results = execute_query(
        """SELECT role, content, tool_calls, created_at
           FROM chat_history
           WHERE session_id = %s
           ORDER BY created_at DESC
           LIMIT %s""",
        (session_id, limit * 2)
    )
    if results:
        messages = [dict(r) for r in results]
        messages.reverse()
        return messages
    return []


def clear_history(session_id):
    """Clear chat history for a session."""
    execute_query(
        "DELETE FROM chat_history WHERE session_id = %s",
        (session_id,),
        fetch=False
    )


# ============================================
# CART OPERATIONS
# ============================================

def add_to_cart(session_id, product_id, quantity=1):
    """Add a product to the cart."""
    existing = execute_query(
        "SELECT id, quantity FROM cart_items WHERE session_id = %s AND product_id = %s",
        (session_id, product_id)
    )
    if existing:
        new_qty = existing[0]["quantity"] + quantity
        execute_query(
            "UPDATE cart_items SET quantity = %s WHERE id = %s",
            (new_qty, existing[0]["id"]),
            fetch=False
        )
    else:
        execute_query(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (%s, %s, %s)",
            (session_id, product_id, quantity),
            fetch=False
        )


def get_cart(session_id):
    """Get cart contents."""
    results = execute_query(
        """SELECT ci.id, ci.product_id, ci.quantity, ci.added_at,
                  p.product_name, p.brand, p.price_usd, p.image_url
           FROM cart_items ci
           JOIN products p ON ci.product_id = p.id
           WHERE ci.session_id = %s
           ORDER BY ci.added_at""",
        (session_id,)
    )
    return [dict(r) for r in results] if results else []


def update_cart_item(cart_item_id, quantity):
    """Update cart item quantity."""
    if quantity <= 0:
        execute_query("DELETE FROM cart_items WHERE id = %s", (cart_item_id,), fetch=False)
    else:
        execute_query(
            "UPDATE cart_items SET quantity = %s WHERE id = %s",
            (quantity, cart_item_id),
            fetch=False
        )


def remove_from_cart(cart_item_id):
    """Remove item from cart."""
    execute_query("DELETE FROM cart_items WHERE id = %s", (cart_item_id,), fetch=False)


def clear_cart(session_id):
    """Clear entire cart."""
    execute_query("DELETE FROM cart_items WHERE session_id = %s", (session_id,), fetch=False)


def get_cart_total(session_id):
    """Get cart total."""
    result = execute_query(
        """SELECT SUM(p.price_usd * ci.quantity) as total
           FROM cart_items ci
           JOIN products p ON ci.product_id = p.id
           WHERE ci.session_id = %s""",
        (session_id,)
    )
    if result and result[0]["total"]:
        return float(result[0]["total"])
    return 0.0


# ============================================
# ORDER OPERATIONS
# ============================================

def create_order(session_id):
    """Create an order from cart items."""
    cart = get_cart(session_id)
    if not cart:
        return None

    total = get_cart_total(session_id)

    result = execute_query(
        """INSERT INTO orders (session_id, total_amount, status)
           VALUES (%s, %s, 'pending')
           RETURNING id""",
        (session_id, total)
    )
    order_id = result[0]["id"]

    for item in cart:
        execute_query(
            """INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase)
               VALUES (%s, %s, %s, %s)""",
            (order_id, item["product_id"], item["quantity"], item["price_usd"]),
            fetch=False
        )

    clear_cart(session_id)
    return order_id


def get_orders(session_id):
    """Get order history."""
    results = execute_query(
        """SELECT o.id, o.total_amount, o.status, o.created_at,
                  json_agg(json_build_object(
                      'product_id', oi.product_id,
                      'quantity', oi.quantity,
                      'price', oi.price_at_purchase
                  )) as items
           FROM orders o
           JOIN order_items oi ON o.id = oi.order_id
           WHERE o.session_id = %s
           GROUP BY o.id
           ORDER BY o.created_at DESC""",
        (session_id,)
    )
    return [dict(r) for r in results] if results else []


def get_order(order_id):
    """Get a single order with items."""
    result = execute_query(
        "SELECT * FROM orders WHERE id = %s",
        (order_id,)
    )
    if not result:
        return None

    order = dict(result[0])
    items = execute_query(
        "SELECT * FROM order_items WHERE order_id = %s",
        (order_id,)
    )
    order["items"] = [dict(i) for i in items] if items else []
    return order

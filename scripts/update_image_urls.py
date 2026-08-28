"""Update product image_url in database from local images directory."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get
import psycopg2
from psycopg2.extras import RealDictCursor

IMAGES_DIR = Path(__file__).parent.parent / "images"


def get_db_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(get("database", "url"))


def get_all_products():
    """Get all products from database."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, product_name, image_url
                FROM products
                WHERE is_deleted = FALSE
                ORDER BY id
            """)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_product_image(product_id, image_url):
    """Update product image_url in database."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE products
                SET image_url = %s, updated_at = NOW()
                WHERE id = %s
            """, (image_url, product_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"  DB error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def main():
    print("=" * 60)
    print("AIFinder - Update Product Image URLs")
    print("=" * 60)

    if not IMAGES_DIR.exists():
        print(f"\nImages directory not found: {IMAGES_DIR}")
        return

    webp_files = list(IMAGES_DIR.glob("*.webp"))
    print(f"\nFound {len(webp_files)} WebP images in {IMAGES_DIR}")

    products = get_all_products()
    print(f"Found {len(products)} products in database")

    updated = 0
    skipped = 0
    not_found = 0

    for product in products:
        product_id = product["id"]
        image_path = IMAGES_DIR / f"{product_id}.webp"

        if image_path.exists():
            image_url = f"/images/{product_id}.webp"

            if product.get("image_url") == image_url:
                skipped += 1
                continue

            if update_product_image(product_id, image_url):
                print(f"  Updated: {product['product_name']} -> {image_url}")
                updated += 1
            else:
                not_found += 1
        else:
            not_found += 1

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Updated: {updated}")
    print(f"Skipped (already set): {skipped}")
    print(f"No image found: {not_found}")
    print(f"Total: {updated + skipped + not_found}")


if __name__ == "__main__":
    main()

"""Upload local images to Cloudinary and update database."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cloudinary
import cloudinary.uploader
from config import get
import psycopg2
from psycopg2.extras import RealDictCursor

IMAGES_DIR = Path(__file__).parent.parent / "images"

# Configure Cloudinary
cloudinary.config(
    cloud_name=get("cloudinary", "cloud_name"),
    api_key=get("cloudinary", "api_key"),
    api_secret=get("cloudinary", "api_secret")
)


def get_db_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(get("database", "url"))


def get_products_with_local_images():
    """Get products that have local image paths."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, product_name, image_url
                FROM products
                WHERE is_deleted = FALSE AND image_url LIKE '/images/%'
                ORDER BY id
            """)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_product_image_url(product_id, new_url):
    """Update product image_url in database."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE products
                SET image_url = %s, updated_at = NOW()
                WHERE id = %s
            """, (new_url, product_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"  DB error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def upload_to_cloudinary(local_path, product_id):
    """Upload image to Cloudinary."""
    try:
        result = cloudinary.uploader.upload(
            str(local_path),
            public_id=f"aifinder/products/{product_id}",
            folder="aifinder/products",
            transformation=[
                {"width": 300, "height": 300, "crop": "limit"},
                {"quality": "auto"}
            ]
        )
        return result.get("secure_url")
    except Exception as e:
        print(f"  Upload error: {e}")
        return None


def main():
    print("=" * 60)
    print("AIFinder - Upload Images to Cloudinary")
    print("=" * 60)

    products = get_products_with_local_images()
    print(f"\nFound {len(products)} products with local images")

    uploaded = 0
    failed = 0
    skipped = 0

    for i, product in enumerate(products, 1):
        product_id = product["id"]
        local_path = IMAGES_DIR / f"{product_id}.webp"

        print(f"\n[{i}/{len(products)}] {product['product_name']}")

        if not local_path.exists():
            print(f"  -> skipped (file not found)")
            skipped += 1
            continue

        cloud_url = upload_to_cloudinary(local_path, product_id)

        if cloud_url:
            if update_product_image_url(product_id, cloud_url):
                print(f"  -> uploaded: {cloud_url}")
                uploaded += 1
            else:
                print(f"  -> failed (DB update)")
                failed += 1
        else:
            print(f"  -> failed (upload)")
            failed += 1

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Uploaded: {uploaded}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print(f"Total: {uploaded + failed + skipped}")


if __name__ == "__main__":
    main()

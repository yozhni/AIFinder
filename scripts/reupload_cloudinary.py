"""Delete old Cloudinary images and re-upload with clean paths."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cloudinary
import cloudinary.api
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

BASE_URL = get("cloudinary", "base_url")
IMAGE_EXT = get("cloudinary", "image_ext")


def get_db_connection():
    return psycopg2.connect(get("database", "url"))


def delete_old_images():
    """Delete all images in aifinder/products folder."""
    print("Deleting old images from Cloudinary...")
    try:
        result = cloudinary.api.resources(type="upload", prefix="aifinder/products/", max_results=500)
        resources = result.get("resources", [])
        print(f"Found {len(resources)} images to delete")

        for r in resources:
            public_id = r["public_id"]
            cloudinary.uploader.destroy(public_id)
            print(f"  Deleted: {public_id}")

        return len(resources)
    except Exception as e:
        print(f"Delete error: {e}")
        return 0


def upload_image(local_path, product_id):
    """Upload image with clean path: aifinder/products/{product_id}.webp"""
    public_id = f"aifinder/products/{product_id}"
    try:
        result = cloudinary.uploader.upload(
            str(local_path),
            public_id=public_id,
            format="webp"
        )
        return result.get("secure_url")
    except Exception as e:
        print(f"  Upload error: {e}")
        return None


def generate_url(product_id):
    """Generate URL from config: base_url/product_id.ext"""
    return f"{BASE_URL}/{product_id}{IMAGE_EXT}"


def update_database(product_id, image_url):
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
    print("AIFinder - Re-upload Images (Clean Path)")
    print("=" * 60)

    # Step 1: Delete old images
    deleted = delete_old_images()
    print(f"\nDeleted {deleted} old images")

    # Step 2: Get all products
    conn = get_db_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, product_name FROM products WHERE is_deleted = FALSE ORDER BY id")
        products = [dict(r) for r in cur.fetchall()]
    conn.close()

    print(f"\nUploading {len(products)} images with clean path...")

    uploaded = 0
    failed = 0

    for i, product in enumerate(products, 1):
        product_id = product["id"]
        local_path = IMAGES_DIR / f"{product_id}.webp"

        print(f"[{i}/{len(products)}] {product['product_name']}", end=" ")

        if not local_path.exists():
            print("NO FILE")
            failed += 1
            continue

        cloud_url = upload_image(local_path, product_id)

        if cloud_url:
            # Generate clean URL from config
            clean_url = generate_url(product_id)
            if update_database(product_id, clean_url):
                print(f"OK")
                uploaded += 1
            else:
                print("DB FAIL")
                failed += 1
        else:
            print("UPLOAD FAIL")
            failed += 1

        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Uploaded: {uploaded}")
    print(f"Failed: {failed}")
    print(f"Total: {uploaded + failed}")


if __name__ == "__main__":
    main()

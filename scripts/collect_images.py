"""Collect product images using Pexels API (free, commercial use)."""

import os
import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get
import psycopg2
from psycopg2.extras import RealDictCursor

IMAGES_DIR = Path(__file__).parent.parent / "images"
IMAGES_DIR.mkdir(exist_ok=True)

PEXELS_API_KEY = "dzLYStfjYCGUElmPvrGAp4AiLboC5NV5LRdfbTfOy68XTnezrp4QTNjP"
HEADERS = {"Authorization": PEXELS_API_KEY}
DELAY = 1


def get_db_connection():
    return psycopg2.connect(get("database", "url"))


def get_all_products():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, product_name, brand, category
                FROM products
                WHERE is_deleted = FALSE
                ORDER BY id
            """)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def search_pexels(query, count=5):
    """Search Pexels for images."""
    url = "https://api.pexels.com/v1/search"
    params = {"query": query, "per_page": count}

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            photos = data.get("photos", [])
            return [p["src"]["medium"] for p in photos]
    except Exception as e:
        print(f"  Pexels error: {e}")
    return []


def download_image(url, save_path):
    """Download image and save as WebP."""
    try:
        resp = requests.get(url, timeout=15, stream=True)
        if resp.status_code == 200:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(resp.content))
            img = img.convert("RGB")
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            img.save(save_path, "WEBP", quality=80)
            return True
    except Exception as e:
        print(f"  Download error: {e}")
    return False


def collect_image_for_product(product):
    """Try to collect image for a single product."""
    product_id = product["id"]
    product_name = product["product_name"]
    brand = product["brand"]
    save_path = IMAGES_DIR / f"{product_id}.webp"

    if save_path.exists():
        return "skipped"

    queries = [
        f"{product_name} lab equipment",
    ]

    for query in queries:
        urls = search_pexels(query, count=5)

        if urls:
            idx = 0
            if download_image(urls[idx], save_path):
                return "downloaded"

        time.sleep(0.5)

    return "failed"


def main():
    print("=" * 60)
    print("AIFinder - Product Image Collector (Pexels)")
    print("=" * 60)

    products = get_all_products()
    print(f"\nFound {len(products)} products in database")

    stats = {"downloaded": 0, "skipped": 0, "failed": 0}

    for i, product in enumerate(products, 1):
        print(f"\n[{i}/{len(products)}] {product['product_name']} ({product['brand']})")

        result = collect_image_for_product(product)
        stats[result] += 1
        print(f"  -> {result}")

        time.sleep(DELAY)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Downloaded: {stats['downloaded']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Failed: {stats['failed']}")
    print(f"Total: {sum(stats.values())}")


if __name__ == "__main__":
    main()

"""Test Wikimedia Commons image search for first 10 products."""

import os
import sys
import time
import requests
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get
import psycopg2
from psycopg2.extras import RealDictCursor

IMAGES_DIR = Path(__file__).parent.parent / "images"
IMAGES_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "AIFinder/1.0 (Lab Equipment Search; educational project)"
}


def get_db_connection():
    return psycopg2.connect(get("database", "url"))


def get_first_products(limit=10):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, product_name, brand, category
                FROM products
                WHERE is_deleted = FALSE
                ORDER BY id
                LIMIT %s
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def search_wikimedia(query):
    """Search Wikimedia Commons API for images."""
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srnamespace": "6",
        "srsearch": query,
        "srlimit": 5,
        "format": "json"
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("query", {}).get("search", [])
            titles = [r["title"] for r in results]
            return titles
    except Exception as e:
        print(f"  Search error: {e}")
    return []


def get_image_url(title):
    """Get direct image URL from Wikimedia title."""
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": 300,
        "format": "json"
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                imageinfo = page.get("imageinfo", [])
                if imageinfo:
                    return imageinfo[0].get("thumburl") or imageinfo[0].get("url")
    except Exception as e:
        print(f"  URL fetch error: {e}")
    return None


def download_image(url, save_path):
    """Download image and save as WebP."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, stream=True)
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


def main():
    print("=" * 60)
    print("Test: Wikimedia Commons for first 10 products")
    print("=" * 60)

    products = get_first_products(10)

    for i, product in enumerate(products, 1):
        product_id = product["id"]
        product_name = product["product_name"]
        brand = product["brand"]
        save_path = IMAGES_DIR / f"{product_id}.webp"

        print(f"\n[{i}] {product_name} ({brand})")

        queries = [
            f"{product_name}",
            f"{product_name} {brand}",
            f"{product_name} laboratory"
        ]

        found = False
        for query in queries:
            print(f"  Search: {query}")
            titles = search_wikimedia(query)

            for title in titles:
                img_url = get_image_url(title)
                if img_url:
                    print(f"  Found: {title} -> {img_url[:80]}...")
                    if download_image(img_url, save_path):
                        print(f"  -> Downloaded!")
                        found = True
                        break

            if found:
                break
            time.sleep(0.5)

        if not found:
            print(f"  -> No image found")

    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    for f in sorted(IMAGES_DIR.glob("*.webp")):
        size = f.stat().st_size
        print(f"  {f.name} ({size:,} bytes)")


if __name__ == "__main__":
    main()

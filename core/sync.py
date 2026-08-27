"""Sync data from PostgreSQL to Neo4j."""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_connection
from core.graph import get_driver, get_graph_stats

load_dotenv()


def sync_products():
    """Sync all products from PostgreSQL to Neo4j."""
    print("Syncing products from PostgreSQL to Neo4j...")

    # Get all products from PostgreSQL
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, product_name, brand, price_usd, category,
                       specifications, application, use_case,
                       refrigerated, sterile, endotoxin_free, volume_or_capacity
                FROM products
                WHERE is_deleted = FALSE
            """)
            products = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
    finally:
        conn.close()

    print(f"  Found {len(products)} products in PostgreSQL")

    # Sync to Neo4j
    driver = get_driver()
    try:
        with driver.session() as session:
            for i, product in enumerate(products):
                product_dict = dict(zip(columns, product))

                session.run("""
                    MERGE (p:Product {id: $id})
                    SET p.name = $name,
                        p.brand = $brand,
                        p.price = $price,
                        p.category = $category,
                        p.specifications = $specifications,
                        p.application = $application,
                        p.use_case = $use_case,
                        p.refrigerated = $refrigerated,
                        p.sterile = $sterile,
                        p.endotoxin_free = $endotoxin_free,
                        p.volume_or_capacity = $volume_or_capacity
                """, {
                    "id": product_dict["id"],
                    "name": product_dict["product_name"],
                    "brand": product_dict["brand"],
                    "price": float(product_dict["price_usd"]) if product_dict["price_usd"] else 0.0,
                    "category": product_dict["category"],
                    "specifications": product_dict["specifications"],
                    "application": product_dict["application"],
                    "use_case": product_dict["use_case"],
                    "refrigerated": product_dict["refrigerated"],
                    "sterile": product_dict["sterile"],
                    "endotoxin_free": product_dict["endotoxin_free"],
                    "volume_or_capacity": product_dict["volume_or_capacity"],
                })

                if (i + 1) % 100 == 0:
                    print(f"  Synced {i + 1}/{len(products)} products...")

            print(f"  Synced {len(products)} products to Neo4j")
    finally:
        driver.close()


def create_relationships():
    """Create all graph relationships from product properties."""
    print("Creating graph relationships...")

    driver = get_driver()
    try:
        with driver.session() as session:
            # Create Category nodes
            session.run("""
                MATCH (p:Product)
                WHERE p.category IS NOT NULL
                MERGE (c:Category {name: p.category})
                MERGE (p)-[:BELONGS_TO]->(c)
            """)
            print("  Created BELONGS_TO relationships")

            # Create Application nodes
            session.run("""
                MATCH (p:Product)
                WHERE p.application IS NOT NULL
                MERGE (a:Application {name: p.application})
                MERGE (p)-[:HAS_APPLICATION]->(a)
            """)
            print("  Created HAS_APPLICATION relationships")

            # Create UseCase nodes
            session.run("""
                MATCH (p:Product)
                WHERE p.use_case IS NOT NULL
                MERGE (u:UseCase {name: p.use_case})
                MERGE (p)-[:HAS_USE_CASE]->(u)
            """)
            print("  Created HAS_USE_CASE relationships")

            # Create Workflow nodes
            session.run("""
                MATCH (p:Product)
                WHERE p.application IS NOT NULL
                MERGE (w:Workflow {name: p.application + ' workflow'})
                MERGE (w)-[:USES_APPLICATION]->(a:Application {name: p.application})
            """)
            print("  Created Workflow nodes")

            # Create Property nodes
            session.run("""
                MATCH (p:Product)
                WHERE p.sterile = true
                MERGE (ps:Property {name: 'sterile', value: true})
                MERGE (p)-[:HAS_PROPERTY]->(ps)
            """)
            session.run("""
                MATCH (p:Product)
                WHERE p.sterile = false
                MERGE (pn:Property {name: 'sterile', value: false})
                MERGE (p)-[:HAS_PROPERTY]->(pn)
            """)
            session.run("""
                MATCH (p:Product)
                WHERE p.refrigerated = true
                MERGE (rs:Property {name: 'refrigerated', value: true})
                MERGE (p)-[:HAS_PROPERTY]->(rs)
            """)
            session.run("""
                MATCH (p:Product)
                WHERE p.refrigerated = false
                MERGE (rn:Property {name: 'refrigerated', value: false})
                MERGE (p)-[:HAS_PROPERTY]->(rn)
            """)
            session.run("""
                MATCH (p:Product)
                WHERE p.endotoxin_free = true
                MERGE (ef:Property {name: 'endotoxin_free', value: true})
                MERGE (p)-[:HAS_PROPERTY]->(ef)
            """)
            print("  Created HAS_PROPERTY relationships")

            # Create ALTERNATIVE_TO relationships (same name, different brand)
            session.run("""
                MATCH (p1:Product), (p2:Product)
                WHERE p1.name = p2.name AND p1.id < p2.id
                MERGE (p1)-[:ALTERNATIVE_TO]->(p2)
                MERGE (p2)-[:ALTERNATIVE_TO]->(p1)
            """)
            print("  Created ALTERNATIVE_TO relationships")

    finally:
        driver.close()


def verify():
    """Verify sync."""
    stats = get_graph_stats()
    print("\nGraph statistics:")
    for s in stats:
        print(f"  {s['label']}: {s['count']}")


def main():
    """Main sync pipeline."""
    sync_products()
    create_relationships()
    verify()
    print("\nSync complete!")


if __name__ == "__main__":
    main()

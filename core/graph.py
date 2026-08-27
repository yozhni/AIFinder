"""Neo4j graph database connection and operations."""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "aifinder_pass")


def get_driver():
    """Get Neo4j driver."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def execute_query(query, parameters=None):
    """Execute a Cypher query and return results."""
    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]
    finally:
        driver.close()


# ============================================
# GRAPH QUERIES FOR TEST SCENARIOS
# ============================================

def find_centrifuges_for_cell_harvest():
    """Test 1: Find centrifuges suitable for mammalian cell harvest."""
    query = """
    MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: "Equipment"})
    WHERE p.name CONTAINS 'centrifuge' AND p.refrigerated = true
    RETURN p.id AS id, p.name AS name, p.brand AS brand,
           p.price AS price, p.specifications AS specs,
           p.volume_or_capacity AS capacity
    ORDER BY p.price
    """
    return execute_query(query)


def find_equipment_for_protein_purification():
    """Test 2: Find equipment for recombinant protein expression and purification."""
    query = """
    MATCH (p:Product)-[:HAS_APPLICATION]->(a:Application)
    WHERE a.name CONTAINS 'protein purification' OR a.name CONTAINS 'Protein purification'
    RETURN p.id AS id, p.name AS name, p.brand AS brand,
           p.price AS price, p.category AS category,
           p.application AS application, p.use_case AS use_case
    ORDER BY p.category, p.price
    """
    return execute_query(query)


def search_products_by_name_graph(name_query):
    """Test 3: Search products by name using full-text index."""
    query = """
    CALL db.index.fulltext.queryNodes('product_fulltext', $query)
    YIELD node, score
    WHERE score > 0.5
    RETURN node.id AS id, node.name AS name, node.brand AS brand,
           node.price AS price, score
    ORDER BY score DESC
    LIMIT 10
    """
    return execute_query(query, {"query": name_query})


def find_sterile_pipette_tips():
    """Test 4: Find sterile pipette tips."""
    query = """
    MATCH (p:Product)
    WHERE p.name CONTAINS 'pipette tips' AND p.sterile = true
    OPTIONAL MATCH (p)-[:COMPATIBLE_WITH]->(compat:Product)
    RETURN p.id AS id, p.name AS name, p.brand AS brand,
           p.price AS price, p.sterile AS sterile,
           collect(compat.name) AS compatible_with
    ORDER BY p.price
    """
    return execute_query(query)


def compare_products_graph(product_name_1, product_name_2):
    """Test 5: Compare two products by name."""
    query = """
    MATCH (p1:Product), (p2:Product)
    WHERE p1.name CONTAINS $name1 AND p2.name CONTAINS $name2
      AND p1.id < p2.id
    RETURN p1 {.*} AS product_1, p2 {.*} AS product_2
    LIMIT 1
    """
    return execute_query(query, {"name1": product_name_1, "name2": product_name_2})


def get_recommendations_graph(use_case=None, application=None, limit=5):
    """Test 6: Get recommendations based on use case or application."""
    if use_case:
        query = """
        MATCH (p:Product)-[:HAS_USE_CASE]->(u:UseCase)
        WHERE u.name CONTAINS $use_case
        RETURN p.id AS id, p.name AS name, p.brand AS brand,
               p.price AS price, p.specifications AS specs
        ORDER BY p.price
        LIMIT $limit
        """
        return execute_query(query, {"use_case": use_case, "limit": limit})
    elif application:
        query = """
        MATCH (p:Product)-[:HAS_APPLICATION]->(a:Application)
        WHERE a.name CONTAINS $application
        RETURN p.id AS id, p.name AS name, p.brand AS brand,
               p.price AS price, p.use_case AS use_case
        ORDER BY p.price
        LIMIT $limit
        """
        return execute_query(query, {"application": application, "limit": limit})
    else:
        query = """
        MATCH (p:Product)
        RETURN p.id AS id, p.name AS name, p.brand AS brand,
               p.price AS price
        ORDER BY p.price
        LIMIT $limit
        """
        return execute_query(query, {"limit": limit})


# ============================================
# RELATIONSHIP QUERIES
# ============================================

def find_alternatives(product_id):
    """Find alternative products."""
    query = """
    MATCH (p:Product {id: $product_id})-[:ALTERNATIVE_TO]->(alt:Product)
    RETURN alt.id AS id, alt.name AS name, alt.brand AS brand,
           alt.price AS price
    """
    return execute_query(query, {"product_id": product_id})


def find_compatible_products(product_id):
    """Find compatible products."""
    query = """
    MATCH (p:Product {id: $product_id})-[:COMPATIBLE_WITH]->(compat:Product)
    RETURN compat.id AS id, compat.name AS name, compat.brand AS brand,
           compat.price AS price
    """
    return execute_query(query, {"product_id": product_id})


def find_products_in_workflow(workflow_name):
    """Find all products in a workflow."""
    query = """
    MATCH (w:Workflow)-[:REQUIRES]->(p:Product)
    WHERE w.name CONTAINS $workflow_name
    RETURN p.id AS id, p.name AS name, p.brand AS brand,
           p.price AS price, p.category AS category
    ORDER BY p.category, p.price
    """
    return execute_query(query, {"workflow_name": workflow_name})


def find_products_by_application(application):
    """Find products by application via graph."""
    query = """
    MATCH (p:Product)-[:HAS_APPLICATION]->(a:Application)
    WHERE a.name CONTAINS $application
    RETURN p.id AS id, p.name AS name, p.brand AS brand,
           p.price AS price, p.use_case AS use_case
    ORDER BY p.price
    """
    return execute_query(query, {"application": application})


def find_products_by_property(property_name, property_value):
    """Find products by property (sterile, refrigerated, etc.)."""
    query = """
    MATCH (p:Product)-[:HAS_PROPERTY]->(pr:Property)
    WHERE pr.name = $prop_name AND pr.value = $prop_value
    RETURN p.id AS id, p.name AS name, p.brand AS brand,
           p.price AS price
    ORDER BY p.price
    """
    return execute_query(query, {"prop_name": property_name, "prop_value": property_value})


# ============================================
# GRAPH SYNC (PostgreSQL -> Neo4j)
# ============================================

def sync_products_from_postgres(products):
    """Sync products from PostgreSQL to Neo4j."""
    driver = get_driver()
    try:
        with driver.session() as session:
            for product in products:
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
                    "id": product["id"],
                    "name": product["product_name"],
                    "brand": product["brand"],
                    "price": float(product["price_usd"]),
                    "category": product["category"],
                    "specifications": product["specifications"],
                    "application": product["application"],
                    "use_case": product["use_case"],
                    "refrigerated": product["refrigerated"],
                    "sterile": product["sterile"],
                    "endotoxin_free": product["endotoxin_free"],
                    "volume_or_capacity": product["volume_or_capacity"],
                })
    finally:
        driver.close()


def create_graph_relationships():
    """Create all graph relationships from product properties."""
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

            # Create Application nodes
            session.run("""
                MATCH (p:Product)
                WHERE p.application IS NOT NULL
                MERGE (a:Application {name: p.application})
                MERGE (p)-[:HAS_APPLICATION]->(a)
            """)

            # Create UseCase nodes
            session.run("""
                MATCH (p:Product)
                WHERE p.use_case IS NOT NULL
                MERGE (u:UseCase {name: p.use_case})
                MERGE (p)-[:HAS_USE_CASE]->(u)
            """)

            # Create Property nodes and relationships
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

            # Create ALTERNATIVE_TO relationships from product names
            session.run("""
                MATCH (p1:Product), (p2:Product)
                WHERE p1.name = p2.name AND p1.id < p2.id
                MERGE (p1)-[:ALTERNATIVE_TO]->(p2)
                MERGE (p2)-[:ALTERNATIVE_TO]->(p1)
            """)

    finally:
        driver.close()


def get_graph_stats():
    """Get graph statistics."""
    result = execute_query("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY label")
    return result

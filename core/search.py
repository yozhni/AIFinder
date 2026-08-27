"""Search orchestration - combines PostgreSQL SQL, Neo4j graph, and semantic search."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import (
    search_products as pg_search,
    semantic_search as pg_semantic,
    get_product_by_name as pg_get_by_name,
    compare_products as pg_compare,
    get_recommendations as pg_recommend,
    get_product,
)
from core.graph import (
    find_centrifuges_for_cell_harvest,
    find_equipment_for_protein_purification,
    search_products_by_name_graph,
    find_sterile_pipette_tips,
    compare_products_graph,
    get_recommendations_graph,
    find_products_by_application,
    find_products_in_workflow,
    find_alternatives,
    find_compatible_products,
)
from core.embeddings import generate_embedding


def search_products(query=None, category=None, brand=None, min_price=None,
                    max_price=None, refrigerated=None, sterile=None, limit=10):
    """Search products with SQL filters."""
    return pg_search(
        query=query, category=category, brand=brand,
        min_price=min_price, max_price=max_price,
        refrigerated=refrigerated, sterile=sterile, limit=limit
    )


def semantic_search(query, limit=10):
    """Natural language vector search."""
    embedding = generate_embedding(query)
    return pg_semantic(embedding, limit=limit)


def graph_search(query, search_type=None, limit=10):
    """Neo4j graph traversal search."""
    if search_type == "centrifuges":
        return find_centrifuges_for_cell_harvest()
    elif search_type == "protein_purification":
        return find_equipment_for_protein_purification()
    elif search_type == "sterile_tips":
        return find_sterile_pipette_tips()
    elif search_type == "workflow":
        return find_products_in_workflow(query)
    elif search_type == "application":
        return find_products_by_application(query)
    else:
        return search_products_by_name_graph(query)


def get_product_by_name(product_name, brand=None):
    """Find products by name."""
    return pg_get_by_name(product_name, brand)


def compare_products(product_name_1, product_name_2, brand_1=None, brand_2=None):
    """Compare two products side by side."""
    return pg_compare(product_name_1, product_name_2, brand_1, brand_2)


def get_recommendations(product_id=None, use_case=None, application=None, limit=5):
    """Get product recommendations."""
    if product_id:
        product = get_product(product_id)
        if product:
            return pg_recommend(product_id=product_id, limit=limit)
    if use_case or application:
        return get_recommendations_graph(use_case=use_case, application=application, limit=limit)
    return pg_recommend(limit=limit)


def resolve_product_name(name_query, brand=None):
    """Find product by name, handle multiple matches."""
    results = get_product_by_name(name_query, brand)

    if not results:
        return {"status": "not_found", "message": f"No products found matching '{name_query}'"}
    elif len(results) == 1:
        return {"status": "found", "product": results[0]}
    else:
        return {"status": "multiple", "products": results}

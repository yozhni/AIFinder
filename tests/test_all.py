"""AIFinder test suite."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config():
    """Test config.yaml loading."""
    from config import get

    assert get("database", "url") is not None
    assert get("neo4j", "uri") is not None
    assert get("llm", "groq_model") is not None
    assert get("data", "source") is not None
    assert get("csv_columns") is not None
    assert get("embedding_fields") is not None
    assert len(get("csv_columns")) > 0
    assert len(get("embedding_fields")) > 0
    print("  config.py: OK")


def test_embeddings():
    """Test embedding generation."""
    from core.embeddings import generate_embedding, build_embedding_text, EMBEDDING_DIM, MODEL_NAME

    text = "I need protein purification"
    vector = generate_embedding(text)
    assert len(vector) == EMBEDDING_DIM

    product = {
        "product_name": "Test Product",
        "brand": "Test Brand",
        "category": "Test Category",
        "application": "Test Application",
        "use_case": "Test Use Case",
        "specifications": "Test specs",
        "used_for": "Test",
        "requires": "Test",
        "alternative_to": "Test",
        "typical_user_question": "Test?"
    }
    text = build_embedding_text(product)
    assert len(text) > 0
    print("  embeddings.py: OK")


def test_database():
    """Test PostgreSQL operations."""
    from core.database import (
        get_connection, get_total_products, get_categories, get_brands,
        get_price_range, search_products, get_product_by_name
    )

    conn = get_connection()
    conn.close()

    count = get_total_products()
    assert count >= 0

    cats = get_categories()
    assert isinstance(cats, list)

    brands = get_brands()
    assert isinstance(brands, list)

    pr = get_price_range()
    assert "min" in pr
    assert "max" in pr

    results = search_products(query="centrifuge", limit=3)
    assert isinstance(results, list)

    results = get_product_by_name("Size Exclusion Column")
    assert isinstance(results, list)
    print("  database.py: OK")


def test_graph():
    """Test Neo4j operations."""
    from core.graph import (
        get_driver, get_graph_stats,
        find_centrifuges_for_cell_harvest,
        find_equipment_for_protein_purification,
        search_products_by_name_graph,
        find_sterile_pipette_tips,
        find_products_by_application
    )

    driver = get_driver()
    driver.close()

    stats = get_graph_stats()
    assert isinstance(stats, list)

    r = find_centrifuges_for_cell_harvest()
    assert isinstance(r, list)
    assert len(r) > 0

    r = find_equipment_for_protein_purification()
    assert isinstance(r, list)
    assert len(r) > 0

    r = search_products_by_name_graph("pipette")
    assert isinstance(r, list)
    assert len(r) > 0

    r = find_sterile_pipette_tips()
    assert isinstance(r, list)
    assert len(r) > 0

    r = find_products_by_application("cell culture")
    assert isinstance(r, list)
    assert len(r) > 0
    print("  graph.py: OK")


def run_all():
    """Run all tests."""
    print("=" * 60)
    print("AIFINDER TEST SUITE")
    print("=" * 60)
    print()

    tests = [
        ("Config", test_config),
        ("Embeddings", test_embeddings),
        ("Database", test_database),
        ("Graph", test_graph),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"--- {name} ---")
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1
        print()

    print("=" * 60)
    if failed == 0:
        print(f"ALL {passed} TESTS PASSED!")
    else:
        print(f"{passed} passed, {failed} FAILED")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)

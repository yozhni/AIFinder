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


def test_search():
    """Test search orchestration."""
    from core.search import (
        search_products, semantic_search, graph_search,
        get_product_by_name, compare_products, get_recommendations,
        resolve_product_name
    )

    # SQL search
    results = search_products(query="centrifuge", limit=3)
    assert isinstance(results, list)
    assert len(results) > 0

    # Semantic search
    results = semantic_search("protein purification equipment", limit=3)
    assert isinstance(results, list)
    assert len(results) > 0

    # Graph search
    results = graph_search("pipette", search_type=None, limit=3)
    assert isinstance(results, list)

    # Get by name
    results = get_product_by_name("Size Exclusion Column")
    assert isinstance(results, list)
    assert len(results) > 0

    # Compare
    result = compare_products("Size Exclusion Column", "Desalting Column")
    assert "product_1" in result or "error" in result

    # Recommendations
    results = get_recommendations(use_case="cell culture", limit=3)
    assert isinstance(results, list)

    # Resolve name
    result = resolve_product_name("Size Exclusion Column")
    assert result["status"] in ("found", "multiple", "not_found")

    print("  search.py: OK")


def test_search_queries():
    """Test actual search queries and verify results."""
    from core.search import search_products, semantic_search, get_product_by_name, compare_products

    print()
    print("  Query tests:")

    # Test 1: Search centrifuges
    results = search_products(query="centrifuge", limit=5)
    assert len(results) > 0, "Should find centrifuges"
    names = [r["product_name"] for r in results]
    assert any("centrifuge" in n.lower() or "centrifuge" in n for n in names), \
        f"Results should contain centrifuge, got: {names}"
    print(f"    1. Search 'centrifuge': {len(results)} results - OK")

    # Test 2: Search by category
    results = search_products(category="Equipment", limit=5)
    assert len(results) > 0, "Should find Equipment products"
    assert all(r["category"] == "Equipment" for r in results), "All should be Equipment"
    print(f"    2. Search category 'Equipment': {len(results)} results - OK")

    # Test 3: Search by price range
    results = search_products(min_price=100, max_price=500, limit=5)
    assert len(results) > 0, "Should find products in price range"
    assert all(100 <= r["price_usd"] <= 500 for r in results), "All should be in price range"
    print(f"    3. Search price $100-$500: {len(results)} results - OK")

    # Test 4: Search sterile products
    results = search_products(sterile=True, limit=5)
    assert len(results) > 0, "Should find sterile products"
    assert all(r["sterile"] == True for r in results), "All should be sterile"
    print(f"    4. Search sterile=True: {len(results)} results - OK")

    # Test 5: Semantic search
    results = semantic_search("I need something for protein purification", limit=5)
    assert len(results) > 0, "Should find protein purification products"
    print(f"    5. Semantic search 'protein purification': {len(results)} results - OK")

    # Test 6: Get product by name
    results = get_product_by_name("Size Exclusion Column")
    assert len(results) > 0, "Should find Size Exclusion Column"
    assert results[0]["product_name"] == "Size Exclusion Column"
    print(f"    6. Get 'Size Exclusion Column': {len(results)} matches - OK")

    # Test 7: Compare products
    result = compare_products("Size Exclusion Column", "Desalting Column")
    assert "product_1" in result, "Should have product_1"
    assert "product_2" in result, "Should have product_2"
    assert result["product_1"]["product_name"] == "Size Exclusion Column"
    assert result["product_2"]["product_name"] == "Desalting Column"
    print(f"    7. Compare products: OK")

    # Test 8: Search with multiple filters
    results = search_products(category="Equipment", refrigerated=True, limit=5)
    assert len(results) > 0, "Should find refrigerated equipment"
    assert all(r["category"] == "Equipment" and r["refrigerated"] == True for r in results)
    print(f"    8. Search Equipment + refrigerated: {len(results)} results - OK")

    # Test 9: Search not found
    results = search_products(query="xyznonexistent123", limit=5)
    assert len(results) == 0, "Should return empty for nonexistent"
    print(f"    9. Search nonexistent: {len(results)} results (expected 0) - OK")

    # Test 10: Limit results
    results = search_products(limit=3)
    assert len(results) <= 3, "Should respect limit"
    print(f"    10. Limit to 3: {len(results)} results - OK")

    print("  Query tests: ALL PASSED")


def test_user_queries():
    """Test the actual user queries from the roadmap."""
    from core.search import (
        search_products, semantic_search, graph_search,
        get_product_by_name, compare_products, get_recommendations
    )
    from core.graph import (
        find_centrifuges_for_cell_harvest,
        find_equipment_for_protein_purification,
        find_sterile_pipette_tips,
        find_products_by_application
    )

    print()
    print("  User query tests:")

    # Query 1: "i need to harvest mammalian cells , what centrifuge i needed?"
    # Should find refrigerated centrifuges
    results = find_centrifuges_for_cell_harvest()
    assert len(results) > 0, "Should find refrigerated centrifuges for cell harvest"
    assert all("centrifuge" in r["name"].lower() for r in results)
    assert all(r.get("price", 0) > 0 for r in results)
    print(f"    1. 'i need to harvest mammalian cells, what centrifuge i needed?': {len(results)} refrigerated centrifuges - OK")

    # Query 2: "What equipment i need for recombinant protein expressing and purification"
    # Should find chromatography columns, reagents, etc.
    results = find_equipment_for_protein_purification()
    assert len(results) > 0, "Should find protein purification products"
    categories = set(r.get("category", "") for r in results)
    print(f"    2. 'What equipment i need for recombinant protein expressing and purification': {len(results)} products in {categories} - OK")

    # Query 3: "help to find pipettes"
    # Should find pipette-related products
    results = search_products(query="pipette", limit=10)
    assert len(results) > 0, "Should find pipette products"
    print(f"    3. 'help to find pipettes': {len(results)} products - OK")

    # Query 4: "find sterile pipette tips that are compatible with Ergonomic pipettes"
    # Should find sterile pipette tips
    results = find_sterile_pipette_tips()
    assert len(results) > 0, "Should find sterile pipette tips"
    assert all(r.get("sterile") == True for r in results)
    print(f"    4. 'find sterile pipette tips that are compatible with Ergonomic pipettes': {len(results)} sterile tips - OK")

    # Query 5: "compare the Size Exclusion Column and the Desalting Column"
    result = compare_products("Size Exclusion Column", "Desalting Column")
    assert "product_1" in result, "Should have product_1"
    assert "product_2" in result, "Should have product_2"
    p1 = result["product_1"]
    p2 = result["product_2"]
    assert p1["product_name"] == "Size Exclusion Column"
    assert p2["product_name"] == "Desalting Column"
    assert p1["price_usd"] > 0
    assert p2["price_usd"] > 0
    print(f"    5. 'compare the Size Exclusion Column and the Desalting Column': OK")

    # Query 6: "recommend me.." (based on cell culture context)
    results = get_recommendations(use_case="cell culture", limit=5)
    assert len(results) > 0, "Should find cell culture recommendations"
    print(f"    6. 'recommend me..' (cell culture context): {len(results)} products - OK")

    print("  User query tests: ALL PASSED")


def test_tools():
    """Test LLM tool definitions."""
    from core.tools import get_tools, tools

    # Check tools exist
    assert len(tools) == 7

    # Check tool names
    tool_names = [t["function"]["name"] for t in tools]
    assert "search_products" in tool_names
    assert "semantic_search" in tool_names
    assert "get_product_by_name" in tool_names
    assert "compare_products" in tool_names
    assert "get_recommendations" in tool_names
    assert "add_to_cart" in tool_names
    assert "get_cart" in tool_names

    # Check get_tools returns same
    assert get_tools() == tools

    print("  tools.py: OK")


def test_llm():
    """Test LLM integration (structure only, no API calls)."""
    from core.llm import (
        execute_tool, build_context, SYSTEM_PROMPT,
        GROQ_MODEL, OLLAMA_MODEL
    )

    # Check config loaded
    assert GROQ_MODEL is not None
    assert OLLAMA_MODEL is not None
    assert len(SYSTEM_PROMPT) > 0

    # Test tool execution (search)
    result = execute_tool("search_products", {"query": "centrifuge", "limit": 2})
    assert "products" in result
    assert result["count"] >= 0

    # Test tool execution (get_cart)
    result = execute_tool("get_cart", {}, session_id="test_session")
    assert "items" in result
    assert "total" in result

    # Test tool execution (compare)
    result = execute_tool("compare_products", {
        "product_name_1": "Size Exclusion Column",
        "product_name_2": "Desalting Column"
    })
    assert "product_1" in result or "error" in result

    print("  llm.py: OK")


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
        ("Search", test_search),
        ("Search Queries", test_search_queries),
        ("User Queries", test_user_queries),
        ("Tools", test_tools),
        ("LLM", test_llm),
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

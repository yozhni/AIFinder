"""AIFinder test suite."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config():
    """Test config.yaml loading."""
    from config import get

    assert get("database", "url") is not None
    assert get("neo4j", "uri") is not None
    assert get("llm", "provider") is not None
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
    assert len(tools) >= 7

    # Check tool names
    tool_names = [t["function"]["name"] for t in tools]
    assert "search_products" in tool_names
    assert "semantic_search" in tool_names
    assert "get_product_by_name" in tool_names
    assert "compare_products" in tool_names
    assert "get_recommendations" in tool_names
    assert "add_to_cart" in tool_names
    assert "get_cart" in tool_names
    assert "find_alternatives" in tool_names
    assert "find_compatible_products" in tool_names
    assert "find_products_in_workflow" in tool_names
    assert "find_products_by_application" in tool_names

    # Check get_tools returns same
    assert get_tools() == tools

    print("  tools.py: OK")


def test_llm():
    """Test LLM integration (structure only, no API calls)."""
    from core.llm import (
        execute_tool, build_context, SYSTEM_PROMPT
    )

    # Check config loaded
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


def test_grounding():
    """P0: answers must be grounded - every product link must be real and match
    a product named in the answer. Uses mocks, so no DB/API needed."""
    import re
    from decimal import Decimal
    import core.llm as llm

    # Fake catalogue (pretend only LC-0017 exists)
    catalog = {"LC-0017": "Refrigerated Benchtop Centrifuge"}
    names = ("_id_exists", "get_product", "build_context", "execute_tool",
             "_call_provider", "save_message")
    orig = {n: getattr(llm, n) for n in names}
    try:
        llm._id_exists = lambda pid: pid in catalog
        llm.get_product = lambda pid: ({"id": pid, "product_name": catalog[pid]}
                                       if pid in catalog else None)
        llm.build_context = lambda *a, **k: []
        llm.save_message = lambda *a, **k: None

        # 1) sanitize_links drops unknown IDs, keeps valid ones (markdown + raw)
        dirty = ("Try [Pipette](/products/LC-9999) or [Centrifuge](/products/LC-0017), "
                 "also see /products/LC-9999")
        clean = llm.sanitize_links(dirty)
        assert "/products/LC-9999" not in clean, "unknown product link must be removed"
        assert "/products/LC-0017" in clean, "valid product link must be kept"
        print("    sanitize_links: OK")

        # 2) agent loop: tool call -> final answer; hallucinated link stripped
        state = {"step": 0}

        def fake_provider(provider, messages, tools, force_tools=False, session_id=None):
            state["step"] += 1
            if state["step"] == 1:
                return {"content": "", "tool_calls": [
                    {"id": "c0", "name": "search_products",
                     "arguments": {"query": "centrifuge"}}]}
            return {"content": (
                "Here is a great option: **Refrigerated Benchtop Centrifuge** "
                "[View Product](/products/LC-0017). Also see "
                "[Mystery Pipette](/products/LC-9999)."), "tool_calls": []}

        def fake_execute(name, args, session_id="default"):
            return {"products": [{
                "id": "LC-0017", "product_name": "Refrigerated Benchtop Centrifuge",
                "brand": "CellForge", "price_usd": Decimal("2156.43"),
            }], "count": 1}

        llm._call_provider = fake_provider
        llm.execute_tool = fake_execute

        answer = llm.get_llm_response("test-session", "I need a centrifuge")

        assert "/products/LC-9999" not in answer, "hallucinated link must not be returned"
        assert "/products/LC-0017" in answer, "valid product link should be present"
        print("    hallucinated link stripped: OK")

        # 3) every link in the answer points to a real product named in the answer
        linked = re.findall(r"/products/([A-Za-z0-9\-]+)", answer)
        assert linked, "answer should contain at least one product link"
        for pid in linked:
            assert pid in catalog, f"link {pid} is not a real product"
            assert catalog[pid] in answer, \
                f"link {pid} does not match a product named in the answer"
        print(f"    links grounded & consistent ({linked}): OK")
    finally:
        for n, fn in orig.items():
            setattr(llm, n, fn)

    print("  grounding (P0): OK")


def test_error_guard():
    """Errors must not be persisted to chat history; is_error detects them."""
    import core.llm as llm

    assert llm.is_error("Ollama error: boom") is True
    assert llm.is_error("Google error: quota") is True
    assert llm.is_error("Error processing request. Please try again.") is True
    assert llm.is_error("Here are some products for you") is False
    assert llm.is_error("") is False

    names = ("_call_provider", "build_context", "save_message", "sanitize_links")
    orig = {n: getattr(llm, n) for n in names}
    saved = []
    try:
        llm.build_context = lambda *a, **k: []
        llm.sanitize_links = lambda t: t
        llm.save_message = lambda *a, **k: saved.append(a)

        # provider error -> must NOT be saved
        llm._call_provider = lambda provider, messages, tools, force_tools=False, session_id=None: {
            "content": "Google error: something broke", "tool_calls": [], "error": True}
        out = llm.get_llm_response("t", "I need a centrifuge")
        assert llm.is_error(out), "returned error text should be detected"
        assert saved == [], "error responses must NOT be saved to history"

        # normal answer -> IS saved
        llm._call_provider = lambda provider, messages, tools, force_tools=False, session_id=None: {
            "content": "Sure, here is a product.", "tool_calls": []}
        llm.get_llm_response("t", "hi")
        assert saved, "normal responses should be saved"
    finally:
        for n, fn in orig.items():
            setattr(llm, n, fn)

    print("  error guard: OK")


def test_openai_compat():
    """OpenAI-compatible provider (OpenCode Go / OpenAI): message/tool conversion."""
    import core.llm as llm
    from config import get

    msgs = [
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c0", "name": "search_products", "arguments": {"query": "x"}}]},
        {"role": "tool", "tool_call_id": "c0", "name": "search_products",
         "content": {"products": [], "count": 0}},
    ]
    out = llm._to_openai_messages(msgs)
    assert out[0]["tool_calls"][0]["function"]["name"] == "search_products"
    assert isinstance(out[0]["tool_calls"][0]["function"]["arguments"], str)  # JSON string
    assert out[1]["role"] == "tool" and out[1]["tool_call_id"] == "c0"

    turn = llm._turn_from_openai_msg({"content": "hi", "tool_calls": [
        {"id": "c1", "function": {"name": "f", "arguments": '{"a": 1}'}}]})
    assert turn["tool_calls"][0]["arguments"] == {"a": 1}  # parsed to dict

    assert (get("providers") or {}).get("opencode_go", {}).get("type") == "openai_compatible"
    print("  openai-compatible (opencode_go): OK")


def test_p1():
    """P1: retrieval upgrades, memory, cart intelligence."""
    from core.tools import get_tools
    from core.database import extract_preferences, find_by_spec, hybrid_search

    # P1.3 preference extraction (no DB)
    prefs = extract_preferences("I need something under $2000 for cell culture")
    assert prefs.get("budget_max") == 2000.0, prefs
    assert "cell culture" in (prefs.get("applications") or []), prefs

    # P1.2 retrieval (needs DB)
    spec = find_by_spec(sterile=True, limit=3)
    assert isinstance(spec, list)
    hy = hybrid_search("cold centrifuge", limit=3)
    assert isinstance(hy, list)

    # new tools present
    names = [t["function"]["name"] for t in get_tools()]
    for n in ("hybrid_search", "find_by_spec", "build_kit",
              "check_cart_compatibility", "suggest_missing_items", "estimate_quote"):
        assert n in names, f"missing tool {n}"

    print("  P1 (retrieval/memory/cart): OK")


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
        ("Grounding", test_grounding),
        ("Error guard", test_error_guard),
        ("OpenAI-compatible", test_openai_compat),
        ("P1", test_p1),
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

"""LLM tool definitions for the sales assistant chatbot."""

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search products by name, category, brand, price range, or other filters. Use this when the user asks to find specific products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (product name, application, use case, or general text)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Product category filter (e.g., 'Equipment', 'Reagents', 'Chromatography')"
                    },
                    "brand": {
                        "type": "string",
                        "description": "Brand name filter"
                    },
                    "min_price": {
                        "type": "number",
                        "description": "Minimum price in USD"
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price in USD"
                    },
                    "refrigerated": {
                        "type": "boolean",
                        "description": "Filter by refrigerated products only"
                    },
                    "sterile": {
                        "type": "boolean",
                        "description": "Filter by sterile products only"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "semantic_search",
            "description": "Find products using natural language description. Use this when the user describes what they need in plain language, like 'something for protein purification' or 'equipment for cell culture'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language description of what the user needs"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_by_name",
            "description": "Find a specific product by its name. Use this when the user mentions a specific product name like 'Size Exclusion Column' or 'pipette tips'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Product name to search for (partial or full match)"
                    },
                    "brand": {
                        "type": "string",
                        "description": "Optional brand name to narrow search"
                    }
                },
                "required": ["product_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_products",
            "description": "Compare two products side by side. Use this when the user asks to compare products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name_1": {
                        "type": "string",
                        "description": "First product name"
                    },
                    "product_name_2": {
                        "type": "string",
                        "description": "Second product name"
                    },
                    "brand_1": {
                        "type": "string",
                        "description": "Optional brand of first product"
                    },
                    "brand_2": {
                        "type": "string",
                        "description": "Optional brand of second product"
                    }
                },
                "required": ["product_name_1", "product_name_2"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": "Get product recommendations based on a product ID or use case. Use this when the user asks for recommendations or suggestions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID to get recommendations for"
                    },
                    "use_case": {
                        "type": "string",
                        "description": "Use case to recommend products for (e.g., 'cell culture', 'protein purification')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of recommendations (default: 5)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add a product to the shopping cart. Use this when the user wants to add an item to their cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID to add to cart"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Quantity to add (default: 1)"
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_cart",
            "description": "Get the current cart contents. Use this when the user asks to see their cart or check what's in it.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


def get_tools():
    """Return the list of tools for the LLM."""
    return tools

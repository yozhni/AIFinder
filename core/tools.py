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
                    "application": {
                        "type": "string",
                        "description": "Application to recommend products for (e.g., 'cell culture', 'protein purification')"
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
    },
    {
        "type": "function",
        "function": {
            "name": "find_alternatives",
            "description": "Find alternative products for a given product ID. Use this when the user asks for alternatives or similar options.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID to find alternatives for"
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_compatible_products",
            "description": "Find products compatible with a given product ID. Use this when the user asks what works with a product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID to find compatible products for"
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_products_in_workflow",
            "description": "Find all products required for a given workflow (e.g., recombinant protein purification). Use this when the user asks what equipment they need for a process.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workflow_name": {
                        "type": "string",
                        "description": "Workflow or application name (e.g., 'protein purification', 'cell harvesting')"
                    }
                },
                "required": ["workflow_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_products_by_application",
            "description": "Find products for a given laboratory application. Use this when the user mentions an application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "description": "Laboratory application name (e.g., 'cell culture', 'protein purification')"
                    }
                },
                "required": ["application"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "hybrid_search",
            "description": "Best general product search: fuses keyword + semantic matching. Prefer this for natural-language product requests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search text"},
                    "limit": {"type": "integer", "description": "Max results (default 10)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_by_spec",
            "description": "Find products by structured specifications (price, category, brand, sterile, refrigerated, max RCF, volume).",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "brand": {"type": "string"},
                    "min_price": {"type": "number"},
                    "max_price": {"type": "number"},
                    "refrigerated": {"type": "boolean"},
                    "sterile": {"type": "boolean"},
                    "min_rcf": {"type": "integer", "description": "Minimum max RCF (x g)"},
                    "volume": {"type": "string", "description": "Volume/capacity text, e.g. '50 mL'"},
                    "limit": {"type": "integer"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "build_kit",
            "description": "Assemble a coherent kit for an application/workflow within a budget and add it to the cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {"type": "string", "description": "Workflow/application, e.g. 'protein purification'"},
                    "budget": {"type": "number", "description": "Optional total budget in USD"}
                },
                "required": ["application"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_cart_compatibility",
            "description": "Check whether the items currently in the cart are compatible with each other.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_missing_items",
            "description": "Suggest items that are missing from the cart for the workflow(s) it contains.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_quote",
            "description": "Estimate the current cart's quote (items, subtotal, total).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]


def get_tools():
    """Return the list of tools for the LLM."""
    return tools

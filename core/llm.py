"""LLM integration - Groq (cloud) and Ollama (local) with tool calling."""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get
from core.tools import get_tools
from core.database import (
    search_products, semantic_search as db_semantic,
    get_product_by_name, compare_products,
    get_recommendations, add_to_cart, get_cart,
    save_message, load_history,
)

# Load config
SYSTEM_PROMPT = get("llm", "system_prompt")
GROQ_MODEL = get("llm", "groq_model")
OLLAMA_MODEL = get("llm", "ollama_model")
OLLAMA_HOST = get("ollama", "host")
TEMPERATURE = get("llm", "temperature")
MAX_TOKENS = get("llm", "max_tokens")


def execute_tool(tool_name, arguments, session_id="default"):
    """Execute a tool call and return results."""
    try:
        if tool_name == "search_products":
            results = search_products(
                query=arguments.get("query"),
                category=arguments.get("category"),
                brand=arguments.get("brand"),
                min_price=arguments.get("min_price"),
                max_price=arguments.get("max_price"),
                refrigerated=arguments.get("refrigerated"),
                sterile=arguments.get("sterile"),
                limit=arguments.get("limit", 10)
            )
            return {"products": results, "count": len(results)}

        elif tool_name == "semantic_search":
            results = db_semantic(
                query=arguments["query"],
                limit=arguments.get("limit", 10)
            )
            return {"products": results, "count": len(results)}

        elif tool_name == "get_product_by_name":
            results = get_product_by_name(
                arguments["product_name"],
                arguments.get("brand")
            )
            return {"products": results, "count": len(results)}

        elif tool_name == "compare_products":
            result = compare_products(
                arguments["product_name_1"],
                arguments["product_name_2"],
                arguments.get("brand_1"),
                arguments.get("brand_2")
            )
            return result

        elif tool_name == "get_recommendations":
            results = get_recommendations(
                product_id=arguments.get("product_id"),
                use_case=arguments.get("use_case"),
                application=arguments.get("application"),
                limit=arguments.get("limit", 5)
            )
            return {"products": results, "count": len(results)}

        elif tool_name == "add_to_cart":
            add_to_cart(
                session_id,
                arguments["product_id"],
                arguments.get("quantity", 1)
            )
            return {"success": True, "message": f"Added {arguments['product_id']} to cart"}

        elif tool_name == "get_cart":
            cart = get_cart(session_id)
            total = sum(item["price_usd"] * item["quantity"] for item in cart)
            return {"items": cart, "total": total, "count": len(cart)}

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"error": str(e)}


def build_context(session_id, limit=20):
    """Build context window for LLM."""
    history = load_history(session_id, limit)

    if not history:
        return []

    # Keep last 5 messages (10 items) in full detail
    if len(history) > 10:
        recent = history[-10:]
        older = history[:-10]

        # Summarize older messages
        summary_parts = []
        for i in range(0, len(older) - 1, 2):
            if i + 1 < len(older):
                user_msg = older[i]["content"][:50]
                bot_msg = older[i + 1]["content"][:100]
                summary_parts.append(f"User asked about: {user_msg}... Bot discussed: {bot_msg}...")

        summary = "Earlier conversation: " + " | ".join(summary_parts)
        context = [{"role": "system", "content": summary}]
        for msg in recent:
            context.append({"role": msg["role"], "content": msg["content"]})
        return context
    else:
        return [{"role": msg["role"], "content": msg["content"]} for msg in history]


def get_llm_response(session_id, user_message):
    """Get response from LLM with tool calling."""
    # Save user message
    save_message(session_id, "user", user_message)

    # Build context
    context = build_context(session_id)

    # Build messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ] + context + [
        {"role": "user", "content": user_message}
    ]

    tools = get_tools()

    # Try Groq first
    try:
        response = _call_groq(messages, tools)
        return _process_response(response, session_id, messages, tools)
    except Exception as e:
        print(f"Groq error: {e}")

    # Fallback to Ollama
    try:
        response = _call_ollama(messages, tools)
        return _process_response(response, session_id, messages, tools)
    except Exception as e:
        print(f"Ollama error: {e}")
        return "I'm sorry, I couldn't process your request. Please try again."


def _process_response(response, session_id, messages, tools):
    """Process LLM response, handle tool calls if needed."""
    # Check if tool call
    if hasattr(response, 'choices') and response.choices:
        choice = response.choices[0]
        if hasattr(choice, 'message') and choice.message.tool_calls:
            # Execute tools
            tool_results = []
            for tool_call in choice.message.tool_calls:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}

                # Get session_id for cart operations
                session = func_args.pop("session_id", "default")
                result = execute_tool(func_name, func_args, session)
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "result": result
                })

            # Add tool results to messages
            messages.append(choice.message)
            for tr in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_call_id"],
                    "content": json.dumps(tr["result"])
                })

            # Get final response
            try:
                final_response = _call_groq(messages, tools)
                if hasattr(final_response, 'choices') and final_response.choices:
                    content = final_response.choices[0].message.content
                    save_message(session_id, "assistant", content)
                    return content
            except Exception:
                pass

            # Format tool results as response
            return _format_tool_results(tool_results)

        # Regular text response
        content = choice.message.content
        save_message(session_id, "assistant", content)
        return content

    return "I'm sorry, I couldn't process your request."


def _format_tool_results(tool_results):
    """Format tool results into a readable response."""
    parts = []
    for tr in tool_results:
        result = tr["result"]
        if "products" in result:
            products = result["products"]
            if not products:
                parts.append("No products found matching your criteria.")
            else:
                lines = [f"Found {len(products)} products:"]
                for p in products[:5]:
                    lines.append(f"- **{p.get('product_name', 'N/A')}** by {p.get('brand', 'N/A')} - ${p.get('price_usd', 0):.2f}")
                    if p.get('specifications'):
                        lines.append(f"  Specs: {p['specifications'][:100]}")
                if len(products) > 5:
                    lines.append(f"... and {len(products) - 5} more")
                parts.append("\n".join(lines))
        elif "product_1" in result and "product_2" in result:
            p1 = result["product_1"]
            p2 = result["product_2"]
            parts.append(f"**Comparison:**\n{p1.get('product_name', 'N/A')} vs {p2.get('product_name', 'N/A')}")
        elif "success" in result:
            parts.append(result.get("message", "Done"))
        elif "error" in result:
            parts.append(f"Error: {result['error']}")
    return "\n\n".join(parts) if parts else "No results found."


def _call_groq(messages, tools):
    """Call Groq API."""
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")

    client = Groq(api_key=api_key)
    return client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
    )


def _call_ollama(messages, tools):
    """Call Ollama API."""
    import requests

    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "tools": tools,
        "stream": False
    }

    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()

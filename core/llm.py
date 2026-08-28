"""LLM integration - Google AI Studio + Ollama."""

import json
import requests
from decimal import Decimal
from config import get
from core.tools import get_tools
from core.database import (
    search_products, semantic_search as db_semantic,
    get_product_by_name, compare_products,
    get_recommendations, add_to_cart, get_cart,
    save_message, load_history,
)

SYSTEM_PROMPT = get("llm", "system_prompt") or "You are a helpful sales assistant."
OLLAMA_HOST = get("ollama", "host") or "http://localhost:11434"
TEMPERATURE = get("llm", "temperature") or 0.7
MAX_TOKENS = get("llm", "max_tokens") or 2048


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def execute_tool(tool_name, arguments, session_id="default"):
    try:
        if tool_name == "search_products":
            r = search_products(query=arguments.get("query"), category=arguments.get("category"),
                brand=arguments.get("brand"), min_price=arguments.get("min_price"),
                max_price=arguments.get("max_price"), refrigerated=arguments.get("refrigerated"),
                sterile=arguments.get("sterile"), limit=arguments.get("limit", 10))
            return {"products": r, "count": len(r)}
        elif tool_name == "semantic_search":
            from core.embeddings import generate_embedding
            embedding = generate_embedding(arguments["query"])
            r = db_semantic(query_embedding=embedding, limit=arguments.get("limit", 10))
            return {"products": r, "count": len(r)}
        elif tool_name == "get_product_by_name":
            r = get_product_by_name(arguments["product_name"], arguments.get("brand"))
            return {"products": r, "count": len(r)}
        elif tool_name == "compare_products":
            return compare_products(arguments["product_name_1"], arguments["product_name_2"],
                                   arguments.get("brand_1"), arguments.get("brand_2"))
        elif tool_name == "get_recommendations":
            r = get_recommendations(product_id=arguments.get("product_id"),
                use_case=arguments.get("use_case") or arguments.get("application"),
                limit=arguments.get("limit", 5))
            return {"products": r, "count": len(r)}
        elif tool_name == "add_to_cart":
            add_to_cart(session_id, arguments["product_id"], arguments.get("quantity", 1))
            return {"success": True, "message": f"Added {arguments['product_id']} to cart"}
        elif tool_name == "get_cart":
            cart = get_cart(session_id)
            total = sum(item["price_usd"] * item["quantity"] for item in cart)
            return {"items": cart, "total": total, "count": len(cart)}
        return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        return {"error": str(e)}


def build_context(session_id, limit=20):
    try:
        history = load_history(session_id, limit)
    except Exception:
        return []
    if not history:
        return []
    if len(history) > 10:
        recent = history[-10:]
        older = history[:-10]
        parts = []
        for i in range(0, len(older) - 1, 2):
            if i + 1 < len(older):
                parts.append(f"User: {older[i]['content'][:50]}... Bot: {older[i+1]['content'][:100]}...")
        return [{"role": "system", "content": "Earlier: " + " | ".join(parts)}] + \
               [{"role": m["role"], "content": m["content"]} for m in recent]
    return [{"role": m["role"], "content": m["content"]} for m in history]


def get_llm_response(session_id, user_message):
    try:
        save_message(session_id, "user", user_message)
    except Exception:
        pass

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + \
               build_context(session_id) + \
               [{"role": "user", "content": user_message}]

    tools = get_tools()
    provider = get("llm", "provider") or "ollama"

    try:
        if provider == "ollama":
            model = get("ollama", "model") or "qwen2.5:3b"
            result = _call_ollama(messages, tools, model)
        elif provider == "google":
            api_key = get("google", "api_key")
            model = get("google", "model") or "auto"
            result = _call_google(messages, tools, api_key, model)
        else:
            return f"Unknown provider: {provider}"

        response = _process_response(result, session_id, messages, tools)
        try:
            save_message(session_id, "assistant", response)
        except Exception:
            pass
        return response
    except Exception:
        return "Error processing request. Please try again."


def _call_ollama(messages, tools, model):
    try:
        r = requests.post(f"{OLLAMA_HOST}/api/chat",
                         json={"model": model, "messages": messages, "tools": tools, "stream": False},
                         timeout=120)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {})
        tc = None
        if msg.get("tool_calls"):
            tc = [{"id": f"c{i}", "function": {"name": t["function"]["name"],
                   "arguments": json.dumps(t["function"]["arguments"], cls=DecimalEncoder)}} for i, t in enumerate(msg["tool_calls"])]
        return {"choices": [{"message": {"content": msg.get("content", ""), "tool_calls": tc}}]}
    except Exception as e:
        return {"choices": [{"message": {"content": f"Ollama error: {str(e)[:80]}"}}]}


def _call_google(messages, tools, api_key, model):
    try:
        if not api_key:
            return {"choices": [{"message": {"content": "Google API key not set"}}]}
        if not model or model == "auto":
            model = _get_google_model(api_key)

        # Convert messages to Google format (role must be user/model, use parts)
        google_contents = []
        for m in messages:
            role = m["role"]
            if role == "system":
                # Google doesn't have system role - use user/model pair
                google_contents.append({"role": "user", "parts": [{"text": m["content"]}]})
                google_contents.append({"role": "model", "parts": [{"text": "I understand."}]})
            elif role == "assistant":
                google_contents.append({"role": "model", "parts": [{"text": m.get("content", "")}]})
            else:
                google_contents.append({"role": "user", "parts": [{"text": m.get("content", "")}]})

        gt = []
        if tools:
            for t in tools:
                gt.append({"function_declarations": [{"name": t["function"]["name"],
                           "description": t["function"]["description"], "parameters": t["function"]["parameters"]}]})

        payload = {"contents": google_contents}
        if gt:
            payload["tools"] = gt

        r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                         json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()

        parts = data["candidates"][0]["content"].get("parts", [])
        text, tc = "", []
        for p in parts:
            if "text" in p:
                text += p["text"]
            if "functionCall" in p:
                fc = p["functionCall"]
                tc.append({"id": f"c{len(tc)}", "function": {"name": fc["name"],
                          "arguments": json.dumps(fc["args"])}})
        return {"choices": [{"message": {"content": text, "tool_calls": tc if tc else None}}]}
    except Exception as e:
        return {"choices": [{"message": {"content": f"Google error: {str(e)[:80]}"}}]}


def _get_google_model(api_key):
    try:
        r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}", timeout=10)
        if r.status_code == 200:
            models = [m["name"].split("/")[-1] for m in r.json().get("models", [])
                     if "flash" in m["name"].lower() and "image" not in m["name"].lower()
                     and "tts" not in m["name"].lower() and "audio" not in m["name"].lower()
                     and "preview" not in m["name"].lower() and "lite" not in m["name"].lower()]
            # Prefer stable versions (3.6, 3.5, 3.0, 2.5)
            for preferred in ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.0-flash", "gemini-2.5-flash"]:
                if preferred in models:
                    return preferred
            return models[0] if models else "gemini-3.6-flash"
    except Exception:
        pass
    return "gemini-3.6-flash"


def _process_response(response, session_id, messages, tools):
    try:
        if not response or "choices" not in response:
            return "No response received."

        msg = response["choices"][0].get("message", {})
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls")

        if not tool_calls:
            return content or "No response received."

        results = []
        for tc in tool_calls:
            try:
                args = json.loads(tc["function"]["arguments"])
            except Exception:
                args = {}
            args.pop("session_id", None)
            results.append({"id": tc["id"], "result": execute_tool(tc["function"]["name"], args, session_id)})

        # Just format results directly - don't retry (Google requires thoughtSignature)
        return _format_tool_results(results)
    except Exception:
        return "Error processing response."


def _format_tool_results(results):
    """Format tool results into a friendly, conversational response."""
    parts = []
    for r in results:
        res = r["result"]
        if "products" in res:
            products = res["products"]
            if not products:
                parts.append("I couldn't find any products matching your criteria. Could you try a different search?")
            else:
                lines = [f"I found **{len(products)} products** that match your criteria:\n"]
                for p in products[:5]:
                    price = float(p.get('price_usd', 0)) if p.get('price_usd') else 0
                    pid = p.get('id', '')
                    name = p.get('product_name', 'N/A')
                    brand = p.get('brand', 'N/A')
                    specs = p.get('specifications', '')[:80] if p.get('specifications') else ''
                    lines.append(f"**{name}** by {brand}")
                    lines.append(f"  Price: ${price:,.2f}")
                    if specs:
                        lines.append(f"  Specs: {specs}")
                    lines.append(f"  [View Product](/Products?product_id={pid})")
                    lines.append("")
                if len(products) > 5:
                    lines.append(f"I found {len(products) - 5} more products. Would you like me to show you more details on any of these?")
                parts.append("\n".join(lines))
        elif "product_1" in res and "product_2" in res:
            p1, p2 = res["product_1"], res["product_2"]
            price1 = float(p1.get('price_usd', 0)) if p1.get('price_usd') else 0
            price2 = float(p2.get('price_usd', 0)) if p2.get('price_usd') else 0
            parts.append(
                f"Here's a comparison of the two products:\n\n"
                f"**{p1.get('product_name', 'N/A')}**\n"
                f"- Brand: {p1.get('brand', 'N/A')}\n"
                f"- Price: ${price1:,.2f}\n"
                f"- Specs: {p1.get('specifications', 'N/A')[:100]}\n"
                f"- [View Product](/Products?product_id={p1.get('id', '')})\n\n"
                f"**{p2.get('product_name', 'N/A')}**\n"
                f"- Brand: {p2.get('brand', 'N/A')}\n"
                f"- Price: ${price2:,.2f}\n"
                f"- Specs: {p2.get('specifications', 'N/A')[:100]}\n"
                f"- [View Product](/Products?product_id={p2.get('id', '')})\n\n"
                f"Which one would you like to know more about?"
            )
        elif "success" in res:
            parts.append(res.get("message", "Done"))
        elif "error" in res:
            parts.append(res['error'])
    return "\n\n".join(parts) if parts else "I apologize, but I couldn't find what you're looking for. Could you try a different search?"

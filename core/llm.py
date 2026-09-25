"""LLM integration - Google AI Studio + Ollama.

P0 grounding implementation:
- P0.1 force retrieval for product queries (Gemini toolConfig ANY; Ollama nudge)
- P0.2 validate/ground product links against the database before returning
- P0.4 feed tool results back to the model (multi-step agent loop) so answers
  are composed from real data instead of a fixed template
"""

import json
import os
import re
import time
import requests
from decimal import Decimal
from config import get
from core.tools import get_tools
from core.database import (
    search_products, semantic_search as db_semantic,
    get_product_by_name, compare_products, get_product,
    add_to_cart, get_cart,
    save_message, load_history,
    find_by_spec, hybrid_search, get_cart_products, estimate_quote,
    get_profile, upsert_profile, extract_preferences,
)
from core.search import get_recommendations
from core.graph import (
    find_alternatives, find_compatible_products,
    find_products_in_workflow, find_products_by_application,
)

PRODUCT_LINK = get("links", "product")

SYSTEM_PROMPT = get("llm", "system_prompt") or "You are a helpful sales assistant."
OLLAMA_HOST = get("ollama", "host") or "http://localhost:11434"
TEMPERATURE = get("llm", "temperature") or 0.7
MAX_TOKENS = get("llm", "max_tokens") or 2048
MAX_TOOL_STEPS = int(get("llm", "max_tool_steps") or 4)

# Texts that mean "this is an error, not a real answer" (never persisted to history)
ERROR_MARKERS = (
    "Ollama error:", "Google error:", "Google API key not set",
    "Error processing request", "Unknown provider", "No response received",
)


def is_error(text):
    """True if the assistant text is an error rather than a real answer."""
    t = (text or "").strip()
    return bool(t) and any(t.startswith(m) or m in t[:80] for m in ERROR_MARKERS)


def _redact(text):
    """Strip API keys from error strings / logs (never leak secrets)."""
    return re.sub(r"(key=)[A-Za-z0-9_\-\.]+", r"\1***", str(text))

# Heuristic: does the message look like a product/shopping request?
PRODUCT_HINTS = (
    "product", "price", "find", "recommend", "compare", "buy", "order", "cart",
    "need", "looking for", "centrifuge", "pipette", "column", "reagent", "buffer",
    "flask", "beaker", "tips", "culture", "antibody", "kit", "sterile",
    "refrigerated", "filter", "tube", "equipment", "catalog", "stock",
)

MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(/products/([A-Za-z0-9\-]+)\)")
RAW_LINK_RE = re.compile(r"/products/([A-Za-z0-9\-]+)")


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if hasattr(obj, "isoformat"):  # datetime/date
            try:
                return obj.isoformat()
            except Exception:
                pass
        try:
            return list(obj)  # pgvector Vector / numpy / iterables
        except Exception:
            return str(obj)


# ============================================
# TOOL EXECUTION (unchanged behaviour)
# ============================================

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
                use_case=arguments.get("use_case"),
                application=arguments.get("application"),
                limit=arguments.get("limit", 5))
            return {"products": r, "count": len(r)}
        elif tool_name == "find_alternatives":
            r = find_alternatives(arguments["product_id"])
            return {"products": r, "count": len(r), "context": "alternatives"}
        elif tool_name == "find_compatible_products":
            r = find_compatible_products(arguments["product_id"])
            return {"products": r, "count": len(r), "context": "compatible"}
        elif tool_name == "find_products_in_workflow":
            r = find_products_in_workflow(arguments["workflow_name"])
            return {"products": r, "count": len(r), "context": "workflow"}
        elif tool_name == "find_products_by_application":
            r = find_products_by_application(arguments["application"])
            return {"products": r, "count": len(r), "context": "application"}
        elif tool_name == "add_to_cart":
            add_to_cart(session_id, arguments["product_id"], arguments.get("quantity", 1))
            return {"success": True, "message": f"Added {arguments['product_id']} to cart"}
        elif tool_name == "get_cart":
            cart = get_cart(session_id)
            total = sum(item["price_usd"] * item["quantity"] for item in cart)
            return {"items": cart, "total": total, "count": len(cart)}
        elif tool_name == "hybrid_search":
            r = hybrid_search(arguments["query"], limit=arguments.get("limit", 10))
            return {"products": r, "count": len(r), "context": "hybrid"}
        elif tool_name == "find_by_spec":
            r = find_by_spec(category=arguments.get("category"), brand=arguments.get("brand"),
                min_price=arguments.get("min_price"), max_price=arguments.get("max_price"),
                refrigerated=arguments.get("refrigerated"), sterile=arguments.get("sterile"),
                min_rcf=arguments.get("min_rcf"), volume=arguments.get("volume"),
                limit=arguments.get("limit", 10))
            return {"products": r, "count": len(r), "context": "spec"}
        elif tool_name == "build_kit":
            application = arguments.get("application")
            budget = arguments.get("budget")
            products = find_products_in_workflow(application) if application else []
            chosen, total = [], 0.0
            for p in products:
                price = float(p.get("price") or 0)
                if budget is None or total + price <= float(budget):
                    chosen.append(p)
                    total += price
                if len(chosen) >= 8:
                    break
            for p in chosen:
                try:
                    add_to_cart(session_id, p["id"], 1)
                except Exception:
                    pass
            return {"kit": chosen, "count": len(chosen), "total": round(total, 2),
                    "context": "kit"}
        elif tool_name == "check_cart_compatibility":
            items = get_cart_products(session_id)
            ids = [p["id"] for p in items]
            conflicts = []
            for p in items:
                comps = {c["id"] for c in find_compatible_products(p["id"])}
                others = [o for o in ids if o != p["id"]]
                not_comp = [o for o in others if comps and o not in comps]
                if not_comp:
                    conflicts.append({"product": p["id"], "incompatible_with": not_comp})
            return {"items": len(items), "conflicts": conflicts, "context": "compatibility"}
        elif tool_name == "suggest_missing_items":
            items = get_cart_products(session_id)
            have = {p["id"] for p in items}
            apps = {p.get("application") for p in items if p.get("application")}
            missing = []
            for app in apps:
                for p in find_products_in_workflow(app):
                    if p["id"] not in have:
                        missing.append(p)
            return {"products": missing[:5], "count": len(missing), "context": "missing"}
        elif tool_name == "estimate_quote":
            return estimate_quote(session_id)
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


# ============================================
# P0.2 - GROUNDING HELPERS
# ============================================

def _id_exists(product_id):
    try:
        return get_product(product_id) is not None
    except Exception:
        return False


def sanitize_links(text):
    """Keep only product links whose IDs exist in the database."""
    if not text:
        return text

    def md_repl(m):
        label, pid = m.group(1), m.group(2)
        return m.group(0) if _id_exists(pid) else label

    text = MD_LINK_RE.sub(md_repl, text)

    def raw_repl(m):
        return m.group(0) if _id_exists(m.group(1)) else ""

    return RAW_LINK_RE.sub(raw_repl, text)


def _looks_like_product_query(text):
    t = (text or "").lower()
    return any(h in t for h in PRODUCT_HINTS)


HEAVY_KEYS = {"embedding", "created_at", "updated_at"}


def _jsonable(obj):
    """Recursively convert to JSON-serializable values (Decimal, datetime,
    pgvector Vector, numpy, ...) and drop heavy/unneeded keys."""
    if obj is None or isinstance(obj, (str, bool, int, float)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items() if k not in HEAVY_KEYS}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if hasattr(obj, "isoformat"):
        try:
            return obj.isoformat()
        except Exception:
            pass
    if hasattr(obj, "to_list"):
        try:
            return obj.to_list()
        except Exception:
            pass
    try:
        return list(obj)
    except Exception:
        return str(obj)


def _slim(obj, list_cap=10, str_cap=500):
    """Convert to JSON-safe values and trim large tool results."""
    obj = _jsonable(obj)
    if isinstance(obj, dict):
        return {k: _slim(v, list_cap, str_cap) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_slim(v, list_cap, str_cap) for v in obj[:list_cap]]
    if isinstance(obj, str):
        return obj[:str_cap]
    return obj


def _turn_from_ollama(msg):
    tc = []
    for i, t in enumerate(msg.get("tool_calls") or []):
        fn = t.get("function", {}) or {}
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        tc.append({"id": f"c{i}", "name": fn.get("name"), "arguments": args or {}})
    return {"content": msg.get("content") or "", "tool_calls": tc}


def _turn_from_google(parts):
    text, tc = "", []
    for p in parts:
        if "text" in p:
            text += p["text"]
        if "functionCall" in p:
            fc = p["functionCall"]
            tc.append({"id": f"c{len(tc)}", "name": fc.get("name"), "arguments": fc.get("args") or {}})
    # keep raw parts so Gemini thoughtSignatures can be replayed verbatim
    return {"content": text, "tool_calls": tc, "raw_parts": parts}


# ============================================
# PROVIDER WIRE FORMAT CONVERSION
# ============================================

def _to_ollama_messages(messages):
    out = []
    for m in messages:
        role = m.get("role")
        if role == "assistant":
            msg = {"role": "assistant", "content": m.get("content", "")}
            if m.get("tool_calls"):
                msg["tool_calls"] = [
                    {"function": {"name": tc.get("name"), "arguments": tc.get("arguments") or {}}}
                    for tc in m["tool_calls"]
                ]
            out.append(msg)
        elif role == "tool":
            content = m.get("content")
            out.append({"role": "tool",
                        "content": content if isinstance(content, str)
                        else json.dumps(content, cls=DecimalEncoder)})
        else:
            out.append({"role": role, "content": m.get("content", "")})
    return out


def _to_google_contents(messages):
    contents, i, n = [], 0, len(messages)
    while i < n:
        m = messages[i]
        role = m.get("role")
        if role == "system":
            contents.append({"role": "user", "parts": [{"text": m.get("content", "")}]})
            contents.append({"role": "model", "parts": [{"text": "I understand."}]})
        elif role == "assistant":
            if m.get("_google_parts"):
                parts = m["_google_parts"]
            else:
                parts = []
                if m.get("content"):
                    parts.append({"text": m["content"]})
                for tc in m.get("tool_calls") or []:
                    parts.append({"functionCall": {"name": tc.get("name"),
                                                   "args": tc.get("arguments") or {}}})
            contents.append({"role": "model", "parts": parts})
        elif role == "tool":
            parts = []
            while i < n and messages[i].get("role") == "tool":
                tm = messages[i]
                content = _jsonable(tm.get("content"))
                if not isinstance(content, dict):
                    content = {"result": content}
                parts.append({"functionResponse": {"name": tm.get("name"), "response": content}})
                i += 1
            contents.append({"role": "user", "parts": parts})
            continue
        else:
            contents.append({"role": "user", "parts": [{"text": m.get("content", "")}]})
        i += 1
    return contents


# ============================================
# PROVIDER CALLS (normalized turns)
# ============================================

def _to_openai_messages(messages):
    """Convert normalized messages to OpenAI chat-completions format."""
    out = []
    for m in messages:
        role = m.get("role")
        if role == "assistant":
            msg = {"role": "assistant", "content": m.get("content", "")}
            if m.get("tool_calls"):
                msg["tool_calls"] = [{
                    "id": tc.get("id") or f"call_{i}",
                    "type": "function",
                    "function": {"name": tc.get("name"),
                                 "arguments": json.dumps(tc.get("arguments") or {},
                                                         cls=DecimalEncoder)},
                } for i, tc in enumerate(m["tool_calls"])]
            out.append(msg)
        elif role == "tool":
            content = m.get("content")
            out.append({"role": "tool", "tool_call_id": m.get("tool_call_id"),
                        "content": content if isinstance(content, str)
                        else json.dumps(content, cls=DecimalEncoder)})
        else:
            out.append({"role": role, "content": m.get("content", "")})
    return out


def _turn_from_openai_msg(msg):
    tc = []
    for i, t in enumerate(msg.get("tool_calls") or []):
        fn = t.get("function", {}) or {}
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        tc.append({"id": t.get("id") or f"c{i}", "name": fn.get("name"), "arguments": args or {}})
    return {"content": msg.get("content") or "", "tool_calls": tc}


def _call_openai_compat(base_url, api_key, model, messages, tools,
                        force_tools=False, headers=None, session_id=None, label="provider"):
    """Call any OpenAI-compatible /chat/completions endpoint (OpenCode Go, OpenAI, ...)."""
    try:
        url = (base_url or "").rstrip("/") + "/chat/completions"
        hdrs = {"Content-Type": "application/json"}
        if api_key:
            hdrs["Authorization"] = f"Bearer {api_key}"
        if headers:
            hdrs.update({str(k): str(v) for k, v in headers.items()})
        if session_id:
            hdrs.setdefault("x-opencode-session", str(session_id))

        payload = {"model": model, "messages": _to_openai_messages(messages), "stream": False}
        if tools:
            payload["tools"] = tools
            if force_tools:
                payload["tool_choice"] = "required"

        r = requests.post(url, json=payload, headers=hdrs, timeout=120)
        r.raise_for_status()
        data = r.json()
        msg = (data.get("choices") or [{}])[0].get("message", {}) or {}
        return _turn_from_openai_msg(msg)
    except Exception as e:
        return {"content": f"{label} error: {_redact(e)[:120]}", "tool_calls": [], "error": True}


def _call_ollama(messages, tools, model, force_tools=False):
    try:
        payload_messages = _to_ollama_messages(messages)
        if force_tools:
            payload_messages = payload_messages + [
                {"role": "system", "content": "You must call a tool before answering."}
            ]
        payload = {"model": model, "messages": payload_messages, "stream": False}
        if tools:
            payload["tools"] = tools
        r = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        msg = r.json().get("message", {}) or {}
        return _turn_from_ollama(msg)
    except Exception as e:
        return {"content": f"Ollama error: {str(e)[:120]}", "tool_calls": [], "error": True}


def _call_google(messages, tools, api_key, model, force_tools=False):
    if not api_key:
        return {"content": "Google API key not set", "tool_calls": [], "error": True}

    payload = {"contents": _to_google_contents(messages)}

    gt = []
    if tools:
        for t in tools:
            gt.append({"function_declarations": [{
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "parameters": t["function"]["parameters"],
            }]})
    if gt:
        payload["tools"] = gt
        if force_tools:
            payload["toolConfig"] = {"functionCallingConfig": {"mode": "ANY"}}

    # Explicit model -> use only it; "auto" -> discover flash models dynamically.
    if model and model != "auto":
        candidates = [model]
    else:
        candidates = _google_candidates(api_key)
        if not candidates:
            return {"content": "Google error: could not discover models (set google.model in config.yaml)",
                    "tool_calls": [], "error": True}

    last_err = None
    for m in candidates:
        for attempt in range(2):  # initial try + 1 retry
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}",
                    json=payload, timeout=60)
                if r.status_code == 429:
                    # Rate limit is per-key -> retrying/other models won't help; fail fast.
                    return {"content": "Google error: rate limited (429) - free-tier quota exceeded; "
                                       "wait a bit, use another key/project, or switch provider",
                            "tool_calls": [], "error": True}
                if r.status_code in (500, 502, 503, 504) and attempt == 0:
                    time.sleep(2)  # transient overload -> one retry
                    continue
                r.raise_for_status()
                parts = r.json()["candidates"][0].get("content", {}).get("parts", [])
                return _turn_from_google(parts)
            except requests.HTTPError as e:
                last_err = e
                print(f"[google] model {m} failed: {_redact(e)}")
                break  # model-level failure -> try the next candidate
            except Exception as e:
                last_err = e
                print(f"[google] model {m} error: {_redact(e)}")
                break
    tried = ", ".join(candidates)
    return {"content": f"Google error: no model answered (tried {tried}) - {_redact(last_err)[:100]}",
            "tool_calls": [], "error": True}


def _call_provider(provider, messages, tools, force_tools=False, session_id=None):
    if provider == "ollama":
        model = get("ollama", "model") or "qwen2.5:3b"
        return _call_ollama(messages, tools, model, force_tools)
    if provider == "google":
        api_key = get("google", "api_key")
        model = get("google", "model") or "auto"
        return _call_google(messages, tools, api_key, model, force_tools)
    # Any configured OpenAI-compatible provider (e.g. opencode_go, openai, openrouter)
    cfg = (get("providers") or {}).get(provider) or {}
    if cfg.get("type") == "openai_compatible":
        return _call_openai_compat(
            base_url=cfg.get("base_url"), api_key=cfg.get("api_key"), model=cfg.get("model"),
            messages=messages, tools=tools, force_tools=force_tools,
            headers=cfg.get("headers"), session_id=session_id, label=provider)
    raise ValueError(f"Unknown provider: {provider}")


_GOOGLE_VERSION_RE = re.compile(r"gemini-(\d+)(?:\.(\d+))?-flash")
_GOOGLE_EXCLUDE = ("image", "tts", "audio", "preview", "lite", "thinking",
                   "embedding", "aqa", "vision", "exp")


def _model_version(name):
    """Sort key: numeric version parsed from the id (no hardcoded versions)."""
    m = _GOOGLE_VERSION_RE.search(name or "")
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)


def _is_chat_flash(name):
    n = (name or "").lower()
    return "flash" in n and not any(x in n for x in _GOOGLE_EXCLUDE)


def _google_candidates(api_key):
    """Dynamically discover Google flash chat models (no hardcoded versions).

    Order/size are configurable: google.model_order = newest|oldest,
    google.model_count = N.
    """
    order = (get("google", "model_order") or "newest").lower()
    try:
        limit = int(get("google", "model_count") or 3)
    except Exception:
        limit = 3

    try:
        r = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}", timeout=10)
        if r.status_code == 200:
            names = [m["name"].split("/")[-1] for m in r.json().get("models", [])]
            flash = [n for n in names if _is_chat_flash(n)]
            flash.sort(key=_model_version, reverse=(order != "oldest"))
            if flash:
                return flash[:limit]
    except Exception:
        pass
    return []


# ============================================
# P0.1 + P0.4 - AGENT LOOP
# ============================================

def _run_agent(messages, tools, provider, session_id, max_steps=None):
    """Multi-step loop: model may call tools; results are fed back so the final
    answer is composed from real DB data. Forces retrieval for product queries."""
    max_steps = max_steps or MAX_TOOL_STEPS
    user_query = messages[-1].get("content", "") if messages else ""
    needs_grounding = _looks_like_product_query(user_query)

    last_results = []
    last_text = ""

    for step in range(max_steps):
        force = (step == 0 and needs_grounding)
        turn = _call_provider(provider, messages, tools, force_tools=force, session_id=session_id)
        last_text = turn.get("content") or ""
        if turn.get("error"):
            return last_text, True
        tool_calls = turn.get("tool_calls") or []

        if not tool_calls:
            return last_text, False

        assistant_msg = {"role": "assistant", "content": turn.get("content", ""),
                         "tool_calls": tool_calls}
        if turn.get("raw_parts"):
            assistant_msg["_google_parts"] = turn["raw_parts"]
        messages.append(assistant_msg)

        for tc in tool_calls:
            args = dict(tc.get("arguments") or {})
            args.pop("session_id", None)
            result = _slim(execute_tool(tc.get("name"), args, session_id))
            last_results.append({"id": tc.get("id"), "result": result})
            messages.append({"role": "tool", "tool_call_id": tc.get("id"),
                             "name": tc.get("name"), "content": result})

    # Reached max steps -> ask for a final answer without tools; else fall back.
    try:
        final = _call_provider(provider, messages, [], force_tools=False, session_id=session_id)
        if final.get("content") and not final.get("error"):
            return final["content"], False
    except Exception:
        pass
    return _format_tool_results(last_results), False


def get_llm_response(session_id, user_message):
    # NOTE: user message is saved by the caller (nicegui_app.send_msg),
    # so we only save the assistant response.

    # P1.3 - remember user preferences (budget/applications) for personalization
    try:
        prefs = extract_preferences(user_message)
        if prefs:
            upsert_profile(session_id, **prefs)
    except Exception:
        pass

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    try:
        profile = get_profile(session_id)
    except Exception:
        profile = {}
    if profile:
        messages.append({"role": "system",
                         "content": "Known user preferences (use when relevant): " +
                                    json.dumps(profile, cls=DecimalEncoder)})
    messages += build_context(session_id) + [{"role": "user", "content": user_message}]

    tools = get_tools()
    provider = os.getenv("LLM_PROVIDER") or get("llm", "provider") or "ollama"

    configured = get("providers") or {}
    if provider not in ("ollama", "google") and provider not in configured:
        return f"Unknown provider: {provider}"

    try:
        response, is_err = _run_agent(messages, tools, provider, session_id)
        response = sanitize_links(response or "")
        if not is_err and not response:
            response, is_err = "No response received. Please try again.", True
        # Do not persist errors (they would linger in history as stale failures).
        if not is_err and response:
            try:
                save_message(session_id, "assistant", response)
            except Exception:
                pass
        else:
            print(f"[llm] provider={provider} error (not saved): {_redact(response)[:200]}")
        return response
    except Exception:
        return "Error processing request. Please try again."


def _format_tool_results(results):
    """Fallback formatter used only if the model cannot compose an answer."""
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
                    lines.append(f"  [View Product]({PRODUCT_LINK.format(product_id=pid)})")
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
                f"- [View Product]({PRODUCT_LINK.format(product_id=p1.get('id', ''))})\n\n"
                f"**{p2.get('product_name', 'N/A')}**\n"
                f"- Brand: {p2.get('brand', 'N/A')}\n"
                f"- Price: ${price2:,.2f}\n"
                f"- Specs: {p2.get('specifications', 'N/A')[:100]}\n"
                f"- [View Product]({PRODUCT_LINK.format(product_id=p2.get('id', ''))})\n\n"
                f"Which one would you like to know more about?"
            )
        elif "success" in res:
            parts.append(res.get("message", "Done"))
        elif "error" in res:
            parts.append(res['error'])
    return "\n\n".join(parts) if parts else "I apologize, but I couldn't find what you're looking for. Could you try a different search?"

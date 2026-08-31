"""AIFinder - NiceGUI Frontend."""

import sys
import os
import uuid
import ssl
import asyncio
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nicegui import ui, app
from fastapi import Request
from fastapi.responses import JSONResponse
from core.llm import get_llm_response
from core.database import (
    search_products, get_product, add_to_cart as db_add_to_cart,
    get_cart as db_get_cart, update_cart_item, remove_from_cart,
    clear_cart, get_cart_total, create_order,
    save_message, load_history, cleanup_expired_chat_history,
)
from config import get

HERO_IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "main_page.png")
CLOUDINARY_BASE = get("cloudinary", "base_url")
IMAGE_EXT = get("cloudinary", "image_ext")

BG = '#D3D3D3'
TEXT = '#555555'
ACCENT = '#444444'
HISTORY_LIMIT = get("chat", "history_limit") or 50

# Issue 4: in-memory chat history cache (per session)
_history_cache = {}


def get_session_id():
    """Unique session per browser (persisted server-side via session cookie)."""
    import uuid
    if 'sid' not in app.storage.user:
        app.storage.user['sid'] = str(uuid.uuid4())
    return app.storage.user['sid']


def cached_load_history(session_id, limit=None):
    """Issue 4: Load history from memory cache, fallback to PostgreSQL."""
    limit = limit or HISTORY_LIMIT
    if session_id in _history_cache:
        return _history_cache[session_id]
    history = load_history(session_id, limit=limit)
    _history_cache[session_id] = history
    return history


def invalidate_history_cache(session_id):
    """Issue 4: Drop cache entry after a new message is saved."""
    _history_cache.pop(session_id, None)


def md_to_html(text):
    """Pass through markdown for ui.markdown renderer."""
    return text


def scroll_chat_to_bottom():
    """Scroll the chat messages container to the last message."""
    ui.run_javascript('''
        const el = document.getElementById("chat-msgs");
        if (el) el.scrollTop = el.scrollHeight;
    ''')


def get_product_image(pid):
    return f"{CLOUDINARY_BASE}/{pid}{IMAGE_EXT}"


# ── TEMPLATE ────────────────────────────────────────────────────────
def page_template(left_fn, extra_css=''):
    ui.add_head_html(f'''<style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        html, body, .nicegui-content {{ background:{BG}; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        .q-splitter__before, .q-splitter__after {{ background:{BG} !important; border: none !important; }}
        .chat-in {{
            width: 80%; background:white; border:1px solid #ccc; border-radius:12px;
            padding:10px 14px; font-size:14px; color:{TEXT}; outline:none; min-height:42px; box-sizing:border-box;
        }}
        .chat-in::placeholder {{ color:{TEXT}; opacity:0.7; }}
        .chat-in:focus {{ border-color:#999; }}
        .q-btn.send-btn, .q-btn.send-btn:hover, .q-btn.send-btn::before {{
            background: {ACCENT} !important;
            color: white !important;
        }}
        .send-btn {{
            width:42px; height:42px; background:{ACCENT}; color:white; border:none;
            border-radius:50%; cursor:pointer; font-size:16px; flex-shrink:0;
        }}
        a.vl {{ background:{ACCENT} !important; color:white !important; padding:0 16px !important; border-radius:6px !important;
                text-decoration:none !important; font-size:12px !important; display:inline-flex !important; align-items:center !important; justify-content:center !important; min-width:70px !important; height:32px !important; box-sizing:border-box !important; }}
        .q-btn.ab, .q-btn.ab:hover, .q-btn.ab::before {{
            background: {ACCENT} !important; color: white !important; border-radius: 6px !important;
            font-size: 12px !important; height: 32px !important; min-width: 70px !important;
            padding: 0 16px !important; text-transform: none !important; box-sizing: border-box !important;
        }}
        {extra_css}
    </style>''')

    # Header
    with ui.row().classes('w-full justify-end items-center gap-5').style(f'padding:10px 24px; background:{BG};'):
        ui.link('Home', '/').style(f'color:{TEXT}; text-decoration:none; font-size:15px; font-weight:600;')
        ui.link('Products', '/products').style(f'color:{TEXT}; text-decoration:none; font-size:15px; font-weight:600;')
        ui.link('Cart', '/cart').style(f'color:{TEXT}; text-decoration:none; font-size:15px; font-weight:600;')

    # Two-column layout using NiceGUI splitter
    splitter = ui.splitter(horizontal=False).classes('w-full').style('height: calc(100vh - 80px);')

    # Left panel (65%)
    with splitter.before:
        with ui.column().style('width:100%;height:100%;overflow-y:auto;padding:0 12px;'):
            left_fn()

    # Right panel (35%) - Chatbot
    with splitter.after:
        with ui.column().style(f'width:100%;height:100%;background:{BG};display:flex;flex-direction:column;padding:0;'):
            ui.html(f'<div style="padding:16px 16px 8px;"><div style="font-weight:600;font-size:18px;color:{TEXT};">AIFinder</div><div style="font-size:13px;color:{TEXT};margin-top:2px;">AI chatbot to help you find products</div></div>')
            msgs = ui.column().style('flex:1;overflow-y:auto;padding:0 12px;').props('id="chat-msgs"')
            # Welcome message
            with msgs:
                with ui.row().classes('items-start gap-2 mb-3').style('data-welcome:1;'):
                    ui.avatar(icon='smart_toy', color=ACCENT, text_color='white', size='sm')
                    ui.html(f'<div style="background:white;padding:10px 14px;border-radius:12px;color:{TEXT};font-size:14px;line-height:1.4;max-width:80%;">Hello! I\'m AIFinder, your lab equipment assistant. How can I help you today?</div>')
            with ui.row().classes('w-full items-center').style('padding:10px 12px;'):
                inp = ui.input(placeholder='Type your message here...').classes('chat-in')
                send = ui.button(icon='send').classes('send-btn')

    # Chat logic
    async def send_msg(e=None):
        text = inp.value.strip() if inp.value else ''
        if not text:
            return
        page_alive = True
        try:
            inp.value = ''
            inp.disable()
            send.disable()
        except Exception:
            page_alive = False

        # Show user message
        if page_alive:
            try:
                with msgs:
                    with ui.row().classes('items-start gap-2 mb-3 justify-end'):
                        with ui.column().classes('max-w-[80%]'):
                            ui.label(text).style(f'background:{ACCENT};padding:10px 14px;border-radius:12px;color:white;font-size:14px;line-height:1.4;text-align:right;')
                        ui.avatar(icon='person', color='#888', text_color='white', size='sm')
            except Exception:
                page_alive = False
        # Show thinking animation
        thinking = None
        if page_alive:
            try:
                with msgs:
                    with ui.row().classes('items-start gap-2 mb-3'):
                        ui.avatar(icon='smart_toy', color=ACCENT, text_color='white', size='sm')
                        thinking = ui.label('thinking...').style(f'background:white;padding:10px 14px;border-radius:12px;color:{TEXT};font-size:14px;')
                # Case 3: focus on thinking message
                scroll_chat_to_bottom()
            except Exception:
                page_alive = False

        # Call LLM (always runs, even if page is gone)
        try:
            sid = get_session_id()
            # Persist the question synchronously so it survives page navigation
            save_message(sid, "user", text)
            # Drop stale cache so a new page reads fresh history (with the question)
            invalidate_history_cache(sid)
            # get_llm_response() now saves only the assistant message
            response = await asyncio.to_thread(get_llm_response, sid, text)
            response = md_to_html(response)
            # Invalidate cache so next load reads fresh history (with the answer)
            invalidate_history_cache(sid)
        except Exception as ex:
            response = f"Error: {str(ex)[:100]}"

        # Update UI if page is still alive
        if page_alive:
            try:
                if thinking:
                    thinking.delete()
            except Exception:
                pass
            try:
                with msgs:
                    with ui.row().classes('items-start gap-2 mb-3'):
                        ui.avatar(icon='smart_toy', color=ACCENT, text_color='white', size='sm')
                        ui.markdown(response).style(f'background:white;padding:10px 14px;border-radius:12px;color:{TEXT};font-size:14px;line-height:1.4;max-width:80%;')
                # Case 4: scroll to bot response
                scroll_chat_to_bottom()
            except Exception:
                pass
            try:
                inp.enable()
                send.enable()
                inp.focus()
            except Exception:
                pass

    send.on_click(send_msg)
    inp.on('keydown.enter', send_msg)

    # Load history only once per page session
    history_key = f'_history_loaded_{id(msgs)}'
    if history_key not in dir(ui.context):
        history = cached_load_history(get_session_id())
        if history:
            try:
                welcome_row = msgs.element(0)
                if welcome_row:
                    welcome_row.delete()
            except Exception:
                pass
            for m in history:
                is_user = m['role'] == 'user'
                bg = ACCENT if is_user else 'white'
                color = 'white' if is_user else TEXT
                avatar_bg = '#888' if is_user else ACCENT
                avatar = 'person' if is_user else 'smart_toy'
                flex_dir = 'justify-end' if is_user else ''
                with msgs:
                    with ui.row().classes(f'items-start gap-2 mb-3 {flex_dir}'):
                        ui.avatar(icon=avatar, color=avatar_bg, text_color='white', size='sm')
                        content = m['content']
                        if is_user:
                            ui.label(content).style(f'background:{bg};padding:10px 14px;border-radius:12px;color:{color};font-size:14px;line-height:1.4;max-width:80%;')
                        else:
                            ui.markdown(content).style(f'background:white;padding:10px 14px;border-radius:12px;color:{TEXT};font-size:14px;line-height:1.4;max-width:80%;')
            # Case 5: scroll to last message on open / navigation
            scroll_chat_to_bottom()
        setattr(ui.context, history_key, True)

        # Issue 3: if last message is from user (no bot response yet), show thinking and poll
        if history and history[-1]['role'] == 'user':
            sid = get_session_id()
            thinking = None
            try:
                with msgs:
                    with ui.row().classes('items-start gap-2 mb-3'):
                        ui.avatar(icon='smart_toy', color=ACCENT, text_color='white', size='sm')
                        thinking = ui.label('thinking...').style(f'background:white;padding:10px 14px;border-radius:12px;color:{TEXT};font-size:14px;')
                # Case 6: scroll to pending thinking message
                scroll_chat_to_bottom()
            except Exception:
                thinking = None

            def poll_for_response():
                nonlocal thinking
                try:
                    fresh = load_history(sid, limit=2)
                    if fresh and fresh[-1]['role'] == 'assistant':
                        if thinking is not None:
                            try:
                                thinking.delete()
                            except Exception:
                                pass
                        # No need for further polling
                        return fresh
                except Exception:
                    pass
                return None

            timer = ui.timer(2.0, lambda: None)
            def check():
                nonlocal thinking
                fresh = poll_for_response()
                if fresh is not None:
                    timer.cancel()
                    # Case 7: append the pending bot response in place, no page reload
                    try:
                        content = fresh[-1]['content']
                        with msgs:
                            with ui.row().classes('items-start gap-2 mb-3'):
                                ui.avatar(icon='smart_toy', color=ACCENT, text_color='white', size='sm')
                                ui.markdown(content).style(f'background:white;padding:10px 14px;border-radius:12px;color:{TEXT};font-size:14px;line-height:1.4;max-width:80%;')
                        scroll_chat_to_bottom()
                    except Exception:
                        pass
            timer = ui.timer(2.0, check)
            setattr(ui.context, history_key, True)

    # Footer
    ui.html(f'<div style="text-align:center;padding:10px 0;font-size:11px;color:{TEXT};background:{BG};position:fixed;bottom:0;width:100%;z-index:10;">&copy; 2026 AIFinder. All rights reserved.</div>')


# ── PAGE CONTENT ────────────────────────────────────────────────────
def home_content():
    ui.image(HERO_IMG).style('width:100%;height:calc(100vh - 100px);object-fit:cover;border-radius:12px;')


def products_content():
    ui.label('Product Catalog').style(f'font-size:24px;font-weight:700;color:{TEXT};margin-bottom:8px;')

    all_products = search_products(limit=200)
    per_page = 12
    total = len(all_products)
    total_pages = max(1, (total + per_page - 1) // per_page)

    state = {'page': 0}

    container = ui.column()

    def render(e=None):
        container.clear()
        p = state['page']
        start = p * per_page
        products = all_products[start:start + per_page]
        with container:
            ui.label(f'{p + 1} / {total_pages}').style(f'color:{TEXT};margin-bottom:8px;')
            if not products:
                ui.label('No products found.').style(f'color:{TEXT};padding:20px;')
                return
            for i in range(0, len(products), 4):
                with ui.row().classes('w-full gap-3').style('margin-bottom:12px;'):
                    for j in range(4):
                        if i + j < len(products):
                            pr = products[i + j]
                            with ui.card().style('flex:1;background:white;border-radius:8px;padding:8px;border:none;'):
                                ui.image(get_product_image(pr['id'])).style('width:100%;height:100px;object-fit:contain;border-radius:6px;')
                                ui.label(pr['product_name']).style(f'font-weight:600;font-size:12px;color:{TEXT};margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;')
                                ui.label(f"${pr['price_usd']:,.2f}").style(f'font-weight:700;font-size:13px;color:{TEXT};')
                                with ui.row().classes('w-full gap-1'):
                                    ui.link('view', f'/products/{pr["id"]}').classes('vl')
                                    def add_h(pid=pr['id'], e=None):
                                        db_add_to_cart(get_session_id(), pid, 1)
                                        ui.notify(f'Added {pid} to cart!', type='positive')
                                    ui.button('add', on_click=add_h).classes('ab')

    def go_prev(e=None):
        if state['page'] > 0:
            state['page'] -= 1
            render()

    def go_next(e=None):
        if state['page'] < total_pages - 1:
            state['page'] += 1
            render()

    with ui.row().classes('w-full justify-center items-center gap-4').style('margin-top:12px;'):
        ui.button(icon='chevron_left', on_click=go_prev).style(f'background:{ACCENT};color:white;border-radius:50%;')
        page_label = ui.label(f'{state["page"] + 1} / {total_pages}').style(f'color:{TEXT};')
        ui.button(icon='chevron_right', on_click=go_next).style(f'background:{ACCENT};color:white;border-radius:50%;')

    render()


def cart_content():
    ui.label('Shopping Cart').style(f'font-size:24px;font-weight:700;color:{TEXT};margin-bottom:8px;')
    cart = db_get_cart(get_session_id())
    if not cart:
        ui.label('Your cart is empty.').style(f'color:{TEXT};padding:20px;')
        ui.link('Browse Products', '/products').style(f'color:{TEXT};text-decoration:underline;')
        return
    for item in cart:
        with ui.row().classes('w-full items-center gap-4').style('background:white;border-radius:8px;padding:12px;margin-bottom:8px;'):
            ui.image(get_product_image(item['product_id'])).style('width:60px;height:60px;object-fit:contain;border-radius:6px;')
            with ui.column().style('flex:2;'):
                ui.label(item['product_name']).style(f'font-weight:600;color:{TEXT};')
                ui.label(f"{item['brand']} | {item['product_id']}").style(f'font-size:12px;color:{TEXT};')
            ui.label(f"${item['price_usd']:,.2f}").style(f'font-weight:600;color:{TEXT};')
            qty = ui.number(value=item['quantity'], min=1).style('width:80px;')
            def update_h(cid=item['id'], qi=qty, e=None):
                update_cart_item(cid, int(qi.value))
            qty.on('value-change', update_h)
            def remove_h(cid=item['id'], e=None):
                remove_from_cart(cid)
                ui.navigate.reload()
            ui.button(icon='delete', on_click=remove_h).style('color:red;')
    total = get_cart_total(get_session_id())
    ui.label(f'Total: ${total:,.2f}').style(f'font-size:20px;font-weight:700;color:{TEXT};margin-top:12px;')
    with ui.row().classes('w-full gap-4').style('margin-top:12px;'):
        def clear_h(e=None):
            clear_cart(get_session_id())
            ui.navigate.reload()
        ui.button('clear', on_click=clear_h).classes('ab')
        def checkout():
            oid = create_order(get_session_id())
            if oid:
                ui.notify(f'Order #{oid} placed!', type='positive')
        ui.button('checkout', on_click=checkout).classes('ab')


# ── PAGES ───────────────────────────────────────────────────────────
@ui.page('/')
def index():
    page_template(home_content)
    # Daily cleanup (runs while app is serving)
    ui.timer(86400, _run_cleanup)

@ui.page('/products')
def products_page():
    page_template(products_content)

@ui.page('/products/{product_id}')
def product_detail_page(product_id):
    page_template(lambda: _product_detail_content(product_id))


def _product_detail_content(product_id):
    product = get_product(product_id)
    if not product:
        ui.label('Product not found').style(f'color:{TEXT};padding:40px;')
        return
    ui.link('← Back to Products', '/products').style(f'color:{TEXT};text-decoration:none;font-size:14px;')
    ui.image(get_product_image(product['id'])).style('width:100%;max-width:250px;border-radius:8px;margin:16px 0;')
    ui.label(product['product_name']).style(f'font-size:24px;font-weight:700;color:{TEXT};')
    ui.label(f"${product['price_usd']:,.2f}").style(f'font-size:20px;font-weight:700;color:{TEXT};margin-top:8px;')
    ui.label(product.get('specifications', '')).style(f'color:{TEXT};font-size:14px;white-space:pre-wrap;margin-top:12px;')
    with ui.row().classes('w-full gap-4 items-center').style('margin-top:16px;'):
        qty = ui.number(value=1, min=1).style('width:100px;')
        def add_h(e=None):
            db_add_to_cart(get_session_id(), product_id, int(qty.value))
            ui.notify(f'Added {int(qty.value)}x to cart!', type='positive')
        ui.button('add', on_click=add_h).classes('ab')

@ui.page('/cart')
def cart_page():
    page_template(cart_content)


# ── API ─────────────────────────────────────────────────────────────
app.add_static_files('/static', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))
FAVICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'microscope.png')

@app.post('/api/chat')
async def chat_api(request: Request):
    data = await request.json()
    message = data.get('message', '')
    session_id = data.get('session_id') or get_session_id()
    try:
        response = await asyncio.to_thread(get_llm_response, session_id, message)
        response = md_to_html(response)
        invalidate_history_cache(session_id)
    except Exception as e:
        response = f"Error: {str(e)[:100]}"
    return JSONResponse({'response': response})


# ── DB CLEANUP ──────────────────────────────────────────────────────
def _run_cleanup():
    """Run expired chat history / cart cleanup."""
    try:
        cleanup_expired_chat_history()
    except Exception as e:
        print(f"[cleanup] error: {e}")


# Run once on startup
@app.on_startup
async def _startup_cleanup():
    await asyncio.to_thread(_run_cleanup)

ui.run(host='0.0.0.0', port=8080, title='AIFinder', reload=False, favicon=FAVICON,
       storage_secret=get("chat", "storage_secret") or "aifinder_secret_key")

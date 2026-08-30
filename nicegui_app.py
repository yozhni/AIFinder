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
    search_products, get_categories, get_brands, get_price_range,
    get_product, add_to_cart as db_add_to_cart, get_cart as db_get_cart,
    update_cart_item, remove_from_cart, clear_cart, get_cart_total, create_order,
)
from config import get

HERO_IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "main_page.png")
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
PLACEHOLDER_IMG = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), get("paths", "placeholder_img")))
CLOUDINARY_BASE = get("cloudinary", "base_url")
IMAGE_EXT = get("cloudinary", "image_ext")

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

BG = '#D3D3D3'
TEXT = '#555555'
ACCENT = '#444444'


def md_to_html(text):
    """Simple markdown to HTML converter."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank" style="color:#0066cc;">\1</a>', text)
    text = text.replace('\n', '<br>')
    return text


def get_product_image(product_id):
    cloudinary_url = f"{CLOUDINARY_BASE}/{product_id}{IMAGE_EXT}"
    return cloudinary_url


COMMON_CSS = f'''
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body, .nicegui-content {{ background: {BG}; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
</style>
'''


def page_header():
    """Common header with nav."""
    nav_bar()


def page_footer():
    """Common footer with copyright."""
    ui.html(f'''
    <div style="text-align:center; padding:10px 0; font-size:11px; color:{TEXT};
                background:{BG}; position:fixed; bottom:0; width:100%; z-index:10;">
        &copy; 2026 AIFinder. All rights reserved.
    </div>
    ''')


def nav_bar():
    with ui.row().classes('w-full justify-end items-center gap-5').style(
        f'padding: 10px 24px; background: {BG};'
    ):
        ui.link('Home', '/').style(f'color: {TEXT}; text-decoration: none; font-size: 15px; font-weight: 600;')
        ui.link('Products', '/products').style(f'color: {TEXT}; text-decoration: none; font-size: 15px; font-weight: 600;')
        ui.link('Cart', '/cart').style(f'color: {TEXT}; text-decoration: none; font-size: 15px; font-weight: 600;')


def get_session_id():
    """Get or create a consistent session ID stored in localStorage."""
    import hashlib
    # Use a fixed session ID for all pages (stored in browser localStorage via JS)
    return "aifinder_session"


def chatbot_js():
    """Shared chatbot JavaScript for all pages."""
    session_id = get_session_id()
    ui.add_head_html(f'''
    <style>
        .chat-input {{
            width: 80%;
            background: white;
            border: 1px solid #ccc;
            border-radius: 12px;
            padding: 10px 14px;
            font-size: 14px;
            color: {TEXT};
            outline: none;
            line-height: 1.4;
            box-sizing: border-box;
            min-height: 46px;
        }}
        .chat-input::placeholder {{
            color: {TEXT};
            font-size: 14px;
            opacity: 0.7;
        }}
        .chat-input:focus {{ border-color: #999; }}
        .send-btn {{
            width: 42px; height: 42px;
            background: #888; color: white;
            border: none; border-radius: 50%;
            cursor: pointer; font-size: 16px;
            display: flex; align-items: center; justify-content: center;
            flex-shrink: 0;
        }}
    </style>
    ''')
    ui.run_javascript(f'''
    window._sid = "{session_id}";
    function addMsg(role, text, isHtml) {{
        const chatMsgs = document.getElementById("chat-messages");
        if (!chatMsgs) return;
        const isUser = role === "user";
        const bg = isUser ? "{ACCENT}" : "white";
        const color = isUser ? "white" : "{TEXT}";
        const avatarBg = isUser ? "#888" : "{ACCENT}";
        const avatar = isUser ? "👤" : "🤖";
        const flexDir = isUser ? "row-reverse" : "row";
        const html = `
            <div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:12px; flex-direction:${{flexDir}};">
                <div style="width:32px;height:32px;border-radius:50%;background:${{avatarBg}};color:white;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;">${{avatar}}</div>
                <div style="background:${{bg}}; padding:10px 14px; border-radius:12px; color:${{color}};
                            font-size:14px; line-height:1.4; max-width:80%;">${{isHtml ? text : text}}</div>
            </div>`;
        chatMsgs.insertAdjacentHTML("beforeend", html);
        chatMsgs.scrollTop = chatMsgs.scrollHeight;
    }}
    function saveMsg(role, text, isHtml) {{
        const history = JSON.parse(localStorage.getItem("chat_history") || "[]");
        history.push({{ role, text, isHtml }});
        localStorage.setItem("chat_history", JSON.stringify(history));
    }}
    function initChat() {{
        const chatMsgs = document.getElementById("chat-messages");
        if (!chatMsgs) return;
        const saved = localStorage.getItem("chat_history");
        if (saved) {{
            try {{
                const history = JSON.parse(saved);
                history.forEach(m => addMsg(m.role, m.text, m.isHtml || false));
            }} catch(e) {{}}
        }} else {{
            addMsg("assistant", "Hello! I'm AIFinder, your lab equipment assistant. How can I help you today?", false);
            saveMsg("assistant", "Hello! I'm AIFinder, your lab equipment assistant. How can I help you today?", false);
        }}
    }}
    function showLoading() {{
        const chatMsgs = document.getElementById("chat-messages");
        if (!chatMsgs) return;
        const html = `
            <div id="loading" style="display:flex; align-items:flex-start; gap:8px; margin-bottom:12px;">
                <div style="width:32px;height:32px;border-radius:50%;background:{ACCENT};color:white;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;">🤖</div>
                <div style="background:white; padding:10px 14px; border-radius:12px; color:{TEXT}; font-size:14px;">thinking...</div>
            </div>`;
        chatMsgs.insertAdjacentHTML("beforeend", html);
        chatMsgs.scrollTop = chatMsgs.scrollHeight;
    }}
    function removeLoading() {{
        const el = document.getElementById("loading");
        if (el) el.remove();
    }}
    async function sendMsg() {{
        const inp = document.getElementById("chat-in");
        const text = inp.value.trim();
        if (!text) return;
        inp.value = "";
        addMsg("user", text, false);
        saveMsg("user", text, false);
        showLoading();
        try {{
            const r = await fetch("/api/chat", {{
                method: "POST",
                headers: {{"Content-Type": "application/json"}},
                body: JSON.stringify({{session_id: window._sid, message: text }})
            }});
            const data = await r.json();
            removeLoading();
            addMsg("assistant", data.response, true);
            saveMsg("assistant", data.response, true);
        }} catch(e) {{
            removeLoading();
            addMsg("assistant", "Error: " + e.message, false);
        }}
    }}
    document.addEventListener("DOMContentLoaded", function() {{
        initChat();
        const btn = document.getElementById("chat-send");
        const inp = document.getElementById("chat-in");
        if (btn) btn.onclick = sendMsg;
        if (inp) inp.onkeydown = (e) => {{ if (e.key === "Enter") sendMsg(); }};
    }});
    ''')


# ── HOME PAGE ───────────────────────────────────────────────────────
@ui.page('/')
def index():
    session_id = str(uuid.uuid4())

    ui.add_head_html(f'''
    {COMMON_CSS}
    <style>
        .home-grid {{
            display: grid;
            grid-template-columns: 60% 40%;
            height: calc(100vh - 80px);
            width: 100%;
        }}
        .hero-left {{ overflow: hidden; }}
        .hero-left img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
        .chat-right {{
            background: {BG};
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .chat-input {{
            width: 80%;
            background: white;
            border: 1px solid #ccc;
            border-radius: 12px;
            padding: 10px 14px;
            font-size: 14px;
            color: {TEXT};
            outline: none;
            line-height: 1.4;
            box-sizing: border-box;
            min-height: 46px;
            resize: none;
        }}
        .chat-input::placeholder {{
            color: {TEXT};
            font-size: 14px;
            opacity: 0.7;
        }}
        .chat-input:focus {{ border-color: #999; }}
        .send-btn {{
            width: 42px; height: 42px;
            background: #888; color: white;
            border: none; border-radius: 50%;
            cursor: pointer; font-size: 16px;
            display: flex; align-items: center; justify-content: center;
            flex-shrink: 0;
        }}
        .send-btn:hover {{ background: #666; }}
        @media (max-width: 768px) {{
            .home-grid {{ grid-template-columns: 100%; }}
            .hero-left {{ display: none; }}
        }}
    </style>
    ''')

    nav_bar()

    ui.html(f'''
    <div style="display:grid; grid-template-columns:65fr 35fr; height:calc(100vh - 80px); width:100%; padding:12px; box-sizing:border-box;">
        <div class="hero-left" style="overflow:hidden; border-radius:12px;">
            <img src="/static/main_page.png" style="width:100%; height:100%; object-fit:cover; display:block; border-radius:12px;" />
        </div>
        <div class="chat-right" style="background:{BG}; display:flex; flex-direction:column; overflow:hidden;">
            <div style="padding:16px 16px 8px 16px;">
                <div style="font-weight:600; font-size:18px; color:{TEXT};">AIFinder</div>
                <div style="font-size:13px; color:{TEXT}; margin-top:2px;">AI chatbot to help you find products</div>
            </div>
            <div id="chat-messages" style="overflow-y:auto; padding:0 12px;"></div>
            <div style="padding:10px 12px; display:flex; align-items:center; justify-content:flex-end; gap:8px;">
                <input id="chat-in" class="chat-input" type="text" placeholder="Type your message here..." />
                <button id="chat-send" class="send-btn">▶</button>
            </div>
        </div>
    </div>
    ''')

    chatbot_js()

    ui.html(f'''
    <div style="text-align:center; padding:10px 0; font-size:11px; color:{TEXT};
                background:{BG}; position:fixed; bottom:0; width:100%; z-index:10;">
        &copy; 2026 AIFinder. All rights reserved.
    </div>
    ''')


# ── PRODUCTS PAGE ───────────────────────────────────────────────────
@ui.page('/products')
def products_page():
    ui.add_head_html(COMMON_CSS)
    page_header()

    with ui.row().classes('w-full').style('height: calc(100vh - 80px);'):
        # Main content
        with ui.column().style('flex: 65; padding: 16px; overflow-y: auto;'):
            ui.label('Product Catalog').style(f'font-size: 24px; font-weight: 700; color: {TEXT}; padding: 0 0 8px 0;')

            # Search only
            search_input = ui.input(placeholder='Search products...').style('width: 100%; margin-bottom: 12px;')

            products_container = ui.column().classes('w-full')

            def render_products(e=None):
                products_container.clear()
                query = search_input.value.strip() if search_input.value else None

                products = search_products(query=query, limit=50)

                with products_container:
                    if not products:
                        ui.label('No products found.').style(f'color: {TEXT}; padding: 20px;')
                        return

                    for i in range(0, len(products), 4):
                        with ui.row().classes('w-full gap-3').style('margin-bottom: 12px;'):
                            for j in range(4):
                                if i + j < len(products):
                                    p = products[i + j]
                                    with ui.card().style('flex: 1; background: white; border-radius: 8px; padding: 8px; border: none;'):
                                        ui.image(get_product_image(p['id'])).style('width: 100%; height: 100px; object-fit: contain; border-radius: 6px;')
                                        ui.label(p['product_name']).style(f'font-weight: 600; font-size: 12px; color: {TEXT}; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;')
                                        ui.label(f"${p['price_usd']:,.2f}").style(f'font-weight: 700; font-size: 13px; color: {TEXT};')
                                        with ui.row().classes('w-full gap-1'):
                                            ui.link('View', f'/products/{p["id"]}').style(
                                                f'background: {ACCENT}; color: white; padding: 4px 12px; border-radius: 6px; text-decoration: none; font-size: 11px; flex: 1; text-align: center;'
                                            )
                                            def add_handler(pid=p['id'], e=None):
                                                db_add_to_cart(get_session_id(), pid, 1)
                                                ui.notify(f'Added {pid} to cart!', type='positive')
                                            ui.button('Add', on_click=add_handler).style(
                                                f'background: {ACCENT}; color: white; border-radius: 6px; font-size: 11px; flex: 1; min-height: 28px;'
                                            )

            search_input.on('value-change', render_products)
            render_products()

        # Chatbot sidebar
        with ui.column().style(f'flex: 35; background: {BG}; padding: 0;'):
            ui.html(f'''
            <div style="padding:16px 16px 8px 16px;">
                <div style="font-weight:600; font-size:18px; color:{TEXT};">AIFinder</div>
                <div style="font-size:13px; color:{TEXT}; margin-top:2px;">AI chatbot to help you find products</div>
            </div>
            <div id="chat-messages" style="overflow-y:auto; padding:0 12px;"></div>
            <div style="padding:10px 12px; display:flex; align-items:center; justify-content:flex-end; gap:8px;">
                <input id="chat-in" class="chat-input" type="text" placeholder="Type your message here..." />
                <button id="chat-send" class="send-btn">▶</button>
            </div>
            ''')
            chatbot_js()

    page_footer()


# ── PRODUCT DETAIL ──────────────────────────────────────────────────
def _render_product(product_id):
    ui.add_head_html(COMMON_CSS)
    nav_bar()

    product = get_product(product_id)
    if not product:
        ui.label('Product not found').style(f'color: {TEXT}; padding: 40px;')
        return

    ui.link('← Back to Catalog', '/products').style(f'color: {TEXT}; text-decoration: none; font-size: 14px; padding: 8px 0;')

    with ui.row().classes('w-full gap-8').style('padding: 16px 0;'):
        with ui.column().style('flex: 2;'):
            ui.image(get_product_image(product['id'])).style('width: 100%; max-width: 400px; border-radius: 8px;')
            ui.label('Specifications').style(f'font-size: 18px; font-weight: 600; color: {TEXT}; margin-top: 16px;')
            ui.label(product.get('specifications', '')).style(f'color: {TEXT}; font-size: 14px; white-space: pre-wrap;')
            ui.label('Details').style(f'font-size: 18px; font-weight: 600; color: {TEXT}; margin-top: 16px;')
            for field in ['application', 'use_case', 'volume_or_capacity', 'compatible_with', 'requires', 'alternative_to']:
                if product.get(field):
                    ui.label(f"{field.replace('_', ' ').title()}: {product[field]}").style(f'color: {TEXT}; font-size: 14px;')

        with ui.column().style('flex: 1;'):
            ui.label(product['product_name']).style(f'font-size: 24px; font-weight: 700; color: {TEXT};')
            ui.label(f"${product['price_usd']:,.2f}").style(f'font-size: 28px; font-weight: 700; color: {TEXT}; margin-top: 16px;')
            if product.get('discount'):
                ui.label(f"Discount: {product['discount']}%").style('color: green;')
            quantity_input = ui.number(value=1, min=1, label='Quantity').style('margin-top: 16px; width: 120px;')
            def add_handler(e=None):
                db_add_to_cart(get_session_id(), product_id, int(quantity_input.value))
                ui.notify(f'Added {int(quantity_input.value)}x to cart!', type='positive')
            ui.button('Add to Cart', on_click=add_handler).style(f'background: {ACCENT}; color: white; border-radius: 8px; margin-top: 8px; width: 100%;')


@ui.page('/products/{product_id}')
def product_detail_page(product_id):
    _render_product(product_id)

@ui.page('/Products')
def product_detail_page_alt():
    ui.run_javascript('''
        const params = new URLSearchParams(window.location.search);
        const pid = params.get("product_id");
        if (pid) {
            window.location.href = "/products/" + pid;
        } else {
            window.location.href = "/products";
        }
    ''')


# ── CART PAGE ───────────────────────────────────────────────────────
@ui.page('/cart')
def cart_page():
    ui.add_head_html(COMMON_CSS)
    page_header()

    session_id_cart = get_session_id()

    with ui.row().classes('w-full').style('height: calc(100vh - 80px);'):
        with ui.column().style('flex: 65; padding: 16px; overflow-y: auto;'):
            ui.label('Shopping Cart').style(f'font-size: 24px; font-weight: 700; color: {TEXT}; padding: 0 0 8px 0;')

            cart = db_get_cart(session_id_cart)
            if not cart:
                ui.label('Your cart is empty.').style(f'color: {TEXT}; padding: 20px;')
                ui.link('Browse Products', '/products').style(f'color: {TEXT}; text-decoration: underline;')
            else:
                for item in cart:
                    with ui.row().classes('w-full items-center gap-4').style(f'background: white; border-radius: 8px; padding: 12px; margin-bottom: 8px;'):
                        ui.image(get_product_image(item['product_id'])).style('width: 60px; height: 60px; object-fit: contain; border-radius: 6px;')
                        with ui.column().style('flex: 2;'):
                            ui.label(item['product_name']).style(f'font-weight: 600; color: {TEXT};')
                            ui.label(f"{item['brand']} | {item['product_id']}").style(f'font-size: 12px; color: {TEXT};')
                        ui.label(f"${item['price_usd']:,.2f}").style(f'font-weight: 600; color: {TEXT};')
                        qty = ui.number(value=item['quantity'], min=1).style('width: 80px;')
                        def update_handler(cid=item['id'], qi=qty, e=None):
                            update_cart_item(cid, int(qi.value))
                        qty.on('value-change', update_handler)
                        def remove_handler(cid=item['id'], e=None):
                            remove_from_cart(cid)
                        ui.button(icon='delete', on_click=remove_handler).style('color: red;')

                total = get_cart_total(session_id_cart)
                ui.label(f'Total: ${total:,.2f}').style(f'font-size: 20px; font-weight: 700; color: {TEXT}; margin-top: 12px;')

                with ui.row().classes('w-full gap-4').style('margin-top: 12px;'):
                    ui.button('Clear Cart', on_click=lambda: clear_cart(session_id_cart)).style('background: #888; color: white; border-radius: 8px;')
                    def checkout():
                        oid = create_order(session_id_cart)
                        if oid:
                            ui.notify(f'Order #{oid} placed!', type='positive')
                    ui.button('Checkout', on_click=checkout).style(f'background: {ACCENT}; color: white; border-radius: 8px;')

        with ui.column().style(f'flex: 35; background: {BG}; padding: 0;'):
            ui.html(f'''
            <div style="padding:16px 16px 8px 16px;">
                <div style="font-weight:600; font-size:18px; color:{TEXT};">AIFinder</div>
                <div style="font-size:13px; color:{TEXT}; margin-top:2px;">AI chatbot to help you find products</div>
            </div>
            <div id="chat-messages" style="overflow-y:auto; padding:0 12px;"></div>
            <div style="padding:10px 12px; display:flex; align-items:center; justify-content:flex-end; gap:8px;">
                <input id="chat-in" class="chat-input" type="text" placeholder="Type your message here..." />
                <button id="chat-send" class="send-btn">▶</button>
            </div>
            ''')
            chatbot_js()

    page_footer()


# ── ORDERS PAGE ─────────────────────────────────────────────────────
@ui.page('/orders')
def orders_page():
    ui.add_head_html(COMMON_CSS)
    page_header()

    session_id_ord = get_session_id()

    with ui.row().classes('w-full').style('height: calc(100vh - 80px);'):
        with ui.column().style('flex: 65; padding: 16px; overflow-y: auto;'):
            ui.label('Order History').style(f'font-size: 24px; font-weight: 700; color: {TEXT}; padding: 0 0 8px 0;')

            from core.database import get_orders
            orders = get_orders(session_id_ord)
            if not orders:
                ui.label('No orders yet.').style(f'color: {TEXT}; padding: 20px;')
                ui.link('Browse Products', '/products').style(f'color: {TEXT}; text-decoration: underline;')
            else:
                for order in orders:
                    with ui.expander(f"Order #{order['id']} - ${order['total_amount']:,.2f} ({order['status']})"):
                        ui.label(f"Date: {order['created_at']}").style(f'color: {TEXT};')
                        ui.label(f"Status: {order['status']}").style(f'color: {TEXT};')
                        ui.label(f"Total: ${order['total_amount']:,.2f}").style(f'color: {TEXT};')
                        if order.get('items'):
                            ui.label('Items:').style(f'color: {TEXT}; font-weight: 600;')
                            for item in order['items']:
                                ui.label(f"- {item['product_id']} x {item['quantity']} @ ${item['price']:,.2f}").style(f'color: {TEXT};')

        with ui.column().style(f'flex: 35; background: {BG}; padding: 0;'):
            ui.html(f'''
            <div style="padding:16px 16px 8px 16px;">
                <div style="font-weight:600; font-size:18px; color:{TEXT};">AIFinder</div>
                <div style="font-size:13px; color:{TEXT}; margin-top:2px;">AI chatbot to help you find products</div>
            </div>
            <div id="chat-messages" style="overflow-y:auto; padding:0 12px;"></div>
            <div style="padding:10px 12px; display:flex; align-items:center; justify-content:flex-end; gap:8px;">
                <input id="chat-in" class="chat-input" type="text" placeholder="Type your message here..." />
                <button id="chat-send" class="send-btn">▶</button>
            </div>
            ''')
            chatbot_js()

    page_footer()


app.add_static_files('/static', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))
app.add_static_files('/static/images', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images'))

FAVICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'microscope.png')


@app.post('/api/chat')
async def chat_api(request: Request):
    data = await request.json()
    session_id = data.get('session_id', 'default')
    message = data.get('message', '')
    try:
        response = await asyncio.to_thread(get_llm_response, session_id, message)
        response = md_to_html(response)
    except Exception as e:
        response = f"Error: {str(e)[:100]}"
    return JSONResponse({'response': response})


ui.run(host='0.0.0.0', port=8080, title='AIFinder', reload=False, favicon=FAVICON)

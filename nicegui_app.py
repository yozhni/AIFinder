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
)
from config import get

HERO_IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "main_page.png")
CLOUDINARY_BASE = get("cloudinary", "base_url")
IMAGE_EXT = get("cloudinary", "image_ext")

BG = '#D3D3D3'
TEXT = '#555555'
ACCENT = '#444444'
SID = "aifinder_session"


def md_to_html(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank" style="color:#0066cc;">\1</a>', text)
    return text.replace('\n', '<br>')


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
            msgs = ui.column().style('flex:1;overflow-y:auto;padding:0 12px;')
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
                ui.run_javascript(f'localStorage.setItem("chat_history", JSON.stringify(JSON.parse(localStorage.getItem("chat_history") || "[]").concat([{{role:"user",text:{repr(text)},isHtml:false}}])));')
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
            except Exception:
                page_alive = False

        # Call LLM (always runs, even if page is gone)
        try:
            response = await asyncio.to_thread(get_llm_response, SID, text)
            response = md_to_html(response)
        except Exception as ex:
            response = f"Error: {str(ex)[:100]}"

        # Save to localStorage (always runs)
        try:
            ui.run_javascript(f'localStorage.setItem("chat_history", JSON.stringify(JSON.parse(localStorage.getItem("chat_history") || "[]").concat([{{role:"assistant",text:{repr(response)},isHtml:true}}])));')
        except Exception:
            pass

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
                        ui.html(f'<div style="background:white;padding:10px 14px;border-radius:12px;color:{TEXT};font-size:14px;line-height:1.4;max-width:80%;">{response}</div>')
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

    # Only show welcome if no history
    ui.run_javascript('''
        const saved = localStorage.getItem("chat_history");
        if (saved && JSON.parse(saved).length > 0) {
            const welcomeEl = document.querySelector("[data-welcome]");
            if (welcomeEl) welcomeEl.remove();
        }
    ''')

    # Footer
    ui.html(f'<div style="text-align:center;padding:10px 0;font-size:11px;color:{TEXT};background:{BG};position:fixed;bottom:0;width:100%;z-index:10;">&copy; 2026 AIFinder. All rights reserved.</div>')


# ── PAGE CONTENT ────────────────────────────────────────────────────
def home_content():
    ui.image(HERO_IMG).style('width:100%;height:calc(100vh - 100px);object-fit:cover;border-radius:12px;')


def products_content():
    ui.label('Product Catalog').style(f'font-size:24px;font-weight:700;color:{TEXT};margin-bottom:8px;')
    with ui.row().classes('w-full gap-2').style('margin-bottom:12px;'):
        search = ui.input(placeholder='Search products...').style('flex:1;')
        search_btn = ui.button(icon='search').classes('ab')
    container = ui.column()

    def render(e=None):
        container.clear()
        q = search.value.strip() if search.value else None
        products = search_products(query=q, limit=50)
        with container:
            if not products:
                ui.label('No products found.').style(f'color:{TEXT};padding:20px;')
                return
            for i in range(0, len(products), 4):
                with ui.row().classes('w-full gap-3').style('margin-bottom:12px;'):
                    for j in range(4):
                        if i + j < len(products):
                            p = products[i + j]
                            with ui.card().style('flex:1;background:white;border-radius:8px;padding:8px;border:none;'):
                                ui.image(get_product_image(p['id'])).style('width:100%;height:100px;object-fit:contain;border-radius:6px;')
                                ui.label(p['product_name']).style(f'font-weight:600;font-size:12px;color:{TEXT};margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;')
                                ui.label(f"${p['price_usd']:,.2f}").style(f'font-weight:700;font-size:13px;color:{TEXT};')
                                with ui.row().classes('w-full gap-1'):
                                    ui.link('view', f'/products/{p["id"]}').classes('vl')
                                    def add_h(pid=p['id'], e=None):
                                        db_add_to_cart(SID, pid, 1)
                                        ui.notify(f'Added {pid} to cart!', type='positive')
                                    ui.button('add', on_click=add_h).classes('ab')

    search.on('keydown.enter', render)
    search_btn.on_click(render)
    render()


def cart_content():
    ui.label('Shopping Cart').style(f'font-size:24px;font-weight:700;color:{TEXT};margin-bottom:8px;')
    cart = db_get_cart(SID)
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
    total = get_cart_total(SID)
    ui.label(f'Total: ${total:,.2f}').style(f'font-size:20px;font-weight:700;color:{TEXT};margin-top:12px;')
    with ui.row().classes('w-full gap-4').style('margin-top:12px;'):
        def clear_h(e=None):
            clear_cart(SID)
            ui.navigate.reload()
        ui.button('clear', on_click=clear_h).classes('ab')
        def checkout():
            oid = create_order(SID)
            if oid:
                ui.notify(f'Order #{oid} placed!', type='positive')
        ui.button('checkout', on_click=checkout).classes('ab')


# ── PAGES ───────────────────────────────────────────────────────────
@ui.page('/')
def index():
    page_template(home_content)

@ui.page('/products')
def products_page():
    page_template(products_content)

@ui.page('/products/{product_id}')
def product_detail_page(product_id):
    def detail():
        product = get_product(product_id)
        if not product:
            ui.label('Product not found').style(f'color:{TEXT};padding:40px;')
            return
        ui.link('← Back', '/products').style(f'color:{TEXT};text-decoration:none;')
        ui.image(get_product_image(product['id'])).style('width:100%;max-width:250px;border-radius:8px;margin-top:8px;')
        ui.label(product['product_name']).style(f'font-size:24px;font-weight:700;color:{TEXT};margin-top:12px;')
        ui.label(f"${product['price_usd']:,.2f}").style(f'font-size:20px;font-weight:700;color:{TEXT};')
        ui.label(product.get('specifications', '')).style(f'color:{TEXT};font-size:14px;white-space:pre-wrap;margin-top:8px;')
        qty = ui.number(value=1, min=1).style('width:100px;margin-top:12px;')
        def add_h(e=None):
            db_add_to_cart(SID, product_id, int(qty.value))
            ui.notify(f'Added {int(qty.value)}x to cart!', type='positive')
        ui.button('add', on_click=add_h).classes('ab')
    page_template(detail)

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
    try:
        response = await asyncio.to_thread(get_llm_response, SID, message)
        response = md_to_html(response)
    except Exception as e:
        response = f"Error: {str(e)[:100]}"
    return JSONResponse({'response': response})

ui.run(host='0.0.0.0', port=8080, title='AIFinder', reload=False, favicon=FAVICON)

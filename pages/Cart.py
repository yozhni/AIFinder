"""Shopping Cart - View and manage cart."""

import streamlit as st
import streamlit.components.v1 as components
import sys
import os
import ssl
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_cart, update_cart_item, remove_from_cart, clear_cart, get_cart_total
from config import get
from pathlib import Path

IMAGES_DIR = Path(__file__).parent.parent / "images"
PLACEHOLDER_IMG = Path(__file__).parent.parent / get("paths", "placeholder_img")
CLOUDINARY_BASE = get("cloudinary", "base_url")
IMAGE_EXT = get("cloudinary", "image_ext")

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def get_product_image(product_id):
    cloudinary_url = f"{CLOUDINARY_BASE}/{product_id}{IMAGE_EXT}"
    try:
        req = urllib.request.Request(cloudinary_url, method="HEAD")
        urllib.request.urlopen(req, timeout=5, context=_SSL_CTX)
        return cloudinary_url
    except (urllib.error.URLError, OSError):
        pass
    local_path = IMAGES_DIR / f"{product_id}.webp"
    if local_path.exists():
        return str(local_path)
    return str(PLACEHOLDER_IMG)


st.set_page_config(page_title="Cart - AIFinder", page_icon="C", layout="centered",
                   initial_sidebar_state="collapsed")

st.markdown("""<style>
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    /* Position floating chat button */
    iframe {
        position: fixed !important;
        bottom: 24px !important;
        right: 24px !important;
        z-index: 999999 !important;
        border: none !important;
        border-radius: 50% !important;
        overflow: hidden !important;
    }
</style>""", unsafe_allow_html=True)

if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

session_id = st.session_state.session_id

col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
with col1:
    st.markdown("**AIFinder**")
with col2:
    st.page_link("app.py", label="Home")
with col3:
    st.page_link("pages/Products.py", label="Products")
with col4:
    cart = get_cart(session_id)
    cart_count = len(cart) if cart else 0
    st.page_link("pages/Cart.py", label=f"Cart ({cart_count})")

st.markdown("---")

st.markdown("# Shopping Cart")

cart = get_cart(session_id)

if not cart:
    st.info("Your cart is empty.")
    st.markdown("[Browse Products](/Products)")
else:
    for item in cart:
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

        with col1:
            img_url = get_product_image(item['product_id'])
            st.image(img_url, width=80)
            st.markdown(f"**{item['product_name']}**")
            st.caption(f"{item['brand']} | {item['product_id']}")

        with col2:
            st.write(f"${item['price_usd']:,.2f}")

        with col3:
            new_qty = st.number_input(
                "Qty",
                min_value=1,
                value=item['quantity'],
                key=f"qty_{item['id']}"
            )
            if new_qty != item['quantity']:
                update_cart_item(item['id'], new_qty)
                st.rerun()

        with col4:
            if st.button("Remove", key=f"remove_{item['id']}"):
                remove_from_cart(item['id'])
                st.rerun()

        st.markdown("---")

    total = get_cart_total(session_id)
    st.markdown(f"### Total: ${total:,.2f}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear Cart"):
            clear_cart(session_id)
            st.rerun()
    with col2:
        if st.button("Checkout", type="primary"):
            from core.database import create_order
            order_id = create_order(session_id)
            if order_id:
                st.success(f"Order #{order_id} placed!")
                st.markdown("[View Orders](/Orders)")
                st.rerun()

components.html("""
<style>
    html, body { margin:0; padding:0; height:100%; overflow:hidden; background:transparent; }
    .chat-btn {
        width: 100%; height: 100%;
        border-radius: 50%;
        background: #111;
        color: white;
        border: none;
        cursor: pointer;
        font-size: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        display: flex; align-items: center; justify-content: center;
    }
    .chat-btn:hover { background: #333; }
</style>
<button class="chat-btn" onclick="window.parent.location.href='/'">💬</button>
""", height=60, width=60)

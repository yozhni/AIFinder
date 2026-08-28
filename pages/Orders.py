"""Order History - View past orders."""

import streamlit as st
import streamlit.components.v1 as components
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_orders, get_cart

st.set_page_config(page_title="Orders - AIFinder", page_icon="O", layout="centered",
                   initial_sidebar_state="collapsed")

st.markdown("""<style>
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
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

# Session ID
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

session_id = st.session_state.session_id

# Header
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

st.markdown("# Order History")

orders = get_orders(session_id)

if not orders:
    st.info("No orders yet.")
    st.markdown("[Browse Products](/Products)")
else:
    for order in orders:
        with st.expander(f"Order #{order['id']} - ${order['total_amount']:,.2f} ({order['status']})"):
            st.write(f"**Date:** {order['created_at']}")
            st.write(f"**Status:** {order['status']}")
            st.write(f"**Total:** ${order['total_amount']:,.2f}")

            if order.get('items'):
                st.markdown("**Items:**")
                for item in order['items']:
                    st.write(f"- {item['product_id']} x {item['quantity']} @ ${item['price']:,.2f}")

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

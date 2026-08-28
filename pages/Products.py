"""Product Catalog - Browse and search products."""

import streamlit as st
import streamlit.components.v1 as components
import sys
import os
import ssl
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import (
    search_products, get_categories, get_brands,
    get_price_range, get_product, add_to_cart, get_cart
)
from config import get

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")
PLACEHOLDER_IMG = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), get("paths", "placeholder_img")))
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
    local_path = os.path.join(IMAGES_DIR, f"{product_id}.webp")
    if os.path.exists(local_path):
        return local_path
    return PLACEHOLDER_IMG


st.set_page_config(page_title="Products - AIFinder", page_icon="P", layout="centered",
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

product_id = st.query_params.get("product_id")

if product_id:
    product = get_product(product_id)
    if product:
        st.markdown(f"# {product['product_name']}")
        st.caption(f"ID: {product['id']} | Brand: {product['brand']} | Category: {product['category']}")

        col1, col2 = st.columns([2, 1])

        with col1:
            img_path = get_product_image(product['id'])
            st.image(img_path, width=300)
            st.markdown("### Specifications")
            st.text(product["specifications"])

            st.markdown("### Details")
            st.write(f"**Application:** {product['application']}")
            st.write(f"**Use Case:** {product['use_case']}")
            st.write(f"**Volume/Capacity:** {product['volume_or_capacity']}")
            st.write(f"**Compatible With:** {product['compatible_with']}")
            st.write(f"**Requires:** {product['requires']}")
            st.write(f"**Alternative To:** {product['alternative_to']}")

        with col2:
            st.markdown("### Price")
            st.markdown(f"## ${product['price_usd']:,.2f}")
            if product['discount']:
                st.success(f"Discount: {product['discount']}%")

            st.markdown("### Properties")
            st.write(f"Refrigerated: {'Yes' if product['refrigerated'] else 'No'}")
            st.write(f"Sterile: {'Yes' if product['sterile'] else 'No'}")
            st.write(f"Endotoxin Free: {'Yes' if product['endotoxin_free'] else 'No'}")

            st.markdown("### Add to Cart")
            quantity = st.number_input("Quantity", min_value=1, value=1, key="qty")
            if st.button("Add to Cart", type="primary"):
                add_to_cart(session_id, product_id, quantity)
                st.success(f"Added {quantity}x to cart!")
                st.rerun()

            if st.button("Back to Catalog"):
                st.query_params.clear()
                st.rerun()
    else:
        st.error("Product not found")
else:
    st.markdown("# Product Catalog")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        categories = ["All"] + get_categories()
        selected_category = st.selectbox("Category", categories)

    with col2:
        brands = ["All"] + get_brands()
        selected_brand = st.selectbox("Brand", brands)

    with col3:
        price_range = get_price_range()
        min_price, max_price = st.slider(
            "Price Range",
            min_value=float(price_range["min"]),
            max_value=float(price_range["max"]),
            value=(float(price_range["min"]), float(price_range["max"]))
        )

    with col4:
        search_query = st.text_input("Search", placeholder="Search products...")

    filters = {
        "query": search_query if search_query else None,
        "category": selected_category if selected_category != "All" else None,
        "brand": selected_brand if selected_brand != "All" else None,
        "min_price": min_price,
        "max_price": max_price,
        "limit": 50
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    products = search_products(**filters)

    st.markdown(f"**{len(products)} products found**")

    if products:
        for i in range(0, len(products), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(products):
                    p = products[i + j]
                    with col:
                        with st.container():
                            img_path = get_product_image(p['id'])
                            st.image(img_path, width=150)
                            st.markdown(f"**{p['product_name']}**")
                            st.caption(f"{p['brand']} | {p['category']}")
                            st.markdown(f"**${p['price_usd']:,.2f}**")

                            props = []
                            if p['refrigerated']:
                                props.append("Refrigerated")
                            if p['sterile']:
                                props.append("Sterile")
                            if props:
                                st.caption(" | ".join(props))

                            c1, c2 = st.columns(2)
                            with c1:
                                st.link_button("View", f"/Products?product_id={p['id']}")
                            with c2:
                                if st.button("Add", key=f"cat_{p['id']}"):
                                    add_to_cart(session_id, p['id'], 1)
                                    st.rerun()

                            st.markdown("---")
    else:
        st.info("No products found matching your criteria.")

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

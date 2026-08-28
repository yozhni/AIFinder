"""AIFinder - AI Chat Assistant."""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get

st.set_page_config(
    page_title="AIFinder",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="collapsed"
)

HERO_IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "main_page.png")

st.markdown("""<style>
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #D3D3D3 !important;
    }
    section[data-testid="stMain"] { background: #D3D3D3 !important; }
    div[data-testid="stChatInput"] {
        background: #D3D3D3 !important;
        border-top: 1px solid #bbb !important;
    }
    div[data-testid="stChatInput"] textarea {
        background: #fff !important;
        color: #555 !important;
        border: 1px solid #ccc !important;
        border-radius: 8px !important;
    }
    div[data-testid="stChatInput"] button {
        background: #555 !important;
        color: #fff !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] { border: none !important; }
    [data-testid="stHorizontalBlock"] { gap: 0 !important; }
</style>""", unsafe_allow_html=True)

if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Navigation ──────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; justify-content:flex-end; align-items:center; gap:12px;
            padding:10px 24px; border-bottom:1px solid #bbb; background:#D3D3D3;">
    <a href="/Products" style="color:#555; text-decoration:none; font-size:15px; font-weight:600;">Products</a>
    <span style="color:#999;">|</span>
    <a href="/Cart" style="color:#555; text-decoration:none; font-size:15px; font-weight:600;">Cart</a>
</div>
""", unsafe_allow_html=True)

# ── Two-column layout ───────────────────────────────────────────────
left, right = st.columns([65, 35])

# ── LEFT: Hero image (no overlay) ───────────────────────────────────
with left:
    st.image(HERO_IMG, use_container_width=True)

# ── RIGHT: Chatbot ──────────────────────────────────────────────────
with right:
    st.markdown("""
    <div style="padding:12px 16px 8px 16px;">
        <div style="font-weight:600; font-size:18px; color:#555;">AIFinder</div>
        <div style="font-size:13px; color:#555; margin-top:2px;">AI chatbot to help you find products</div>
    </div>
    """, unsafe_allow_html=True)

    if "history_loaded" not in st.session_state:
        try:
            from core.database import load_history
            history = load_history(st.session_state.session_id, limit=40)
            st.session_state.messages = [{"role": m["role"], "content": m["content"]} for m in history]
        except Exception:
            pass
        st.session_state.history_loaded = True

    if not st.session_state.messages:
        welcome = "Hello! I'm AIFinder, your lab equipment assistant. How can I help you today?"
        st.session_state.messages.append({"role": "assistant", "content": welcome})

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ── Chat input (pinned at bottom) ───────────────────────────────────
if user_input := st.chat_input("Type your message here..."):
    from core.llm import get_llm_response
    from core.database import save_message
    sid = st.session_state.session_id

    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        try:
            response = get_llm_response(sid, user_input)
        except OSError:
            response = "Sorry, the request was interrupted. Please try again."
        except Exception as e:
            response = f"Error: {str(e)[:100]}"
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

# ── Copyright ───────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding:10px 0; font-size:11px; color:#555;
            border-top:1px solid #bbb; background:#D3D3D3;">
    &copy; 2026 AIFinder. All rights reserved.
</div>
""", unsafe_allow_html=True)

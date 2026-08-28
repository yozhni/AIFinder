"""Chat Interface - Popup Dialog."""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm import get_llm_response
from core.database import save_message, load_history, get_cart

st.set_page_config(page_title="Chat - AIFinder", page_icon="C", layout="centered",
                   initial_sidebar_state="collapsed")

st.markdown("""<style>
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>""", unsafe_allow_html=True)

if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

session_id = st.session_state.session_id


def ask_bot(message):
    try:
        save_message(session_id, "user", message)
    except Exception:
        pass
    st.session_state.messages.append({"role": "user", "content": message})

    with st.chat_message("user"):
        st.markdown(message)

    with st.chat_message("assistant"):
        try:
            response = get_llm_response(session_id, message)
        except OSError:
            response = "Sorry, the request was interrupted. Please try again."
        except Exception as e:
            response = f"Error: {str(e)[:100]}"
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})


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
st.markdown("# Chat with AIFinder")
st.caption("Ask about products, compare items, get recommendations")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "history_loaded" not in st.session_state:
    try:
        history = load_history(session_id, limit=20)
        st.session_state.messages = [{"role": m["role"], "content": m["content"]} for m in history]
    except Exception:
        pass
    st.session_state.history_loaded = True

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("Ask about lab products..."):
    ask_bot(user_input)

with st.sidebar:
    st.markdown("### Quick Actions")
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.history_loaded = False
        try:
            from core.database import clear_history
            clear_history(session_id)
        except Exception:
            pass

    st.markdown("---")
    st.markdown("### Try Asking")
    examples = [
        "I need centrifuges for cell culture",
        "Compare Size Exclusion Column and Desalting Column",
        "What do you recommend for protein purification?",
        "Show me sterile pipette tips",
        "Add LC-0017 to cart",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{hash(ex)}"):
            ask_bot(ex)

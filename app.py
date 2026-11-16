import streamlit as st
import requests
from firebase_client import sign_in, sign_up
from rag import load_and_embed_kb, retrieve_top_k, generate_answer

st.set_page_config(page_title="Lumen Travel", layout="wide")

st.markdown(
    """
    <style>
    #MainMenu, footer {visibility: hidden;}
    .stApp {background: linear-gradient(160deg, #1b1f27 0%, #20262f 60%, #262230 100%);}
    .block-container {max-width: 980px; padding-top: 2rem; padding-bottom: 6rem;}
    [data-testid="stSidebar"] {background: #171b22; border-right: 1px solid #2b323d;}

    .hero {
        background: linear-gradient(120deg, #2a3140 0%, #343046 100%);
        border: 1px solid #3a4150; border-radius: 14px;
        padding: 1.6rem 1.8rem; margin-bottom: 1.4rem;
    }
    .hero h1 {margin: 0; font-size: 1.9rem; font-weight: 650; color: #f2f3f5; padding: 0;}
    .hero p {margin: 0.35rem 0 0 0; color: #a9b0bd; font-size: 0.98rem;}
    .brand {color: #e0a458; font-size: 0.8rem; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 0.4rem;}

    div[data-testid="stForm"] {
        background: #242a35; border: 1px solid #333b49; border-radius: 12px; padding: 1.4rem;
    }
    [data-testid="stChatMessage"] {
        background: #242a35; border: 1px solid #303846; border-radius: 12px; padding: 0.9rem 1.1rem;
    }
    [data-testid="stChatInput"] {border-radius: 12px;}
    .stButton button, .stFormSubmitButton button {
        border-radius: 8px; border: 1px solid #3a4352; background: #2a3140; color: #e6e8ec;
    }
    .stButton button:hover, .stFormSubmitButton button:hover {border-color: #e0a458; color: #e0a458;}

    .src {background: #1d222b; border: 1px solid #2f3643; border-left: 3px solid #e0a458;
          border-radius: 8px; padding: 0.7rem 0.9rem; margin-bottom: 0.7rem;}
    .src .t {font-weight: 600; color: #f2f3f5;}
    .src .m {color: #98a0ae; font-size: 0.82rem; margin: 0.15rem 0 0.4rem 0;}
    .src .b {color: #cfd3da; font-size: 0.92rem;}
    .badge {display: inline-block; background: #3a3326; color: #e0a458; border-radius: 6px;
            padding: 0 0.45rem; font-size: 0.8rem; margin-left: 0.4rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

SUGGESTIONS = [
    "What are the opening hours and ticket price of Independence Palace?",
    "How do I get from Tan Son Nhat airport to District 1?",
    "When do the night food stalls at Ben Thanh Market open?",
    "What should I pack in the rainy season?",
]

if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None


def hero(title: str, subtitle: str):
    st.markdown(
        f"<div class='hero'><div class='brand'>Lumen Travel</div>"
        f"<h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def render_sources(sources):
    with st.expander("Sources"):
        for s in sources:
            st.markdown(
                f"<div class='src'><div class='t'>[{s['id']}] {s['title']}"
                f"<span class='badge'>{s['score']:.3f}</span></div>"
                f"<div class='m'>{s['source']}</div>"
                f"<div class='b'>{s['text']}</div></div>",
                unsafe_allow_html=True,
            )


# ---------- Not signed in ----------
if st.session_state.user is None:
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        hero("Welcome back", "Sign in to ask about Ho Chi Minh City.")
        tab_login, tab_signup = st.tabs(["Sign in", "Sign up"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Sign in", use_container_width=True):
                    ok, result = sign_in(email, password)
                    if ok:
                        st.session_state.user = {"email": result["email"], "uid": result["localId"]}
                        st.session_state.messages = []
                        st.rerun()
                    else:
                        st.error(result)

        with tab_signup:
            with st.form("signup_form"):
                new_email = st.text_input("Email")
                new_password = st.text_input("Password (at least 6 characters)", type="password")
                if st.form_submit_button("Create account", use_container_width=True):
                    ok, result = sign_up(new_email, new_password)
                    if ok:
                        st.session_state.user = {"email": result["email"], "uid": result["localId"]}
                        st.session_state.messages = []
                        st.rerun()
                    else:
                        st.error(result)

# ---------- Signed in ----------
else:
    with st.sidebar:
        st.markdown("**Account**")
        st.write(st.session_state.user["email"])
        if st.button("Sign out", use_container_width=True):
            st.session_state.user = None
            st.session_state.messages = []  # clear chat on sign-out
            st.session_state.pending = None
            st.rerun()

    hero("Ho Chi Minh City Guide", "Ask about opening hours, ticket prices and getting around.")

    try:
        kb = load_and_embed_kb("knowledge_base.json")
    except Exception as exc:
        st.error("Cannot reach the Ollama server. Check that it is running and that OLLAMA_URL in .env is correct.")
        with st.expander("Details"):
            st.code(str(exc))
        if st.button("Retry"):
            st.rerun()
        st.stop()

    # Suggested questions fill the empty state
    if not st.session_state.messages:
        st.markdown("<div style='color:#a9b0bd; margin-bottom:0.5rem;'>Try asking</div>", unsafe_allow_html=True)
        cols = st.columns(2)
        for i, q in enumerate(SUGGESTIONS):
            if cols[i % 2].button(q, key=f"sug{i}", use_container_width=True):
                st.session_state.pending = q
                st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                render_sources(msg["sources"])

    typed = st.chat_input("Type your question")
    query = typed if typed is not None else st.session_state.pending
    st.session_state.pending = None

    if query is not None:
        if not query.strip():
            st.warning("Please enter a question.")
        else:
            query = query.strip()
            st.session_state.messages.append({"role": "user", "content": query})
            with st.chat_message("user"):
                st.markdown(query)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        retrieved = retrieve_top_k(query, kb, k=3)
                        answer = generate_answer(query, retrieved)
                        st.markdown(answer)
                        render_sources(retrieved)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": answer, "sources": retrieved}
                        )
                    except (requests.exceptions.RequestException, ValueError) as exc:
                        st.error("Cannot reach the Ollama server. Check your Pinggy URL in .env.")
                        with st.expander("Details"):
                            st.code(str(exc))

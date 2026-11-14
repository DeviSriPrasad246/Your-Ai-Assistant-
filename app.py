import base64
import json
import os
import uuid
from datetime import datetime

import streamlit as st
import ollama

from prompts import get_personas
from safety import check_input, check_output

# =====================================================
#  EASY SETTINGS: change these to personalise your bot
# =====================================================
BOT_NAME = "Your AI Assistant"
COMPANY_NAME = "Matrix Root"
TAGLINE = "Safe, honest answers and project building help"
COLOR_1 = "#FEBD03"   # brand yellow
COLOR_2 = "#FF6100"   # brand orange
LOGO_PATH = "logo.png"

DEFAULT_MODEL = "llama3.2:1b"
MAX_HISTORY = 8          # how many past messages the AI remembers
MAX_ANSWER_TOKENS = 300  # answer length limit (higher = longer but slower)
CHAT_DIR = "chats"

STARTER_QUESTIONS = [
    "💡 Explain AI in simple words",
    "📝 Write a polite leave request email",
    "🐍 What is Python used for?",
    "🧭 Give me tips for a job interview",
]

PERSONAS = get_personas(BOT_NAME, COMPANY_NAME)
os.makedirs(CHAT_DIR, exist_ok=True)
HAS_LOGO = os.path.exists(LOGO_PATH)
AVATAR = LOGO_PATH if HAS_LOGO else "🤖"

# ---------- Page setup ----------
page_icon = "🤖"
if HAS_LOGO:
    try:
        from PIL import Image
        page_icon = Image.open(LOGO_PATH)
    except Exception:
        page_icon = "🤖"

st.set_page_config(
    page_title=f"{BOT_NAME} | {COMPANY_NAME}",
    page_icon=page_icon,
    layout="centered",
)


def logo_base64():
    try:
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


st.markdown(
    f"""
    <style>
      .block-container {{padding-top: 1.5rem; max-width: 820px;}}
      .hero {{
        display: flex; align-items: center; gap: 1.2rem;
        background: linear-gradient(135deg, #111114 0%, #1f1408 100%);
        border: 1px solid rgba(255, 140, 0, 0.35);
        border-radius: 18px; padding: 1.1rem 1.4rem; margin-bottom: 1.2rem;
        box-shadow: 0 8px 28px rgba(255, 97, 0, 0.14);
      }}
      .hero-logo {{width: 84px; height: 84px; border-radius: 14px;}}
      .hero-emoji {{font-size: 3rem;}}
      .hero-title {{
        font-size: 1.8rem; font-weight: 800; line-height: 1.2;
        background: linear-gradient(90deg, {COLOR_1}, {COLOR_2});
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      }}
      .hero-sub {{color: #d1d5db; margin-top: 0.3rem; font-size: 0.95rem;}}
      .chip {{
        display: inline-block; margin: 0.5rem 0.4rem 0 0; padding: 0.15rem 0.65rem;
        border-radius: 999px; font-size: 0.75rem; color: #fdba74;
        border: 1px solid rgba(255, 140, 0, 0.4); background: rgba(255, 97, 0, 0.08);
      }}
      .stButton > button {{border-radius: 10px;}}
      .footer-note {{text-align: center; color: #9ca3af; font-size: 0.8rem; margin-top: 1rem;}}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Saved chat functions ----------
def chat_path(chat_id):
    return os.path.join(CHAT_DIR, f"{chat_id}.json")


def save_chat():
    messages = st.session_state.messages
    if not messages:
        return
    first_user = next((m["content"] for m in messages if m["role"] == "user"), "New chat")
    data = {
        "id": st.session_state.chat_id,
        "title": first_user[:40],
        "updated": datetime.now().isoformat(timespec="seconds"),
        "messages": messages,
    }
    with open(chat_path(st.session_state.chat_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_chats():
    items = []
    for name in os.listdir(CHAT_DIR):
        if name.endswith(".json"):
            try:
                with open(os.path.join(CHAT_DIR, name), "r", encoding="utf-8") as f:
                    items.append(json.load(f))
            except Exception:
                continue
    items.sort(key=lambda d: d.get("updated", ""), reverse=True)
    return items


def start_new_chat():
    st.session_state.chat_id = uuid.uuid4().hex
    st.session_state.messages = []


def load_chat(chat_id):
    try:
        with open(chat_path(chat_id), "r", encoding="utf-8") as f:
            data = json.load(f)
        st.session_state.chat_id = chat_id
        st.session_state.messages = data.get("messages", [])
    except Exception:
        start_new_chat()


def delete_current_chat():
    path = chat_path(st.session_state.chat_id)
    if os.path.exists(path):
        os.remove(path)
    start_new_chat()


def delete_all_chats():
    for name in os.listdir(CHAT_DIR):
        if name.endswith(".json"):
            os.remove(os.path.join(CHAT_DIR, name))
    start_new_chat()


# ---------- Other helpers ----------
def get_installed_models():
    try:
        return [m.model for m in ollama.list().models]
    except Exception:
        return None


def build_chat_text(messages):
    lines = []
    for m in messages:
        who = "You" if m["role"] == "user" else BOT_NAME
        lines.append(f"{who}: {m['content']}\n")
    return "\n".join(lines)


def set_pending(text):
    st.session_state.pending_prompt = text


# ---------- Start-up state ----------
if "chat_id" not in st.session_state:
    start_new_chat()

# ---------- Sidebar ----------
with st.sidebar:
    if HAS_LOGO:
        st.image(LOGO_PATH, width=90)
    st.markdown(f"### {BOT_NAME}")
    st.caption(COMPANY_NAME)

    st.button("➕ New chat", use_container_width=True, on_click=start_new_chat)

    st.markdown("**🕘 Chat history**")
    saved = list_chats()
    if not saved:
        st.caption("No saved chats yet. Your chats are saved automatically.")
    for c in saved[:12]:
        is_current = c["id"] == st.session_state.chat_id
        st.button(
            "💬 " + c.get("title", "Chat"),
            key=f"chat_{c['id']}",
            use_container_width=True,
            type="primary" if is_current else "secondary",
            on_click=load_chat,
            args=(c["id"],),
        )

    if saved:
        with st.expander("🧹 Manage history"):
            if os.path.exists(chat_path(st.session_state.chat_id)):
                st.button("🗑️ Delete this chat", use_container_width=True, on_click=delete_current_chat)
            confirm = st.checkbox("Yes, I want to delete ALL saved chats")
            st.button(
                "Delete all chats",
                use_container_width=True,
                disabled=not confirm,
                on_click=delete_all_chats,
            )

    st.divider()
    st.markdown("**⚙️ Settings**")

    models = get_installed_models()
    if models is None:
        st.error("Ollama is not running. Open the Ollama app and refresh this page.")
        st.stop()
    if not models:
        st.warning(f"No model installed. Run in a terminal:\n\nollama pull {DEFAULT_MODEL}")
        st.stop()

    model = st.selectbox("AI model", models, index=0)
    persona = st.radio("Mode", list(PERSONAS.keys()))
    temperature = st.slider(
        "Creativity", 0.0, 1.0, 0.3, 0.1,
        help="Lower = more factual and consistent. Higher = more creative.",
    )

    if st.session_state.messages:
        st.download_button(
            "⬇️ Download this chat",
            build_chat_text(st.session_state.messages),
            file_name="chat.txt",
            use_container_width=True,
        )

    st.divider()
    st.caption("🔒 Runs locally. Your data never leaves this computer.")
    st.caption("🛡️ Safety filter: ON")
    st.caption("✅ Honesty rules: ON")

# ---------- Header ----------
logo_b64 = logo_base64()
if logo_b64:
    logo_html = f'<img class="hero-logo" src="data:image/png;base64,{logo_b64}">'
else:
    logo_html = '<div class="hero-emoji">🤖</div>'

st.markdown(
    f"""
    <div class="hero">
      {logo_html}
      <div>
        <div class="hero-title">{BOT_NAME}</div>
        <div class="hero-sub">{COMPANY_NAME} · {TAGLINE}</div>
        <span class="chip">🔒 Private</span>
        <span class="chip">🛡️ Safe</span>
        <span class="chip">✅ Honest</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Show chat ----------
pending = st.session_state.pop("pending_prompt", None)

if not st.session_state.messages and not pending:
    st.markdown("**Try asking:**")
    cols = st.columns(2)
    for i, q in enumerate(STARTER_QUESTIONS):
        cols[i % 2].button(
            q, key=f"starter_{i}", use_container_width=True,
            on_click=set_pending, args=(q,),
        )

for msg in st.session_state.messages:
    avatar = AVATAR if msg["role"] == "assistant" else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ---------- Handle a new message ----------
typed = st.chat_input("Type your question here...")
prompt = typed or pending

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=AVATAR):
        allowed, blocked_msg = check_input(prompt)

        if not allowed:
            reply = blocked_msg
            st.markdown(reply)
        else:
            placeholder = st.empty()
            reply = ""
            try:
                history = st.session_state.messages[-MAX_HISTORY:]
                messages = [{"role": "system", "content": PERSONAS[persona]}] + history

                stream = ollama.chat(
                    model=model,
                    messages=messages,
                    stream=True,
                    keep_alive="30m",
                    options={
                        "temperature": temperature,
                        "num_ctx": 1024,
                        "num_predict": MAX_ANSWER_TOKENS,
                    },
                )
                for chunk in stream:
                    reply += chunk["message"]["content"]
                    placeholder.markdown(reply + "▌")

                reply = check_output(reply)
                placeholder.markdown(reply)
            except Exception as e:
                reply = f"⚠️ Something went wrong while generating the answer: {e}"
                placeholder.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    save_chat()

st.markdown(
    f'<p class="footer-note">{BOT_NAME} can make mistakes. Please verify important information.</p>',
    unsafe_allow_html=True,
)
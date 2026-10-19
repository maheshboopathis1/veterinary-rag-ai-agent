# streamlit_app.py
import json
import uuid
from datetime import datetime

import requests
import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------
# Configuration
# --------------------------------------------------
st.set_page_config(
    page_title="VetCare AI",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_BASE_URL = "http://127.0.0.1:8000"
REQUEST_TIMEOUT = 120
SIDEBAR_WIDTH = 300  # px
MAX_SAVED_CHATS = 10

SUGGESTIONS = [
    ("🩺", "What are the early signs of dehydration in dogs and cats?"),
    ("🥣", "What are the key nutritional requirements for adult dogs?"),
    ("💊", "Show catalog products used to manage vomiting in dogs."),
    ("🧾", "I would like to prepare an invoice for a catalog product."),
]


# --------------------------------------------------
# Session state
# --------------------------------------------------
def _is_mobile() -> bool:
    try:
        ua = st.context.headers.get("User-Agent", "").lower()
        return any(k in ua for k in ("mobile", "android", "iphone"))
    except Exception:
        return False


def _valid_sid(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def load_history_from_backend(session_id: str) -> list[dict]:
    try:
        r = requests.get(f"{API_BASE_URL}/history/{session_id}", timeout=5)
        if r.ok:
            return [
                {"role": m["role"], "content": m["content"]}
                for m in r.json().get("messages", [])
            ]
    except requests.RequestException:
        pass
    return []


if "session_id" not in st.session_state:
    sid = st.query_params.get("sid")
    if sid and _valid_sid(sid):
        st.session_state.session_id = str(sid)
        st.session_state.messages = load_history_from_backend(str(sid))
        st.session_state.scroll_to_bottom = bool(st.session_state.messages)
    else:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
    st.query_params["sid"] = st.session_state.session_id
if "messages" not in st.session_state:
    st.session_state.messages = []

if "history" not in st.session_state:
    st.session_state.history = []
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
if "awaiting" not in st.session_state:
    st.session_state.awaiting = False
if "scroll_to_bottom" not in st.session_state:
    st.session_state.scroll_to_bottom = False  # used only when opening an old chat
if "scroll_count" not in st.session_state:
    st.session_state.scroll_count = 0
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = not _is_mobile()


# --------------------------------------------------
# Callbacks
# --------------------------------------------------
def toggle_sidebar() -> None:
    st.session_state.sidebar_open = not st.session_state.sidebar_open


def set_prompt(text: str) -> None:
    st.session_state.pending_prompt = text


def archive_current_chat() -> None:
    msgs = st.session_state.messages
    if not msgs:
        return
    first_user = next((m["content"] for m in msgs if m["role"] == "user"), "Chat")
    title = first_user if len(first_user) <= 34 else first_user[:34].rstrip() + "…"
    st.session_state.history.insert(
        0,
        {"id": st.session_state.session_id, "title": title, "messages": msgs},
    )
    del st.session_state.history[MAX_SAVED_CHATS:]


def new_chat() -> None:
    archive_current_chat()
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.pending_prompt = None
    st.session_state.awaiting = False
    st.query_params["sid"] = st.session_state.session_id


def open_chat(chat_id: str) -> None:
    target = next((h for h in st.session_state.history if h["id"] == chat_id), None)
    if target is None:
        return
    st.session_state.history.remove(target)
    archive_current_chat()
    st.session_state.session_id = target["id"]
    st.session_state.messages = target["messages"]
    st.session_state.pending_prompt = None
    st.session_state.awaiting = False
    st.session_state.scroll_to_bottom = True
    st.query_params["sid"] = st.session_state.session_id


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def scroll_to_latest_message() -> None:
    """
    Bring the START of the newest chat message into view.
    Called once while waiting (shows the 'Thinking...' area) and once when
    the answer arrives (shows the top of the answer, not the bottom).
    A counter in the HTML forces Streamlit to re-run the script each time.
    """
    st.session_state.scroll_count += 1
    components.html(
        """
        <script>
        // run id: %d
        const doc = window.parent.document;
        const go = () => {
            const msgs = doc.querySelectorAll('[data-testid="stChatMessage"]');
            if (msgs.length) {
                msgs[msgs.length - 1].scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        };
        setTimeout(go, 120);
        setTimeout(go, 500);
        </script>
        """
        % st.session_state.scroll_count,
        height=0,
    )


def build_transcript() -> str:
    lines = [
        "VetCare AI - Conversation transcript",
        f"Session: {st.session_state.session_id}",
        f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 50,
        "",
    ]
    for m in st.session_state.messages:
        who = "You" if m["role"] == "user" else "VetCare AI"
        lines.append(f"{who}:")
        lines.append(m["content"])
        lines.append("")
    lines.append("-" * 50)
    lines.append("AI responses do not replace professional veterinary advice.")
    return "\n".join(lines)

def submit_feedback(idx: int) -> None:
    key = f"fb_{st.session_state.session_id[:8]}_{idx}"
    value = st.session_state.get(key)  # st.feedback("thumbs"): 1 = up, 0 = down
    if value is None or idx >= len(st.session_state.messages):
        return
    msg = st.session_state.messages[idx]
    msg["feedback"] = value
    try:
        requests.post(
            f"{API_BASE_URL}/feedback",
            json={
                "session_id": st.session_state.session_id,
                "rating": "up" if value == 1 else "down",
                "message_excerpt": msg["content"][:500],
            },
            timeout=5,
        )
    except requests.RequestException:
        pass


def copy_button(text: str) -> None:
    payload = json.dumps(text).replace("</", "<\\/")
    components.html(
        f"""
        <style>
          body {{ margin: 0; }}
          button {{
            font: 500 12px Inter, system-ui, sans-serif; color: #64748B;
            background: transparent; border: 1px solid #E2E8F0;
            border-radius: 8px; padding: 5px 10px; cursor: pointer;
          }}
          button:hover {{ color: #0F766E; border-color: #0F766E; }}
        </style>
        <button id="b" type="button">⧉ Copy</button>
        <script>
          const text = {payload};
          const btn = document.getElementById('b');
          function fallback() {{
            const t = document.createElement('textarea');
            t.value = text; document.body.appendChild(t); t.select();
            try {{ document.execCommand('copy'); }} catch (e) {{}}
            document.body.removeChild(t);
          }}
          btn.onclick = async () => {{
            try {{ await navigator.clipboard.writeText(text); }} catch (e) {{ fallback(); }}
            btn.textContent = '✓ Copied';
            setTimeout(() => btn.textContent = '⧉ Copy', 1500);
          }};
        </script>
        """,
        height=36,
    )


def render_message_actions(idx: int, message: dict) -> None:
    key = f"fb_{st.session_state.session_id[:8]}_{idx}"
    if key not in st.session_state and message.get("feedback") is not None:
        st.session_state[key] = message["feedback"]

    c_copy, c_fb, _ = st.columns([0.22, 0.22, 0.56], vertical_alignment="center")
    with c_copy:
        copy_button(message["content"])
    with c_fb:
        st.feedback("thumbs", key=key, on_change=submit_feedback, args=(idx,))


@st.dialog("Invoice sent")
def invoice_sent_dialog(invoice_number: str | None, email: str | None) -> None:
    st.markdown("✅  **Your invoice email was submitted successfully.**")
    if email:
        st.markdown(f"**Recipient:** {email}")
    if invoice_number:
        st.markdown(f"**Invoice number:** `{invoice_number}`")
    st.caption(
        "Please check your inbox or spam folder. "
        "Successful submission does not guarantee delivery."
    )
    if st.button("Done", type="primary", use_container_width=True):
        st.rerun()

# --------------------------------------------------
# Styling
# --------------------------------------------------
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {{
        --text-main: #0F172A;
        --text-muted: #64748B;
        --bg-page: #F8FAFC;
        --bg-sidebar: #F1F5F9;
        --bg-user: #E6F4F1;
        --bg-card: #FFFFFF;
        --accent: #0F766E;
        --accent-dark: #115E59;
        --border: #E2E8F0;
        --ok: #059669;
        --bad: #DC2626;
        --sidebar-w: {SIDEBAR_WIDTH}px;
    }}

    .stApp {{ color-scheme: light; }}
    html, body, .stApp, button, textarea, input {{
        font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif !important;
    }}
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {{
        background: var(--bg-page) !important;
        color: var(--text-main);
    }}
    .stApp :where(p, li, label, h1, h2, h3, h4) {{ color: var(--text-main); }}

    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"],
    [data-testid="stExpandSidebarButton"],
    #MainMenu, footer {{ display: none !important; }}

    .block-container,
    [data-testid="stMainBlockContainer"] {{
        max-width: 860px;
        padding-top: 1.25rem;
        padding-bottom: 9rem;
    }}
    html {{ scroll-behavior: smooth; }}
    [data-testid="stMain"] {{ overflow-anchor: none; }}

    /* Keeps a little space above a message when we scroll to it */
    [data-testid="stChatMessage"] {{ scroll-margin-top: 1rem; }}

    /* ---------- Custom sidebar ---------- */
    .st-key-mysidebar {{
        position: fixed;
        top: 0; left: 0; bottom: 0;
        width: var(--sidebar-w);
        z-index: 1000;
        box-sizing: border-box;
        padding: 1.25rem 1rem;
        background: var(--bg-sidebar);
        border-right: 1px solid var(--border);
        overflow-y: auto;
        overflow-x: hidden;
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }}
    .brand {{
        display: flex; align-items: center; gap: 10px;
        font-size: 1.15rem; font-weight: 700; color: var(--text-main);
        padding-bottom: 1rem; margin-bottom: 0.5rem;
        border-bottom: 1px solid var(--border);
    }}
    .brand-mark {{
        width: 32px; height: 32px; border-radius: 9px; background: var(--accent);
        display: flex; align-items: center; justify-content: center; font-size: 17px;
    }}
    .sidebar-heading {{
        color: var(--text-main); font-size: 0.85rem; font-weight: 600;
        margin: 1.25rem 0 0.2rem;
    }}
    .sidebar-caption {{ color: var(--text-muted); font-size: 0.85rem; line-height: 1.55; }}
    .sidebar-status {{ font-size: 0.85rem; font-weight: 500; }}
    .sidebar-status.online {{ color: var(--ok); }}
    .sidebar-status.offline {{ color: var(--bad); }}

    .st-key-mysidebar .stButton > button,
    .st-key-mysidebar [data-testid="stDownloadButton"] button {{
        min-height: 2.5rem; padding: 0 0.8rem;
    }}
    .st-key-mysidebar .stButton > button p {{
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%;
    }}
    [class*="st-key-hist_"] button {{
        background: transparent !important;
        border-color: transparent !important;
        box-shadow: none !important;
        font-size: 0.85rem !important;
        min-height: 2.25rem !important;
    }}
    [class*="st-key-hist_"] button:hover {{
        background: var(--bg-card) !important;
        border-color: var(--border) !important;
    }}

    .side-card {{
        background: var(--bg-card); border: 1px solid var(--border);
        border-radius: 12px; padding: 0.55rem 0.9rem; margin-top: 0.35rem;
    }}
    .side-item {{
        display: flex; gap: 10px; align-items: flex-start;
        padding: 0.4rem 0; font-size: 0.8rem; color: var(--text-muted); line-height: 1.4;
    }}
    .side-item b {{ display: block; color: var(--text-main); font-weight: 600; font-size: 0.85rem; }}
    .side-row {{
        display: flex; justify-content: space-between;
        font-size: 0.82rem; padding: 0.25rem 0; color: var(--text-muted);
    }}
    .side-row span:last-child {{ color: var(--text-main); font-weight: 500; }}

    [class*="st-key-sideq_"] button {{
        min-height: 2.25rem !important; font-size: 0.82rem !important;
        padding: 0 0.7rem !important; box-shadow: none !important;
    }}

    /* Pin the bottom group to the bottom of the sidebar */
    .st-key-sidebar_bottom {{
        margin-top: auto; padding-top: 1rem; border-top: 1px solid var(--border);
    }}
    .st-key-toggle_side button {{
        min-height: 2.5rem !important; background: var(--bg-card) !important;
        border: 1px solid var(--border) !important; color: var(--text-main) !important;
        box-shadow: none !important;
    }}
    .st-key-toggle_side button:hover {{
        border-color: var(--accent) !important; color: var(--accent) !important;
    }}

    /* Download button: same look as other secondary buttons */
    [data-testid="stDownloadButton"] button {{
        border-radius: 12px;
        border: 1px solid var(--border);
        background: var(--bg-card);
        color: var(--text-main);
        font-size: 0.9rem;
        font-weight: 500;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }}
    [data-testid="stDownloadButton"] button:hover {{
        border-color: var(--accent); color: var(--accent);
    }}
    [data-testid="stDownloadButton"] button p {{ color: inherit !important; margin: 0; }}

    /* ---------- Top bar ---------- */
    .st-key-topbar {{
        border-bottom: 1px solid var(--border);
        padding-bottom: 0.75rem;
        margin-bottom: 1.5rem;
    }}
    .topbar-title {{ font-size: 1rem; font-weight: 600; color: var(--text-main); line-height: 1.25; }}
    .topbar-sub {{ font-size: 0.78rem; color: var(--text-muted); }}
    .status-pill {{
        display: inline-flex; align-items: center; gap: 6px;
        font-size: 0.8rem; font-weight: 500;
        padding: 4px 10px; border-radius: 999px;
        border: 1px solid var(--border); background: var(--bg-card);
        float: right;
    }}
    .status-pill::before {{
        content: ""; width: 8px; height: 8px; border-radius: 50%; background: currentColor;
    }}
    .status-pill.online {{ color: var(--ok); }}
    .status-pill.offline {{ color: var(--bad); }}

    /* ---------- Buttons (default look = suggestion cards) ---------- */
    .stButton > button {{
        border-radius: 12px;
        border: 1px solid var(--border);
        background: var(--bg-card);
        color: var(--text-main);
        font-size: 0.9rem;
        font-weight: 500;
        min-height: 3.75rem;
        padding: 0.75rem 1rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        transition: border-color .15s ease, box-shadow .15s ease, color .15s ease;
    }}
    .stButton > button > div {{ justify-content: flex-start; }}
    .stButton > button p {{ text-align: left; margin: 0; color: inherit !important; }}
    .stButton > button:hover,
    .stButton > button:focus-visible {{
        border-color: var(--accent);
        color: var(--accent);
        box-shadow: 0 4px 12px rgba(15, 118, 110, 0.10);
    }}

    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {{
        background: var(--accent);
        border-color: var(--accent);
        color: #FFFFFF;
        box-shadow: none;
    }}
    .stButton > button[kind="primary"] > div,
    .stButton > button[data-testid="stBaseButton-primary"] > div {{ justify-content: center; }}
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {{
        background: var(--accent-dark); border-color: var(--accent-dark); color: #FFFFFF;
    }}

    .st-key-toggle_top button {{
        width: 2.5rem; min-height: 2.5rem; padding: 0; box-shadow: none;
    }}
    .st-key-toggle_top button > div {{ justify-content: center; }}

    /* ---------- Welcome ---------- */
    .welcome {{ text-align: center; padding: 3rem 1rem 1.5rem; }}
    .welcome-icon {{
        width: 64px; height: 64px; margin: 0 auto 1.25rem;
        border-radius: 18px; background: var(--accent);
        display: flex; align-items: center; justify-content: center; font-size: 30px;
    }}
    .welcome h1 {{
        font-size: 2rem; font-weight: 700; letter-spacing: -0.02em;
        color: var(--text-main); margin: 0 0 0.6rem; padding: 0;
    }}
    .welcome p {{
        color: var(--text-muted); font-size: 1rem; line-height: 1.6;
        max-width: 480px; margin: 0 auto;
    }}
    .section-label {{
        color: var(--text-muted); font-size: 0.85rem; font-weight: 500;
        margin: 2rem 0 0.75rem;
    }}

    /* ---------- Chat messages ---------- */
    [data-testid="stChatMessage"] {{
        padding: 1.1rem 1.25rem;
        border-radius: 14px;
        margin-bottom: 0.9rem;
        border: 1px solid transparent;
        gap: 0.9rem;
    }}
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
        background: var(--bg-user);
    }}
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {{
        background: var(--bg-card);
        border-color: var(--border);
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }}
    [data-testid="stChatMessageAvatarAssistant"] {{ background: var(--accent) !important; color: #fff !important; }}
    [data-testid="stChatMessageAvatarUser"] {{ background: #475569 !important; color: #fff !important; }}

    [data-testid="stChatMessageContent"] {{
        color: var(--text-main); font-size: 0.95rem; line-height: 1.65;
    }}
    [data-testid="stChatMessageContent"] table {{
        border-collapse: collapse; width: 100%; font-size: 0.88rem;
    }}
    [data-testid="stChatMessageContent"] th {{
        background: var(--bg-sidebar); text-align: left;
        border: 1px solid var(--border); padding: 8px 10px;
    }}
    [data-testid="stChatMessageContent"] td {{
        border: 1px solid var(--border); padding: 8px 10px;
    }}
    [data-testid="stChatMessageContent"] code {{
        background: var(--bg-sidebar); color: var(--accent-dark);
        padding: 1px 6px; border-radius: 6px;
    }}
    [data-testid="stSpinner"] * {{ color: var(--text-muted) !important; }}
    [data-testid="stAlert"] * {{ color: #7F1D1D !important; }}

    /* ---------- Chat input ---------- */
    [data-testid="stBottom"],
    [data-testid="stBottom"] > div {{
        background: var(--bg-page) !important;
    }}
    [data-testid="stBottomBlockContainer"] {{
        max-width: 860px;
        padding-top: 0.5rem;
        padding-bottom: 1.25rem;
    }}
    [data-testid="stChatInput"] {{
        background: var(--bg-card) !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 28px !important;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
        padding: 4px 6px 4px 14px;
        transition: border-color .15s ease, box-shadow .15s ease;
    }}
    [data-testid="stChatInput"]:focus-within {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.15), 0 8px 24px rgba(15, 23, 42, 0.08);
    }}
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] textarea {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }}
    [data-testid="stChatInput"] textarea {{
        color: var(--text-main) !important;
        font-size: 0.95rem;
        min-height: 44px;
    }}
    [data-testid="stChatInput"] textarea::placeholder {{ color: var(--text-muted) !important; opacity: 1; }}
    [data-testid="stChatInputSubmitButton"] {{
        background: var(--accent) !important;
        color: #FFFFFF !important;
        border-radius: 50% !important;
        width: 36px; height: 36px;
    }}
    [data-testid="stChatInputSubmitButton"]:hover {{ background: var(--accent-dark) !important; }}
    [data-testid="stChatInputSubmitButton"]:disabled {{ background: #CBD5E1 !important; }}
    [data-testid="stChatInputSubmitButton"] svg {{ fill: #FFFFFF; color: #FFFFFF; }}

    .footer-note {{
        color: var(--text-muted); font-size: 0.78rem; text-align: center; padding-top: 0.75rem;
    }}

    @media (max-width: 900px) {{
        .st-key-mysidebar {{
            width: min(var(--sidebar-w), 85vw);
            box-shadow: 8px 0 24px rgba(15, 23, 42, 0.18);
        }}
        .welcome h1 {{ font-size: 1.6rem; }}
        .block-container, [data-testid="stMainBlockContainer"] {{
            padding-left: 1rem; padding-right: 1rem;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.sidebar_open:
    st.markdown(
        f"""
        <style>
        @media (min-width: 901px) {{
            [data-testid="stAppViewContainer"] {{
                padding-left: {SIDEBAR_WIDTH}px;
                box-sizing: border-box;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------
# Backend integration
# --------------------------------------------------
def send_message(message: str) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/chat",
        json={"message": message, "session_id": st.session_state.session_id},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    data = response.json()
    answer = data.get("response")
    if answer is None:
        raise ValueError("The backend response does not contain a 'response' field.")

    return {
        "answer": str(answer),
        "invoice_sent": bool(data.get("invoice_sent")),
        "invoice_number": data.get("invoice_number"),
        "invoice_email": data.get("invoice_email"),
    }


@st.cache_data(ttl=10, show_spinner=False)
def backend_is_available() -> bool:
    try:
        return requests.get(f"{API_BASE_URL}/health", timeout=3).ok
    except requests.RequestException:
        return False


online = backend_is_available()


# --------------------------------------------------
# Read new input first
# --------------------------------------------------
typed = st.chat_input("Message VetCare AI…")
prompt = st.session_state.pending_prompt or typed
st.session_state.pending_prompt = None

if prompt and prompt.strip():
    st.session_state.messages.append({"role": "user", "content": prompt.strip()})
    st.session_state.awaiting = True


# --------------------------------------------------
# Sidebar
# --------------------------------------------------
if st.session_state.sidebar_open:
    with st.container(key="mysidebar"):
        st.markdown(
            '<div class="brand"><div class="brand-mark">🐾</div>VetCare AI</div>',
            unsafe_allow_html=True,
        )

        st.button(
            "New chat",
            key="new_chat",
            type="primary",
            use_container_width=True,
            icon=":material/add:",
            on_click=new_chat,
        )

        if st.session_state.messages:
            st.download_button(
                "Download conversation",
                data=build_transcript(),
                file_name=f"vetcare-chat-{st.session_state.session_id[:8]}.txt",
                mime="text/plain",
                key="download_chat",
                use_container_width=True,
                icon=":material/download:",
            )

        if st.session_state.history:
            st.markdown('<div class="sidebar-heading">Recent chats</div>', unsafe_allow_html=True)
            for item in st.session_state.history:
                st.button(
                    item["title"],
                    key=f"hist_{item['id']}",
                    use_container_width=True,
                    on_click=open_chat,
                    args=(item["id"],),
                )

        st.markdown('<div class="sidebar-heading">What I can help with</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="side-card">
              <div class="side-item"><span>🩺</span><div><b>Veterinary knowledge</b>Answers from reference documents</div></div>
              <div class="side-item"><span>💊</span><div><b>Product search</b>Find catalog products by animal, disease or ingredient</div></div>
              <div class="side-item"><span>🧾</span><div><b>Invoices</b>Email an invoice for verified products</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sidebar-heading">Quick prompts</div>', unsafe_allow_html=True)
        for i, (icon, text) in enumerate(SUGGESTIONS[:3]):
            short = text if len(text) <= 30 else text[:30].rstrip() + "…"
            st.button(
                f"{icon}  {short}",
                key=f"sideq_{i}",
                use_container_width=True,
                on_click=set_prompt,
                args=(text,),
            )

        st.markdown('<div class="sidebar-heading">System</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="side-card">
              <div class="side-row"><span>Service</span>
                <span class="sidebar-status {"online" if online else "offline"}">
                  ● {"Online" if online else "Offline"}</span></div>
              <div class="side-row"><span>Session</span><span>{st.session_state.session_id[:8]}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(key="sidebar_bottom"):
            st.button(
                "Collapse sidebar",
                key="toggle_side",
                use_container_width=True,
                icon=":material/left_panel_close:",
                on_click=toggle_sidebar,
            )
            st.markdown(
                '<div class="sidebar-caption" style="font-size:0.74rem; margin-top:0.6rem;">'
                "AI responses do not replace professional veterinary advice.</div>",
                unsafe_allow_html=True,
            )


# --------------------------------------------------
# Top bar
# --------------------------------------------------
with st.container(key="topbar"):
    c_toggle, c_title, c_status = st.columns([0.09, 0.61, 0.30], vertical_alignment="center")
    with c_toggle:
        st.button("☰", key="toggle_top", on_click=toggle_sidebar, help="Show or hide the sidebar")
    with c_title:
        st.markdown(
            '<div class="topbar-title">VetCare Assistant</div>'
            '<div class="topbar-sub">Veterinary knowledge, products and invoices</div>',
            unsafe_allow_html=True,
        )
    with c_status:
        st.markdown(
            f'<span class="status-pill {"online" if online else "offline"}">'
            f'{"Connected" if online else "Offline"}</span>',
            unsafe_allow_html=True,
        )


# --------------------------------------------------
# Welcome screen (only before the first message)
# --------------------------------------------------
if not st.session_state.messages:
    st.markdown(
        """
        <div class="welcome">
            <div class="welcome-icon">🐾</div>
            <h1>How can I help you today?</h1>
            <p>Ask a veterinary question, search the product catalog,
            or request an invoice.</p>
        </div>
        <div class="section-label">Suggested questions</div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    for index, (icon, text) in enumerate(SUGGESTIONS):
        with (col1 if index % 2 == 0 else col2):
            st.button(
                f"{icon}  {text}",
                key=f"sug_{index}",
                use_container_width=True,
                on_click=set_prompt,
                args=(text,),
            )


# --------------------------------------------------
# Chat history
# --------------------------------------------------
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message.get("error"):
            st.error(message["content"])
        else:
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_message_actions(idx, message)


# --------------------------------------------------
# Get the assistant's answer
# --------------------------------------------------
if st.session_state.awaiting and st.session_state.messages:
    last_user_message = st.session_state.messages[-1]["content"]
    answer, error_text, result = None, None, None

    with st.chat_message("assistant"):
        scroll_to_latest_message()

        try:
            with st.spinner("Thinking…"):
                result = send_message(last_user_message)
                answer = result["answer"]
        except requests.Timeout:
            error_text = "The request timed out. Please try again."
        except requests.HTTPError:
            error_text = (
                "The assistant could not process your request. "
                "Please try again in a moment."
            )
        except requests.RequestException:
            error_text = (
                "Unable to reach the service right now. "
                "Please check your connection and try again."
            )
        except (ValueError, TypeError, KeyError):
            error_text = "The service returned an unexpected response. Please try again."

        if error_text:
            st.error(error_text)
        else:
            st.markdown(answer)
            render_message_actions(
                len(st.session_state.messages), {"content": answer}
            )

    if error_text:
        st.session_state.messages.append(
            {"role": "assistant", "content": error_text, "error": True}
        )
    else:
        st.session_state.messages.append({"role": "assistant", "content": answer})

    st.session_state.awaiting = False
    scroll_to_latest_message()

    if result and result.get("invoice_sent"):
        invoice_sent_dialog(result.get("invoice_number"), result.get("invoice_email"))


# --------------------------------------------------
# Footer
# --------------------------------------------------
if st.session_state.messages:
    st.markdown(
        '<div class="footer-note">VetCare AI can make mistakes. '
        "Consult a veterinarian for critical care.</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------
# Scroll after opening a saved chat
# --------------------------------------------------
if st.session_state.scroll_to_bottom:
    scroll_to_latest_message()
    st.session_state.scroll_to_bottom = False

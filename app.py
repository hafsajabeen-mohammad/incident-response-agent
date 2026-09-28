import json
import os
import re
import html
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from hindsight_memory import get_memory, save_memory

BASE_DIR = Path(__file__).resolve().parent
# Load .env from this project folder; also check its parent folders so moving
# the project one level deeper does not silently break configuration.
for _env_path in [BASE_DIR / ".env", BASE_DIR.parent / ".env", BASE_DIR.parent.parent / ".env"]:
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path, override=False)
        break
else:
    load_dotenv()
DATA_FILE = BASE_DIR / "data" / "tickets.csv"
HISTORY_FILE = BASE_DIR / "data" / "investigated_incidents.json"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
HINDSIGHT_URL = os.getenv("HINDSIGHT_URL", "https://api.hindsight.vectorize.io").strip()
BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "incident-response").strip()

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

st.set_page_config(
    page_title="Incident Response Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>

    /* =====================================================
       COLOR PALETTE
       ===================================================== */
    :root {
        --black: #050b14;
        --navy: #071426;
        --navy2: #0b1d35;
        --blue: #1677ff;
        --blue2: #2196ff;
        --light-blue: #7dd3fc;

        --text: #eaf4ff;
        --text2: #c7d9ee;
        --muted: #8da4bd;

        --card: #0b1b30;
        --card2: #0e2440;
        --input: #08172a;
        --line: #1d4f7a;
    }


    /* =====================================================
       MAIN APPLICATION BACKGROUND
       ===================================================== */

    html,
    body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stApp"] {
        background:
            radial-gradient(
                circle at 15% 10%,
                rgba(22,119,255,0.15),
                transparent 35%
            ),
            radial-gradient(
                circle at 90% 80%,
                rgba(33,150,255,0.10),
                transparent 35%
            ),
            var(--black) !important;

        color: var(--text) !important;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    .block-container {
        max-width: 1220px !important;
        padding-top: 1.7rem !important;
    }


    /* =====================================================
       TEXT
       ===================================================== */

    h1, h2, h3, h4, h5, h6 {
        color: var(--text) !important;
    }

    p,
    label,
    span {
        color: var(--text2) !important;
    }

    .stMarkdown,
    .stCaption {
        color: var(--text2) !important;
    }

    .muted {
        color: var(--muted) !important;
    }


    /* =====================================================
       SIDEBAR
       ===================================================== */

    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div {
        background:
            linear-gradient(
                180deg,
                #030914 0%,
                #071426 55%,
                #081b32 100%
            ) !important;

        border-right: 1px solid #12395f !important;
    }

    [data-testid="stSidebar"] * {
        color: var(--text) !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: #173957 !important;
    }

    .brand {
        font-size: 25px;
        font-weight: 800;
        color: #ffffff !important;
    }

    .sub {
        color: #8fb3d8 !important;
        font-size: 13px;
        margin-top: 5px;
    }


    /* =====================================================
       SIDEBAR STATUS
       ===================================================== */

    .status {
        background: #0a1b31;
        border: 1px solid #174a78;
        border-radius: 12px;
        padding: 12px 14px;
        margin: 8px 0;
        color: #dceeff !important;

        box-shadow:
            0 4px 15px rgba(0,0,0,0.25);
    }

    .status .dot {
        color: #38bdf8 !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label,
    [data-testid="stSidebar"] [data-testid="stRadio"] label p {
        color: #dceeff !important;
    }


    /* =====================================================
       METRIC CARDS
       ===================================================== */

    .metric {
        background:
            linear-gradient(
                145deg,
                #0b1d35,
                #071426
            ) !important;

        border: 1px solid #164b79;
        border-radius: 16px;

        padding: 20px 22px;

        box-shadow:
            0 8px 25px rgba(0,0,0,0.30),
            inset 0 1px 0 rgba(125,211,252,0.05);
    }

    .metric-title {
        color: #8fb3d8 !important;
        font-size: 13px;
    }

    .metric-value {
        color: #eaf6ff !important;
        font-size: 27px;
        font-weight: 800;
        margin-top: 10px;
    }


    /* =====================================================
       INCIDENT / MEMORY / AI / HISTORY CARDS
       ===================================================== */

    .incident-card,
    .memory-card,
    .ai-card,
    .history-card {

        background:
            linear-gradient(
                145deg,
                #0c2039,
                #071527
            ) !important;

        border: 1px solid #164b79;
        border-radius: 15px;

        padding: 20px;
        margin: 10px 0;

        box-shadow:
            0 7px 22px rgba(0,0,0,0.30);
    }

    .incident-card {
        border-left: 5px solid #2196ff;
    }

    .memory-card {
        border-left: 4px solid #38bdf8;
    }

    .ai-card {
        border-left: 5px solid #1677ff;
    }

    .history-card {
        border-left: 4px solid #60a5fa;
    }

    .memory-title {
        color: #eaf6ff !important;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .memory-text {
        color: #c7d9ee !important;
        line-height: 1.65;
    }


    /* =====================================================
       TEXT INPUTS / TEXT AREAS
       ===================================================== */

    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {

        background: #08172a !important;
        background-color: #08172a !important;

        color: #eaf6ff !important;
        -webkit-text-fill-color: #eaf6ff !important;

        border: 1px solid #245b88 !important;
        border-radius: 10px !important;

        box-shadow:
            inset 0 1px 4px rgba(0,0,0,0.25);
    }

    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stTextArea"] textarea::placeholder {
        color: #7590aa !important;
        -webkit-text-fill-color: #7590aa !important;
    }

    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {

        border-color: #2196ff !important;

        box-shadow:
            0 0 0 1px #2196ff,
            0 0 12px rgba(33,150,255,0.20) !important;
    }


    /* =====================================================
       SELECT BOX
       ===================================================== */

    [data-testid="stSelectbox"] [data-baseweb="select"],
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] [role="combobox"] {

        background: #08172a !important;
        background-color: #08172a !important;

        border-color: #245b88 !important;
        color: #eaf6ff !important;

        border-radius: 10px !important;

        -webkit-text-fill-color: #eaf6ff !important;
    }

    [data-testid="stSelectbox"] [data-baseweb="select"] *,
    [data-testid="stSelectbox"] [role="combobox"],
    [data-testid="stSelectbox"] input {

        color: #eaf6ff !important;
        -webkit-text-fill-color: #eaf6ff !important;
    }

    [data-testid="stSelectbox"] svg {
        color: #38bdf8 !important;
        fill: #38bdf8 !important;
    }


    /* =====================================================
       DROPDOWN MENU
       ===================================================== */

    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [data-baseweb="popover"] [data-baseweb="menu"],
    [data-baseweb="menu"],
    [role="listbox"] {

        background: #0a1b31 !important;
        background-color: #0a1b31 !important;

        border: 1px solid #245b88 !important;

        color: #eaf6ff !important;
    }

    [data-baseweb="menu"] li,
    [data-baseweb="menu"] [role="option"],
    [role="listbox"] [role="option"] {

        background: #0a1b31 !important;
        color: #eaf6ff !important;

        -webkit-text-fill-color: #eaf6ff !important;
    }

    [data-baseweb="menu"] li *,
    [data-baseweb="menu"] [role="option"] *,
    [role="listbox"] [role="option"] * {

        color: #eaf6ff !important;
        -webkit-text-fill-color: #eaf6ff !important;
    }

    [data-baseweb="menu"] li:hover,
    [data-baseweb="menu"] [role="option"]:hover,
    [role="listbox"] [role="option"]:hover {

        background: #123a63 !important;
        color: #ffffff !important;
    }


    /* =====================================================
       BUTTONS
       ===================================================== */

    .stButton > button {

        background:
            linear-gradient(
                135deg,
                #1677ff,
                #0756c9
            ) !important;

        color: #ffffff !important;

        border: 1px solid #3698ff !important;

        border-radius: 10px !important;

        min-height: 46px !important;

        font-weight: 700 !important;

        box-shadow:
            0 5px 15px rgba(22,119,255,0.25);
    }

    .stButton > button:hover {

        background:
            linear-gradient(
                135deg,
                #2196ff,
                #1677ff
            ) !important;

        box-shadow:
            0 7px 20px rgba(33,150,255,0.35);
    }

    .stButton > button p {
        color: #ffffff !important;
    }


    /* =====================================================
       TABS
       ===================================================== */

    [data-baseweb="tab-list"] {
        background: #071426 !important;
        border-radius: 10px;
        padding: 4px;
    }

    [data-baseweb="tab"] {
        color: #9bb6d1 !important;
        background: transparent !important;
    }

    [data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        background: #123a63 !important;
        border-radius: 8px;
    }


    /* =====================================================
       DATAFRAME
       ===================================================== */

    [data-testid="stDataFrame"] {

        background: #08172a !important;
        border: 1px solid #164b79 !important;
        border-radius: 12px !important;
    }


    /* =====================================================
       ALERTS / NOTES
       ===================================================== */

    [data-testid="stAlert"] {
        border-radius: 12px !important;
        background: #0b1d35 !important;
    }

    [data-testid="stAlert"] p {
        color: #dceeff !important;
    }

    [data-testid="stAlert"] svg {
        color: #38bdf8 !important;
    }


    /* =====================================================
       CUSTOM NOTES
       ===================================================== */

    .neutral-note {
        background: #0b2340;
        border: 1px solid #245b88;
        border-radius: 12px;

        padding: 14px 16px;

        color: #cce8ff !important;
        margin: 10px 0;
    }

    .success-note {
        background: #06271f;
        border: 1px solid #087f63;
        border-radius: 12px;

        padding: 14px 16px;

        color: #9ff3dc !important;
        margin: 10px 0;
    }

    .error-note {
        background: #2b1015;
        border: 1px solid #8f2838;
        border-radius: 12px;

        padding: 14px 16px;

        color: #ffb4bd !important;
        margin: 10px 0;
    }

    .warning-note {
        background: #2b1d08;
        border: 1px solid #9a6a16;
        border-radius: 12px;

        padding: 14px 16px;

        color: #ffd98a !important;
        margin: 10px 0;
    }


    /* =====================================================
       EXPANDERS
       ===================================================== */

    [data-testid="stExpander"] {

        background: #0b1d35 !important;

        border: 1px solid #164b79 !important;

        border-radius: 12px !important;
    }

    [data-testid="stExpander"] summary {
        color: #eaf6ff !important;
    }


    /* =====================================================
       FILE / UPLOAD / MISC STREAMLIT AREAS
       ===================================================== */

    [data-testid="stFileUploader"] {
        background: #08172a !important;
        border: 1px solid #164b79 !important;
        border-radius: 12px !important;
    }


    /* =====================================================
       SCROLLBAR
       ===================================================== */

    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #030914;
    }

    ::-webkit-scrollbar-thumb {
        background: #164b79;
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #2196ff;
    }


    /* =====================================================
       HIDE STREAMLIT DEFAULT FOOTER / MENU
       ===================================================== */

    footer {
        visibility: hidden;
    }

    #MainMenu {
        visibility: hidden;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- Helpers --------------------
def clean_memory(text: str) -> str:
    text = html.unescape(str(text))
    text = re.sub(r"\s*\|\s*(?:When|Date):\s*\d{4}-\d{2}-\d{2}", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def load_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE).fillna("")
    return df[(df["type"].str.lower() == "incident") & (df["language"].str.lower() == "en")].copy()


def load_investigated() -> list:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_investigated(item: dict) -> None:
    records = load_investigated()
    records.insert(0, item)
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(records[:100], indent=2, ensure_ascii=False), encoding="utf-8")


def render_note(kind: str, text: str):
    st.markdown(f'<div class="{kind}-note">{html.escape(text)}</div>', unsafe_allow_html=True)


def analyze_with_groq(incident_text: str, memories: list) -> str:
    if not groq_client:
        raise RuntimeError("GROQ_API_KEY is missing in .env")

    memory_text = "\n\n".join(
        f"Historical Incident {i}:\n{clean_memory(m)}" for i, m in enumerate(memories, 1)
    ) or "No relevant historical incidents were found."

    prompt = f"""You are an Incident Response Agent for an IT operations team.

CURRENT INCIDENT
{incident_text}

HISTORICAL MEMORY RETRIEVED FROM HINDSIGHT
{memory_text}

Use historical memory as evidence. Never invent previous incidents, fixes,
outcomes, dates, versions, commands, or infrastructure details.

Return exactly these sections:

### Incident Summary
Briefly summarize the current incident.

### Similar Historical Incidents
Identify the most relevant remembered incidents and explain the connection.
If none are relevant, say so.

### Previous Resolutions
List only actions explicitly supported by the historical memory.

### Recommended Response
Give a practical ordered troubleshooting plan. Clearly distinguish historical
remedies from new diagnostic checks.

### Information Gap
List the information an engineer should collect before confirming root cause.

Keep the response concise and useful for an IT engineer."""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a professional IT incident response analyst."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def local_fallback_memories(df: pd.DataFrame, query: str, limit: int = 5) -> list:
    """Fallback only when Hindsight is unreachable; Hindsight remains the primary memory source."""
    terms = [t for t in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(t) > 3]
    if not terms:
        return []
    scores = []
    for _, row in df.iterrows():
        text = f"{row['subject']} {row['body']} {row['answer']}".lower()
        score = sum(1 for t in terms if t in text)
        if score:
            scores.append((score, row))
    scores.sort(key=lambda x: x[0], reverse=True)
    out = []
    for _, row in scores[:limit]:
        out.append(
            f"Subject: {row['subject']}\nDescription: {row['body']}\nPrevious Resolution: {row['answer']}"
        )
    return out

# -------------------- Sidebar --------------------
with st.sidebar:
    st.markdown('<div class="brand">🛡️ Incident Response</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub">AI-powered incident investigation</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["🚨 Report Incident", "📋 Incident History"],
        label_visibility="collapsed",
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div style='font-weight:800;'>System Status</div>", unsafe_allow_html=True)

    hindsight_ready = bool(os.getenv("HINDSIGHT_API_KEY", "").strip())
    groq_ready = bool(GROQ_API_KEY)
    st.markdown(
        f'<div class="status"><span class="dot">●</span>&nbsp; '
        f'Hindsight configured: {"Yes" if hindsight_ready else "No"}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="status"><span class="dot">●</span>&nbsp; '
        f'AI Engine configured: {"Yes" if groq_ready else "No"}</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Memory bank: {BANK_ID}")

# -------------------- Report page --------------------
if page == "🚨 Report Incident":
    st.markdown("# 🛡️ Incident Response Agent")
    st.markdown("AI-powered incident investigation with persistent organizational memory.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="metric"><div class="metric-title">🚨 Incident Status</div><div class="metric-value">READY</div></div>', unsafe_allow_html=True)
    with c2:
        memory_status = "ACTIVE" if hindsight_ready else "SETUP"
        st.markdown(f'<div class="metric"><div class="metric-title">🧠 Memory System</div><div class="metric-value">{memory_status}</div></div>', unsafe_allow_html=True)
    with c3:
        ai_status = "ONLINE" if groq_ready else "SETUP"
        st.markdown(f'<div class="metric"><div class="metric-title">⚙️ AI Engine</div><div class="metric-value">{ai_status}</div></div>', unsafe_allow_html=True)

    st.markdown("## 🚨 Report New Incident")
    st.write("Describe the incident and let the agent recall similar incidents, previous resolutions, and troubleshooting patterns.")

    col1, col2 = st.columns(2)
    with col1:
        incident_type = st.selectbox("Incident Type", ["Database", "Server", "Network", "Application", "Security", "Cloud", "API", "Other"])
    with col2:
        priority = st.selectbox("Priority", ["Critical", "High", "Medium", "Low"])

    subject = st.text_input("Incident Subject", placeholder="Example: API server unable to connect to database")
    description = st.text_area("Incident Description", placeholder="Describe symptoms, errors, affected service, or observations...", height=150)

    investigate = st.button("🔎 Investigate Incident", use_container_width=True)

    if investigate:
        if not subject.strip() or not description.strip():
            render_note("warning", "Please enter both the incident subject and description.")
            st.stop()

        incident_text = (
            f"Incident Type: {incident_type}\n"
            f"Priority: {priority}\n"
            f"Incident Subject: {subject.strip()}\n"
            f"Incident Description: {description.strip()}"
        )

        # Recall first so the current incident does not contaminate its own memory search.
        memories = []
        hindsight_error = None
        with st.spinner("🧠 Searching Hindsight memory..."):
            try:
                memories = get_memory(f"{incident_type} {subject} {description}", max_tokens=4096)
            except Exception as exc:
                hindsight_error = str(exc)

        cleaned = []
        for memory in memories:
            text = clean_memory(getattr(memory, "text", memory))
            if text and text not in cleaned:
                cleaned.append(text)
        cleaned = cleaned[:8]

        # If Hindsight is temporarily unreachable, use the local incident dataset as a transparent fallback.
        if hindsight_error:
            df = load_dataset()
            fallback = local_fallback_memories(df, f"{subject} {description}")
            if fallback:
                cleaned = fallback
                render_note("warning", "Hindsight could not be reached right now, so the local incident dataset is being used temporarily. Reconnect Hindsight before the final demo.")
            else:
                render_note("error", f"Hindsight connection failed: {hindsight_error}")

        try:
            save_memory(incident_text)
        except Exception as exc:
            render_note("warning", f"The incident could not be saved to Hindsight: {exc}")

        st.markdown("## 🚨 Current Incident")
        st.markdown(
            f'<div class="incident-card"><h3>{html.escape(subject)}</h3>'
            f'<p><b>Type:</b> {html.escape(incident_type)} &nbsp; | &nbsp; '
            f'<b>Priority:</b> {html.escape(priority)}</p>'
            f'<p>{html.escape(description).replace(chr(10), "<br>")}</p></div>',
            unsafe_allow_html=True,
        )

        st.markdown("## 🧠 Hindsight Memory")
        st.caption(f"Found {len(cleaned)} relevant historical memories. Dates are not displayed because the source dataset has no incident-date field.")
        if cleaned:
            for i, memory in enumerate(cleaned, 1):
                st.markdown(
                    f'<div class="memory-card"><div class="memory-title">🧠 Historical Incident {i}</div>'
                    f'<div class="memory-text">{html.escape(memory).replace(chr(10), "<br>")}</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="neutral-note">No closely matching historical incidents were found.</div>', unsafe_allow_html=True)

        ai_response = None
        ai_error = None
        with st.spinner("🤖 AI is analyzing the incident..."):
            try:
                ai_response = analyze_with_groq(incident_text, cleaned)
            except Exception as exc:
                ai_error = str(exc)

        st.markdown("## 🤖 AI Response")
        if ai_response:
            with st.container(border=True):
                st.markdown(ai_response)
        else:
            render_note("error", f"AI analysis failed: {ai_error}")
            st.caption("Check that your Groq key is active and that your computer can reach api.groq.com.")

        save_investigated({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": incident_type,
            "priority": priority,
            "subject": subject.strip(),
            "description": description.strip(),
            "memories": cleaned,
            "ai_response": ai_response or "",
        })

# -------------------- History page --------------------
else:
    st.markdown("# 📋 Incident History")
    st.write("Browse historical incidents from the dataset and incidents investigated in this app.")

    tab1, tab2 = st.tabs(["Historical Dataset", "Investigated Incidents"])

    with tab1:
        df = load_dataset()
        search = st.text_input("Search historical incidents", placeholder="database, timeout, server, API...")
        view = df.copy()
        if search.strip():
            q = search.lower()
            mask = (
                view["subject"].str.lower().str.contains(q, na=False)
                | view["body"].str.lower().str.contains(q, na=False)
                | view["answer"].str.lower().str.contains(q, na=False)
            )
            view = view[mask]

        if view.empty:
            st.markdown('<div class="neutral-note">No matching incidents found.</div>', unsafe_allow_html=True)
        else:
            options = [f"{i}: {row['subject']}" for i, row in view.iterrows()]
            selected = st.selectbox("Select an incident to inspect", options)
            selected_index = int(selected.split(":", 1)[0])
            row = view.loc[selected_index]

            st.markdown(
                f'<div class="history-card"><h3>{html.escape(str(row["subject"]))}</h3>'
                f'<p><b>Type:</b> {html.escape(str(row["type"]))} &nbsp; | &nbsp; '
                f'<b>Priority:</b> {html.escape(str(row["priority"]))} &nbsp; | &nbsp; '
                f'<b>Queue:</b> {html.escape(str(row["queue"]))}</p>'
                f'<p><b>Description</b><br>{html.escape(str(row["body"])).replace(chr(10), "<br>")}</p>'
                f'<p><b>Previous Support Response</b><br>{html.escape(str(row["answer"])).replace(chr(10), "<br>")}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.caption(f"Showing {len(view)} matching English incident records.")
            st.dataframe(
                view[["subject", "priority", "queue"]].reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
            )

    with tab2:
        records = load_investigated()
        if not records:
            st.markdown('<div class="neutral-note">No incidents have been investigated in this app yet.</div>', unsafe_allow_html=True)
        else:
            options = [f"{r['timestamp']} — {r['subject']}" for r in records]
            selected = st.selectbox("Select an investigated incident", options)
            r = records[options.index(selected)]
            st.markdown(
                f'<div class="history-card"><h3>{html.escape(r["subject"])}</h3>'
                f'<p><b>Time:</b> {html.escape(r["timestamp"])} &nbsp; | &nbsp; '
                f'<b>Type:</b> {html.escape(r["type"])} &nbsp; | &nbsp; '
                f'<b>Priority:</b> {html.escape(r["priority"])}</p>'
                f'<p>{html.escape(r["description"]).replace(chr(10), "<br>")}</p></div>',
                unsafe_allow_html=True,
            )
            if r.get("memories"):
                st.markdown("### Recalled Memory")
                for i, memory in enumerate(r["memories"], 1):
                    st.markdown(
                        f'<div class="memory-card"><div class="memory-title">Historical Incident {i}</div>'
                        f'<div class="memory-text">{html.escape(memory).replace(chr(10), "<br>")}</div></div>',
                        unsafe_allow_html=True,
                    )
            if r.get("ai_response"):
                st.markdown("### AI Response")
                st.markdown(r["ai_response"])

st.markdown("<div style='text-align:center;color:#64748b;font-size:13px;margin-top:40px;'>🧠 Powered by Hindsight Memory • 🤖 AI Incident Investigation</div>", unsafe_allow_html=True)

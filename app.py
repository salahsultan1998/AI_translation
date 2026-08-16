import os
import time
import html
import tempfile
import io
from textwrap import dedent
import pandas as pd
import streamlit as st
from streamlit_cookies_controller import CookieController

from excel_engine import ExcelHandler
from db_engine import SupabaseDBEngine
from rag_engine import RAGEngine
from agents import DEFAULT_MODEL, translator_agent, reviewer_agent
from custom_types import BatchTranslationRequest


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="LocaTool — AI Localization Workspace",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# HTML HELPER
# ============================================================

def render_html(html_string):
    """
    Render custom HTML safely.
    dedent() is important because Streamlit Markdown can
    interpret indented HTML as a code block.
    """
    st.markdown(
        dedent(html_string).strip(),
        unsafe_allow_html=True,
    )


# ============================================================
# CACHE & DB WRAPPERS (PERFORMANCE)
# ============================================================

db = SupabaseDBEngine()
cookie_controller = CookieController()

# Cache database reads for 5 minutes so we don't exceed API limits
@st.cache_data(ttl=300, show_spinner=False)
def fetch_game_profile(_db, game_id):
    return _db.get_game_profile(game_id)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_terms(_db, game_id, target_language):
    return _db.get_terms_for_game(game_id, target_language)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_tm(_db, game_id, target_language):
    return _db.get_tm_for_game(game_id, target_language)


# ============================================================
# CUSTOM CSS (THEME-AWARE)
# ============================================================

render_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* =========================================================
   GLOBAL
   ========================================================= */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background-color: var(--background-color);
    background-image:
        radial-gradient(
            circle at 5% 0%,
            rgba(99, 102, 241, 0.07),
            transparent 28%
        ),
        radial-gradient(
            circle at 95% 5%,
            rgba(14, 165, 233, 0.06),
            transparent 28%
        );
}

.main .block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}

/* =========================================================
   SIDEBAR (Kept permanently dark for high-contrast design)
   ========================================================= */
section[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid rgba(255,255,255,0.06);
}

section[data-testid="stSidebar"] > div {
    padding-top: 1.5rem;
}

section[data-testid="stSidebar"] * {
    color: #e5e7eb;
}

section[data-testid="stSidebar"] label {
    color: #9ca3af !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
}

/* Hide the "Press Enter to submit form" text to prevent overlapping */
[data-testid="InputInstructions"] {
    display: none !important;
}

section[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #1f2937;
    border-color: #374151;
}

section[data-testid="stSidebar"] .stSelectbox svg {
    fill: #9ca3af;
}

.sidebar-brand {
    padding: 0.25rem 0.25rem 1.5rem 0.25rem;
}

.brand-mark {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    color: white;
    font-size: 20px;
    font-weight: 800;
    box-shadow: 0 8px 20px rgba(79,70,229,0.35);
    margin-right: 10px;
    vertical-align: middle;
}

.brand-name {
    color: #ffffff;
    font-size: 1.15rem;
    font-weight: 800;
    vertical-align: middle;
    letter-spacing: -0.02em;
}

.brand-subtitle {
    color: #6b7280;
    font-size: 0.72rem;
    margin-top: 7px;
    margin-left: 2px;
}

.sidebar-section {
    color: #6b7280;
    font-size: 0.69rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 1.3rem;
    margin-bottom: 0.55rem;
}

.db-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 10px 12px;
    margin-top: 8px;
}

.db-label {
    font-size: 0.67rem;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.db-name {
    font-size: 0.78rem;
    color: #c7d2fe;
    margin-top: 3px;
    word-break: break-all;
    font-weight: 600;
}

.sidebar-credit {
    margin-top: 45px;
    padding-top: 15px;
    border-top: 1px solid rgba(255,255,255,0.07);
    color: #6b7280;
    font-size: 0.68rem;
    line-height: 1.5;
}

.sidebar-credit strong {
    color: #d1d5db;
    font-weight: 600;
}

/* =========================================================
   HERO
   ========================================================= */
.hero {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 18px;
    padding: 25px 30px;
    margin-bottom: 22px;
    box-shadow: 0 10px 35px rgba(0,0,0,0.05);
}

.hero-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
}

.hero-left {
    display: flex;
    align-items: center;
    gap: 16px;
}

.hero-icon {
    width: 58px;
    height: 58px;
    min-width: 58px;
    border-radius: 16px;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 26px;
    font-weight: 800;
    box-shadow: 0 10px 25px rgba(79,70,229,0.22);
}

.hero-title {
    font-size: 1.55rem;
    font-weight: 800;
    color: var(--text-color);
    letter-spacing: -0.04em;
    line-height: 1.15;
}

.hero-description {
    color: var(--text-color);
    opacity: 0.7;
    font-size: 0.84rem;
    margin-top: 5px;
}

.designer-credit {
    text-align: right;
    white-space: nowrap;
}

.designer-label {
    color: var(--text-color);
    opacity: 0.5;
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.designer-name {
    color: var(--text-color);
    font-size: 0.82rem;
    font-weight: 700;
    margin-top: 3px;
}

/* =========================================================
   PROJECT INFO CARDS
   ========================================================= */
.info-card {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 14px;
    padding: 16px 18px;
    min-height: 88px;
    box-shadow: 0 5px 18px rgba(0,0,0,0.035);
}

.info-label {
    color: var(--text-color);
    opacity: 0.5;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 700;
    margin-bottom: 7px;
}

.info-value {
    color: var(--text-color);
    font-size: 1rem;
    font-weight: 700;
}

.info-sub {
    color: var(--text-color);
    opacity: 0.7;
    font-size: 0.72rem;
    margin-top: 4px;
}

/* =========================================================
   TABS
   ========================================================= */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: transparent;
    border-bottom: 1px solid rgba(128, 128, 128, 0.2);
}

.stTabs [data-baseweb="tab"] {
    height: 48px;
    padding: 0 20px;
    color: var(--text-color);
    opacity: 0.7;
    font-weight: 600;
    font-size: 0.84rem;
    border-radius: 9px 9px 0 0;
}

.stTabs [aria-selected="true"] {
    color: #4f46e5 !important;
    opacity: 1;
}

.stTabs [data-baseweb="tab-highlight"] {
    background-color: #4f46e5;
    height: 2px;
}

/* =========================================================
   SECTION TITLES
   ========================================================= */
.section-title {
    color: var(--text-color);
    font-size: 1.05rem;
    font-weight: 750;
    margin-top: 18px;
    margin-bottom: 4px;
    letter-spacing: -0.02em;
}

.section-description {
    color: var(--text-color);
    opacity: 0.7;
    font-size: 0.78rem;
    margin-bottom: 15px;
}

/* =========================================================
   FILE UPLOADER
   ========================================================= */
[data-testid="stFileUploader"] {
    background: var(--background-color);
    border: 1.5px dashed #6366f1;
    border-radius: 15px;
    padding: 7px;
}

[data-testid="stFileUploaderDropzone"] {
    background: var(--secondary-background-color);
    border-radius: 11px;
}

/* =========================================================
   BUTTONS
   ========================================================= */
.stButton > button {
    border-radius: 9px;
    min-height: 40px;
    font-weight: 650;
    font-size: 0.79rem;
    border: 1px solid rgba(128, 128, 128, 0.2);
    background: var(--secondary-background-color);
    color: var(--text-color);
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 5px 14px rgba(0,0,0,0.1);
    border-color: #6366f1;
    color: #6366f1;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    border: none;
    color: white !important;
}

.stDownloadButton > button {
    border-radius: 9px;
    font-weight: 650;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    border: none;
    color: white;
}

/* =========================================================
   METRICS
   ========================================================= */
[data-testid="stMetric"] {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 13px;
    padding: 15px 17px;
    box-shadow: 0 5px 18px rgba(0,0,0,0.035);
}

[data-testid="stMetricLabel"] {
    color: var(--text-color) !important;
    opacity: 0.6;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

[data-testid="stMetricValue"] {
    color: var(--text-color) !important;
    font-size: 1.25rem !important;
    font-weight: 750 !important;
}

/* =========================================================
   DATAFRAME
   ========================================================= */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 12px;
    overflow: hidden;
    background: var(--secondary-background-color);
}

/* =========================================================
   PROGRESS
   ========================================================= */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #6366f1, #818cf8);
}

/* =========================================================
   INPUTS
   ========================================================= */
.stTextArea textarea,
.stTextInput input {
    border-radius: 9px;
    border: 1px solid rgba(128, 128, 128, 0.3);
    background: var(--secondary-background-color);
    color: var(--text-color);
    font-size: 0.82rem;
}

/* =========================================================
   STATUS
   ========================================================= */
.status-card {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 13px;
    padding: 18px;
    margin-top: 12px;
    box-shadow: 0 5px 18px rgba(0,0,0,0.035);
}

.status-title {
    color: var(--text-color);
    font-size: 0.88rem;
    font-weight: 700;
}

.status-description {
    color: var(--text-color);
    opacity: 0.7;
    font-size: 0.75rem;
    margin-top: 4px;
}

/* =========================================================
   DATABASE HEADER
   ========================================================= */
.database-header {
    background: linear-gradient(135deg, #111827, #1f2937);
    border-radius: 15px;
    padding: 20px 22px;
    color: white;
    margin-bottom: 18px;
}

.database-header-title {
    font-size: 1rem;
    font-weight: 750;
    color: white;
}

.database-header-description {
    color: #9ca3af;
    font-size: 0.75rem;
    margin-top: 5px;
}

/* =========================================================
   FOOTER
   ========================================================= */
.main-footer {
    margin-top: 45px;
    padding-top: 18px;
    border-top: 1px solid rgba(128, 128, 128, 0.2);
    text-align: center;
    color: var(--text-color);
    opacity: 0.6;
    font-size: 0.68rem;
}

.main-footer strong {
    color: var(--text-color);
    opacity: 0.9;
}
</style>
""")


# ============================================================
# AUTHENTICATION LOGIC (COOKIE + SESSION + TIMEOUT)
# ============================================================

if "user" not in st.session_state:
    st.session_state.user = None


def clear_authenticated_session():
    """Clear authentication and all user/session-specific state."""
    try:
        db.sign_out()
    except Exception:
        pass

    try:
        cookie_controller.remove("locatool_auth_token")
    except Exception:
        pass

    st.query_params.clear()
    # Correct, safe way to clear Streamlit session state
    st.session_state.clear()


# 1. Auto-login / session restore via browser cookie
if st.session_state.user is None:
    try:
        saved_token = cookie_controller.get("locatool_auth_token")
    except Exception:
        saved_token = None

    if saved_token:
        try:
            auto_user = db.get_user_from_token(saved_token)
        except Exception:
            auto_user = None

        if auto_user:
            st.session_state.user = auto_user


def show_login_page():
    _, col, _ = st.columns([1, 1.5, 1])

    with col:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>🔒 LocaTool Access</h2>", unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align: center; opacity: 0.7;'>"
            "Please sign in to access the translation workspace."
            "</p><br>",
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button(
                "Log In",
                use_container_width=True,
            )

            if submit_button:
                email = email.strip()

                if not email or not password:
                    st.error("Please enter both your email and password.")
                else:
                    try:
                        user, token, error = db.sign_in(email, password)
                    except Exception as e:
                        user, token, error = None, None, str(e)

                    if error or not user or not token:
                        st.error(f"Login failed: {error or 'Invalid login response.'}")
                    else:
                        st.session_state.clear() # Clear state before starting session
                        st.session_state.user = user
                        st.session_state.last_active = time.time()

                        try:
                            cookie_controller.set(
                                "locatool_auth_token",
                                token,
                            )
                        except Exception as e:
                            clear_authenticated_session()
                            st.error(f"Login failed while saving the session: {e}")
                            st.stop()

                        st.rerun()


# 2. Gatekeeper Check
if st.session_state.user is None:
    show_login_page()
    st.stop()


# 3. 10-Minute Rolling Inactivity Timer
INACTIVITY_LIMIT = 600

if "last_active" not in st.session_state:
    st.session_state.last_active = time.time()

current_time = time.time()

if current_time - st.session_state.last_active > INACTIVITY_LIMIT:
    clear_authenticated_session()
    st.warning(
        "Session expired due to 10 minutes of inactivity. Please log in again."
    )
    st.stop()

st.session_state.last_active = current_time


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    
    if st.session_state.user:
        # Sanitize email before injection
        safe_email = html.escape(str(st.session_state.user.email))
        st.caption(f"👤 **{safe_email}**")

    if st.button("Log Out", use_container_width=True):
        clear_authenticated_session()
        st.rerun()

    st.divider()

    render_html("""
    <div class="sidebar-brand">
        <span class="brand-mark">◈</span>
        <span class="brand-name">LocaTool</span>
        <div class="brand-subtitle">
            AI Game Localization Workspace
        </div>
    </div>
    """)

    render_html("""
    <div class="sidebar-section">
        Project
    </div>
    """)

    game_list = [
        "DM_03",
        "Tarbi3a_Baloot",
        "Baloot_Challenges",
        "+ Add New Game",
    ]

    selected_game = st.selectbox(
        "Active Game",
        options=game_list,
        label_visibility="collapsed",
    )

    if selected_game == "+ Add New Game":
        game_id = st.text_input(
            "Game Identifier",
            value="new_game",
            placeholder="e.g. game_dragon_quest",
        )
    else:
        game_id = selected_game


    render_html("""
    <div class="sidebar-section">
        Language
    </div>
    """)

    supported_languages = [
        "Arabic",
        "English",
        "Turkish",
    ]

    target_language = st.selectbox(
        "Target Language",
        options=supported_languages,
        index=0,
        label_visibility="collapsed",
    )

    # Secure HTML Escaping for User Data
    safe_game_id = html.escape(game_id.lower().strip())
    safe_target_lang = html.escape(target_language.lower().strip())

    render_html(f"""
    <div class="db-card">
        <div class="db-label">
            Active Database
        </div>
        <div class="db-name">
            {safe_game_id}_{safe_target_lang}
        </div>
    </div>
    """)

    render_html("""
    <div class="sidebar-section">
        AI Configuration
    </div>
    """)

    model_options = [
        "qwen/qwen3-235b-a22b-2507",
        "qwen/qwen3.7-plus"
    ]

    model_choice = st.selectbox(
        "Model",
        options=model_options,
        index=1,
        help="Select the AI model used for translation batches.",
        label_visibility="collapsed",
    )

    st.caption(f"Active: {model_choice}")

    # --- UPDATED: Batching Strategy (Auto / Manual) ---
    render_html("""
    <div class="sidebar-section">
        Batching Strategy
    </div>
    """)

    batch_mode = st.radio(
        "Batching Strategy",
        options=["Auto", "Manual"],
        horizontal=True,
        help="Auto uses a smart character budget to handle mixed long/short text safely.",
        label_visibility="collapsed",
    )

    if batch_mode == "Manual":
        manual_batch_size = st.slider(
            "Rows per batch",
            min_value=1,
            max_value=50,
            value=10,
            step=1,
            help="Set to 1 for line-by-line or higher numbers for fixed batching.",
        )
    else:
        manual_batch_size = 10
        st.caption("🤖 **Auto Mode Active:** Dynamically groups text by character count.")
    # ------------------------------------------------

    render_html("""
    <div class="sidebar-credit">
        Designed by<br>
        <strong>SALAH SULTAN （萨利）</strong>
    </div>
    """)


# ============================================================
# MAIN HERO
# ============================================================

render_html("""
<div class="hero">
    <div class="hero-content">
        <div class="hero-left">
            <div class="hero-icon">
                ◈
            </div>
            <div>
                <div class="hero-title">
                    Localization Dashboard
                </div>
                <div class="hero-description">
                    Translate, review and manage game localization
                    with AI-powered workflows.
                </div>
            </div>
        </div>
        <div class="designer-credit">
            <div class="designer-label">
                Designed by
            </div>
            <div class="designer-name">
                SALAH SULTAN （萨利）
            </div>
        </div>
    </div>
</div>
""")


# ============================================================
# PROJECT SUMMARY CARDS
# ============================================================

info_col1, info_col2, info_col3 = st.columns(3)

with info_col1:
    render_html(f"""
    <div class="info-card">
        <div class="info-label">
            Active Project
        </div>
        <div class="info-value">
            {html.escape(game_id)}
        </div>
        <div class="info-sub">
            Current game localization project
        </div>
    </div>
    """)

with info_col2:
    render_html(f"""
    <div class="info-card">
        <div class="info-label">
            Target Language
        </div>
        <div class="info-value">
            {html.escape(target_language)}
        </div>
        <div class="info-sub">
            Chinese → {html.escape(target_language)}
        </div>
    </div>
    """)

with info_col3:
    short_model = html.escape(model_choice.split("/")[-1])
    render_html(f"""
    <div class="info-card">
        <div class="info-label">
            AI Model
        </div>
        <div class="info-value">
            {short_model}
        </div>
        <div class="info-sub">
            Translation engine
        </div>
    </div>
    """)

st.markdown(
    "<div style='height:20px'></div>",
    unsafe_allow_html=True,
)


# ============================================================
# TABS
# ============================================================

tab1, tab2 = st.tabs([
    "◈  Localize Game Text",
    "▣  Database & Context",
])


# ============================================================
# TAB 1 — LOCALIZATION
# ============================================================

with tab1:
    render_html("""
    <div class="section-title">
        Game Text Localization
    </div>
    """)

    render_html(f"""
    <div class="section-description">
        Upload your game text and translate Chinese content into
        <strong>{html.escape(target_language)}</strong> for
        <strong>{html.escape(game_id)}</strong>.
    </div>
    """)

    uploaded_file = st.file_uploader(
        "Upload Game Text File",
        type=["xlsx", "csv"],
        key="game_text_uploader",
    )

    if uploaded_file is not None:
        
        # --- NEW FIX: Clear old translation state when a NEW file is uploaded ---
        if st.session_state.get("last_uploaded_file_id") != uploaded_file.file_id:
            # Update the tracker to the new file
            st.session_state.last_uploaded_file_id = uploaded_file.file_id
            # Wipe the old translation results from memory
            st.session_state.translation_complete = False
            st.session_state.pop("final_download_bytes", None)
            st.session_state.pop("final_elapsed_time", None)
        # ------------------------------------------------------------------------

        # Load File preview directly into memory (zero temp files generated)
        if uploaded_file.name.lower().endswith(".csv"):
            df_preview = pd.read_csv(uploaded_file).fillna("").astype(str)
        else:
            df_preview = pd.read_excel(uploaded_file).fillna("").astype(str)
            
        # Reset the uploaded file pointer so it can be read again securely later
        uploaded_file.seek(0)

        safe_file_name = html.escape(uploaded_file.name)
        render_html(f"""
        <div class="section-title">
            File Preview
        </div>
        <div class="section-description">
            {len(df_preview):,} rows detected in
            <strong>{safe_file_name}</strong>.
        </div>
        """)

        st.dataframe(
            df_preview,
            use_container_width=True,
            height=300,
        )

        if len(df_preview.columns) == 0:
            st.error("The uploaded file has no columns.")
        else:
            # Column mapping setup
            render_html("""
            <div class="section-title" style="margin-top: 10px;">
                Map Data Columns
            </div>
            """)
            
            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                selected_source_col = st.selectbox(
                    "Source Text Column (Required)",
                    options=df_preview.columns,
                    index=0,
                )
            
            with col_sel2:
                ctx_options = ["-- No Context Column --"] + list(df_preview.columns)
                
                # Auto-detect context column if available
                default_ctx_idx = 0
                for i, col in enumerate(df_preview.columns):
                    if col.lower() in ["text_type", "context", "type", "description"]:
                        default_ctx_idx = i + 1
                        break
                        
                selected_context_col = st.selectbox(
                    "Context/Type Column (Optional)",
                    options=ctx_options,
                    index=default_ctx_idx,
                )
                
            actual_context_col = None if selected_context_col == "-- No Context Column --" else selected_context_col

            # Init state strictly for UI tracking
            if "translation_complete" not in st.session_state:
                st.session_state.translation_complete = False

            # Determine batch configuration parameters
            if batch_mode == "Auto":
                use_smart_budget = True
                display_desc = "Dynamic Character Budget (~1000 chars/batch)"
            else:
                use_smart_budget = False
                display_desc = f"{manual_batch_size} rows per API request"

            render_html("""
            <div class="section-title">
                Translation Controls
            </div>
            """)

            col_btn1, col_btn2, col_info = st.columns([1.1, 1.1, 3])

            with col_btn1:
                start_clicked = st.button(
                    "Start Translation",
                    type="primary",
                    use_container_width=True,
                )

            with col_btn2:
                # Placed as visual only. A blocking Python loop will ignore this until finished.
                st.button(
                    "Stop Translation",
                    type="secondary",
                    use_container_width=True,
                )

            with col_info:
                render_html(f"""
                <div class="status-card" style="margin-top:0; padding:10px 15px;">
                    <div class="status-title">
                        Batch configuration ({html.escape(batch_mode)})
                    </div>
                    <div class="status-description">
                        {html.escape(display_desc)}
                        · {html.escape(target_language)} output
                    </div>
                </div>
                """)

            # ----------------------------------------------------
            # THE TRANSLATION ENGINE (SAFE, IN-PLACE EXECUTION)
            # ----------------------------------------------------
            if start_clicked:
                st.session_state.translation_complete = False
                
                # We use a temporary directory that the OS auto-cleans the moment the block ends.
                # No files are left behind in your project directory.
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_input_path = os.path.join(temp_dir, f"input_{uploaded_file.name}")
                    temp_output_path = os.path.join(temp_dir, f"output_{uploaded_file.name}")
                    
                    with open(temp_input_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Fetch Database items cleanly with error handling
                    try:
                        glossary_dict = fetch_terms(db, game_id, target_language)
                        tm_dict = fetch_tm(db, game_id, target_language)
                        game_profile = fetch_game_profile(db, game_id)
                        
                        rag = RAGEngine()
                        rag.load_resources(
                            glossary_dict=glossary_dict,
                            tm_dict=tm_dict,
                            game_profile=game_profile,
                        )
                    except Exception as e:
                        st.error(f"Failed to fetch database context: {e}")
                        st.stop()

                    # Prepare Batches using dynamic columns and smart budget strategy flag
                    rows = ExcelHandler.read_game_sheet(
                        temp_input_path,
                        text_column=selected_source_col,
                        context_column=actual_context_col,
                    )
                    
                    batches = ExcelHandler.create_batches(
                        rows, 
                        batch_size=manual_batch_size, 
                        use_smart_budget=use_smart_budget
                    )
                    
                    total_batches = len(batches)
                    translations_dict = {}
                    
                    # Setup UI Placeholders to update dynamically without st.rerun()
                    progress_bar = st.progress(0.0)
                    ui_col1, ui_col2, ui_col3 = st.columns(3)
                    metric_progress = ui_col1.empty()
                    metric_time = ui_col2.empty()
                    metric_status = ui_col3.empty()
                    
                    start_time = time.time()
                    
                    # Processing Loop
                    for current_idx, batch_rows in enumerate(batches):
                        
                        # UI Updates in place
                        progress_val = current_idx / max(1, total_batches)
                        progress_bar.progress(progress_val)
                        
                        elapsed = time.time() - start_time
                        mins, secs = divmod(int(elapsed), 60)
                        
                        metric_progress.metric("Progress", f"Batch {current_idx + 1} / {total_batches}")
                        metric_time.metric("Elapsed Time", f"{mins:02d}:{secs:02d}")
                        metric_status.metric("Status", "Processing API")
                        
                        rag_context = rag.get_batch_context(
                            batch_rows=batch_rows,
                            target_language=target_language,
                        )

                        batch_request = BatchTranslationRequest(
                            batch_id=current_idx + 1,
                            rows=batch_rows,
                            target_language=target_language,
                        )

                        try:
                            response = translator_agent(
                                batch_request=batch_request,
                                rag_context=rag_context,
                                feedback="",
                                model_name=model_choice,
                                fallback_model_name="openai/gpt-4o-mini",
                                game_id=game_id,
                            )

                            # Reviewer step (Assuming it acts on response)
                            review = reviewer_agent(
                                original_rows=batch_rows,
                                translated_batch=response,
                            )

                            for item in (response.translations or []):
                                translations_dict[item.row_id] = item.translated_text
                                
                        except Exception as e:
                            st.toast(f"Error on Batch {current_idx + 1}: {e}", icon="🚨")
                            
                        # Assure mapping exists for failed rows
                        for r in batch_rows:
                            if r.row_id not in translations_dict:
                                translations_dict[r.row_id] = r.source_text

                    # Loop finished. Save to temp output.
                    progress_bar.progress(1.0)
                    metric_status.metric("Status", "Completed")
                    
                    target_col_name = f"{target_language.strip().replace(' ', '_')}"
                    
                    ExcelHandler.write_translated_sheet(
                        original_file=temp_input_path,
                        translations=translations_dict,
                        target_column=target_col_name,
                        output_file=temp_output_path,
                    )
                    
                    # Load the newly created file directly into memory for download
                    with open(temp_output_path, "rb") as f:
                        st.session_state.final_download_bytes = f.read()
                        
                    st.session_state.final_elapsed_time = time.time() - start_time
                    st.session_state.translation_complete = True
                    
                # Rerun just ONCE at the very end to reveal the download block below
                st.rerun()

            # ----------------------------------------------------
            # DOWNLOAD SECTION (MEMORY ONLY)
            # ----------------------------------------------------
            if st.session_state.get("translation_complete") and "final_download_bytes" in st.session_state:
                mins, secs = divmod(int(st.session_state.final_elapsed_time), 60)
                st.success(f"Translation completed successfully in {mins}m {secs}s.")

                render_html("""
                <div class="section-title">
                    Translated Output
                </div>
                """)

                # Determine extension securely
                is_csv = uploaded_file.name.lower().endswith(".csv")
                
                # --- Read the bytes directly into memory for preview ---
                file_bytes = st.session_state.final_download_bytes
                
                try:
                    if is_csv:
                        translated_df = pd.read_csv(io.BytesIO(file_bytes)).fillna("").astype(str)
                    else:
                        translated_df = pd.read_excel(io.BytesIO(file_bytes)).fillna("").astype(str)
                        
                    st.dataframe(
                        translated_df,
                        use_container_width=True,
                        height=300
                    )
                except Exception as e:
                    st.error(f"Could not load preview: {e}")
                # ---------------------------------------------------------------

                lang_clean = target_language.lower().strip().replace(" ", "_")
                mime_type = "text/csv" if is_csv else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                
                st.download_button(
                    label=f"Download {html.escape(target_language)} File",
                    data=st.session_state.final_download_bytes,
                    file_name=f"{game_id}_{lang_clean}_{uploaded_file.name}",
                    mime=mime_type,
                    type="primary",
                    use_container_width=True,
                )

# ============================================================
# TAB 2 — DATABASE & CONTEXT
# ============================================================

with tab2:
    render_html("""
    <div class="database-header">
        <div class="database-header-title">
            Database &amp; Context Management
        </div>
        <div class="database-header-description">
            Configure game-specific tone, terminology,
            translation memory and localization context.
        </div>
    </div>
    """)

    render_html("""
    <div class="section-title">
        Game Profile
    </div>
    """)

    render_html("""
    <div class="section-description">
        Define the writing style and localization rules
        that the AI should follow for this game.
    </div>
    """)

    # Cached Fetch
    existing_profile = fetch_game_profile(db, game_id)

    with st.form("profile_form"):
        tone_input = st.text_area(
            "Game Profile Instructions",
            value=existing_profile,
            height=160,
            placeholder=(
                "Example: Epic strategy game, commanding tone, "
                "historical empire-building atmosphere. "
                "Keep UI text concise and natural."
            ),
        )

        if st.form_submit_button("Save Game Profile", type="primary"):
            db.upsert_game_profile(game_id, tone_input)
            fetch_game_profile.clear() # Clear cache to show new data on refresh
            st.success(f"Game Profile for `{html.escape(game_id)}` saved successfully.")

    st.divider()

    # ============================================================
    # MANUAL TERM ENTRY (MULTI-ROW TABLE WITH CONFLICT RESOLUTION)
    # ============================================================
    render_html(f"""
    <div class="section-title">
        Manual Term Entry (Glossary)
    </div>
    <div class="section-description">
        Add multiple glossary terms directly into the table below for <strong>{html.escape(game_id)}</strong>. 
        Conflicting terms will be flagged for your review before saving.
    </div>
    """)

    if "manual_terms_df" not in st.session_state:
        st.session_state.manual_terms_df = pd.DataFrame(
            {"Chinese Source": [""], "Target Translation": [""]}
        )

    edited_df = st.data_editor(
        st.session_state.manual_terms_df,
        num_rows="dynamic",
        use_container_width=True,
        key="manual_terms_grid",
        column_config={
            "Chinese Source": st.column_config.TextColumn("Chinese Source", required=True),
            "Target Translation": st.column_config.TextColumn(f"{target_language} Target", required=True),
        }
    )

    # Initialize conflict session states if not present
    if "pending_conflicts" not in st.session_state:
        st.session_state.pending_conflicts = None
    if "pending_pairs_to_save" not in st.session_state:
        st.session_state.pending_pairs_to_save = None

    if st.button("Save Manual Terms to Database", type="primary"):
        pairs = []
        source_terms_list = []
        for _, row in edited_df.iterrows():
            src = str(row.get("Chinese Source", "")).strip()
            tgt = str(row.get("Target Translation", "")).strip()
            
            if src and tgt and src.lower() != "nan" and tgt.lower() != "nan":
                pairs.append({"source": src, "target": tgt})
                source_terms_list.append(src)

        if not pairs:
            st.error("Please fill in at least one valid row with both a source and target term.")
        else:
            # Check against database for existing conflicts
            existing_records = db.check_conflicting_terms(game_id, target_language, source_terms_list)
            existing_map = {item["source_term"]: item["target_term"] for item in existing_records}
            
            conflicts = []
            clean_pairs = []
            
            for p in pairs:
                src = p["source"]
                tgt = p["target"]
                if src in existing_map:
                    conflicts.append({
                        "source": src,
                        "existing_target": existing_map[src],
                        "new_target": tgt
                    })
                else:
                    clean_pairs.append(p)
            
            if conflicts:
                st.session_state.pending_conflicts = conflicts
                st.session_state.pending_pairs_to_save = clean_pairs
                st.rerun()
            else:
                try:
                    count = db.upsert_terms(game_id, target_language, clean_pairs)
                    fetch_terms.clear()
                    st.success(f"Successfully saved {count:,} term(s) to the database!")
                    st.session_state.pending_conflicts = None
                    st.session_state.pending_pairs_to_save = None
                except Exception as e:
                    st.error(f"Failed to save terms: {e}")

    # ============================================================
    # INTERACTIVE CONFLICT RESOLUTION UI BLOCK
    # ============================================================
    if st.session_state.pending_conflicts:
        st.warning(f"⚠️ Found {len(st.session_state.pending_conflicts)} conflicting term(s) already in the database!")
        
        with st.form("conflict_resolution_form"):
            st.markdown("Choose whether to **Overwrite** with your new translation or **Ignore** (keep existing) for each conflict:")
            
            resolution_decisions = {}
            for idx, conflict in enumerate(st.session_state.pending_conflicts):
                src = conflict["source"]
                exist_tgt = conflict["existing_target"]
                new_tgt = conflict["new_target"]
                
                st.markdown(f"**Chinese Source:** `{src}`")
                decision = st.radio(
                    f"Action for `{src}`",
                    options=["Ignore (Keep Existing)", "Overwrite (Use New)"],
                    index=0,
                    key=f"conflict_{idx}",
                    horizontal=True,
                    format_func=lambda x: f"Existing: [{exist_tgt}] vs New: [{new_tgt}] ➔ {x}"
                )
                resolution_decisions[src] = decision
                st.divider()

            if st.form_submit_button("Confirm Resolutions & Save", type="primary"):
                final_pairs_to_save = list(st.session_state.pending_pairs_to_save)
                
                for conflict in st.session_state.pending_conflicts:
                    src = conflict["source"]
                    if "Overwrite" in resolution_decisions[src]:
                        final_pairs_to_save.append({"source": src, "target": conflict["new_target"]})
                
                try:
                    count = db.upsert_terms(game_id, target_language, final_pairs_to_save)
                    fetch_terms.clear()
                    st.success(f"Successfully resolved conflicts and saved {count:,} term(s)!")
                    st.session_state.pending_conflicts = None
                    st.session_state.pending_pairs_to_save = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save resolved terms: {e}")

    st.divider()

    render_html("""
    <div class="section-title">
        Localization Knowledge Base (File Upload)
    </div>
    """)

    render_html(f"""
    <div class="section-description">
        Upload reference translations for
        <strong>{html.escape(game_id)}</strong> into
        <strong>{html.escape(target_language)}</strong>.
    </div>
    """)

    target_type = st.radio(
        "Target Type",
        options=["terms", "translation_memory"],
        format_func=lambda x: (
            "Glossary Terms · Exact Match" if x == "terms"
            else "Translation Memory · Fuzzy Match"
        ),
        horizontal=True,
    )

    rag_file = st.file_uploader(
        "Upload Reference File",
        type=["xlsx", "csv"],
        key="rag_file_uploader",
    )

    df_rag = None

    if rag_file is not None:
        # Load directly into memory
        if rag_file.name.lower().endswith(".csv"):
            df_rag = pd.read_csv(rag_file).fillna("").astype(str)
        else:
            try:
                excel_obj = pd.ExcelFile(rag_file)
                sheet_names = excel_obj.sheet_names

                selected_sheet = st.selectbox(
                    "Excel Sheet",
                    options=sheet_names,
                    key="rag_sheet_select",
                )

                df_rag = pd.read_excel(excel_obj, sheet_name=selected_sheet).fillna("").astype(str)
            except Exception as e:
                st.error(f"Error reading Excel sheets: {e}")

        if df_rag is not None:
            render_html("""
            <div class="section-title">
                Reference Data Preview
            </div>
            """)

            st.dataframe(
                df_rag,
                use_container_width=True,
                height=300
            )

            if len(df_rag.columns) < 2:
                st.warning(
                    "Uploaded file has fewer than 2 columns. "
                    "Ensure it has both source and target columns."
                )

            col_source, col_target = st.columns(2)

            with col_source:
                selected_source_column = st.selectbox(
                    "Source Column",
                    options=df_rag.columns,
                    index=0,
                )

            with col_target:
                selected_target_column = st.selectbox(
                    f"{target_language} Column",
                    options=df_rag.columns,
                    index=min(1, len(df_rag.columns) - 1),
                )

            if st.button("Upload to Database", type="primary"):
                status_rag = st.status(
                    f"Uploading to {target_type}...",
                    expanded=True,
                )

                try:
                    pairs = []

                    for _, row in df_rag.iterrows():
                        src_val = row.get(selected_source_column)
                        tgt_val = row.get(selected_target_column)

                        if pd.notna(src_val) and pd.notna(tgt_val):
                            src_str = str(src_val).strip()
                            tgt_str = str(tgt_val).strip()

                            if (src_str and tgt_str and 
                                src_str.lower() != "nan" and 
                                tgt_str.lower() != "nan"):
                                pairs.append({
                                    "source": src_str,
                                    "target": tgt_str,
                                })

                    if not pairs:
                        status_rag.update(
                            label="No valid rows found",
                            state="error",
                        )
                        st.error("No valid text pairs found to upload.")
                    else:
                        if target_type == "terms":
                            count = db.upsert_terms(
                                game_id,
                                target_language,
                                pairs,
                            )
                            fetch_terms.clear() # Wipe cache
                            status_rag.update(
                                label="Database Upload Complete",
                                state="complete",
                                expanded=False,
                            )
                            st.success(f"Successfully added {count:,} glossary terms to Database.")
                        else:
                            count = db.upsert_tm(
                                game_id,
                                target_language,
                                pairs,
                            )
                            fetch_tm.clear() # Wipe cache
                            status_rag.update(
                                label="Database Upload Complete",
                                state="complete",
                                expanded=False,
                            )
                            st.success(f"Successfully added {count:,} Translation Memory records to Database.")

                except Exception as e:
                    status_rag.update(label="Upload Failed", state="error")
                    st.error(f"Error uploading data: {e}")
# ============================================================
# FOOTER
# ============================================================

render_html("""
<div class="main-footer">
    LocaTool · AI Game Localization Workspace
    &nbsp;•&nbsp;
    Designed by <strong>SALAH SULTAN （萨利）</strong>
</div>
""")
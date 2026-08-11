import os
import time
from textwrap import dedent

import pandas as pd
import streamlit as st

from excel_engine import ExcelHandler
from db_engine import DBEngine
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

def render_html(html):
    """
    Render custom HTML safely.
    dedent() is important because Streamlit Markdown can
    interpret indented HTML as a code block.
    """
    st.markdown(
        dedent(html).strip(),
        unsafe_allow_html=True,
    )


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
# DATABASE
# ============================================================

db = DBEngine()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

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

    render_html(f"""
    <div class="db-card">
        <div class="db-label">
            Active Database
        </div>
        <div class="db-name">
            {game_id.lower().strip()}_{target_language.lower().strip()}
        </div>
    </div>
    """)

    render_html("""
    <div class="sidebar-section">
        AI Configuration
    </div>
    """)

    model_options = [
        "openai/gpt-4o",
        "anthropic/claude-3.5-sonnet",
        "qwen/qwen-2.5-72b-instruct",
        "openai/gpt-4o-mini",
        "qwen/qwen3.7-flash",
        "x-ai/grok-4.5",
        "google/gemini-3.1-flash-lite-preview",
        "qwen/qwen3.7-plus"
    ]

    model_choice = st.selectbox(
        "Model",
        options=model_options,
        index=2,
        help="Select the AI model used for translation batches.",
        label_visibility="collapsed",
    )

    st.caption(f"Active: {model_choice}")

    batch_size = st.slider(
        "Batch Size",
        min_value=1,
        max_value=50,
        value=10,
        step=1,
        help="Set to 1 for line-by-line or higher numbers for context-window batching.",
    )

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
            {game_id}
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
            {target_language}
        </div>
        <div class="info-sub">
            Chinese → {target_language}
        </div>
    </div>
    """)

with info_col3:
    short_model = model_choice.split("/")[-1]
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
        <strong>{target_language}</strong> for
        <strong>{game_id}</strong>.
    </div>
    """)

    uploaded_file = st.file_uploader(
        "Upload Game Text File",
        type=["xlsx", "csv"],
        key="game_text_uploader",
    )

    if uploaded_file is not None:
        os.makedirs("data", exist_ok=True)

        temp_input_path = os.path.join(
            "data",
            uploaded_file.name,
        )

        temp_output_path = os.path.join(
            "data",
            f"translated_{uploaded_file.name}",
        )

        # Optimization: Only write the file if it hasn't been saved yet to avoid disk I/O on every rerun
        if "last_uploaded_filename" not in st.session_state or st.session_state.last_uploaded_filename != uploaded_file.name:
            with open(temp_input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state.last_uploaded_filename = uploaded_file.name


        if temp_input_path.lower().endswith(".csv"):
            df_preview = pd.read_csv(temp_input_path)
        else:
            df_preview = pd.read_excel(temp_input_path)


        render_html(f"""
        <div class="section-title">
            File Preview
        </div>
        <div class="section-description">
            {len(df_preview):,} rows detected in
            <strong>{uploaded_file.name}</strong>.
        </div>
        """)

        st.dataframe(
            df_preview,
            use_container_width=True,
            height=300,
        )

        if "text" not in df_preview.columns:
            st.error(
                "Required column 'text' was not found in the uploaded file."
            )
        else:
            # =================================================
            # SESSION STATE
            # =================================================
            if "is_translating" not in st.session_state:
                st.session_state.is_translating = False
            
            if "translation_complete" not in st.session_state:
                st.session_state.translation_complete = False

            if "current_batch" not in st.session_state:
                st.session_state.current_batch = 0

            if "total_batches" not in st.session_state:
                st.session_state.total_batches = 0

            if "translations_dict" not in st.session_state:
                st.session_state.translations_dict = {}

            if "start_time" not in st.session_state:
                st.session_state.start_time = 0.0


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
                    disabled=st.session_state.is_translating,
                )

            with col_btn2:
                stop_clicked = st.button(
                    "Stop Translation",
                    type="secondary",
                    use_container_width=True,
                    disabled=not st.session_state.is_translating,
                )

            with col_info:
                render_html(f"""
                <div class="status-card" style="margin-top:0; padding:10px 15px;">
                    <div class="status-title">
                        Batch configuration
                    </div>
                    <div class="status-description">
                        {batch_size} rows per API request
                        · {target_language} output
                    </div>
                </div>
                """)

            # =================================================
            # START TRANSLATION
            # =================================================
            if start_clicked:
                st.session_state.is_translating = True
                st.session_state.translation_complete = False
                st.session_state.current_batch = 0
                st.session_state.translations_dict = {}
                st.session_state.start_time = time.time()

                rows = ExcelHandler.read_game_sheet(
                    temp_input_path,
                    text_column="text",
                    context_column="text_type",
                )

                st.session_state.rows = rows
                st.session_state.batches = ExcelHandler.create_batches(
                    rows,
                    batch_size=batch_size,
                )
                st.session_state.total_batches = len(st.session_state.batches)

                rag = RAGEngine()
                glossary_dict = db.get_terms_for_game(game_id, target_language)
                tm_dict = db.get_tm_for_game(game_id, target_language)
                game_profile = db.get_game_profile(game_id)

                rag.load_resources(
                    glossary_dict=glossary_dict,
                    tm_dict=tm_dict,
                    game_profile=game_profile,
                )

                st.session_state.rag_engine = rag
                st.rerun()

            # =================================================
            # STOP TRANSLATION
            # =================================================
            if stop_clicked:
                st.session_state.is_translating = False
                st.warning("Translation process cancelled by user.")
                # Removed st.rerun() here so the warning message actually stays on screen

            # =================================================
            # ACTIVE TRANSLATION LOOP
            # =================================================
            if st.session_state.is_translating:
                batches = st.session_state.batches
                total_batches = st.session_state.total_batches
                current_idx = st.session_state.current_batch

                if current_idx < total_batches:
                    progress_val = current_idx / total_batches
                    st.progress(progress_val)

                    elapsed = time.time() - st.session_state.start_time
                    mins, secs = divmod(int(elapsed), 60)
                    time_str = f"{mins:02d}:{secs:02d}"

                    col_m1, col_m2, col_m3 = st.columns(3)

                    col_m1.metric("Progress", f"Batch {current_idx + 1} / {total_batches}")
                    col_m2.metric("Elapsed Time", time_str)
                    col_m3.metric("Status", "Processing")

                    batch_rows = batches[current_idx]
                    rag = st.session_state.rag_engine

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

                        review = reviewer_agent(
                            original_rows=batch_rows,
                            translated_batch=response,
                        )

                        for item in (response.translations or []):
                            st.session_state.translations_dict[item.row_id] = item.translated_text

                    except Exception as e:
                        # Use st.toast so the error shows up without breaking the UI flow on rerun
                        st.toast(f"Error on Batch {current_idx + 1}: {e}", icon="🚨")
                        for r in batch_rows:
                            if r.row_id not in st.session_state.translations_dict:
                                st.session_state.translations_dict[r.row_id] = r.source_text

                    # -----------------------------------------
                    # ENSURE ALL ROWS HAVE OUTPUT (Fallback)
                    # -----------------------------------------
                    for r in batch_rows:
                        if r.row_id not in st.session_state.translations_dict:
                            st.session_state.translations_dict[r.row_id] = r.source_text

                    st.session_state.current_batch += 1
                    time.sleep(0.1)
                    st.rerun()

                else:
                    # -----------------------------------------
                    # FINALIZE TRANSLATION
                    # -----------------------------------------
                    st.session_state.is_translating = False
                    st.session_state.translation_complete = True

                    target_col_name = f"text_{target_language.strip().replace(' ', '_')}"

                    ExcelHandler.write_translated_sheet(
                        original_file=temp_input_path,
                        translations=st.session_state.translations_dict,
                        target_column=target_col_name,
                        output_file=temp_output_path,
                    )
                    
                    st.rerun() # Rerun to break the loop and show the final results cleanly

            # =================================================
            # DISPLAY FINAL RESULTS
            # =================================================
            if st.session_state.get("translation_complete"):
                total_elapsed = time.time() - st.session_state.start_time
                mins, secs = divmod(int(total_elapsed), 60)

                st.success(f"Translation completed successfully in {mins}m {secs}s.")

                render_html("""
                <div class="section-title">
                    Translated Data
                </div>
                """)

                if temp_output_path.lower().endswith(".csv"):
                    translated_df = pd.read_csv(temp_output_path)
                else:
                    translated_df = pd.read_excel(temp_output_path)

                st.dataframe(
                    translated_df,
                    use_container_width=True,
                    height=300
                    
                )

                lang_clean = target_language.lower().strip().replace(" ", "_")
                mime_type = (
                    "text/csv" if temp_output_path.lower().endswith(".csv")
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                with open(temp_output_path, "rb") as file:
                    st.download_button(
                        label=f"Download {target_language} File",
                        data=file,
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

    # ========================================================
    # GAME PROFILE
    # ========================================================
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

    existing_profile = db.get_game_profile(game_id)

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
            st.success(f"Game Profile for `{game_id}` saved successfully.")

    st.divider()

    # ========================================================
    # DATABASE SEEDING
    # ========================================================
    render_html("""
    <div class="section-title">
        Localization Knowledge Base
    </div>
    """)

    render_html(f"""
    <div class="section-description">
        Upload reference translations for
        <strong>{game_id}</strong> into
        <strong>{target_language}</strong>.
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
        if rag_file.name.lower().endswith(".csv"):
            df_rag = pd.read_csv(rag_file)
        else:
            try:
                excel_obj = pd.ExcelFile(rag_file)
                sheet_names = excel_obj.sheet_names

                selected_sheet = st.selectbox(
                    "Excel Sheet",
                    options=sheet_names,
                    key="rag_sheet_select",
                )

                df_rag = pd.read_excel(excel_obj, sheet_name=selected_sheet)
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
                            status_rag.update(
                                label="Database Upload Complete",
                                state="complete",
                                expanded=False,
                            )
                            st.success(f"Successfully added {count:,} glossary terms to SQLite.")
                        else:
                            count = db.upsert_tm(
                                game_id,
                                target_language,
                                pairs,
                            )
                            status_rag.update(
                                label="Database Upload Complete",
                                state="complete",
                                expanded=False,
                            )
                            st.success(f"Successfully added {count:,} Translation Memory records to SQLite.")

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

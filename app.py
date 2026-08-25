import os
import time
import html
import tempfile
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from textwrap import dedent
import pandas as pd
import streamlit as st
from streamlit_cookies_controller import CookieController

# Number of translation batches to run in parallel against the LLM API.
MAX_CONCURRENT_BATCHES = 4

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
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# HTML HELPER
# ============================================================

def render_html(html_string):
    st.markdown(
        dedent(html_string).strip(),
        unsafe_allow_html=True,
    )


# ============================================================
# CACHE & DB WRAPPERS (PERFORMANCE)
# ============================================================

db = SupabaseDBEngine()
cookie_controller = CookieController()

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
# DESIGN SYSTEM — DYNAMIC THEME CSS
# ============================================================

render_html("""
<style>
/* ── Typeface ─────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Dynamic Design Tokens ────────────────────────────────── */
/* These tokens inherit from Streamlit's native theme to seamlessly 
   support BOTH Light and Dark mode switches */
:root {
  --surface-0:   var(--background-color);
  --surface-1:   var(--secondary-background-color);
  --surface-2:   var(--secondary-background-color);
  --surface-3:   rgba(128, 128, 128, 0.1);

  --accent:      #6366f1;
  --accent-dim:  #4f46e5;
  --accent-glow: rgba(99, 102, 241, 0.25);
  --accent-soft: rgba(99, 102, 241, 0.1);

  --success:     #22c55e;
  --success-text:#16a34a;
  --success-soft: rgba(34, 197, 94, 0.15);
  
  --warning:     #f59e0b;
  --warning-soft: rgba(245, 158, 11, 0.15);

  /* Transparent grey borders work perfectly on both white and black backgrounds */
  --border:       rgba(128, 128, 128, 0.25);
  --border-hover: rgba(128, 128, 128, 0.4);

  --r-sm:  6px;
  --r-md:  10px;
  --r-lg:  14px;
  --r-xl:  20px;

  --shadow-sm: 0 1px 3px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 16px rgba(0,0,0,0.08);
  --shadow-lg: 0 12px 40px rgba(0,0,0,0.12);
}

/* ── Global Reset ─────────────────────────────────────────── */
html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  -webkit-font-smoothing: antialiased;
}

.main .block-container {
  padding: 1.5rem 2rem 3rem 2rem;
  max-width: 1440px;
}

/* ── Forms Globally ───────────────────────────────────────── */
[data-testid="stForm"] {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 24px;
}

/* Specific styling for the Login Form via pseudo-selector */
[data-testid="stForm"]:has(.login-marker) {
  border-radius: var(--r-xl) !important;
  padding: 40px 36px !important;
  box-shadow: var(--shadow-lg) !important;
}

/* ── Sidebar ──────────────────────────────────────────────── */
section[data-testid="stSidebar"] > div { padding: 0; }

section[data-testid="stSidebar"] label {
  color: var(--text-color) !important;
  opacity: 0.7 !important;
  font-size: 0.8rem !important;
  font-weight: 600 !important;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

section[data-testid="stSidebar"] .stSelectbox > div > div {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  color: var(--text-color);
}

[data-testid="InputInstructions"] { display: none !important; }

/* ── Sidebar Brand ────────────────────────────────────────── */
.sb-brand {
  padding: 20px 20px 16px 20px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 11px;
}

.sb-logo {
  width: 36px; height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 14px var(--accent-glow);
}

.sb-logo svg { width: 18px; height: 18px; }

.sb-wordmark { line-height: 1.2; }

.sb-title {
  color: var(--text-color);
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.sb-sub {
  color: var(--text-color);
  opacity: 0.6;
  font-size: 0.75rem;
  font-weight: 500;
  margin-top: 2px;
}

/* ── Sidebar Section Label ────────────────────────────────── */
.sb-section {
  padding: 16px 20px 6px 20px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-color);
  opacity: 0.5;
}

/* ── DB Context Badge ─────────────────────────────────────── */
.sb-db-badge {
  margin: 6px 16px 4px 16px;
  background: var(--success-soft);
  border: 1px solid var(--success-soft);
  border-radius: var(--r-md);
  padding: 8px 12px;
}

.sb-db-label {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--success-text);
  opacity: 0.8;
}

.sb-db-value {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--success-text);
  margin-top: 3px;
  font-family: 'JetBrains Mono', monospace;
  word-break: break-all;
}

/* ── Sidebar User/Footer ──────────────────────────────────── */
.sb-user {
  margin: 8px 16px 4px 16px;
  background: var(--surface-3);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 9px 12px;
  display: flex;
  align-items: center;
  gap: 9px;
}

.sb-avatar {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent-dim));
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: white;
  flex-shrink: 0;
}

.sb-user-email {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-color);
  opacity: 0.8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sb-credit {
  padding: 12px 20px 20px 20px;
  font-size: 0.75rem;
  color: var(--text-color);
  opacity: 0.5;
  line-height: 1.6;
}

/* ── Page Header ──────────────────────────────────────────── */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 0 0 20px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 22px;
}

.page-header-left { display: flex; align-items: center; gap: 14px; }

.page-title {
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--text-color);
  letter-spacing: -0.04em;
  line-height: 1.15;
}

.page-desc {
  color: var(--text-color);
  opacity: 0.7;
  font-size: 0.85rem;
  margin-top: 4px;
  font-weight: 400;
}

.page-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-color);
  opacity: 0.8;
  white-space: nowrap;
}

.header-badge .dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 6px var(--success);
}

/* ── Metric Cards ─────────────────────────────────────────── */
.metric-card {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 15px 18px;
  min-height: 82px;
  transition: border-color 0.15s;
}

.metric-card:hover { border-color: var(--border-hover); }

.metric-eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-color);
  opacity: 0.6;
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 7px;
}

.metric-value {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-color);
  letter-spacing: -0.02em;
}

.metric-sub {
  font-size: 0.75rem;
  color: var(--text-color);
  opacity: 0.6;
  margin-top: 3px;
}

/* ── Tabs ─────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  gap: 2px;
  background: transparent;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0;
}

.stTabs [data-baseweb="tab"] {
  height: 44px;
  padding: 0 18px;
  color: var(--text-color);
  opacity: 0.6;
  font-weight: 600;
  font-size: 0.9rem;
  border-radius: var(--r-sm) var(--r-sm) 0 0;
  background: transparent;
  letter-spacing: -0.01em;
}

.stTabs [aria-selected="true"] {
  color: var(--text-color) !important;
  opacity: 1 !important;
  background: var(--surface-2) !important;
}

.stTabs [data-baseweb="tab-highlight"] {
  background: var(--accent);
  height: 2px;
}

/* ── Section Headers ──────────────────────────────────────── */
.sec-header {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 22px 0 6px 0;
}

.sec-header-icon {
  width: 28px; height: 28px;
  border-radius: var(--r-sm);
  background: var(--accent-soft);
  border: 1px solid var(--accent-soft);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.sec-header-icon svg { width: 14px; height: 14px; color: var(--accent); }

.sec-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-color);
  letter-spacing: -0.02em;
}

.sec-desc {
  font-size: 0.85rem;
  color: var(--text-color);
  opacity: 0.7;
  margin: 3px 0 14px 0;
  line-height: 1.55;
}

/* ── Upload Zone ──────────────────────────────────────────── */
[data-testid="stFileUploader"] {
  background: var(--surface-1);
  border: 1.5px dashed rgba(128,128,128,0.4);
  border-radius: var(--r-lg);
  padding: 6px;
  transition: border-color 0.2s;
}

[data-testid="stFileUploader"]:hover {
  border-color: var(--accent);
}

[data-testid="stFileUploaderDropzone"] {
  background: var(--surface-3);
  border-radius: 10px;
}

/* ── Data Preview Container ───────────────────────────────── */
.preview-wrap {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  overflow: hidden;
  margin-bottom: 4px;
}

.preview-bar {
  padding: 9px 14px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.preview-bar-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-color);
  opacity: 0.8;
  display: flex; align-items: center; gap: 6px;
}

.preview-bar-count {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--surface-3);
  color: var(--text-color);
  opacity: 0.8;
  font-weight: 600;
}

/* ── Batch Status Strip ───────────────────────────────────── */
.batch-strip {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.batch-strip-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-color);
  opacity: 0.8;
}

.batch-strip-value {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-color);
  opacity: 0.6;
  font-family: 'JetBrains Mono', monospace;
}

/* ── Buttons ──────────────────────────────────────────────── */
.stButton > button {
  border-radius: var(--r-md);
  min-height: 38px;
  font-weight: 600;
  font-size: 0.9rem;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-color);
  transition: all 0.15s;
  letter-spacing: -0.01em;
}

.stButton > button:hover {
  border-color: var(--border-hover);
  background: var(--surface-3);
}

.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
  border: none !important;
  color: white !important;
  box-shadow: 0 4px 14px var(--accent-glow);
}

.stButton > button[kind="primary"]:hover {
  box-shadow: 0 6px 20px rgba(99,102,241,0.35);
  transform: translateY(-1px);
}

.stDownloadButton > button {
  border-radius: var(--r-md);
  font-weight: 700;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  border: none;
  color: white !important;
  font-size: 0.9rem;
  box-shadow: 0 4px 16px var(--accent-glow);
}

/* ── Progress Block ───────────────────────────────────────── */
.progress-card {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 20px;
  margin: 14px 0;
}

.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.progress-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--text-color);
  display: flex; align-items: center; gap: 8px;
}

.progress-spinner {
  width: 14px; height: 14px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes spin { to { transform: rotate(360deg); } }

.stProgress > div > div > div {
  background: linear-gradient(90deg, #6366f1, #818cf8);
  border-radius: 999px;
}

/* ── Metrics (native) override ────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 12px 15px;
}

[data-testid="stMetricLabel"] {
  color: var(--text-color) !important;
  opacity: 0.7 !important;
  font-size: 0.75rem !important;
  font-weight: 700 !important;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

[data-testid="stMetricValue"] {
  color: var(--text-color) !important;
  font-size: 1.1rem !important;
  font-weight: 700 !important;
}

/* ── Dataframe ────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  overflow: hidden;
}

/* ── Inputs / Text ────────────────────────────────────────── */
.stTextArea textarea,
.stTextInput input,
.stSelectbox > div > div {
  background: var(--surface-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-md) !important;
  color: var(--text-color) !important;
  font-size: 0.9rem;
}

.stTextArea textarea:focus,
.stTextInput input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px var(--accent-soft) !important;
}

/* ── Radio ────────────────────────────────────────────────── */
.stRadio > div { gap: 8px; }

.stRadio > div > label {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 7px 14px;
  font-size: 0.9rem;
  color: var(--text-color);
  cursor: pointer;
  transition: all 0.15s;
}

.stRadio > div > label:hover {
  border-color: var(--border-hover);
}

/* ── DB Panel Header ──────────────────────────────────────── */
.db-panel-header {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 18px 22px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
}


/* ── Conflict Card ────────────────────────────────────────── */
.conflict-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--warning-soft);
  border: 1px solid var(--warning-soft);
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--warning);
  margin-bottom: 12px;
}

/* ── Divider ──────────────────────────────────────────────── */
.stDivider { border-color: var(--border) !important; }

hr { border-color: var(--border) !important; }

/* ── Caption ──────────────────────────────────────────────── */
.stCaption { color: var(--text-color) !important; opacity: 0.6 !important; font-size: 0.8rem !important; }

/* ── Footer ───────────────────────────────────────────────── */
.main-footer {
  margin-top: 48px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
  text-align: center;
  color: var(--text-color);
  opacity: 0.5;
  font-size: 0.8rem;
  letter-spacing: 0.05em;
}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--surface-3); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--border-hover); }
</style>

<script>
// Prevent Ctrl+C / Cmd+C from triggering Streamlit's cache-clear shortcut modal
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'c') {
        e.stopImmediatePropagation();
    }
}, true);
</script>
""")


# ============================================================
# SVG ICON LIBRARY
# ============================================================

def icon(name, size=16, color="currentColor"):
    """Return an inline SVG icon string."""
    icons = {
        "globe": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
        "database": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
        "upload": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>',
        "play": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
        "check-circle": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
        "project": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="6" height="4"/><rect x="16" y="3" width="6" height="4"/><rect x="9" y="10" width="6" height="4"/><line x1="5" y1="7" x2="5" y2="19"/><line x1="19" y1="7" x2="19" y2="19"/><line x1="5" y1="19" x2="19" y2="19"/></svg>',
        "language": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="m22 22-5-10-5 10"/><path d="M14 18h6"/></svg>',
        "cpu": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>',
        "columns": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="8" height="18" rx="1"/><rect x="13" y="3" width="8" height="18" rx="1"/></svg>',
        "settings": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 1.41 1.41L19.07 4.93zM12 2v2M12 20v2M4.93 4.93 3.51 6.34M19.07 19.07l-1.41-1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M19.07 4.93 17.66 6.34"/></svg>',
        "file": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>',
        "book": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
        "warning": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        "lock": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
        "download": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
        "layers": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 17 22 12"/></svg>',
    }
    return icons.get(name, "")


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
        # Give the browser a brief moment to process cookie deletion
        time.sleep(0.5)
    except Exception:
        pass
    
    # Set a flag to prevent immediate auto-login from a lingering cookie read
    st.session_state.just_logged_out = True
    st.session_state.user = None
    
    # Clear all other keys safely without losing our logout flag
    keys_to_keep = {"just_logged_out"}
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
            
    st.query_params.clear()


# 1. Auto-login / session restore via browser cookie

if st.session_state.user is None and not st.session_state.get("just_logged_out", False):
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
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Use native layout columns to center the form cleanly
    _, col, _ = st.columns([1, 1.2, 1])
    
    with col:
        with st.form("login_form"):
            # Hidden marker lets us target this exact form via CSS
            st.markdown('<div class="login-marker"></div>', unsafe_allow_html=True)
            
            st.markdown("""
            <div style="display:flex; flex-direction: column; align-items:center; gap:12px; margin-bottom:24px;">
                <div style="width:48px;height:48px;border-radius:12px;
                            background:linear-gradient(135deg,#6366f1,#4f46e5);
                            display:flex;align-items:center;justify-content:center;
                            box-shadow:0 6px 20px rgba(99,102,241,0.25);">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                         stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="2" y1="12" x2="22" y2="12"/>
                        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10
                                 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                    </svg>
                </div>
                <div style="text-align: center;">
                    <div style="color:var(--text-color);font-size:1.4rem;font-weight:800;letter-spacing:-0.03em;">
                        LocaTool
                    </div>
                    <div style="color:var(--text-color); opacity:0.6; font-size:0.9rem;margin-top:4px;">
                        Sign in to access your localization workspace
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            email = st.text_input(
                "Email address",
                placeholder="e.g. you@gmail.com",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••••",
            )
            submit_button = st.form_submit_button(
                "Sign in →",
                use_container_width=True,
                type="primary",
            )

            if submit_button:
                email = email.strip()
                if not email or not password:
                    st.error("Enter both email and password.")
                else:
                    try:
                        user, token, error = db.sign_in(email, password)
                    except Exception as e:
                        user, token, error = None, None, str(e)

                    if error or not user or not token:
                        st.error(f"Sign-in failed: {error or 'Invalid credentials.'}")
                    else:
                        st.session_state.clear()
                        st.session_state.user = user
                        st.session_state.last_active = time.time()
                        try:
                            cookie_controller.set("locatool_auth_token", token, max_age=3600*24*7)  # 7 days
                            time.sleep(0.5)  # Ensure cookie is set before rerun
                        except Exception as e:
                            clear_authenticated_session()
                            st.error(f"Session error: {e}")
                            st.stop()
                        st.rerun()

        st.markdown("""
        <div style="margin-top:20px;text-align:center;color:var(--text-color); opacity:0.5; font-size:0.75rem;">
            Protected workspace · Authorized access only
        </div>
        """, unsafe_allow_html=True)


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
    st.warning("Session expired after 10 minutes of inactivity. Please sign in again.")
    st.stop()

st.session_state.last_active = current_time


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    # Brand
    render_html(f"""
    <div class="sb-brand">
        <div class="sb-logo">
            {icon("globe", 18, "white")}
        </div>
        <div class="sb-wordmark">
            <div class="sb-title">LocaTool</div>
            <div class="sb-sub">AI Localization Workspace</div>
        </div>
    </div>
    """)

    # User
    if st.session_state.user:
        safe_email = html.escape(str(st.session_state.user.email))
        initial = safe_email[0].upper() if safe_email else "U"
        render_html(f"""
        <div class="sb-user">
            <div class="sb-avatar">{initial}</div>
            <div class="sb-user-email">{safe_email}</div>
        </div>
        """)

    if st.button("Sign out", use_container_width=True, key="logout_btn"):
        clear_authenticated_session()
        st.rerun()

    # Project Section
    render_html('<div class="sb-section">Project Setup</div>')

    project_list = [
        "DM_03",
        "Tarbi3a_Baloot",
        "Baloot_Challenges",
        "Direct_translation",
        "sawa",
        "S06"
    ]

    selected_project = st.selectbox(
        "Active Project",
        options=project_list,
        label_visibility="visible",
    )

    if selected_project == "+ Add New Project":
        game_id = st.text_input(
            "Project identifier",
            value="new_project",
            placeholder="e.g. S06",
        )
    else:
        game_id = selected_project

    # Language Section
    supported_languages = ["Arabic", "English", "Turkish"]

    target_language = st.selectbox(
        "Target language",
        options=supported_languages,
        index=0,
        label_visibility="visible",
    )

    # DB context badge
    safe_game_id = html.escape(game_id.lower().strip())
    safe_target_lang = html.escape(target_language.lower().strip())

    render_html(f"""
    <div class="sb-db-badge">
        <div class="sb-db-label">Active database</div>
        <div class="sb-db-value">{safe_game_id}_{safe_target_lang}</div>
    </div>
    """)


# ============================================================
# PAGE HEADER
# ============================================================

render_html(f"""
<div class="page-header">
    <div class="page-header-left">
        <div>
            <div class="page-title">Localization Dashboard</div>
            <div class="page-desc">
                Translate, review and manage game text with AI-powered workflows.
            </div>
        </div>
    </div>
    <div class="page-header-right">
        <div class="header-badge">
            <span class="dot"></span>
            {html.escape(game_id)}
        </div>
        <div class="header-badge">
            {icon("language", 12, "currentColor")}
            {html.escape(target_language)}
        </div>
        <div class="header-badge">
            {icon("check-circle", 12, "currentColor")}
            System Ready
        </div>
    </div>
</div>
""")


# ============================================================
# PROJECT METRIC CARDS
# ============================================================

mc1, mc2, mc3 = st.columns(3)

with mc1:
    render_html(f"""
    <div class="metric-card">
        <div class="metric-eyebrow">
            {icon("project", 12, "#6366f1")}
            Active project
        </div>
        <div class="metric-value">{html.escape(game_id)}</div>
        <div class="metric-sub">Current localization target</div>
    </div>
    """)

with mc2:
    render_html(f"""
    <div class="metric-card">
        <div class="metric-eyebrow">
            {icon("language", 12, "#6366f1")}
            Target language
        </div>
        <div class="metric-value">{html.escape(target_language)}</div>
        <div class="metric-sub">Chinese → {html.escape(target_language)}</div>
    </div>
    """)

with mc3:
    render_html(f"""
    <div class="metric-card">
        <div class="metric-eyebrow">
            <div style="background: var(--accent-soft); border-radius: 4px; padding: 2px;">
                {icon("database", 12, "#6366f1")}
            </div>
            Knowledge Base
        </div>
        <div class="metric-value">Connected</div>
        <div class="metric-sub">TM & Glossary ready for translation</div>
    </div>
    """)

render_html('<div style="height:18px"></div>')


# ============================================================
# TABS
# ============================================================

tab1, tab2 = st.tabs([
    "  🌐  Localize Game Text  ",
    "  🗄️  Database & Context  ",
])


# ============================================================
# TAB 1 — LOCALIZATION WORKSPACE
# ============================================================

# ============================================================
# TAB 1 — LOCALIZATION WORKSPACE
# ============================================================

with tab1:

    # ── Step 1: Configuration (Moved from Sidebar) ────────────
    with st.expander("⚙️ Advanced Settings (AI Model & Batching)"):
        cfg_col1, cfg_col2 = st.columns(2)

        with cfg_col1:
            model_options = [
                # "qwen/qwen3-235b-a22b-2507",
                # "qwen/qwen3.7-plus",
                # "google/gemini-3.1-flash-lite",
                "google/gemini-3.7-flash"
            ]
            model_choice = st.selectbox(
                "AI Model",
                options=model_options,
                index=0,
                help="Select the AI model used for translation.",
            )

        with cfg_col2:
            batch_mode = st.radio(
                "Batching Strategy",
                options=["Auto", "Manual"],
                horizontal=True,
                help="Auto uses a smart character budget to handle mixed long/short text safely.",
            )

            if batch_mode == "Manual":
                manual_batch_size = st.slider("Rows per batch", 1, 50, 10, 1)
            else:
                manual_batch_size = 10

   # ── Step 2: Input Method Selection ────────────────────────────────────────
    render_html(f"""
    <div class="sec-header">
        <div class="sec-header-icon">{icon("upload", 14, "#6366f1")}</div>
        <div class="sec-title">Provide game text</div>
    </div>
    <div class="sec-desc">
        Upload a file (<strong>.xlsx</strong> / <strong>.csv</strong>) or manually enter text to translate into <strong>{html.escape(target_language)}</strong> for <strong>{html.escape(game_id)}</strong>.
    </div>
    """)

    input_mode = st.radio(
        "Input Mode",
        options=["File Upload", "Manual Entry"],
        horizontal=True,
        label_visibility="collapsed"
    )

    is_data_ready = False
    df_preview = None
    uploaded_file_name = None
    file_bytes_buffer = None
    is_csv = False

    if input_mode == "File Upload":
        # Empty State Helper
        if "game_text_uploader" not in st.session_state or not st.session_state.game_text_uploader:
            render_html("""
            <div style="background: var(--surface-2); padding: 16px 20px; border-radius: var(--r-md); border: 1px dashed var(--border); margin-bottom: 16px;">
                <div style="font-size: 0.85rem; color: var(--text-color); opacity: 0.8;">
                    <strong>💡 Pro Tip:</strong> Before uploading, ensure your file has clear headers. The app will let you select which column contains the source text.
                </div>
            </div>
            """)

        uploaded_file = st.file_uploader(
            "Drop your file here or click to browse",
            type=["xlsx", "csv"],
            key="game_text_uploader",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            # Clear old translation state when a NEW file is uploaded
            if st.session_state.get("last_uploaded_file_id") != uploaded_file.file_id:
                st.session_state.last_uploaded_file_id = uploaded_file.file_id
                st.session_state.translation_complete = False
                st.session_state.pop("final_download_bytes", None)
                st.session_state.pop("final_elapsed_time", None)

            is_csv = uploaded_file.name.lower().endswith(".csv")
            selected_sheet_trans = None
            
            if is_csv:
                df_preview = pd.read_csv(uploaded_file).fillna("").astype(str)
            else:
                try:
                    excel_obj = pd.ExcelFile(uploaded_file)
                    sheet_names = excel_obj.sheet_names
                    selected_sheet_trans = st.selectbox(
                        "Select sheet to translate",
                        options=sheet_names,
                        key="trans_sheet_select"
                    )
                    df_preview = pd.read_excel(
                        excel_obj, sheet_name=selected_sheet_trans
                    ).fillna("").astype(str)
                except Exception as e:
                    st.error(f"Error reading Excel: {e}")
                    
            # Save the sheet name to session state so the Start button can use it
            st.session_state.selected_sheet_trans = selected_sheet_trans

            uploaded_file.seek(0)
            file_bytes_buffer = uploaded_file.getbuffer()
            uploaded_file_name = uploaded_file.name
            is_data_ready = True

    else:
        # Manual Entry State
        if "manual_trans_df" not in st.session_state:
            st.session_state.manual_trans_df = pd.DataFrame(
                {"Source Text": [""], "Context": [""]}
            )

        st.caption("Paste or type your text directly below. Add new rows as needed.")
        edited_df = st.data_editor(
            st.session_state.manual_trans_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Source Text": st.column_config.TextColumn("Source text (required)", required=True),
                "Context": st.column_config.TextColumn("Context / type (optional)")
            }
        )

        # Check if user has actually entered text
        valid_rows = edited_df[edited_df["Source Text"].str.strip() != ""]
        if not valid_rows.empty:
            df_preview = edited_df.copy()
            # Convert to CSV in memory so the pipeline handles it like a file upload
            csv_buffer = io.BytesIO()
            df_preview.to_csv(csv_buffer, index=False)
            file_bytes_buffer = csv_buffer.getvalue()
            uploaded_file_name = "manual_input.csv"
            is_csv = True
            is_data_ready = True

            # Clear old state if the manual text is edited
            current_hash = hash(file_bytes_buffer)
            if st.session_state.get("last_manual_hash") != current_hash:
                st.session_state.last_manual_hash = current_hash
                st.session_state.translation_complete = False
                st.session_state.pop("final_download_bytes", None)
                st.session_state.pop("final_elapsed_time", None)

    # ── Step 3 & 4: Preview & Mapping ───────────────────────────────────
    if is_data_ready and df_preview is not None:
        safe_file_name = html.escape(uploaded_file_name)

        if len(df_preview.columns) == 0:
            st.error("The provided data has no columns.")
        else:
            if input_mode == "File Upload":
                # Only show file preview and mapping if a file was uploaded 
                # (Manual entry already shows the grid)
                render_html(f"""
                <div class="sec-header" style="margin-top:20px;">
                    <div class="sec-header-icon">{icon("file", 14, "#6366f1")}</div>
                    <div class="sec-title">File preview</div>
                </div>
                <div class="preview-wrap">
                    <div class="preview-bar">
                        <div class="preview-bar-title">
                            {icon("file", 14, "currentColor")}
                            {safe_file_name}
                        </div>
                        <div class="preview-bar-count">{len(df_preview):,} rows</div>
                    </div>
                </div>
                """)
                st.dataframe(df_preview, use_container_width=True, height=260)

                render_html(f"""
                <div class="sec-header" style="margin-top:20px;">
                    <div class="sec-header-icon">{icon("columns", 14, "#6366f1")}</div>
                    <div class="sec-title">Map data columns</div>
                </div>
                <div class="sec-desc">
                    Select which column contains the source text to translate,
                    and optionally a context/type column to improve AI accuracy.
                </div>
                """)

                col_sel1, col_sel2, col_sel3 = st.columns(3)
                with col_sel1:
                    selected_source_col = st.selectbox(
                        "Source text column (required)",
                        options=df_preview.columns,
                        index=0,
                    )
                with col_sel2:
                    ctx_options = ["— No context column —"] + list(df_preview.columns)
                    default_ctx_idx = 0
                    for i, col in enumerate(df_preview.columns):
                        if col.lower() in ["text_type", "context", "type", "description"]:
                            default_ctx_idx = i + 1
                            break
                    selected_context_col = st.selectbox(
                        "Context / type column (optional)",
                        options=ctx_options,
                        index=default_ctx_idx,
                    )
                with col_sel3:
                    tgt_options = ["— Create new column —"] + list(df_preview.columns)
                    target_col_selection = st.selectbox(
                        "Target column",
                        options=tgt_options,
                        index=0,
                    )

                actual_context_col = (
                    None if selected_context_col == "— No context column —"
                    else selected_context_col
                )

                # If user wants to create a new column, show a text input
                if target_col_selection == "— Create new column —":
                    final_target_col_name = st.text_input("New target column name", value=target_language)
                else:
                    final_target_col_name = target_col_selection
                    
                # Save the final target column name to session state for the translator
                st.session_state.final_target_col_name = final_target_col_name
            else:
                # Auto-map for Manual Entry
                selected_source_col = "Source Text"
                # Only use context if the user actually typed something in the context column
                has_context = "Context" in df_preview.columns and not df_preview["Context"].eq("").all()
                actual_context_col = "Context" if has_context else None
                st.session_state.final_target_col_name = target_language
                st.session_state.selected_sheet_trans = None

            if "translation_complete" not in st.session_state:
                st.session_state.translation_complete = False

            # Batch config strings for display
            if batch_mode == "Auto":
                use_smart_budget = True
                display_desc = "Dynamic character budget · ~1000 chars / batch"
            else:
                use_smart_budget = False
                display_desc = f"{manual_batch_size} rows per API request"
            
            # ── Step 4.5: Custom Instructions ──────────────────
            render_html(f"""
            <div class="sec-header" style="margin-top:20px;">
                <div class="sec-header-icon">{icon("cpu", 14, "#6366f1")}</div>
                <div class="sec-title">Custom AI Instructions (Optional)</div>
            </div>
            <div class="sec-desc">
                Add specific rules for this translation run (e.g., "Keep character names in English", "Use a casual tone"). 
                Leave empty to use the default Game Profile.
            </div>
            """)

            custom_instructions_input = st.text_area(
                "Custom AI Instructions",
                placeholder="Type your on-the-fly instructions here...",
                label_visibility="collapsed",
                height=100
            )

            # ── Step 5: Start ──────────────────────────
            render_html(f"""
            <div class="sec-header" style="margin-top:20px;">
                <div class="sec-header-icon">{icon("play", 14, "#6366f1")}</div>
                <div class="sec-title">Run translation</div>
            </div>
            """)

            render_html(f"""
            <div class="batch-strip" style="margin-bottom:14px;">
                <div class="batch-strip-label">Batch mode: {html.escape(batch_mode)}</div>
                <div class="batch-strip-value">{html.escape(display_desc)}</div>
            </div>
            """)

            start_clicked = st.button(
                "▶  Start Translation",
                type="primary",
                use_container_width=True,
            )

            # ── Step 6: Translation Engine + Progress ───────
            if start_clicked:
                st.session_state.translation_complete = False

                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_input_path = os.path.join(temp_dir, f"input_{uploaded_file_name}")
                    temp_output_path = os.path.join(temp_dir, f"output_{uploaded_file_name}")

                    with open(temp_input_path, "wb") as f:
                        f.write(file_bytes_buffer)

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

                    rows = ExcelHandler.read_game_sheet(
                        temp_input_path,
                        text_column=selected_source_col,
                        context_column=actual_context_col,
                        sheet_name=st.session_state.get("selected_sheet_trans")
                    )

                    # Dedupe identical rows and group near-duplicates (same text,
                    # different embedded number) so they translate once / together
                    # instead of scattering across separate batches.
                    batches, alias_map = ExcelHandler.prepare_batches(
                        rows,
                        batch_size=manual_batch_size,
                        use_smart_budget=use_smart_budget,
                    )

                    total_batches = len(batches)
                    translations_dict = {}

                    # Progress UI
                    render_html(f"""
                    <div class="progress-card">
                        <div class="progress-header">
                            <div class="progress-title">
                                <span class="progress-spinner"></span>
                                Processing — {html.escape(target_language)} translation
                            </div>
                        </div>
                    </div>
                    """)

                    progress_bar = st.progress(0.0)
                    ui_col1, ui_col2, ui_col3 = st.columns(3)
                    metric_progress = ui_col1.empty()
                    metric_time = ui_col2.empty()
                    metric_status = ui_col3.empty()

                    start_time = time.time()

                    def _translate_one_batch(batch_idx, batch_rows):
                        rag_context = rag.get_batch_context(
                            batch_rows=batch_rows,
                            target_language=target_language,
                        )

                        batch_request = BatchTranslationRequest(
                            batch_id=batch_idx + 1,
                            rows=batch_rows,
                            target_language=target_language,
                        )

                        response = translator_agent(
                            batch_request=batch_request,
                            rag_context=rag_context,
                            feedback="",
                            model_name=model_choice,
                            fallback_model_name="openai/gpt-4o-mini",
                            game_id=game_id,
                            custom_instructions=custom_instructions_input,
                        )

                        reviewer_agent(
                            original_rows=batch_rows,
                            translated_batch=response,
                        )

                        return response

                    completed_batches = 0

                    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BATCHES) as executor:
                        future_to_batch = {
                            executor.submit(_translate_one_batch, idx, batch_rows): (idx, batch_rows)
                            for idx, batch_rows in enumerate(batches)
                        }

                        for future in as_completed(future_to_batch):
                            current_idx, batch_rows = future_to_batch[future]

                            try:
                                response = future.result()
                                for item in (response.translations or []):
                                    translations_dict[item.row_id] = item.translated_text
                            except Exception as e:
                                st.toast(f"Batch {current_idx + 1} error: {e}", icon="⚠️")

                            for r in batch_rows:
                                if r.row_id not in translations_dict:
                                    translations_dict[r.row_id] = r.source_text

                            completed_batches += 1
                            elapsed = time.time() - start_time
                            mins, secs = divmod(int(elapsed), 60)

                            progress_bar.progress(completed_batches / max(1, total_batches))
                            metric_progress.metric(
                                "Batch", f"{completed_batches} / {total_batches}"
                            )
                            metric_time.metric("Elapsed", f"{mins:02d}:{secs:02d}")
                            metric_status.metric("Status", "Translating")

                    # Fill in rows that were skipped as exact/near duplicates
                    # by reusing their representative row's translation.
                    row_lookup = {r.row_id: r for r in rows}
                    for dup_row_id, rep_row_id in alias_map.items():
                        translations_dict[dup_row_id] = translations_dict.get(
                            rep_row_id, row_lookup[dup_row_id].source_text
                        )

                    progress_bar.progress(1.0)
                    metric_status.metric("Status", "Complete ✓")

                    ExcelHandler.write_translated_sheet(
                        original_file=temp_input_path,
                        translations=translations_dict,
                        target_column=st.session_state.get("final_target_col_name", target_language),
                        output_file=temp_output_path,
                        sheet_name=st.session_state.get("selected_sheet_trans")
                    )

                    with open(temp_output_path, "rb") as f:
                        st.session_state.final_download_bytes = f.read()

                    st.session_state.final_elapsed_time = time.time() - start_time
                    st.session_state.translation_complete = True

                st.rerun()

            # ── Step 7: Result + Download ───────────────────
            if st.session_state.get("translation_complete") and "final_download_bytes" in st.session_state:

                mins, secs = divmod(int(st.session_state.final_elapsed_time), 60)
                row_count = len(df_preview)

                render_html(f"""
                <div class="result-card" style="background: var(--success-soft); border: 1px solid var(--success-soft); border-radius: var(--r-lg); padding: 16px 20px; display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 16px 0 10px 0;">
                    <div class="result-left" style="display: flex; align-items: center; gap: 12px;">
                        <div class="result-icon" style="width: 38px; height: 38px; border-radius: 50%; background: var(--success-soft); border: 1px solid var(--success-soft); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            {icon("check-circle", 20, "#22c55e")}
                        </div>
                        <div>
                            <div class="result-title" style="font-size: 0.95rem; font-weight: 700; color: var(--success-text);">Translation complete</div>
                            <div class="result-sub" style="font-size: 0.85rem; color: var(--text-color); opacity: 0.7; margin-top: 3px;">
                                {row_count:,} rows · {mins}m {secs}s · {html.escape(target_language)} output ready
                            </div>
                        </div>
                    </div>
                </div>
                """)

                render_html(f"""
                <div class="sec-header">
                    <div class="sec-header-icon">{icon("file", 14, "#22c55e")}</div>
                    <div class="sec-title">Output preview</div>
                </div>
                """)

                file_bytes = st.session_state.final_download_bytes

                try:
                    if is_csv:
                        translated_df = pd.read_csv(io.BytesIO(file_bytes)).fillna("").astype(str)
                    else:
                        translated_df = pd.read_excel(io.BytesIO(file_bytes)).fillna("").astype(str)
                    st.dataframe(translated_df, use_container_width=True, height=280)
                except Exception as e:
                    st.error(f"Could not load preview: {e}")

                # Generate new filename: [Original Name]_translated.[ext]
                base_name, ext = os.path.splitext(uploaded_file_name)
                new_file_name = f"{base_name}_translated{ext}"

                mime_type = (
                    "text/csv" if is_csv
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                st.download_button(
                    label=f" 📥 Download {html.escape(target_language)} file",
                    data=st.session_state.final_download_bytes,
                    file_name=new_file_name,
                    mime=mime_type,
                    type="primary",
                    use_container_width=True,
                )

# ============================================================
# TAB 2 — DATABASE & CONTEXT
# ============================================================

with tab2:

    render_html(f"""
    <div class="db-panel-header">
        <div class="db-panel-icon" style="background: var(--accent-soft); border: 1px solid var(--accent-soft);">
            {icon("database", 20, "#6366f1")}
        </div>
        <div>
            <div class="db-panel-title">Database & Context Management</div>
            <div class="db-panel-desc">
                Configure game-specific tone, terminology, translation memory
                and localization context for <strong
                style="color:var(--text-color); opacity:0.8;">{html.escape(game_id)}</strong>.
            </div>
        </div>
    </div>
    """)

    # ── Game Profile ──────────────────────────────────────────
    render_html(f"""
    <div class="sec-header">
        <div class="sec-header-icon">{icon("settings", 14, "#6366f1")}</div>
        <div class="sec-title">Game profile</div>
    </div>
    <div class="sec-desc">
        Define the writing style and localization rules the AI follows
        when translating text for this game.
    </div>
    """)

    existing_profile = fetch_game_profile(db, game_id)

    with st.form("profile_form"):
        tone_input = st.text_area(
            "Profile instructions",
            value=existing_profile,
            height=150,
            placeholder=(
                "e.g. Epic strategy game with a commanding, formal tone. "
                "Use historical empire-building atmosphere. Keep UI text concise."
            ),
        )
        if st.form_submit_button("Save profile", type="primary"):
            db.upsert_game_profile(game_id, tone_input)
            fetch_game_profile.clear()
            st.success(f"Game profile for `{html.escape(game_id)}` saved.")

    st.divider()

    # ── Manual Term Entry ──────────────────────────────────────
    render_html(f"""
    <div class="sec-header">
        <div class="sec-header-icon">{icon("book", 14, "#6366f1")}</div>
        <div class="sec-title">Manual glossary entry</div>
    </div>
    <div class="sec-desc">
        Add or edit glossary terms directly. Conflicting entries are flagged
        for review before saving to <strong
        style="color:var(--text-color); opacity:0.8;">{html.escape(game_id)}</strong>.
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
            "Chinese Source": st.column_config.TextColumn(
                "Chinese source", required=True
            ),
            "Target Translation": st.column_config.TextColumn(
                f"{target_language} target", required=True
            ),
        },
    )

    if "pending_conflicts" not in st.session_state:
        st.session_state.pending_conflicts = None
    if "pending_pairs_to_save" not in st.session_state:
        st.session_state.pending_pairs_to_save = None

    if st.button("Save terms to database", type="primary"):
        pairs = []
        source_terms_list = []
        for _, row in edited_df.iterrows():
            src = str(row.get("Chinese Source", "")).strip()
            tgt = str(row.get("Target Translation", "")).strip()
            if src and tgt and src.lower() != "nan" and tgt.lower() != "nan":
                pairs.append({"source": src, "target": tgt})
                source_terms_list.append(src)

        if not pairs:
            st.error("Fill in at least one row with both source and target.")
        else:
            existing_records = db.check_conflicting_terms(
                game_id, target_language, source_terms_list
            )
            existing_map = {
                item["source_term"]: item["target_term"] for item in existing_records
            }

            conflicts = []
            clean_pairs = []

            for p in pairs:
                src = p["source"]
                tgt = p["target"]
                if src in existing_map:
                    conflicts.append({
                        "source": src,
                        "existing_target": existing_map[src],
                        "new_target": tgt,
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
                    st.success(f"Saved {count:,} term(s) to the database.")
                    st.session_state.pending_conflicts = None
                    st.session_state.pending_pairs_to_save = None
                except Exception as e:
                    st.error(f"Failed to save terms: {e}")

    # ── Conflict Resolution (Bulk Actions) ─────────────
    if st.session_state.pending_conflicts:

        n = len(st.session_state.pending_conflicts)
        render_html(f"""
        <div class="conflict-badge">
            {icon("warning", 12, "#f59e0b")}
            {n} conflict{"s" if n != 1 else ""} detected — review before saving
        </div>
        """)

        with st.form("conflict_resolution_form"):
            st.markdown("### Bulk Actions")
            bulk_decision = st.radio(
                "Apply to all conflicts below:", 
                ["Review individually", "Keep all existing", "Overwrite all with new"], 
                horizontal=True
            )
            st.divider()

            resolution_decisions = {}
            for idx, conflict in enumerate(st.session_state.pending_conflicts):
                src = conflict["source"]
                exist_tgt = conflict["existing_target"]
                new_tgt = conflict["new_target"]

                st.markdown(f"**Source:** `{src}`")

                col_a, col_b = st.columns(2)
                with col_a:
                    render_html(f"""
                    <div style="background:var(--success-soft);border:1px solid
                    var(--success-soft);border-radius:8px;padding:8px 12px;
                    font-size:0.85rem;color:var(--text-color);margin-bottom:6px;">
                        <div style="font-size:0.75rem;text-transform:uppercase;
                        letter-spacing:0.08em;opacity:0.7;margin-bottom:4px;">
                            Existing
                        </div>
                        {html.escape(exist_tgt)}
                    </div>
                    """)
                with col_b:
                    render_html(f"""
                    <div style="background:var(--accent-soft);border:1px solid
                    var(--accent-soft);border-radius:8px;padding:8px 12px;
                    font-size:0.85rem;color:var(--text-color);margin-bottom:6px;">
                        <div style="font-size:0.75rem;text-transform:uppercase;
                        letter-spacing:0.08em;opacity:0.7;margin-bottom:4px;">
                            New
                        </div>
                        {html.escape(new_tgt)}
                    </div>
                    """)

                # Determine default state based on bulk action
                default_idx = 0
                if bulk_decision == "Overwrite all with new":
                    default_idx = 1

                decision = st.radio(
                    f"Decision for `{src}`",
                    options=["Keep existing", "Overwrite with new"],
                    index=default_idx,
                    key=f"conflict_{idx}",
                    horizontal=True,
                )
                resolution_decisions[src] = decision
                st.divider()

            if st.form_submit_button("Confirm & save", type="primary"):
                final_pairs_to_save = list(st.session_state.pending_pairs_to_save)

                for conflict in st.session_state.pending_conflicts:
                    src = conflict["source"]
                    if "Overwrite" in resolution_decisions[src]:
                        final_pairs_to_save.append({
                            "source": src,
                            "target": conflict["new_target"],
                        })

                try:
                    count = db.upsert_terms(game_id, target_language, final_pairs_to_save)
                    fetch_terms.clear()
                    st.success(f"Conflicts resolved. Saved {count:,} term(s).")
                    st.session_state.pending_conflicts = None
                    st.session_state.pending_pairs_to_save = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save: {e}")

    st.divider()

    # ── Knowledge Base Upload ──────────────────────────────────
    render_html(f"""
    <div class="sec-header">
        <div class="sec-header-icon">{icon("layers", 14, "#6366f1")}</div>
        <div class="sec-title">Knowledge base upload</div>
    </div>
    <div class="sec-desc">
        Upload reference translations for
        <strong style="color:var(--text-color); opacity:0.8;">{html.escape(game_id)}</strong> →
        <strong style="color:var(--text-color); opacity:0.8;">{html.escape(target_language)}</strong>.
        Choose the target type before uploading.
    </div>
    """)

    target_type = st.radio(
        "Knowledge base type",
        options=["terms", "translation_memory"],
        format_func=lambda x: (
            "📌  Glossary terms  ·  Exact match"
            if x == "terms"
            else "🧠  Translation memory  ·  Fuzzy match"
        ),
        horizontal=True,
    )

    rag_file = st.file_uploader(
        "Upload reference file",
        type=["xlsx", "csv"],
        key="rag_file_uploader",
    )

    df_rag = None

    if rag_file is not None:
        if rag_file.name.lower().endswith(".csv"):
            df_rag = pd.read_csv(rag_file).fillna("").astype(str)
        else:
            try:
                excel_obj = pd.ExcelFile(rag_file)
                sheet_names = excel_obj.sheet_names
                selected_sheet = st.selectbox(
                    "Select sheet",
                    options=sheet_names,
                    key="rag_sheet_select",
                )
                df_rag = pd.read_excel(
                    excel_obj, sheet_name=selected_sheet
                ).fillna("").astype(str)
            except Exception as e:
                st.error(f"Error reading Excel: {e}")

        if df_rag is not None:
            render_html(f"""
            <div class="sec-header" style="margin-top:14px;">
                <div class="sec-header-icon">{icon("file", 14, "#6366f1")}</div>
                <div class="sec-title">Reference data preview</div>
            </div>
            """)

            render_html(f"""
            <div class="preview-wrap">
                <div class="preview-bar">
                    <div class="preview-bar-title">
                        {icon("file", 14, "currentColor")}
                        {html.escape(rag_file.name)}
                    </div>
                    <div class="preview-bar-count">{len(df_rag):,} rows</div>
                </div>
            </div>
            """)

            st.dataframe(df_rag, use_container_width=True, height=240)

            if len(df_rag.columns) < 2:
                st.warning(
                    "File has fewer than 2 columns. "
                    "Ensure it has both source and target columns."
                )

            col_source, col_target = st.columns(2)
            with col_source:
                selected_source_column = st.selectbox(
                    "Source column",
                    options=df_rag.columns,
                    index=0,
                )
            with col_target:
                selected_target_column = st.selectbox(
                    f"{target_language} target column",
                    options=df_rag.columns,
                    index=min(1, len(df_rag.columns) - 1),
                )

            if st.button("Upload to database", type="primary"):
                status_rag = st.status(
                    f"Uploading to {target_type}…",
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
                            if (src_str and tgt_str
                                    and src_str.lower() != "nan"
                                    and tgt_str.lower() != "nan"):
                                pairs.append({"source": src_str, "target": tgt_str})

                    if not pairs:
                        status_rag.update(label="No valid rows found", state="error")
                        st.error("No valid text pairs found to upload.")
                    else:
                        if target_type == "terms":
                            count = db.upsert_terms(game_id, target_language, pairs)
                            fetch_terms.clear()
                            status_rag.update(
                                label="Upload complete",
                                state="complete",
                                expanded=False,
                            )
                            st.success(
                                f"Added {count:,} glossary terms to the database."
                            )
                        else:
                            count = db.upsert_tm(game_id, target_language, pairs)
                            fetch_tm.clear()
                            status_rag.update(
                                label="Upload complete",
                                state="complete",
                                expanded=False,
                            )
                            st.success(
                                f"Added {count:,} translation memory records."
                            )

                except Exception as e:
                    status_rag.update(label="Upload failed", state="error")
                    st.error(f"Error uploading data: {e}")


# ============================================================
# FOOTER
# ============================================================

render_html("""
<div class="main-footer">
    LocaTool &nbsp;·&nbsp; AI Game Localization Workspace
    &nbsp;&nbsp;—&nbsp;&nbsp;
    Designed by&nbsp;<strong>SALAH SULTAN （萨利）</strong>
</div>
""")

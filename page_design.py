"""
LocaTool page design system.

Owns all CSS, SVG icons, and reusable HTML chrome so app.py stays
focused on Streamlit flow, auth, data, and translation logic.
"""

from textwrap import dedent
import html as html_lib
import streamlit as st


# ============================================================
# HTML HELPER
# ============================================================

def render_html(html_string: str) -> None:
    """Inject raw HTML/CSS into the Streamlit page."""
    st.markdown(dedent(html_string).strip(), unsafe_allow_html=True)


# ============================================================
# SVG ICON LIBRARY
# ============================================================

def icon(name: str, size: int = 16, color: str = "currentColor") -> str:
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
# GLOBAL THEME CSS + SHORTCUT GUARD
# ============================================================

_GLOBAL_STYLES = """
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

/* ── Batch Status Strip ────────────────────────────────     */
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
"""


def inject_global_styles() -> None:
    """Inject the full design-system CSS and keyboard-shortcut guard."""
    render_html(_GLOBAL_STYLES)


# ============================================================
# LAYOUT COMPONENTS
# ============================================================

def spacer(height_px: int = 18) -> None:
    render_html(f'<div style="height:{height_px}px"></div>')


def render_sidebar_brand() -> None:
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


def render_sidebar_user(email: str) -> None:
    safe_email = html_lib.escape(str(email))
    initial = safe_email[0].upper() if safe_email else "U"
    render_html(f"""
    <div class="sb-user">
        <div class="sb-avatar">{initial}</div>
        <div class="sb-user-email">{safe_email}</div>
    </div>
    """)


def render_sidebar_section(title: str) -> None:
    render_html(f'<div class="sb-section">{html_lib.escape(title)}</div>')


def render_db_badge(game_id: str, target_language: str) -> None:
    safe_game_id = html_lib.escape(game_id.lower().strip())
    safe_target_lang = html_lib.escape(target_language.lower().strip())
    render_html(f"""
    <div class="sb-db-badge">
        <div class="sb-db-label">Active database</div>
        <div class="sb-db-value">{safe_game_id}_{safe_target_lang}</div>
    </div>
    """)


def render_page_header(game_id: str, target_language: str) -> None:
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
                {html_lib.escape(game_id)}
            </div>
            <div class="header-badge">
                {icon("language", 12, "currentColor")}
                {html_lib.escape(target_language)}
            </div>
            <div class="header-badge">
                {icon("check-circle", 12, "currentColor")}
                System Ready
            </div>
        </div>
    </div>
    """)


def render_metric_card(
    icon_name: str,
    eyebrow: str,
    value: str,
    subtitle: str,
    wrap_icon: bool = False,
) -> None:
    icon_html = icon(icon_name, 12, "#6366f1")
    if wrap_icon:
        icon_html = (
            f'<div style="background: var(--accent-soft); border-radius: 4px; padding: 2px;">'
            f"{icon_html}</div>"
        )
    render_html(f"""
    <div class="metric-card">
        <div class="metric-eyebrow">
            {icon_html}
            {html_lib.escape(eyebrow)}
        </div>
        <div class="metric-value">{html_lib.escape(value)}</div>
        <div class="metric-sub">{html_lib.escape(subtitle)}</div>
    </div>
    """)


def render_section(icon_name: str, title: str, description=None, extra_style: str = ""):
    style_attr = f' style="{extra_style}"' if extra_style else ""
    render_html(f"""
    <div class="sec-header"{style_attr}>
        <div class="sec-header-icon">{icon(icon_name, 14, "#6366f1")}</div>
        <div class="sec-title">{html_lib.escape(title)}</div>
    </div>
    """)
    if description:
        render_html(f'<div class="sec-desc">{description}</div>')


def render_pro_tip(message: str) -> None:
    render_html(f"""
    <div style="background: var(--surface-2); padding: 16px 20px; border-radius: var(--r-md); border: 1px dashed var(--border); margin-bottom: 16px;">
        <div style="font-size: 0.85rem; color: var(--text-color); opacity: 0.8;">
            {message}
        </div>
    </div>
    """)


def render_success_banner(title: str, subtitle: str) -> None:
    render_html(f"""
    <div class="result-card" style="background: var(--success-soft); border: 1px solid var(--success-soft); border-radius: var(--r-lg); padding: 16px 20px; display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 16px 0 10px 0;">
        <div class="result-left" style="display: flex; align-items: center; gap: 12px;">
            <div class="result-icon" style="width: 38px; height: 38px; border-radius: 50%; background: var(--success-soft); border: 1px solid var(--success-soft); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                {icon("check-circle", 20, "#22c55e")}
            </div>
            <div>
                <div class="result-title" style="font-size: 0.95rem; font-weight: 700; color: var(--success-text);">{html_lib.escape(title)}</div>
                <div class="result-sub" style="font-size: 0.85rem; color: var(--text-color); opacity: 0.7; margin-top: 3px;">
                    {html_lib.escape(subtitle)}
                </div>
            </div>
        </div>
    </div>
    """)


def render_db_panel_header(game_id: str) -> None:
    safe_game = html_lib.escape(game_id)
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
                style="color:var(--text-color); opacity:0.8;">{safe_game}</strong>.
            </div>
        </div>
    </div>
    """)


def render_conflict_badge(count: int) -> None:
    suffix = "s" if count != 1 else ""
    render_html(f"""
    <div class="conflict-badge">
        {icon("warning", 12, "#f59e0b")}
        {count} conflict{suffix} detected — review before saving
    </div>
    """)


def render_term_choice_box(kind: str, target: str, note: str) -> None:
    """kind is 'existing' (green) or 'new' (accent)."""
    is_existing = kind == "existing"
    bg = "var(--success-soft)" if is_existing else "var(--accent-soft)"
    label = "Existing" if is_existing else "New"
    render_html(f"""
    <div style="background:{bg};border:1px solid
    {bg};border-radius:8px;padding:8px 12px;
    font-size:0.85rem;color:var(--text-color);margin-bottom:6px;">
        <div style="font-size:0.75rem;text-transform:uppercase;
        letter-spacing:0.08em;opacity:0.7;margin-bottom:4px;">
            {label}
        </div>
        Target: {html_lib.escape(target)} <br> Note: {html_lib.escape(note or 'None')}
    </div>
    """)


def render_preview_bar(filename: str, row_count: int) -> None:
    render_html(f"""
    <div class="preview-wrap">
        <div class="preview-bar">
            <div class="preview-bar-title">
                {icon("file", 14, "currentColor")}
                {html_lib.escape(filename)}
            </div>
            <div class="preview-bar-count">{row_count:,} rows</div>
        </div>
    </div>
    """)


def render_login_brand() -> None:
    render_html("""
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
    """)


def render_login_form_marker() -> None:
    render_html('<div class="login-marker"></div>')


def render_login_footer() -> None:
    render_html("""
    <div style="margin-top:20px;text-align:center;color:var(--text-color); opacity:0.5; font-size:0.75rem;">
        Protected workspace · Authorized access only
    </div>
    """)


def render_footer() -> None:
    render_html("""
    <div class="main-footer">
        LocaTool &nbsp;·&nbsp; AI Game Localization Workspace
        &nbsp;&nbsp;—&nbsp;&nbsp;
        Designed by&nbsp;<strong>SALAH SULTAN （萨利）</strong>
    </div>
    """)

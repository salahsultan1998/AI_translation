import os
import time
import html
import tempfile
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import streamlit as st
from streamlit_cookies_controller import CookieController

from excel_engine import ExcelHandler
from db_engine import SupabaseDBEngine
from rag_engine import RAGEngine
from agents import DEFAULT_MODEL, translator_agent, reviewer_agent
from custom_types import BatchTranslationRequest
from config import (
    MAX_CONCURRENT_BATCHES,
    INACTIVITY_LIMIT_SECONDS,
    MODEL_OPTIONS,
    SUPPORTED_LANGUAGES,
    PROJECT_OPTIONS,
)
from page_design import (
    inject_global_styles,
    render_sidebar_brand,
    render_sidebar_user,
    render_sidebar_section,
    render_db_badge,
    render_page_header,
    render_metric_card,
    render_section,
    render_pro_tip,
    render_success_banner,
    render_db_panel_header,
    render_conflict_badge,
    render_term_choice_box,
    render_preview_bar,
    render_login_brand,
    render_login_form_marker,
    render_login_footer,
    render_footer,
    spacer,
)


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


inject_global_styles()


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
        time.sleep(0.5)
    except Exception:
        pass

    st.session_state.just_logged_out = True
    st.session_state.user = None

    keys_to_keep = {"just_logged_out"}
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]

    st.query_params.clear()


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
    _, col, _ = st.columns([1, 1.2, 1])

    with col:
        with st.form("login_form"):
            render_login_form_marker()
            render_login_brand()

            email = st.text_input("Email address", placeholder="e.g. you@gmail.com")
            password = st.text_input("Password", type="password", placeholder="••••••••••")
            submit_button = st.form_submit_button("Sign in →", use_container_width=True, type="primary")

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
                            cookie_controller.set("locatool_auth_token", token, max_age=3600*24*7)
                            time.sleep(0.5)
                        except Exception as e:
                            clear_authenticated_session()
                            st.error(f"Session error: {e}")
                            st.stop()
                        st.rerun()

        render_login_footer()


if st.session_state.user is None:
    show_login_page()
    st.stop()


if "last_active" not in st.session_state:
    st.session_state.last_active = time.time()

current_time = time.time()

if current_time - st.session_state.last_active > INACTIVITY_LIMIT_SECONDS:
    clear_authenticated_session()
    st.warning("Session expired after 10 minutes of inactivity. Please sign in again.")
    st.stop()

st.session_state.last_active = current_time


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    render_sidebar_brand()

    if st.session_state.user:
        render_sidebar_user(st.session_state.user.email)

    if st.button("Sign out", use_container_width=True, key="logout_btn"):
        clear_authenticated_session()
        st.rerun()

    render_sidebar_section("Project Setup")

    selected_project = st.selectbox("Active Project", options=PROJECT_OPTIONS, label_visibility="visible")

    if selected_project == "+ Add New Project":
        game_id = st.text_input("Project identifier", value="new_project", placeholder="e.g. S06")
    else:
        game_id = selected_project

    target_language = st.selectbox("Target language", options=SUPPORTED_LANGUAGES, index=0, label_visibility="visible")

    render_db_badge(game_id, target_language)


# ============================================================
# PAGE HEADER + METRIC CARDS
# ============================================================

render_page_header(game_id, target_language)

mc1, mc2, mc3 = st.columns(3)

with mc1:
    render_metric_card("project", "Active project", game_id, "Current localization target")

with mc2:
    render_metric_card("language", "Target language", target_language, f"Chinese → {target_language}")

with mc3:
    render_metric_card(
        "database",
        "Knowledge Base",
        "Connected",
        "TM & Glossary ready for translation",
        wrap_icon=True,
    )

spacer(18)


# ============================================================
# TABS
# ============================================================

tab1, tab2 = st.tabs(["  🌐  Localize Game Text  ", "  🗄️  Database & Context  "])


# ============================================================
# TAB 1 — LOCALIZATION WORKSPACE
# ============================================================

with tab1:
    with st.expander("⚙️ Advanced Settings (AI Model & Batching)"):
        cfg_col1, cfg_col2 = st.columns(2)

        with cfg_col1:
            model_options = MODEL_OPTIONS
            model_choice = st.selectbox("AI Model", options=model_options, index=0)

        with cfg_col2:
            batch_mode = st.radio("Batching Strategy", options=["Auto", "Manual"], horizontal=True)
            if batch_mode == "Manual":
                manual_batch_size = st.slider("Rows per batch", 1, 50, 10, 1)
            else:
                manual_batch_size = 10

    render_section("upload", "Provide game text")

    input_mode = st.radio("Input Mode", options=["File Upload", "Manual Entry"], horizontal=True, label_visibility="collapsed")

    is_data_ready = False
    df_preview = None
    preview_dfs = {}
    uploaded_file_name = None
    file_bytes_buffer = None
    is_csv = False
    selected_sheets_trans = []

    if input_mode == "File Upload":
        if "game_text_uploader" not in st.session_state or not st.session_state.game_text_uploader:
            render_pro_tip(
                "<strong>💡 Pro Tip:</strong> You can now select sheets with different column layouts and configure them individually below!"
            )

        uploaded_file = st.file_uploader("Drop your file here", type=["xlsx", "csv"], key="game_text_uploader", label_visibility="collapsed")

        if uploaded_file is not None:
            if st.session_state.get("last_uploaded_file_id") != uploaded_file.file_id:
                st.session_state.last_uploaded_file_id = uploaded_file.file_id
                st.session_state.translation_complete = False
                st.session_state.pop("final_download_bytes", None)

            is_csv = uploaded_file.name.lower().endswith(".csv")

            if is_csv:
                selected_sheets_trans = ["CSV_Sheet"]
                df_preview = pd.read_csv(uploaded_file).fillna("").astype(str)
                preview_dfs["CSV_Sheet"] = df_preview
            else:
                try:
                    excel_obj = pd.ExcelFile(uploaded_file)
                    sheet_names = excel_obj.sheet_names

                    selected_sheets_trans = st.multiselect(
                        "Select sheets to translate",
                        options=sheet_names,
                        default=[sheet_names[0]],
                        key="trans_sheet_select"
                    )

                    if selected_sheets_trans:
                        for s in selected_sheets_trans:
                            preview_dfs[s] = pd.read_excel(excel_obj, sheet_name=s).fillna("").astype(str)
                        df_preview = preview_dfs[selected_sheets_trans[0]]
                except Exception as e:
                    st.error(f"Error reading Excel: {e}")

            st.session_state.selected_sheets_trans = selected_sheets_trans
            uploaded_file.seek(0)
            file_bytes_buffer = uploaded_file.getbuffer()
            uploaded_file_name = uploaded_file.name
            is_data_ready = bool(selected_sheets_trans)

    else:
        if "manual_trans_df" not in st.session_state:
            st.session_state.manual_trans_df = pd.DataFrame({"Source Text": [""], "Context": [""]})

        edited_df = st.data_editor(st.session_state.manual_trans_df, num_rows="dynamic", use_container_width=True)
        valid_rows = edited_df[edited_df["Source Text"].str.strip() != ""]

        if not valid_rows.empty:
            df_preview = edited_df.copy()
            csv_buffer = io.BytesIO()
            df_preview.to_csv(csv_buffer, index=False)
            file_bytes_buffer = csv_buffer.getvalue()
            uploaded_file_name = "manual_input.csv"
            is_csv = True
            is_data_ready = True
            selected_sheets_trans = ["Manual_Sheet"]
            preview_dfs["Manual_Sheet"] = df_preview
            st.session_state.selected_sheets_trans = selected_sheets_trans

    if is_data_ready and df_preview is not None:
        sheet_configurations = {}

        if len(df_preview.columns) == 0:
            st.error("The provided data has no columns.")
        else:
            if input_mode == "File Upload":
                mapping_desc = (
                    "Switch tabs below to configure unique column mappings for each individual sheet."
                    if not is_csv
                    else "Map the source, context, and target columns for your CSV file."
                )
                render_section(
                    "columns",
                    "Configure and Map Columns",
                    description=mapping_desc,
                    extra_style="margin-top:20px;",
                )

                mapping_tabs = st.tabs(selected_sheets_trans)
                for i, s_name in enumerate(selected_sheets_trans):
                    with mapping_tabs[i]:
                        df_s = preview_dfs[s_name]
                        st.dataframe(df_s, use_container_width=True, height=180)

                        col_sel1, col_sel2, col_sel3 = st.columns(3)
                        with col_sel1:
                            src_col = st.selectbox("Source text column", options=df_s.columns, index=0, key=f"src_{s_name}")
                        with col_sel2:
                            ctx_options = ["— No context column —"] + list(df_s.columns)
                            default_ctx_idx = 0
                            for idx, c in enumerate(df_s.columns):
                                if c.lower() in ["text_type", "context", "type", "description"]:
                                    default_ctx_idx = idx + 1
                                    break
                            ctx_col = st.selectbox("Context column", options=ctx_options, index=default_ctx_idx, key=f"ctx_{s_name}")
                        with col_sel3:
                            tgt_options = ["— Create new column —"] + list(df_s.columns)
                            tgt_col_sel = st.selectbox("Target column", options=tgt_options, index=0, key=f"tgt_{s_name}")

                        actual_ctx = None if ctx_col == "— No context column —" else ctx_col
                        if tgt_col_sel == "— Create new column —":
                            final_tgt = st.text_input("New target column name", value=target_language, key=f"new_tgt_{s_name}")
                        else:
                            final_tgt = tgt_col_sel

                        sheet_configurations[s_name] = {
                            "source": src_col,
                            "context": actual_ctx,
                            "target": final_tgt
                        }
            else:
                s_name = selected_sheets_trans[0]
                st.dataframe(df_preview, use_container_width=True, height=200)
                sheet_configurations[s_name] = {
                    "source": "Source Text",
                    "context": "Context" if "Context" in df_preview.columns else None,
                    "target": target_language
                }

            st.session_state.sheet_configurations = sheet_configurations
            use_smart_budget = (batch_mode == "Auto")

            render_section("cpu", "Custom AI Instructions (Optional)", extra_style="margin-top:20px;")
            custom_instructions_input = st.text_area("Custom AI Instructions", placeholder="Type rules here...", label_visibility="collapsed", height=100)

            st.divider()

            if "is_translating" not in st.session_state:
                st.session_state.is_translating = False

            start_clicked = st.button(
                "⏳ Translating..." if st.session_state.is_translating else "▶  Start Translation",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.is_translating
            )

            if start_clicked:
                st.session_state.is_translating = True
                st.rerun()

            if st.session_state.is_translating:
                st.session_state.translation_complete = False

                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_input_path = os.path.join(temp_dir, f"input_{uploaded_file_name}")
                    temp_output_path = os.path.join(temp_dir, f"output_{uploaded_file_name}")

                    with open(temp_input_path, "wb") as f:
                        f.write(file_bytes_buffer)

                    rag = RAGEngine()
                    try:
                        rag.load_resources(
                            glossary_dict=fetch_terms(db, game_id, target_language),
                            tm_dict=fetch_tm(db, game_id, target_language),
                            game_profile=fetch_game_profile(db, game_id),
                        )
                    except Exception as e:
                        st.error("Context fetch failed.")
                        st.session_state.is_translating = False
                        st.stop()

                    all_batches = []
                    final_sheet_results = {s: {} for s in selected_sheets_trans}
                    sheet_target_cols = {}

                    for sheet_name in selected_sheets_trans:
                        config = sheet_configurations[sheet_name]
                        sheet_target_cols[sheet_name] = config["target"]

                        read_sheet_arg = sheet_name if not is_csv else None
                        try:
                            rows = ExcelHandler.read_game_sheet(
                                temp_input_path,
                                text_column=config["source"],
                                context_column=config["context"],
                                sheet_name=read_sheet_arg
                            )
                            batches, alias_map = ExcelHandler.prepare_batches(rows, batch_size=manual_batch_size, use_smart_budget=use_smart_budget)

                            for b in batches:
                                all_batches.append({"sheet": sheet_name, "rows": b, "alias": alias_map, "original_rows": rows})
                        except Exception as e:
                            st.error(f"Could not read sheet '{sheet_name}' using source column '{config['source']}': {e}")

                    total_batches = len(all_batches)

                    progress_bar = st.progress(0.0)
                    ui_col1, ui_col2 = st.columns(2)
                    metric_progress = ui_col1.empty()
                    metric_time = ui_col2.empty()

                    start_time = time.time()
                    completed_batches = 0

                    def _translate_batch_dict(batch_dict, b_idx):
                        rag_context = rag.get_batch_context(batch_rows=batch_dict["rows"], target_language=target_language)
                        batch_req = BatchTranslationRequest(batch_id=b_idx, rows=batch_dict["rows"], target_language=target_language)

                        resp = translator_agent(
                            batch_request=batch_req,
                            rag_context=rag_context,
                            feedback="",
                            model_name=model_choice,
                            fallback_model_name="openai/gpt-4o-mini",
                            game_id=game_id,
                            custom_instructions=custom_instructions_input,
                        )
                        return batch_dict["sheet"], batch_dict["rows"], batch_dict["alias"], batch_dict["original_rows"], resp

                    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BATCHES) as executor:
                        future_to_b = {executor.submit(_translate_batch_dict, b, idx): b for idx, b in enumerate(all_batches)}

                        for future in as_completed(future_to_b):
                            try:
                                sheet, b_rows, alias_map, orig_rows, response = future.result()

                                current_sheet_dict = final_sheet_results[sheet]
                                for item in (response.translations or []):
                                    current_sheet_dict[item.row_id] = item.translated_text

                                for r in b_rows:
                                    if r.row_id not in current_sheet_dict:
                                        current_sheet_dict[r.row_id] = r.source_text

                                row_lookup = {r.row_id: r for r in orig_rows}
                                for dup_id, rep_id in alias_map.items():
                                    current_sheet_dict[dup_id] = current_sheet_dict.get(rep_id, row_lookup[dup_id].source_text)

                            except Exception as e:
                                st.toast(f"Batch error: {e}")

                            completed_batches += 1
                            elapsed = int(time.time() - start_time)
                            progress_bar.progress(completed_batches / max(1, total_batches))
                            metric_progress.metric("Batches done", f"{completed_batches} / {total_batches}")
                            metric_time.metric("Time", f"{elapsed//60:02d}:{elapsed%60:02d}")

                    ExcelHandler.write_translated_workbook(
                        original_file=temp_input_path,
                        sheet_translations=final_sheet_results,
                        sheet_target_columns=sheet_target_cols,
                        output_file=temp_output_path
                    )

                    with open(temp_output_path, "rb") as f:
                        st.session_state.final_download_bytes = f.read()

                    st.session_state.translation_complete = True
                    st.session_state.is_translating = False
                st.rerun()

            if st.session_state.get("translation_complete") and "final_download_bytes" in st.session_state:
                sheet_count = len(st.session_state.get("selected_sheets_trans", []))
                render_success_banner(
                    "Multi-sheet translation complete",
                    f"{sheet_count} sheet(s) successfully processed with unique layouts",
                )
                render_section("file", "Output preview (All workbook sheets)")

                file_bytes = st.session_state.final_download_bytes

                try:
                    if is_csv:
                        translated_df = pd.read_csv(io.BytesIO(file_bytes)).fillna("").astype(str)
                        st.dataframe(translated_df, use_container_width=True, height=280)
                    else:
                        out_excel = pd.ExcelFile(io.BytesIO(file_bytes))
                        out_sheet_names = out_excel.sheet_names

                        out_tabs = st.tabs(out_sheet_names)
                        for i, s_name in enumerate(out_sheet_names):
                            with out_tabs[i]:
                                out_df = pd.read_excel(out_excel, sheet_name=s_name).fillna("").astype(str)
                                st.dataframe(out_df, use_container_width=True, height=280)
                except Exception as e:
                    st.error(f"Could not load preview: {e}")

                base_name, ext = os.path.splitext(uploaded_file_name)
                new_file_name = f"{base_name}_translated{ext}"
                mime = "text/csv" if is_csv else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

                st.download_button(
                    label=f" 📥 Download translated file",
                    data=st.session_state.final_download_bytes,
                    file_name=new_file_name,
                    mime=mime,
                    type="primary",
                    use_container_width=True,
                )


# ============================================================
# TAB 2 — DATABASE & CONTEXT
# ============================================================

with tab2:
        render_db_panel_header(game_id)

        render_section(
            "settings",
            "Game profile",
            description="Define the writing style and localization rules the AI follows when translating text for this game.",
        )

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
                st.success(f"Game profile for `{game_id}` saved.")

        st.divider()

        render_section(
            "book",
            "Manual glossary entry",
            description=(
                "Add or edit glossary terms and optional notes directly. Conflicting entries are flagged "
                f"for review before saving to <strong style=\"color:var(--text-color); opacity:0.8;\">{html.escape(game_id)}</strong>."
            ),
        )

        if "manual_terms_df" not in st.session_state:
            st.session_state.manual_terms_df = pd.DataFrame(
                {"Chinese Source": [""], "Target Translation": [""], "Note (Optional)": [""]}
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
                "Note (Optional)": st.column_config.TextColumn(
                    "Note (Optional)", required=False
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
                note = str(row.get("Note (Optional)", "")).strip()

                if src and tgt and src.lower() != "nan" and tgt.lower() != "nan":
                    pairs.append({
                        "source": src,
                        "target": tgt,
                        "note": note if note.lower() != "nan" else ""
                    })
                    source_terms_list.append(src)

            if not pairs:
                st.error("Fill in at least one row with both source and target.")
            else:
                existing_records = db.check_conflicting_terms(
                    game_id, target_language, source_terms_list
                )
                existing_map = {
                    item["source_term"]: {"target": item["target_term"], "note": item.get("note", "")}
                    for item in existing_records
                }

                conflicts = []
                clean_pairs = []

                for p in pairs:
                    src = p["source"]
                    tgt = p["target"]
                    note = p["note"]
                    if src in existing_map:
                        conflicts.append({
                            "source": src,
                            "existing_target": existing_map[src]["target"],
                            "existing_note": existing_map[src]["note"],
                            "new_target": tgt,
                            "new_note": note,
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

        if st.session_state.pending_conflicts:
            render_conflict_badge(len(st.session_state.pending_conflicts))

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
                    exist_note = conflict["existing_note"]
                    new_tgt = conflict["new_target"]
                    new_note = conflict["new_note"]

                    st.markdown(f"**Source:** `{src}`")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        render_term_choice_box("existing", exist_tgt, exist_note)
                    with col_b:
                        render_term_choice_box("new", new_tgt, new_note)

                    decision = st.radio(
                        f"Decision for `{src}`",
                        options=["Keep existing", "Overwrite with new"],
                        index=0,
                        key=f"conflict_{idx}_{hash(src)}",
                        horizontal=True,
                    )
                    resolution_decisions[idx] = decision
                    st.divider()

                if st.form_submit_button("Confirm & save", type="primary"):
                    final_pairs_to_save = list(st.session_state.pending_pairs_to_save)

                    for idx, conflict in enumerate(st.session_state.pending_conflicts):
                        src = conflict["source"]

                        if bulk_decision == "Overwrite all with new" or \
                           (bulk_decision == "Review individually" and "Overwrite" in resolution_decisions[idx]):
                            final_pairs_to_save.append({
                                "source": src,
                                "target": conflict["new_target"],
                                "note": conflict["new_note"]
                            })

                    try:
                        if final_pairs_to_save:
                            count = db.upsert_terms(game_id, target_language, final_pairs_to_save)
                        else:
                            count = 0

                        fetch_terms.clear()
                        st.success(f"Conflicts resolved. Saved {count:,} term(s).")
                        st.session_state.pending_conflicts = None
                        st.session_state.pending_pairs_to_save = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save: {e}")

        st.divider()

        render_section(
            "layers",
            "Knowledge base upload",
            description=(
                "Upload reference translations for "
                f"<strong style=\"color:var(--text-color); opacity:0.8;\">{html.escape(game_id)}</strong> → "
                f"<strong style=\"color:var(--text-color); opacity:0.8;\">{html.escape(target_language)}</strong>. "
                "Choose the target type before uploading."
            ),
        )

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

        rag_file = st.file_uploader("Upload reference file", type=["xlsx", "csv"], key="rag_file_uploader")

        df_rag = None

        if rag_file is not None:
            if rag_file.name.lower().endswith(".csv"):
                df_rag = pd.read_csv(rag_file).fillna("").astype(str)
            else:
                try:
                    excel_obj = pd.ExcelFile(rag_file)
                    sheet_names = excel_obj.sheet_names
                    selected_sheet = st.selectbox("Select sheet", options=sheet_names, key="rag_sheet_select")
                    df_rag = pd.read_excel(excel_obj, sheet_name=selected_sheet).fillna("").astype(str)
                except Exception as e:
                    st.error(f"Error reading Excel: {e}")

            if df_rag is not None:
                render_section("file", "Reference data preview", extra_style="margin-top:14px;")
                render_preview_bar(rag_file.name, len(df_rag))

                st.dataframe(df_rag, use_container_width=True, height=240)

                if len(df_rag.columns) < 2:
                    st.warning("File has fewer than 2 columns. Ensure it has both source and target columns.")
                    st.stop()

                col_source, col_target, col_note = st.columns(3)

                with col_source:
                    selected_source_column = st.selectbox(
                        "Source column",
                        options=df_rag.columns,
                        index=0
                    )
                with col_target:
                    selected_target_column = st.selectbox(
                        f"{target_language} target column",
                        options=df_rag.columns,
                        index=min(1, len(df_rag.columns) - 1)
                    )
                with col_note:
                    note_options = ["-- None --"] + list(df_rag.columns)
                    selected_note_column = st.selectbox(
                        "Note column (Optional)",
                        options=note_options,
                        index=0
                    )

                if st.button("Upload to database", type="primary"):
                    status_rag = st.status(f"Uploading to {target_type}…", expanded=True)

                    try:
                        pairs = []
                        for _, row in df_rag.iterrows():
                            src_val = row.get(selected_source_column)
                            tgt_val = row.get(selected_target_column)

                            note_str = ""
                            if selected_note_column != "-- None --":
                                note_val = row.get(selected_note_column)
                                if pd.notna(note_val):
                                    temp_note = str(note_val).strip()
                                    if temp_note.lower() != "nan":
                                        note_str = temp_note

                            if pd.notna(src_val) and pd.notna(tgt_val):
                                src_str = str(src_val).strip()
                                tgt_str = str(tgt_val).strip()
                                if src_str and tgt_str and src_str.lower() != "nan" and tgt_str.lower() != "nan":
                                    pairs.append({
                                        "source": src_str,
                                        "target": tgt_str,
                                        "note": note_str
                                    })

                        if not pairs:
                            status_rag.update(label="No valid rows found", state="error")
                            st.error("No valid text pairs found to upload.")
                        else:
                            if target_type == "terms":
                                count = db.upsert_terms(game_id, target_language, pairs)
                                fetch_terms.clear()
                                status_rag.update(label="Upload complete", state="complete", expanded=False)
                                st.success(f"Added {count:,} glossary terms to the database.")
                            else:
                                count = db.upsert_tm(game_id, target_language, pairs)
                                fetch_tm.clear()
                                status_rag.update(label="Upload complete", state="complete", expanded=False)
                                st.success(f"Added {count:,} translation memory records.")

                    except Exception as e:
                        status_rag.update(label="Upload failed", state="error")
                        st.error(f"Error uploading data: {e}")


# ============================================================
# FOOTER
# ============================================================

render_footer()

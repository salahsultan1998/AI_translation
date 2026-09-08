"""
LocaTool REST API
=================
Standalone FastAPI service that reuses the existing translation stack
(agents, RAG, Excel handler, Supabase) without touching app.py.

Run (from the same folder as app.py):

    pip install fastapi uvicorn python-multipart
    uvicorn API:app --host 0.0.0.0 --port 8000 --reload

Docs:  http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import io
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from agents import reviewer_agent, translator_agent, validate_translation_quality
from config import (
    DEFAULT_MODEL,
    FALLBACK_MODEL,
    MAX_CONCURRENT_BATCHES,
    MODEL_OPTIONS,
    PROJECT_OPTIONS,
    SUPPORTED_LANGUAGES,
)
from custom_types import BatchTranslationRequest, RowItem
from db_engine import SupabaseDBEngine
from excel_engine import ExcelHandler
from rag_engine import RAGEngine


# ============================================================
# APP + AUTH
# ============================================================

API_TITLE = "LocaTool Translation API"
API_VERSION = "1.0.0"
API_KEY_ENV = "LOCATOOL_API_KEY"

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=(
        "Programmatic access to the LocaTool translation pipeline. "
        "The Streamlit workspace in app.py is unchanged — this service "
        "is an independent entry point for quick checks and embedding."
    ),
)

_cors_origins = os.getenv("LOCATOOL_CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_bearer = HTTPBearer(auto_error=False)
db = SupabaseDBEngine()


def _configured_api_key() -> str:
    return (os.getenv(API_KEY_ENV) or "").strip()


def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    Accept either:
      - X-API-Key: <LOCATOOL_API_KEY>   (best for embedding in other apps)
      - Authorization: Bearer <Supabase access token>
    """
    configured_key = _configured_api_key()
    incoming_key = (x_api_key or "").strip()

    if configured_key and incoming_key and incoming_key == configured_key:
        return {"auth": "api_key"}

    token = credentials.credentials if credentials else ""
    if token:
        # Allow the same env API key to be sent as a Bearer token.
        if configured_key and token == configured_key:
            return {"auth": "api_key"}
        user = db.get_user_from_token(token)
        if user:
            return {"auth": "supabase", "user": user}

    detail = "Provide a valid Supabase Bearer token"
    if configured_key:
        detail += " or X-API-Key header"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: Optional[str] = None


class TranslateItemIn(BaseModel):
    id: Optional[str] = Field(
        default=None,
        description="Caller-defined id echoed back. If omitted, the list index is used.",
    )
    source_text: str
    context: Optional[str] = None


class TranslateRequest(BaseModel):
    texts: List[TranslateItemIn] = Field(..., min_length=1)
    target_language: str = Field(..., examples=["Arabic"])
    game_id: str = Field(..., examples=["S06"])
    model: Optional[str] = None
    fallback_model: Optional[str] = None
    custom_instructions: str = ""
    use_rag: bool = True
    batch_size: int = Field(default=10, ge=1, le=50)
    use_smart_budget: bool = True
    validate: bool = True


class QuickTranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_language: str
    game_id: str
    context: Optional[str] = None
    model: Optional[str] = None
    fallback_model: Optional[str] = None
    custom_instructions: str = ""
    use_rag: bool = True
    validate: bool = True


class TranslateItemOut(BaseModel):
    id: str
    source_text: str
    translated_text: str
    context: Optional[str] = None
    issues: List[str] = Field(default_factory=list)


class TranslateResponse(BaseModel):
    game_id: str
    target_language: str
    model: str
    count: int
    elapsed_ms: int
    translations: List[TranslateItemOut]
    is_valid: bool = True
    issues: List[str] = Field(default_factory=list)


class OptionsResponse(BaseModel):
    projects: List[str]
    languages: List[str]
    models: List[str]
    default_model: str
    fallback_model: str


# ============================================================
# TRANSLATION CORE (shared by JSON + file endpoints)
# ============================================================

def _resolve_model(model_name: Optional[str]) -> str:
    return model_name or DEFAULT_MODEL


def _load_rag(game_id: str, target_language: str, enabled: bool) -> RAGEngine:
    rag = RAGEngine()
    if not enabled:
        return rag
    rag.load_resources(
        glossary_dict=db.get_terms_for_game(game_id, target_language),
        tm_dict=db.get_tm_for_game(game_id, target_language),
        game_profile=db.get_game_profile(game_id),
    )
    return rag


def _run_batches(
    rows: List[RowItem],
    *,
    target_language: str,
    game_id: str,
    model_name: str,
    fallback_model_name: Optional[str],
    custom_instructions: str,
    rag: RAGEngine,
    batch_size: int,
    use_smart_budget: bool,
) -> Dict[int, str]:
    batches, alias_map = ExcelHandler.prepare_batches(
        rows,
        batch_size=batch_size,
        use_smart_budget=use_smart_budget,
    )
    results: Dict[int, str] = {}

    def _one(batch_rows: List[RowItem], batch_id: int):
        rag_context = rag.get_batch_context(
            batch_rows=batch_rows,
            target_language=target_language,
        )
        request = BatchTranslationRequest(
            batch_id=batch_id,
            rows=batch_rows,
            target_language=target_language,
        )
        response = translator_agent(
            batch_request=request,
            rag_context=rag_context,
            feedback="",
            model_name=model_name,
            fallback_model_name=fallback_model_name or FALLBACK_MODEL,
            game_id=game_id,
            custom_instructions=custom_instructions or "",
        )
        return batch_rows, response

    workers = max(1, min(MAX_CONCURRENT_BATCHES, len(batches) or 1))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_one, batch, idx): idx
            for idx, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            try:
                batch_rows, response = future.result()
            except Exception as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"Translation batch failed: {exc}",
                ) from exc

            for item in response.translations or []:
                results[item.row_id] = item.translated_text

            for row in batch_rows:
                results.setdefault(row.row_id, row.source_text)

    row_lookup = {row.row_id: row for row in rows}
    for dup_id, rep_id in alias_map.items():
        results[dup_id] = results.get(
            rep_id,
            row_lookup[dup_id].source_text if dup_id in row_lookup else "",
        )

    return results


def translate_rows(
    rows: List[RowItem],
    *,
    target_language: str,
    game_id: str,
    model_name: Optional[str] = None,
    fallback_model_name: Optional[str] = None,
    custom_instructions: str = "",
    use_rag: bool = True,
    batch_size: int = 10,
    use_smart_budget: bool = True,
    validate: bool = True,
) -> tuple[Dict[int, str], List[str], bool]:
    if target_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language '{target_language}'. Allowed: {SUPPORTED_LANGUAGES}",
        )
    if not rows:
        return {}, [], True

    resolved_model = _resolve_model(model_name)
    rag = _load_rag(game_id, target_language, use_rag)
    translations = _run_batches(
        rows,
        target_language=target_language,
        game_id=game_id,
        model_name=resolved_model,
        fallback_model_name=fallback_model_name,
        custom_instructions=custom_instructions,
        rag=rag,
        batch_size=batch_size,
        use_smart_budget=use_smart_budget,
    )

    issues: List[str] = []
    is_valid = True
    if validate:
        from custom_types import SingleRowResult

        review_payload = [
            SingleRowResult(
                row_id=row.row_id,
                translated_text=translations.get(row.row_id, ""),
            )
            for row in rows
        ]
        is_valid, feedback = validate_translation_quality(rows, review_payload)
        if feedback:
            issues = [line for line in feedback.split("\n") if line.strip()]
        # reviewer_agent is the same zero-cost check; keep the import live
        _ = reviewer_agent
    return translations, issues, is_valid


# ============================================================
# PUBLIC ROUTES
# ============================================================

@app.get("/", tags=["meta"])
def root():
    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "locatool-api", "version": API_VERSION}


@app.post("/auth/login", response_model=LoginResponse, tags=["auth"])
def login(payload: LoginRequest):
    user, token, error = db.sign_in(payload.email.strip(), payload.password)
    if error or not user or not token:
        raise HTTPException(
            status_code=401,
            detail=f"Sign-in failed: {error or 'Invalid credentials.'}",
        )
    return LoginResponse(
        access_token=token,
        email=getattr(user, "email", None),
    )


@app.get("/v1/options", response_model=OptionsResponse, tags=["meta"])
def options(_: Any = Depends(require_auth)):
    return OptionsResponse(
        projects=PROJECT_OPTIONS,
        languages=SUPPORTED_LANGUAGES,
        models=MODEL_OPTIONS,
        default_model=DEFAULT_MODEL,
        fallback_model=FALLBACK_MODEL,
    )


@app.get("/v1/profile/{game_id}", tags=["context"])
def get_profile(game_id: str, _: Any = Depends(require_auth)):
    return {"game_id": game_id, "tone_style": db.get_game_profile(game_id)}


@app.get("/v1/terms", tags=["context"])
def get_terms(
    game_id: str = Query(...),
    target_language: str = Query(...),
    _: Any = Depends(require_auth),
):
    terms = db.get_terms_for_game(game_id, target_language)
    return {
        "game_id": game_id,
        "target_language": target_language,
        "count": len(terms),
        "terms": terms,
    }


@app.post("/v1/translate", response_model=TranslateResponse, tags=["translate"])
def translate_json(payload: TranslateRequest, _: Any = Depends(require_auth)):
    started = time.time()
    rows: List[RowItem] = []
    id_map: Dict[int, str] = {}

    for index, item in enumerate(payload.texts):
        source = (item.source_text or "").strip()
        if not source:
            continue
        rows.append(
            RowItem(row_id=index, source_text=source, context=item.context)
        )
        id_map[index] = item.id if item.id is not None else str(index)

    if not rows:
        raise HTTPException(status_code=400, detail="No non-empty source_text values provided.")

    translations, issues, is_valid = translate_rows(
        rows,
        target_language=payload.target_language,
        game_id=payload.game_id,
        model_name=payload.model,
        fallback_model_name=payload.fallback_model,
        custom_instructions=payload.custom_instructions,
        use_rag=payload.use_rag,
        batch_size=payload.batch_size,
        use_smart_budget=payload.use_smart_budget,
        validate=payload.validate,
    )

    issues_by_row: Dict[int, List[str]] = {}
    for issue in issues:
        # "Row {id}: ..."
        if issue.startswith("Row "):
            try:
                row_part = issue.split(":", 1)[0]
                row_id = int(row_part.replace("Row", "").strip())
                issues_by_row.setdefault(row_id, []).append(issue)
            except ValueError:
                pass

    items = [
        TranslateItemOut(
            id=id_map[row.row_id],
            source_text=row.source_text,
            translated_text=translations.get(row.row_id, row.source_text),
            context=row.context,
            issues=issues_by_row.get(row.row_id, []),
        )
        for row in rows
    ]

    return TranslateResponse(
        game_id=payload.game_id,
        target_language=payload.target_language,
        model=_resolve_model(payload.model),
        count=len(items),
        elapsed_ms=int((time.time() - started) * 1000),
        translations=items,
        is_valid=is_valid,
        issues=issues,
    )


@app.post("/v1/translate/quick", response_model=TranslateResponse, tags=["translate"])
def translate_quick(payload: QuickTranslateRequest, _: Any = Depends(require_auth)):
    wrapped = TranslateRequest(
        texts=[
            TranslateItemIn(
                id="0",
                source_text=payload.text,
                context=payload.context,
            )
        ],
        target_language=payload.target_language,
        game_id=payload.game_id,
        model=payload.model,
        fallback_model=payload.fallback_model,
        custom_instructions=payload.custom_instructions,
        use_rag=payload.use_rag,
        validate=payload.validate,
    )
    return translate_json(wrapped)


@app.post("/v1/translate/file", tags=["translate"])
async def translate_file(
    file: UploadFile = File(...),
    game_id: str = Form(...),
    target_language: str = Form(...),
    source_column: str = Form(...),
    context_column: Optional[str] = Form(default=None),
    target_column: Optional[str] = Form(default=None),
    sheet_name: Optional[str] = Form(default=None),
    model: Optional[str] = Form(default=None),
    fallback_model: Optional[str] = Form(default=None),
    custom_instructions: str = Form(default=""),
    use_rag: bool = Form(default=True),
    batch_size: int = Form(default=10),
    use_smart_budget: bool = Form(default=True),
    _: Any = Depends(require_auth),
):
    """
    Upload an .xlsx or .csv file and get a translated file back.
    For Excel workbooks, pass sheet_name to translate one sheet, or omit it
    to translate every sheet with the same column mapping.
    """
    filename = file.filename or "upload.xlsx"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".xlsx", ".xls", ".csv"}:
        raise HTTPException(status_code=400, detail="Only .xlsx, .xls, and .csv files are supported.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    ctx_col = context_column.strip() if context_column else None
    if ctx_col in {"", "— No context column —", "-- None --", "None"}:
        ctx_col = None
    tgt_col = (target_column or target_language).strip() or target_language

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, f"input_{filename}")
        output_path = os.path.join(temp_dir, f"output_{filename}")
        with open(input_path, "wb") as fh:
            fh.write(raw)

        is_csv = ext == ".csv"
        sheet_names: List[str]
        if is_csv:
            sheet_names = ["CSV_Sheet"]
        else:
            import pandas as pd

            sheet_names = pd.ExcelFile(input_path).sheet_names
            if sheet_name:
                if sheet_name not in sheet_names:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Sheet '{sheet_name}' not found. Available: {sheet_names}",
                    )
                sheet_names = [sheet_name]

        sheet_translations: Dict[str, Dict[int, str]] = {}
        sheet_target_cols: Dict[str, str] = {}

        for name in sheet_names:
            read_sheet = None if is_csv else name
            try:
                rows = ExcelHandler.read_game_sheet(
                    input_path,
                    text_column=source_column,
                    context_column=ctx_col,
                    sheet_name=read_sheet,
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not read sheet '{name}' using source column '{source_column}': {exc}",
                ) from exc

            translations, _, _ = translate_rows(
                rows,
                target_language=target_language,
                game_id=game_id,
                model_name=model,
                fallback_model_name=fallback_model,
                custom_instructions=custom_instructions,
                use_rag=use_rag,
                batch_size=batch_size,
                use_smart_budget=use_smart_budget,
                validate=False,
            )
            sheet_translations[name] = translations
            sheet_target_cols[name] = tgt_col

        ExcelHandler.write_translated_workbook(
            original_file=input_path,
            sheet_translations=sheet_translations,
            sheet_target_columns=sheet_target_cols,
            output_file=output_path,
        )

        with open(output_path, "rb") as fh:
            payload = fh.read()

    base, file_ext = os.path.splitext(filename)
    out_name = f"{base}_translated{file_ext}"
    media = (
        "text/csv"
        if is_csv
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return StreamingResponse(
        io.BytesIO(payload),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
    )


@app.exception_handler(ValueError)
async def value_error_handler(_, exc: ValueError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})

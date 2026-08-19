import os
import json
import re
import time
from typing import List, Tuple
from openai import OpenAI, APIError, RateLimitError
from dotenv import load_dotenv
from custom_types import (
    BatchTranslationRequest,
    BatchTranslationResponse,
    SingleRowResult,
    ReviewResult
)

load_dotenv()

DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
FALLBACK_MODEL = os.getenv("OPENROUTER_FALLBACK_MODEL", "openai/gpt-4o-mini")
UNSUPPORTED_MODEL_TOKENS = ("qwen/qwen-2.5-72b-instruct",)

client = OpenAI(
    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Regex to catch standard game variables and rich text tags (e.g., {0}, %s, <color=red>, </color>)
VARIABLE_TAG_REGEX = re.compile(r"(\{[^{}]+\}|\%[sdif]|<[^>]+>)")

def _debug_log(stage: str, message: str) -> None:
    print(f"[DEBUG][{stage}] {message}")

def _normalize_model_name(model_name: str | None) -> str:
    if not model_name:
        return DEFAULT_MODEL
    if model_name in UNSUPPORTED_MODEL_TOKENS:
        return FALLBACK_MODEL
    return model_name

def extract_json_string(raw_string: str) -> str:
    if not raw_string:
        return ""
    cleaned = raw_string.strip()
    json_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if json_block:
        return json_block.group(1).strip()
    start_brace = cleaned.find("{")
    end_brace = cleaned.rfind("}")
    if start_brace != -1 and end_brace != -1:
        return cleaned[start_brace:end_brace + 1]
    return cleaned

def build_dynamic_system_prompt(target_lang: str, game_id: str = "") -> str:
    """Loads and merges prompt layers from prompts.json safely using .replace() to protect literal braces."""
    prompt_path = "prompts.json"
    config = {}
    if os.path.exists(prompt_path):
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            _debug_log("prompts", f"Failed to load prompts.json: {e}")

    # Layer 1: Global Base Rules
    base_template = config.get(
        "global_base", 
        "You are an expert game localizer and translator. Your job is to translate Chinese game text into {target_lang}."
    )
    
    # SAFE STRING REPLACEMENT (Protects {0}, {PlayerName}, etc., from throwing index errors)
    system_prompt = base_template.replace("{target_lang}", target_lang)

    # Layer 2: Language-Specific Rules
    lang_rules = config.get("languages", {}).get(target_lang, {}).get("grammar_rules", "")
    if lang_rules:
        system_prompt += f"\n\n### LANGUAGE GUIDELINES:\n{lang_rules}"

    # Layer 3: Game / Genre Overrides
    if game_id:
        game_key = game_id.lower().strip()
        game_config = config.get("games", {}).get(game_key, {})
        if game_config:
            genre = game_config.get("genre", "Video Game")
            tone = game_config.get("tone_override", "")
            system_prompt += f"\n\n### GAME CONTEXT & GENRE: {genre}\n{tone}"

    return system_prompt

def _create_chat_completion(
    model_name: str | None,
    messages: list[dict],
    temperature: float,
    fallback_model_name: str | None = None,
    max_retries: int = 2
):
    fallback_model = fallback_model_name or FALLBACK_MODEL
    resolved_model = _normalize_model_name(model_name)
    
    kwargs = {
        "model": resolved_model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"}
    }

    for attempt in range(max_retries + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except (RateLimitError, APIError) as e:
            _debug_log("chat", f"API transient error (Attempt {attempt + 1}): {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            
            if resolved_model != fallback_model:
                _debug_log("chat", f"Retrying with fallback: {fallback_model}")
                kwargs["model"] = fallback_model
                return client.chat.completions.create(**kwargs)
            raise e
        except Exception as e:
            raise RuntimeError(f"OpenRouter call failed: {e}") from e

# ==========================================
# 1. SINGLE-PASS TRANSLATOR AGENT
# ==========================================
def translator_agent(
    batch_request: BatchTranslationRequest,
    rag_context: str,
    feedback: str = "",
    model_name: str = DEFAULT_MODEL,
    fallback_model_name: str | None = None,
    game_id: str = "",
    custom_instructions: str = "", # <--- NEW PARAMETER
) -> BatchTranslationResponse:
    target_lang = batch_request.target_language

    dynamic_base_prompt = build_dynamic_system_prompt(target_lang=target_lang, game_id=game_id)

    system_prompt = f"""{dynamic_base_prompt}

CRITICAL FORMAT REQUIREMENT:
Respond ONLY with a valid JSON object matching this exact structure:
{{
  "batch_id": {batch_request.batch_id},
  "translations": [
    {{
      "row_id": <int>,
      "translated_text": "<string>"
    }}
  ]
}}
"""
    input_payload = []
    for row in batch_request.rows:
        item = {"row_id": row.row_id, "source_text": row.source_text}
        if row.context:
            item["context"] = str(row.context)
        input_payload.append(item)

    user_message = f"### TARGET LANGUAGE: {target_lang}\n\n"
    if rag_context:
        user_message += f"### REFERENCE CONTEXT:\n{rag_context}\n\n"
    
    # <--- NEW INJECTION: Add custom instructions if provided
    if custom_instructions.strip():
        user_message += f"### CUSTOM INSTRUCTIONS (PRIORITY OVERRIDES):\n{custom_instructions.strip()}\n\n"
        
    if feedback:
        user_message += f"### PREVIOUS ATTEMPT FIXES REQUIRED:\n{feedback}\n\n"

    user_message += f"### SOURCE TEXT:\n{json.dumps(input_payload, ensure_ascii=False, indent=2)}"

    _debug_log("translator", f"Executing translation for batch_id={batch_request.batch_id} (game_id={game_id})")
    
    response = _create_chat_completion(
        model_name=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.2,
        fallback_model_name=fallback_model_name,
    )
    print("prompt:", user_message)
    content = response.choices[0].message.content or ""
    clean_json = extract_json_string(content)

    try:
        parsed_data = json.loads(clean_json)
        parsed_data["batch_id"] = batch_request.batch_id
        return BatchTranslationResponse(**parsed_data)
    except Exception as e:
        raise ValueError(f"Invalid JSON returned from model: {e}\nRaw: {content[:200]}")
# ==========================================
# 2. ZERO-COST PYTHON REVIEWER AGENT
# ==========================================
def validate_translation_quality(original_rows: list, translations: List[SingleRowResult]) -> Tuple[bool, str]:
    trans_map = {t.row_id: t.translated_text for t in translations}
    issues = []

    for row in original_rows:
        row_id = row.row_id
        source = row.source_text
        translated = trans_map.get(row_id)

        if translated is None:
            issues.append(f"Row {row_id}: Missing translation entry.")
            continue
        if not translated.strip() and source.strip():
            issues.append(f"Row {row_id}: Translation is empty.")
            continue

        source_tags = sorted(VARIABLE_TAG_REGEX.findall(source))
        target_tags = sorted(VARIABLE_TAG_REGEX.findall(translated))

        if source_tags != target_tags:
            issues.append(
                f"Row {row_id}: Variable mismatch. Source had {source_tags} but target returned {target_tags}"
            )

    is_valid = len(issues) == 0
    feedback_prompt = "\n".join(issues) if not is_valid else ""
    return is_valid, feedback_prompt

def reviewer_agent(
    original_rows: list,
    translated_batch: BatchTranslationResponse,
    model_name: str = DEFAULT_MODEL,
    fallback_model_name: str | None = None,
) -> ReviewResult:
    is_valid, feedback = validate_translation_quality(original_rows, translated_batch.translations or [])
    return ReviewResult(is_valid=is_valid, feedback_prompt=feedback)
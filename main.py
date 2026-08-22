import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict
from excel_engine import ExcelHandler
from db_engine import SupabaseDBEngine
from rag_engine import RAGEngine
from agents import DEFAULT_MODEL, translator_agent, reviewer_agent
from custom_types import BatchTranslationRequest

# Number of translation batches to run in parallel against the LLM API.
MAX_CONCURRENT_BATCHES = 4


def _process_one_batch(
    batch_idx: int,
    batch_rows,
    rag: RAGEngine,
    target_language: str,
    model_name: str,
    fallback_model_name: str,
    game_id: str,
) -> Dict[int, str]:
    """Translates one batch, retrying with reviewer feedback. Runs in a worker thread."""
    rag_context = rag.get_batch_context(
        batch_rows=batch_rows,
        target_language=target_language
    )

    batch_request = BatchTranslationRequest(
        batch_id=batch_idx,
        rows=batch_rows,
        target_language=target_language
    )

    result: Dict[int, str] = {}
    feedback = ""
    max_retries = 2
    batch_processed = False

    for attempt in range(max_retries + 1):
        try:
            response = translator_agent(
                batch_request=batch_request,
                rag_context=rag_context,
                feedback=feedback,
                model_name=model_name,
                fallback_model_name=fallback_model_name,
                game_id=game_id,
            )

            review = reviewer_agent(
                original_rows=batch_rows,
                translated_batch=response
            )

            if review.is_valid:
                for item in (response.translations or []):
                    result[item.row_id] = item.translated_text
                batch_processed = True
                break
            else:
                feedback = review.feedback_prompt
                print(f"   ⚠️ Quality check failed on attempt {attempt + 1}: {feedback}")
                if attempt == max_retries:
                    for item in (response.translations or []):
                        result[item.row_id] = item.translated_text
                    batch_processed = True

        except Exception as e:
            print(f"   ❌ Error processing Batch {batch_idx} (Attempt {attempt + 1}): {e}")
            if attempt == max_retries and not batch_processed:
                for r in batch_rows:
                    result[r.row_id] = r.source_text

    for r in batch_rows:
        if r.row_id not in result:
            result[r.row_id] = r.source_text

    return result


def run_translation_pipeline(
        input_file: str,
        game_id: str,
        target_language: str = "Arabic",
        output_file: str = "data/translated_output.xlsx",
        batch_size: int = 10,
        model_name: str = DEFAULT_MODEL,
        fallback_model_name: str = DEFAULT_MODEL,
        text_column: str = "text",
        context_column: str = "text_type"
):
    os.makedirs("data", exist_ok=True)

    print(f"📄 Reading Excel for game [{game_id}] | Target Language: [{target_language}]...")
    rows = ExcelHandler.read_game_sheet(
        file_path=input_file,
        text_column=text_column,
        context_column=context_column
    )
    
    if not rows:
        print("⚠️ No valid rows found in file. Exiting pipeline.")
        return

    # Dedupe identical rows and group near-duplicates (same text, different
    # embedded number) so they translate once / together instead of scattering
    # across separate batches.
    batches, alias_map = ExcelHandler.prepare_batches(rows, batch_size=batch_size)
    print(f"📦 Created {len(batches)} batch(es) with batch size = {batch_size}\n")

    # 1. Initialize Engines
    
    db = SupabaseDBEngine()
    rag = RAGEngine()
    
    # 2. Pre-load Context Data from SQLite directly into Memory (0 API Costs)
    print("🔄 Loading local database into memory...")
    glossary_dict = db.get_terms_for_game(game_id, target_language)
    tm_dict = db.get_tm_for_game(game_id, target_language)
    game_profile = db.get_game_profile(game_id)
    
    rag.load_resources(
        glossary_dict=glossary_dict,
        tm_dict=tm_dict,
        game_profile=game_profile
    )

    translations_dict: Dict[int, str] = {}

    print(f"🚀 Translating {len(batches)} batch(es), up to {MAX_CONCURRENT_BATCHES} in parallel...")

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BATCHES) as executor:
        future_to_batch_idx = {
            executor.submit(
                _process_one_batch,
                batch_idx,
                batch_rows,
                rag,
                target_language,
                model_name,
                fallback_model_name,
                game_id,
            ): batch_idx
            for batch_idx, batch_rows in enumerate(batches, start=1)
        }

        completed = 0
        for future in as_completed(future_to_batch_idx):
            batch_idx = future_to_batch_idx[future]
            translations_dict.update(future.result())
            completed += 1
            print(f"✅ Batch {batch_idx} done ({completed}/{len(batches)})")

    # Fill in rows that were skipped as exact/near duplicates by reusing
    # their representative row's translation.
    row_lookup = {r.row_id: r for r in rows}
    for dup_row_id, rep_row_id in alias_map.items():
        translations_dict[dup_row_id] = translations_dict.get(
            rep_row_id, row_lookup[dup_row_id].source_text
        )

    target_col_name = f"{target_language.strip().replace(' ', '_')}"
    
    print("\n--------------------------------------------------")
    print(f"💾 Saving translated workbook to: {output_file}...")
    
    ExcelHandler.write_translated_sheet(
        original_file=input_file,
        translations=translations_dict,
        target_column=target_col_name,
        output_file=output_file
    )
    print(f"✨ Translation into {target_language} complete!")
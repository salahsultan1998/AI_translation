import os
import pandas as pd
from rag_engine import RAGEngine

# ===================================================
# CONFIGURATION - CHANGE THESE FOR YOUR DM_03 UPLOAD
# ===================================================
FILE_PATH = "data/dm03_tm.xlsx"  # Path to your 8,000-row file
GAME_ID = "DM_03"  # Active game
TARGET_LANGUAGE = "Arabic"  # Target language
NAMESPACE_TYPE = "translation_memory"  # 'terms' or 'translation_memory'
CHINESE_COL = "Chinese"  # Name of source column in Excel
TARGET_COL = "Arabic"  # Name of target column in Excel
BATCH_SIZE = 100  # API batch size


def run_seed():
    if not os.path.exists(FILE_PATH):
        print(f"❌ File not found at: {FILE_PATH}")
        return

    print(f"📄 Reading '{FILE_PATH}'...")
    try:
        if FILE_PATH.endswith(".csv"):
            df = pd.read_csv(FILE_PATH)
        else:
            df = pd.read_excel(FILE_PATH)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    print(f"📊 Loaded {len(df)} total rows.")

    # 1. Validate column existence
    missing_cols = []
    if CHINESE_COL not in df.columns:
        missing_cols.append(CHINESE_COL)
    if TARGET_COL not in df.columns:
        missing_cols.append(TARGET_COL)

    if missing_cols:
        print(f"❌ Column error: Could not find column(s) {missing_cols} in file.")
        print(f"📋 Available columns in file: {list(df.columns)}")
        return

    # 2. Extract valid pairs and filter out NaN / empty strings
    pairs = []
    for _, row in df.iterrows():
        src_val = row[CHINESE_COL]
        tgt_val = row[TARGET_COL]

        if pd.notna(src_val) and pd.notna(tgt_val):
            src = str(src_val).strip()
            tgt = str(tgt_val).strip()
            if src and tgt and src.lower() != "nan" and tgt.lower() != "nan":
                pairs.append({"source": src, "target": tgt})

    total_records = len(pairs)
    print(f"🔍 Valid records to process: {total_records}")

    if total_records == 0:
        print("⚠️ No valid non-empty translation pairs found. Exiting.")
        return

    # 3. Safe progress callback
    def progress(current, total):
        pct = (current / total) * 100 if total > 0 else 0
        print(f"   ⏳ Processed {current}/{total} records ({pct:.1f}%)...")

    rag = RAGEngine()
    lang_key = TARGET_LANGUAGE.lower().strip().replace(" ", "_")
    full_ns = f"{GAME_ID.lower().strip()}_{lang_key}_{NAMESPACE_TYPE}"
    print(f"🚀 Starting seeding for namespace [{full_ns}]...")

    try:
        uploaded = rag.upload_pairs(
            pairs=pairs,
            game_id=GAME_ID,
            target_language=TARGET_LANGUAGE,
            base_namespace=NAMESPACE_TYPE,
            batch_size=BATCH_SIZE,
            progress_callback=progress
        )
        print(f"\n✨ DONE! Successfully seeded {uploaded} vectors into Pinecone!")
    except Exception as e:
        print(f"\n❌ Error during vector seeding: {e}")


if __name__ == "__main__":
    run_seed()
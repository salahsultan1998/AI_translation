import os
import pandas as pd
from typing import List, Dict
from custom_types import RowItem


class ExcelHandler:
    @staticmethod
    def _read_file(file_path: str) -> pd.DataFrame:
        """Helper to safely read both CSV and Excel files."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            return pd.read_csv(file_path)
        return pd.read_excel(file_path)

    @staticmethod
    def read_game_sheet(
        file_path: str,
        text_column: str = "text",
        context_column: str = "text_type"
    ) -> List[RowItem]:
        """Reads game text files (.xlsx or .csv) using specified column mappings and normalizes full-width characters."""
        df = ExcelHandler._read_file(file_path)
        records: List[RowItem] = []

        for index, row in df.iterrows():
            # Safely extract source text
            raw_text = row.get(text_column) if text_column in df.columns else None
            source_str = str(raw_text).strip() if pd.notna(raw_text) else ""

            # Normalize Chinese full-width characters to standard Western characters for clean layout handling
            source_str = (
                source_str
                .replace("【", "[").replace("】", "]")
                .replace("（", "(").replace("）", ")")
                .replace("《", "\"").replace("》", "\"")
                .replace(" ", " ")                      # Replace full-width space with normal space
            )

            # Safely extract context notes/speaker tags
            ctx = None
            if context_column in df.columns and pd.notna(row.get(context_column)):
                ctx = str(row[context_column]).strip()

            records.append(
                RowItem(
                    row_id=int(index),
                    source_text=source_str,
                    context=ctx
                )
            )

        return records

    @staticmethod
    def create_batches(rows: List[RowItem], batch_size: int) -> List[List[RowItem]]:
        """Groups rows into user-defined batch sizes."""
        if batch_size <= 0:
            batch_size = 10

        batches = []
        for i in range(0, len(rows), batch_size):
            batches.append(rows[i: i + batch_size])
        return batches

    @staticmethod
    def write_translated_sheet(
        original_file: str,
        translations: Dict[int, str],
        target_column: str,
        output_file: str
    ):
        """Maps translations back to row_id and exports the localized file."""
        df = ExcelHandler._read_file(original_file)

        # Map translated strings using explicit index position to guarantee row alignment
        translated_list = []
        for idx in range(len(df)):
            # If row_id was translated, fetch it; otherwise keep original text or empty string
            if idx in translations:
                translated_list.append(translations[idx])
            elif "text" in df.columns:
                translated_list.append(df.loc[idx, "text"])
            else:
                translated_list.append("")

        df[target_column] = translated_list

        ext = os.path.splitext(output_file)[1].lower()
        if ext == ".csv":
            df.to_csv(output_file, index=False)
        else:
            df.to_excel(output_file, index=False)
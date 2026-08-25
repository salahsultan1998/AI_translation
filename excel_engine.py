import os
import re
import shutil
import pandas as pd
import openpyxl
from typing import List, Dict, Optional, Tuple
from custom_types import RowItem

# Matches runs of digits, used to detect rows that are identical except for
# an embedded number (e.g. "主城装饰：1级" vs "主城装饰：2级").
_NUMBER_PATTERN = re.compile(r"\d+")


class ExcelHandler:
    @staticmethod
    def _read_file(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """Helper to safely read both CSV and Excel files."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            return pd.read_csv(file_path)
        
        # If sheet_name is provided, read that specific sheet. Otherwise, read the default (first) sheet.
        if sheet_name:
            return pd.read_excel(file_path, sheet_name=sheet_name)
        return pd.read_excel(file_path)

    @staticmethod
    def read_game_sheet(
        file_path: str,
        text_column: str = "text",
        context_column: Optional[str] = "text_type",
        sheet_name: Optional[str] = None
    ) -> List[RowItem]:
        """Reads game text files (.xlsx or .csv) using specified column mappings and normalizes full-width characters."""
        # Pass the sheet_name to the reader
        df = ExcelHandler._read_file(file_path, sheet_name=sheet_name)
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

            # Safely extract context notes/speaker tags (Fixed the None check here)
            ctx = None
            if context_column is not None and context_column in df.columns and pd.notna(row.get(context_column)):
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
    def deduplicate_rows(rows: List[RowItem]) -> Tuple[List[RowItem], Dict[int, int]]:
        """Collapses rows with byte-identical source_text down to one representative
        row. Returns (unique_rows, alias_map), where alias_map maps a duplicate
        row's row_id to the representative row_id whose translation it should
        reuse. This avoids paying for (and re-translating) the exact same string
        twice, and guarantees identical output for identical input."""
        seen: Dict[str, int] = {}
        unique_rows: List[RowItem] = []
        alias_map: Dict[int, int] = {}

        for row in rows:
            key = row.source_text
            representative_id = seen.get(key)
            if representative_id is not None:
                alias_map[row.row_id] = representative_id
            else:
                seen[key] = row.row_id
                unique_rows.append(row)

        return unique_rows, alias_map

    @staticmethod
    def group_near_duplicates(rows: List[RowItem]) -> List[List[RowItem]]:
        """Groups rows whose source_text is identical except for embedded
        numbers (e.g. "Level 1" / "Level 2") into the same family, so a later
        batching step keeps them together in one LLM call. Translating them
        side by side keeps phrasing and target-language grammar (e.g. Arabic
        singular/dual/plural agreement) consistent across the variants,
        without us mechanically splicing numbers into a template ourselves.
        Rows without a near-duplicate partner form a family of one."""
        families: Dict[str, List[RowItem]] = {}
        order: List[str] = []

        for row in rows:
            template = _NUMBER_PATTERN.sub("#", row.source_text)
            if template not in families:
                families[template] = []
                order.append(template)
            families[template].append(row)

        return [families[key] for key in order]

    @staticmethod
    def create_batches(families: List[List[RowItem]], batch_size: int = 10, use_smart_budget: bool = False) -> List[List[RowItem]]:
        """Packs families (groups of rows that must stay together) into batches
        using either fixed row count or a dynamic character budget. A family is
        never split across two batches."""
        if use_smart_budget:
            batches = []
            current_batch: List[RowItem] = []
            current_chars = 0
            target_char_budget = 1000  # Safe character limit per batch

            for family in families:
                family_chars = sum(len(r.source_text) for r in family)

                # If a single family exceeds the budget entirely, give it its own batch
                if family_chars >= target_char_budget:
                    if current_batch:
                        batches.append(current_batch)
                        current_batch = []
                        current_chars = 0
                    batches.append(list(family))
                    continue

                # If adding this family breaks the budget, push current batch and start a new one
                if current_chars + family_chars > target_char_budget:
                    batches.append(current_batch)
                    current_batch = list(family)
                    current_chars = family_chars
                else:
                    current_batch.extend(family)
                    current_chars += family_chars

            if current_batch:
                batches.append(current_batch)
            return batches
        else:
            # Fixed row-count batching for Manual mode
            if batch_size <= 0:
                batch_size = 10
            batches = []
            current_batch: List[RowItem] = []

            for family in families:
                if len(family) >= batch_size:
                    if current_batch:
                        batches.append(current_batch)
                        current_batch = []
                    batches.append(list(family))
                    continue

                if len(current_batch) + len(family) > batch_size:
                    batches.append(current_batch)
                    current_batch = list(family)
                else:
                    current_batch.extend(family)

            if current_batch:
                batches.append(current_batch)
            return batches

    @staticmethod
    def prepare_batches(rows: List[RowItem], batch_size: int = 10, use_smart_budget: bool = False) -> Tuple[List[List[RowItem]], Dict[int, int]]:
        """Full preprocessing pipeline: deduplicates identical rows, groups
        near-duplicates so they translate together for consistency, then packs
        the result into batches.

        Returns (batches, alias_map). After translating every row in `batches`,
        apply alias_map to fill in the skipped duplicate rows:
            for dup_id, rep_id in alias_map.items():
                translations[dup_id] = translations[rep_id]
        """
        unique_rows, alias_map = ExcelHandler.deduplicate_rows(rows)
        families = ExcelHandler.group_near_duplicates(unique_rows)
        batches = ExcelHandler.create_batches(families, batch_size=batch_size, use_smart_budget=use_smart_budget)
        return batches, alias_map

    @staticmethod
    def write_translated_workbook(
        original_file: str,
        sheet_translations: Dict[str, Dict[int, str]],  # { "Sheet1": {0: "Trans", ...}, "Sheet2": {...} }
        target_column: str,
        output_file: str
    ):
        """Maps translations back to multiple sheets, preserving all formatting."""
        ext = os.path.splitext(output_file)[1].lower()
        
        if ext == ".csv":
            # CSVs only have one sheet, we just take the first one available
            sheet_name = list(sheet_translations.keys())[0]
            translations = sheet_translations[sheet_name]
            
            df = ExcelHandler._read_file(original_file)
            translated_list = []
            for idx in range(len(df)):
                translated_list.append(translations.get(idx, ""))
            df[target_column] = translated_list
            df.to_csv(output_file, index=False)
            
        else:
            # Excel: Copy original file to preserve structure and formatting
            shutil.copy2(original_file, output_file)
            wb = openpyxl.load_workbook(output_file)
            
            with pd.ExcelFile(original_file) as xl:
                # Loop through every sheet we have translations for
                for sheet_name, translations in sheet_translations.items():
                    if sheet_name not in wb.sheetnames:
                        continue
                        
                    df = pd.read_excel(xl, sheet_name=sheet_name)
                    ws = wb[sheet_name]
                    
                    # Find or create the target column
                    target_col_idx = None
                    for cell in ws[1]:
                        if cell.value == target_column:
                            target_col_idx = cell.column
                            break
                            
                    if target_col_idx is None:
                        target_col_idx = ws.max_column + 1
                        ws.cell(row=1, column=target_col_idx, value=target_column)
                    
                    # Write translations
                    for idx in range(len(df)):
                        translated_text = translations.get(idx, "")
                        ws.cell(row=idx + 2, column=target_col_idx, value=translated_text)
            
            wb.save(output_file)
            wb.close()
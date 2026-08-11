import sqlite3
import os

class DBEngine:
    def __init__(self, db_path: str = "data/localization.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database schema for terms, TM, and Game Profiles."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 1. Glossary Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS glossaries (
                    game_id TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    source_term TEXT NOT NULL,
                    target_term TEXT NOT NULL,
                    PRIMARY KEY (game_id, target_language, source_term)
                )
            ''')
            
            # 2. Translation Memory Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS translation_memory (
                    game_id TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    target_text TEXT NOT NULL,
                    PRIMARY KEY (game_id, target_language, source_text)
                )
            ''')
            
            # 3. Game Profiles Table (For Tone & Style)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_profiles (
                    game_id TEXT NOT NULL,
                    tone_style TEXT NOT NULL,
                    PRIMARY KEY (game_id)
                )
            ''')
            conn.commit()

    def upsert_terms(self, game_id: str, target_language: str, pairs: list[dict]) -> int:
        """Upserts glossary terms into the database atomically."""
        game_key = game_id.lower().strip()
        lang_key = target_language.lower().strip()
        
        valid_pairs = [
            (game_key, lang_key, str(p["source"]).strip(), str(p["target"]).strip()) 
            for p in pairs if str(p.get("source", "")).strip() and str(p.get("target", "")).strip()
        ]

        if not valid_pairs:
            return 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT INTO glossaries (game_id, target_language, source_term, target_term)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(game_id, target_language, source_term) 
                DO UPDATE SET target_term = excluded.target_term
            ''', valid_pairs)
            conn.commit()
            return cursor.rowcount

    def get_terms_for_game(self, game_id: str, target_language: str) -> dict:
        """Retrieves all glossary terms for a specific game and language."""
        game_key = game_id.lower().strip()
        lang_key = target_language.lower().strip()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT source_term, target_term FROM glossaries
                WHERE game_id = ? AND target_language = ?
            ''', (game_key, lang_key))
            return {row[0]: row[1] for row in cursor.fetchall()}

    def upsert_tm(self, game_id: str, target_language: str, pairs: list[dict]) -> int:
        """Upserts Translation Memory sentences into the database atomically."""
        game_key = game_id.lower().strip()
        lang_key = target_language.lower().strip()
        
        valid_pairs = [
            (game_key, lang_key, str(p["source"]).strip(), str(p["target"]).strip()) 
            for p in pairs if str(p.get("source", "")).strip() and str(p.get("target", "")).strip()
        ]

        if not valid_pairs:
            return 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT INTO translation_memory (game_id, target_language, source_text, target_text)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(game_id, target_language, source_text) 
                DO UPDATE SET target_text = excluded.target_text
            ''', valid_pairs)
            conn.commit()
            return cursor.rowcount

    def get_tm_for_game(self, game_id: str, target_language: str) -> dict:
        """Retrieves the full Translation Memory for a specific game and language."""
        game_key = game_id.lower().strip()
        lang_key = target_language.lower().strip()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT source_text, target_text FROM translation_memory
                WHERE game_id = ? AND target_language = ?
            ''', (game_key, lang_key))
            return {row[0]: row[1] for row in cursor.fetchall()}

    def upsert_game_profile(self, game_id: str, tone_style: str):
        """Saves the style and tone instructions for a game."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO game_profiles (game_id, tone_style)
                VALUES (?, ?)
                ON CONFLICT(game_id) 
                DO UPDATE SET tone_style = excluded.tone_style
            ''', (game_id.lower().strip(), tone_style.strip()))
            conn.commit()

    def get_game_profile(self, game_id: str) -> str:
        """Retrieves the tone and style instructions for a game."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT tone_style FROM game_profiles WHERE game_id = ?', (game_id.lower().strip(),))
            row = cursor.fetchone()
            return row[0] if row else ""
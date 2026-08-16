# db_engine.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseDBEngine:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY")

        self.client: Client = create_client(url, key)

    # ========================================================
    # AUTHENTICATION
    # ========================================================
    def sign_in(self, email: str, password: str):
        """Logs in an existing user and returns user and access token."""
        try:
            response = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            return response.user, response.session.access_token, None
        except Exception as e:
            return None, None, str(e)

    def get_user_from_token(self, token: str):
        """Verifies a saved cookie token and logs the user back in."""
        try:
            response = self.client.auth.get_user(token)
            return response.user
        except Exception:
            return None

    def sign_out(self):
        """Safe placeholder since Supabase JWTs are stateless client-side."""
        pass

    # ========================================================
    # NORMALIZATION HELPER METHODS
    # ========================================================
    def _normalize_game(self, game_id: str) -> str:
        return game_id.lower().strip()

    def _normalize_lang(self, lang: str) -> str:
        return lang.lower().strip()

    # ========================================================
    # GLOSSARY MANAGEMENT
    # ========================================================
    def upsert_terms(self, game_id: str, target_language: str, pairs: list[dict]) -> int:
        game_key = self._normalize_game(game_id)
        lang_key = self._normalize_lang(target_language)

        valid_pairs = [
            {
                "game_id": game_key,
                "target_language": lang_key,
                "source_term": str(p["source"]).strip(),
                "target_term": str(p["target"]).strip()
            }
            for p in pairs
            if str(p.get("source", "")).strip() and str(p.get("target", "")).strip()
        ]

        if not valid_pairs:
            return 0

        res = self.client.table("glossaries").insert(
            valid_pairs
        ).execute()

        return len(res.data)
    
    def upsert_single_term(self, game_id: str, target_language: str, source: str, target: str):
        """Inserts or updates a single term in the database."""
        data = {
            "game_id": game_id,
            "target_language": target_language,
            "source": source.strip(),
            "target": target.strip()
        }
        # Assuming your table is named 'game_terms'
        response = self.client.table("game_terms").upsert(
            data, 
            on_conflict="game_id,target_language,source"
        ).execute()
        return response
    def get_terms_for_game(self, game_id: str, target_language: str) -> dict:
        game_key = self._normalize_game(game_id)
        lang_key = self._normalize_lang(target_language)

        res = self.client.table("glossaries") \
            .select("source_term,target_term") \
            .eq("game_id", game_key) \
            .eq("target_language", lang_key) \
            .execute()

        return {row["source_term"]: row["target_term"] for row in res.data}

    # ========================================================
    # TRANSLATION MEMORY (TM) MANAGEMENT
    # ========================================================
    def upsert_tm(self, game_id: str, target_language: str, pairs: list[dict]) -> int:
        game_key = self._normalize_game(game_id)
        lang_key = self._normalize_lang(target_language)

        valid_pairs = [
            {
                "game_id": game_key,
                "target_language": lang_key,
                "source_text": str(p["source"]).strip(),
                "target_text": str(p["target"]).strip()
            }
            for p in pairs
            if str(p.get("source", "")).strip() and str(p.get("target", "")).strip()
        ]

        if not valid_pairs:
            return 0

        res = self.client.table("translation_memory").insert(
            valid_pairs
        ).execute()

        return len(res.data)

    def get_tm_for_game(self, game_id: str, target_language: str) -> dict:
        game_key = self._normalize_game(game_id)
        lang_key = self._normalize_lang(target_language)

        res = self.client.table("translation_memory") \
            .select("source_text,target_text") \
            .eq("game_id", game_key) \
            .eq("target_language", lang_key) \
            .execute()

        return {row["source_text"]: row["target_text"] for row in res.data}

    # ========================================================
    # GAME PROFILE MANAGEMENT
    # ========================================================
    def upsert_game_profile(self, game_id: str, tone_style: str):
        payload = {
            "game_id": self._normalize_game(game_id),
            "tone_style": tone_style.strip()
        }
        self.client.table("game_profiles").upsert(payload, on_conflict="game_id").execute()

    def get_game_profile(self, game_id: str) -> str:
        game_key = self._normalize_game(game_id)

        res = self.client.table("game_profiles") \
            .select("tone_style") \
            .eq("game_id", game_key) \
            .limit(1) \
            .execute()

        return res.data[0]["tone_style"] if res.data else ""
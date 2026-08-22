import ahocorasick
from rapidfuzz import process, fuzz

class RAGEngine:
    def __init__(self):
        self.glossary_automaton = ahocorasick.Automaton()
        self.has_glossary = False
        
        self.tm_dict = {}
        self.tm_sources = []
        self.game_profile = ""

    def load_resources(self, glossary_dict: dict, tm_dict: dict, game_profile: str):
        """Loads all local resources into memory before the translation loop starts."""
        
        # 1. Build Exact-Match Glossary Tree
        if glossary_dict:
            self.glossary_automaton = ahocorasick.Automaton()
            for chinese_term, target_term in glossary_dict.items():
                self.glossary_automaton.add_word(chinese_term, (chinese_term, target_term))
            self.glossary_automaton.make_automaton()
            self.has_glossary = True
            print(f"📚 Loaded {len(glossary_dict)} exact terms into Aho-Corasick tree.")
        else:
            self.has_glossary = False

        # 2. Load Translation Memory for Fuzzy Matching
        self.tm_dict = tm_dict if tm_dict else {}
        self.tm_sources = list(self.tm_dict.keys())
        if self.tm_sources:
            print(f"🧠 Loaded {len(self.tm_sources)} Translation Memory sentences for Fuzzy Matching.")

        # 3. Load Game Profile (Tone & Style)
        self.game_profile = game_profile
        if self.game_profile:
            print(f"🎭 Loaded Game Profile: {self.game_profile[:50]}...")

    def get_exact_terms(self, source_text: str) -> list[tuple[str, str]]:
        """Scans the text for exact glossary terminology."""
        if not self.has_glossary:
            return []
            
        found_terms = []
        for end_index, (chinese_term, target_term) in self.glossary_automaton.iter(source_text):
            found_terms.append((chinese_term, target_term))
        return found_terms

    def get_fuzzy_tm(self, source_text: str, top_k: int = 2, threshold: float = 85.0) -> list[tuple[str, str]]:
        """Finds highly similar past translations using CPU string matching (no AI vectors needed)."""
        if not self.tm_sources:
            return []
            
        # WRatio handles variations in string length and word order efficiently
        results = process.extract(
            source_text, 
            self.tm_sources, 
            scorer=fuzz.WRatio, 
            limit=top_k, 
            score_cutoff=threshold
        )
        
        matches = []
        # process.extract returns a list of tuples: (matched_string, score, index)
        for match_str, score, _ in results:
            matches.append((match_str, self.tm_dict[match_str]))
            
        return matches

    def get_exact_term_candidates(self, source_text: str, context: str | None = None, row_id: int | None = None) -> list[dict]:
        """Returns exact glossary candidates ready for a human review step."""
        if not self.has_glossary:
            return []

        matches = []
        seen = set()
        for chinese_term, target_term in self.get_exact_terms(source_text):
            key = (chinese_term.lower(), target_term.lower())
            if key in seen:
                continue
            seen.add(key)
            matches.append({
                "row_id": row_id,
                "source_term": chinese_term,
                "suggested_target": target_term,
                "source": "glossary",
                "context": context or source_text,
                "approved": True,
            })
        return matches

    def build_review_candidates(self, batch_rows: list, target_language: str) -> list[dict]:
        """Collects exact glossary hits and prepares them for approval/editing before translation."""
        review_map = {}

        for row in batch_rows:
            source_text = str(getattr(row, "source_text", "")).strip()
            if not source_text:
                continue
            context = str(getattr(row, "context", "") or "")
            row_id = getattr(row, "row_id", None)
            for candidate in self.get_exact_term_candidates(source_text, context=context, row_id=row_id):
                key = candidate["source_term"].strip().lower()
                if key not in review_map:
                    review_map[key] = {
                        **candidate,
                        "source_language": "Chinese",
                        "target_language": target_language,
                    }

        return list(review_map.values())

    def get_batch_context(self, batch_rows: list, target_language: str) -> str:
        """Assembles the final context block (Profile + Terms + TM) for the LLM Prompt."""
        texts = [str(getattr(r, "source_text", "")).strip() for r in batch_rows if str(getattr(r, "source_text", "")).strip()]
        if not texts:
            return ""

        all_terms = set()
        all_memory = set()

        # Process each row in the batch locally
        for text in texts:
            # 1. Exact Glossary Matching
            exact_matches = self.get_exact_terms(text)
            for zh_term, tgt_term in exact_matches:
                all_terms.add(f"Chinese: '{zh_term}' -> {target_language}: '{tgt_term}'")
                
            # 2. Fuzzy Translation Memory Matching
            fuzzy_matches = self.get_fuzzy_tm(text, top_k=2, threshold=85.0)
            for zh_mem, tgt_mem in fuzzy_matches:
                all_memory.add(f"Chinese: '{zh_mem}' -> {target_language}: '{tgt_mem}'")

        # 3. Assemble the Context Block
        formatted_context = ""
        
        if self.game_profile:
            formatted_context += "### GAME TONE & STYLE INSTRUCTIONS:\n"
            formatted_context += f"{self.game_profile}\n\n"
            
        if all_terms:
            formatted_context += "### REQUIRED GLOSSARY TERMS (Do not change these!):\n"
            formatted_context += "\n".join([f"- {t}" for t in all_terms]) + "\n\n"
            
        if all_memory:
            formatted_context += "### TRANSLATION MEMORY (Reference for formatting/style):\n"
            formatted_context += "\n".join([f"- {m}" for m in all_memory])

        return formatted_context.strip()
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-flash")
FALLBACK_MODEL = os.getenv("OPENROUTER_FALLBACK_MODEL", "qwen/qwen3.6-flash")

UNSUPPORTED_MODEL_TOKENS = ("qwen/qwen-2.5-72b-instruct",)

MAX_CONCURRENT_BATCHES = 10
INACTIVITY_LIMIT_SECONDS = 600

MODEL_OPTIONS = [
    "qwen/qwen3.6-flash",
    "google/gemini-3.7-flash"و
    "openai/gpt-6-luna-pro"
]

PROJECT_OPTIONS = [
    "Direct_translation",
    "DM_03", 
    "Tarbi3a_Baloot",
    "Baloot_Challenges",
    "sawa", 
    "S06"
]


SUPPORTED_LANGUAGES = ["Arabic", "English", "Turkish"]

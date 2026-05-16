import os
from dotenv import load_dotenv

load_dotenv()


def _parse_ids(raw: str) -> set[int]:
    return {int(uid.strip()) for uid in raw.split(",") if uid.strip().isdigit()}


TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
GOOGLE_CLOUD_API_KEY: str = os.environ.get("GOOGLE_CLOUD_API_KEY", "")
OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
ASSEMBLYAI_API_KEY: str = os.environ.get("ASSEMBLYAI_API_KEY", "")

ALLOWED_USER_IDS: set[int] = _parse_ids(os.environ.get("ALLOWED_USER_IDS", ""))
ADMIN_USER_ID: int = int(os.environ.get("ADMIN_USER_ID", "0"))

DB_PATH = "opic_bot.db"

# "local" → Ollama (gemma3:4b), "remote" → OpenRouter
GRADER_MODE: str = os.environ.get("GRADER_MODE", "local")

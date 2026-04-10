import os
from dotenv import load_dotenv

load_dotenv()


def _parse_ids(raw: str) -> set[int]:
    return {int(uid.strip()) for uid in raw.split(",") if uid.strip().isdigit()}


TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")

ALLOWED_USER_IDS: set[int] = _parse_ids(os.environ.get("ALLOWED_USER_IDS", ""))
ADMIN_USER_ID: int = int(os.environ.get("ADMIN_USER_ID", "0"))

CLAUDE_MODEL = "claude-sonnet-4-6"
DB_PATH = "opic_bot.db"

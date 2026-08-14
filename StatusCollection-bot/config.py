import os
from pathlib import Path
from dotenv import load_dotenv
from typing import List

_env_path = Path(__file__).parent.resolve() / ".env"
load_dotenv(dotenv_path=_env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")

def _get_admin_ids() -> List[int]:
    raw_ids = os.getenv("ADMIN_IDS", "")
    return [int(uid) for uid in raw_ids.split(",") if uid.strip().isdigit()]

ADMINS = _get_admin_ids()

if not BOT_TOKEN:
    raise RuntimeError("Ошибка конфигурации: отсутствует токен бота в .env")
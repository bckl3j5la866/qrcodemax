# settings.py
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    BOT_TOKEN: Optional[str]
    STATUS_FIELD_NAME: str = "Status"
    ADMIN_CHAT_ID: Optional[str] = None   # новое поле

    @staticmethod
    def load() -> "Settings":
        bot_token = os.getenv("BOT_TOKEN")
        status_field = os.getenv("STATUS_FIELD_NAME", "Status")
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")   # например, "+79001234567"
        return Settings(
            BOT_TOKEN=bot_token,
            STATUS_FIELD_NAME=status_field,
            ADMIN_CHAT_ID=admin_chat_id
        )

settings = Settings.load()
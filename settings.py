# settings.py
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    BOT_TOKEN: Optional[str]
    STATUS_FIELD_NAME: str = "Status"   # значение по умолчанию

    @staticmethod
    def load() -> "Settings":
        bot_token = os.getenv("BOT_TOKEN")
        status_field = os.getenv("STATUS_FIELD_NAME", "Status")
        return Settings(
            BOT_TOKEN=bot_token,
            STATUS_FIELD_NAME=status_field
        )

settings = Settings.load()
"""Application configuration module for ChronoDump."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """Typed application settings loaded from environment."""

    def __init__(self) -> None:
        self.TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        
        user_id_raw = os.getenv("AUTHORIZED_USER_ID", "0").strip()
        try:
            self.AUTHORIZED_USER_ID: int = int(user_id_raw)
        except ValueError:
            self.AUTHORIZED_USER_ID = 0

        self.OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
        self.OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip()

        self.WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base.en").strip()
        self.WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu").strip()
        self.WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8").strip()

        data_dir_env = os.getenv("DATA_DIR", "./data").strip()
        self.DATA_DIR: Path = (BASE_DIR / data_dir_env).resolve() if not os.path.isabs(data_dir_env) else Path(data_dir_env)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

        self.DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{self.DATA_DIR}/chronodump.db").strip()
        self.SCHEDULER_DATABASE_URL: str = os.getenv(
            "SCHEDULER_DATABASE_URL", f"sqlite:///{self.DATA_DIR}/chronodump_scheduler.db"
        ).strip()

        self.DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "UTC").strip()
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    @property
    def is_configured(self) -> bool:
        """Returns True if essential secrets are provided."""
        return (
            bool(self.TELEGRAM_BOT_TOKEN)
            and self.TELEGRAM_BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE"
            and self.AUTHORIZED_USER_ID != 0
        )


settings = Settings()

"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """All configuration is loaded from .env file or environment variables."""

    # --- Application ---
    APP_NAME: str = "IELTS Speaking Practice"
    DEBUG: bool = False

    # --- Paths ---
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DB_PATH: str = "data/ielts.db"
    RECORDINGS_DIR: str = "data/recordings"

    # --- Database ---
    # If DATABASE_URL is set (e.g., PostgreSQL on Cloud Run), use it.
    # Otherwise, fall back to local SQLite.
    DATABASE_URL: str = ""

    # --- OpenAI (Whisper ASR) ---
    OPENAI_API_KEY: str = ""

    # --- Google Gemini (LLM Scoring) ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # --- Azure Speech (Pronunciation Assessment) ---
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = "eastasia"

    # --- Recording ---
    MAX_RECORDING_SECONDS: int = 150  # 2.5 min max (Part 2 = 2 min + buffer)
    ALLOWED_AUDIO_FORMATS: list[str] = ["webm", "wav", "mp3", "ogg"]

    # --- Authentication ---
    JWT_SECRET: str = "change_this_to_a_random_secure_string_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    INVITE_CODE: str = "IELTS2025"  # Default invite code if not set in .env

    @property
    def database_url(self) -> str:
        """Return the database URL.
        
        Priority:
        1. DATABASE_URL env var (for Cloud Run with PostgreSQL)
        2. Local SQLite file (for development)
        """
        if self.DATABASE_URL:
            # Convert postgres:// to postgresql+asyncpg://
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        # Default: local SQLite
        db_path = self.BASE_DIR / self.DB_PATH
        return f"sqlite+aiosqlite:///{db_path}"

    @property
    def recordings_path(self) -> Path:
        path = self.BASE_DIR / self.RECORDINGS_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def data_dir(self) -> Path:
        path = self.BASE_DIR / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

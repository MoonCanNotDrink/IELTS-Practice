"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pathlib import Path
import warnings


class Settings(BaseSettings):
    """All configuration is loaded from .env file or environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "IELTS Speaking Practice"
    APP_BASE_URL: str = "http://localhost:8000"
    DEBUG: bool = False

    # --- Paths ---
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DB_PATH: str = "data/ielts.db"
    RECORDINGS_DIR: str = "data/recordings"

    # --- Database ---
    # If DATABASE_URL is set (e.g., PostgreSQL on Cloud Run), use it.
    # Otherwise, fall back to local SQLite.
    DATABASE_URL: str = ""

    # --- Local Whisper fallback ---
    WHISPER_MODEL_PATH: str = "whisper_base_model"
    WHISPER_MODEL_SIZE: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    # --- Google Gemini (LLM Scoring) ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS: int = 25

    # --- Azure Speech (Pronunciation Assessment) ---
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = "eastasia"
    PRONUNCIATION_TIMEOUT_SECONDS: int = 15

    # --- Recording ---
    MAX_RECORDING_SECONDS: int = 150  # 2.5 min max (Part 2 = 2 min + buffer)
    ALLOWED_AUDIO_FORMATS: list[str] = ["webm", "wav", "mp3", "ogg"]

    # --- Authentication ---
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_RESET_EXPIRE_MINUTES: int = 15
    INVITE_CODE: str = ""

    # --- Email ---
    EMAIL_FROM: str = "no-reply@example.com"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True

    # --- CORS ---
    CORS_ORIGINS: list[str] = []

    @field_validator("JWT_SECRET", mode="after")
    @classmethod
    def warn_empty_jwt_secret(cls, value):
        if not value:
            warnings.warn(
                "JWT_SECRET is empty — set it in .env before deploying to production",
                stacklevel=1,
            )
        return value

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, str):
            token = value.strip().lower()
            if token in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if token in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

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
        db_path.parent.mkdir(parents=True, exist_ok=True)
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

settings = Settings()

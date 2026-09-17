from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root directory of the repository
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """Authoritative application settings for KISANQUEUE V2 backend.

    Loads configuration from environment variables and local .env files.
    All sensitive credentials are kept strictly out of source code.
    """
    PROJECT_NAME: str = "KISANQUEUE API"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Database: PostgreSQL 17 + PostGIS 3.5
    DATABASE_URL: Optional[str] = None

    # Redis (Phase 2+)
    REDIS_URL: Optional[str] = None

    # Security (Phase 2+)
    JWT_SECRET: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=(
            str(BASE_DIR / ".env"),
            str(BASE_DIR / "backend" / ".env"),
            ".env",
            "backend/.env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        """Returns the normalized SQLAlchemy database URL.

        Ensures PostgreSQL URLs use the modern psycopg 3 driver (postgresql+psycopg://)
        unless explicitly specified, avoiding missing psycopg2 errors.
        """
        if not self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL is not configured. "
                "Please configure DATABASE_URL in your local .env file."
            )
        url = self.DATABASE_URL.strip()
        # Normalize postgresql:// to postgresql+psycopg:// for SQLAlchemy 2.x with psycopg 3
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        return url


settings = Settings()

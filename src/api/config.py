from typing import List

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Project
    PROJECT_NAME: str = Field(default="Flight Search API")
    VERSION: str = Field(default="0.1.0")
    DEBUG: bool = Field(default=False)

    # Database
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_USER: str = Field(default="flights_user")
    DB_PASSWORD: str = Field(default="flights_password")
    DB_NAME: str = Field(default="flights_db")
    DB_POOL_SIZE: int = Field(default=5)
    DB_MAX_OVERFLOW: int = Field(default=10)

    @property
    def DATABASE_URL(self) -> str:
        """Get the database URL."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # API
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_WORKERS: int = Field(default=4)
    API_CORS_ORIGINS: List[AnyHttpUrl] = Field(default_factory=list)

    # Security
    SECRET_KEY: str = Field(default="your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    # Worker
    WORKER_CONCURRENCY: int = Field(default=3)
    MAX_RETRIES: int = Field(default=3)
    CHECKPOINT_INTERVAL: int = Field(default=300)  # 5 minutes in seconds
    WORKER_BATCH_SIZE: int = Field(default=100)

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_prefix="",
        extra="allow",
    )


settings = Settings()

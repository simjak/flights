from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Project settings
    PROJECT_NAME: str = "Flight Search API"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "flights_user"
    DB_PASSWORD: str = "flights_password"
    DB_NAME: str = "flights_db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    @property
    def DATABASE_URL(self) -> str:
        """Get database URL."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEBUG: bool = False
    API_CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    API_WORKERS: int = 4
    API_TITLE: str = "Flight Search API"
    API_DESCRIPTION: str = "API for searching flight prices"
    API_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api/v1"

    # Worker settings
    WORKER_CONCURRENCY: int = 3
    MAX_RETRIES: int = 3
    CHECKPOINT_INTERVAL: int = 300  # 5 minutes in seconds
    WORKER_BATCH_SIZE: int = 100
    WORKER_RATE_LIMIT: int = 60
    WORKER_TIME_WINDOW: int = 60

    # Security settings
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: list[str] = ["*"]
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]

    # RabbitMQ settings
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "flights"
    RABBITMQ_PASSWORD: str = "flights"
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_QUEUE_NAME: str = "flight_search_tasks"
    RABBITMQ_EXCHANGE_NAME: str = "flight_search"
    RABBITMQ_ROUTING_KEY: str = "flight_search_tasks"
    RABBITMQ_PREFETCH_COUNT: int = 10

    @property
    def RABBITMQ_URL(self) -> str:
        """Get RabbitMQ URL."""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@lru_cache
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()

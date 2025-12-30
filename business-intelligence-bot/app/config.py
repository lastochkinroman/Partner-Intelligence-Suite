import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import logging

class Settings(BaseSettings):
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")

    mistral_api_key: str = Field(..., env="MISTRAL_API_KEY")
    mistral_model: str = Field(default="mistral-medium")
    mistral_temperature: float = Field(default=0.7)

    mysql_host: str = Field(default="mysql", env="MYSQL_HOST")
    mysql_port: int = Field(default=3306, env="MYSQL_PORT")
    mysql_database: str = Field(default="partner_db", env="MYSQL_DATABASE")
    mysql_user: str = Field(default="bi_bot_user", env="MYSQL_USER")
    mysql_password: str = Field(..., env="MYSQL_PASSWORD")

    redis_host: str = Field(default="redis", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")

    app_env: str = Field(default="production", env="APP_ENV")
    app_debug: bool = Field(default=False, env="APP_DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    documents_dir: str = Field(default="/app/documents", env="DOCUMENTS_DIR")
    logs_dir: str = Field(default="/app/logs")

    max_document_size_mb: int = Field(default=10, env="MAX_DOCUMENT_SIZE_MB")
    request_timeout_seconds: int = Field(default=30)
    cache_ttl_seconds: int = Field(default=3600)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def mysql_connection_string(self) -> str:
        return f"mysql+mysqlconnector://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    @property
    def redis_connection_string(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def setup_logging(level: str = "INFO"):
    log_level = getattr(logging, level.upper())

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("/app/logs/bot.log")
        ]
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)

    return logging.getLogger(__name__)

settings = Settings()
logger = setup_logging(settings.log_level)

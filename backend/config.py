from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:
    from pydantic import BaseModel as BaseSettings

    SettingsConfigDict = dict


class Settings(BaseSettings):
    app_name: str = "PaperHermes"
    app_env: str = "development"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://paperhermes:paperhermes@localhost:5432/paperhermes"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "paper_chunks"
    upload_dir: Path = Path("uploads")
    llm_provider: str = "stub"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""
    llm_api_style: str = "responses"
    embedding_provider: str = "stub"
    embedding_api_key: str = ""
    embedding_model: str = ""
    embedding_dim: int = 384
    embedding_device: str = "cuda"
    embedding_batch_size: int = 2
    embedding_max_length: int = 1024
    feishu_webhook_url: str = ""
    wecom_webhook_url: str = ""

    if hasattr(BaseSettings, "model_config"):
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def __init__(self, **data):
        env_data = {
            "app_name": os.getenv("APP_NAME"),
            "app_env": os.getenv("APP_ENV"),
            "api_prefix": os.getenv("API_PREFIX"),
            "database_url": os.getenv("DATABASE_URL"),
            "qdrant_url": os.getenv("QDRANT_URL"),
            "qdrant_collection": os.getenv("QDRANT_COLLECTION"),
            "upload_dir": os.getenv("UPLOAD_DIR"),
            "llm_provider": os.getenv("LLM_PROVIDER"),
            "llm_api_key": os.getenv("LLM_API_KEY"),
            "llm_model": os.getenv("LLM_MODEL"),
            "llm_base_url": os.getenv("LLM_BASE_URL"),
            "llm_api_style": os.getenv("LLM_API_STYLE"),
            "embedding_provider": os.getenv("EMBEDDING_PROVIDER"),
            "embedding_api_key": os.getenv("EMBEDDING_API_KEY"),
            "embedding_model": os.getenv("EMBEDDING_MODEL"),
            "embedding_dim": os.getenv("EMBEDDING_DIM"),
            "embedding_device": os.getenv("EMBEDDING_DEVICE"),
            "embedding_batch_size": os.getenv("EMBEDDING_BATCH_SIZE"),
            "embedding_max_length": os.getenv("EMBEDDING_MAX_LENGTH"),
            "feishu_webhook_url": os.getenv("FEISHU_WEBHOOK_URL"),
            "wecom_webhook_url": os.getenv("WECOM_WEBHOOK_URL"),
        }
        clean_data = {key: value for key, value in env_data.items() if value not in (None, "")}
        clean_data.update(data)
        super().__init__(**clean_data)


@lru_cache
def get_settings() -> Settings:
    return Settings()

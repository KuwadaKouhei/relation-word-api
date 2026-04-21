from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    api_keys: str = "dev-key"

    redis_url: str = "redis://localhost:6379/0"
    rate_limit_default: str = "60/minute"

    model_ja_path: str | None = None
    ann_index_path: str | None = None
    ann_labels_path: str | None = None

    cache_ttl_seconds: int = 86400
    top_k_max: int = 100
    batch_max: int = 50

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()

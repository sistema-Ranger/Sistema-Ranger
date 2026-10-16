# BACK/app/config.py
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída del entorno (.env). Los secretos no tienen valor por defecto."""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", protected_namespaces=("settings_",)
    )

    app_env: str = "development"
    database_url: str
    test_database_url: str | None = None
    cors_origins: str = "http://localhost:5173"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    collector_api_key: str
    admin_email: str
    admin_password: str

    analysis_interval_seconds: int = 60
    model_dir: str = "/code/ml/models"
    alert_cooldown_minutes: int = 15
    collect_interval: int = 10
    max_batch_size: int = 500

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()

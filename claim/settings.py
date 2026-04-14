from enum import Enum

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    DEV = "dev"
    PROD = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLAIMCRAFT_",
        env_file=".env",
        extra="ignore",
    )

    app_env: AppEnv = AppEnv.DEV

    # Optional explicit override. If unset, environment-specific defaults are used.
    pricing_service_base_url: str = "http://127.0.0.1:8080"
    pricing_service_base_url_dev: str = "http://127.0.0.1:8080"
    pricing_service_base_url_prod: str = "http://127.0.0.1:8080"

    pricing_service_timeout_seconds: float = 10.0
    pricing_service_retry_total: int = 3
    pricing_service_retry_backoff_seconds: float = 0.5
    pricing_service_retry_statuses: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504]
    )

    log_level: str = "INFO"
    log_json: bool = True

    @model_validator(mode="after")
    def set_env_defaults(self):
        if not self.pricing_service_base_url:
            if self.app_env == AppEnv.PROD:
                self.pricing_service_base_url = self.pricing_service_base_url_prod
            else:
                self.pricing_service_base_url = self.pricing_service_base_url_dev
        return self


settings = Settings()


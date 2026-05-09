from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_LOCAL_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AEGIS_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "Aegis Scanner API"
    app_version: str = "0.2.0"
    environment: str = Field(default="development", validation_alias=AliasChoices("ENV_MODE", "AEGIS_ENVIRONMENT"))
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "AEGIS_LOG_LEVEL"))

    scan_engine: Literal["nmap", "mock"] = "nmap"
    allowed_target_mode: Literal["private", "any"] = "private"
    max_scan_hosts: int = Field(default=16, ge=1, le=256)
    local_hostnames: list[str] | str = Field(default_factory=lambda: ["localhost", "host.docker.internal"])

    nmap_host_timeout_seconds: int = Field(default=120, ge=10, le=900)
    nmap_script_timeout_seconds: int = Field(default=20, ge=5, le=120)
    nmap_stats_interval_seconds: int = Field(default=5, ge=1, le=60)
    nmap_max_retries: int = Field(default=2, ge=0, le=10)
    enable_os_detection: bool = False
    enable_vuln_scripts: bool = False
    nmap_vuln_script_selector: str = "vuln"

    allowed_origins: list[str] | str = Field(
        default_factory=lambda: DEFAULT_LOCAL_ORIGINS.copy(),
        validation_alias=AliasChoices("ALLOWED_ORIGINS", "AEGIS_CORS_ORIGINS"),
    )

    @field_validator("allowed_origins", "local_hostnames", mode="before")
    @classmethod
    def parse_csv_list(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_production_settings(self):
        if any(origin == "*" for origin in self.allowed_origins):
            if self.environment.lower() == "production":
                raise ValueError("Wildcard CORS origins are not allowed in production.")

        if self.environment.lower() == "production" and self.allowed_origins == DEFAULT_LOCAL_ORIGINS:
            raise ValueError("ALLOWED_ORIGINS must be set for production deployments.")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

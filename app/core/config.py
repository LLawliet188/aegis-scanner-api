from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AEGIS_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Aegis Scanner API"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000

    scan_engine: Literal["nmap", "mock"] = "nmap"
    allowed_target_mode: Literal["private", "any"] = "private"
    max_scan_hosts: int = Field(default=16, ge=1, le=256)
    local_hostnames: list[str] | str = Field(default_factory=lambda: ["localhost", "host.docker.internal"])

    nmap_path: str = "nmap"
    nmap_host_timeout_seconds: int = Field(default=120, ge=10, le=900)
    nmap_script_timeout_seconds: int = Field(default=20, ge=5, le=120)
    nmap_stats_interval_seconds: int = Field(default=5, ge=1, le=60)
    nmap_max_retries: int = Field(default=2, ge=0, le=10)
    enable_os_detection: bool = False
    enable_vuln_scripts: bool = False
    nmap_vuln_script_selector: str = "vuln"

    cors_origins: list[str] | str = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    @field_validator("cors_origins", "local_hostnames", mode="before")
    @classmethod
    def parse_csv_list(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

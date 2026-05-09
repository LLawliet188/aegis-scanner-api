from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    ready: bool
    version: str
    environment: str
    scan_engine: str
    nmap_available: bool
    allowed_target_mode: str


class DependencyStatus(BaseModel):
    ok: bool
    detail: str


class DetailedHealthResponse(HealthResponse):
    uptime_seconds: float
    environment_valid: bool
    dependencies: dict[str, DependencyStatus]
    system: dict[str, str | int | float | bool | None]

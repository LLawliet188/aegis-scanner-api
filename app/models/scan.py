from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.targeting import validate_ports_expression, validate_target_syntax


class ScanStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class ScanOptions(BaseModel):
    ports: str | None = Field(default=None, description="Optional ports such as 22,80,443 or 1-1024.")
    top_ports: int = Field(default=100, ge=1, le=1000)
    service_detection: bool = True
    os_detection: bool = False
    vuln_scripts: bool = False
    intensity: Literal["quick", "standard", "deep"] = "standard"

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, value: str | None) -> str | None:
        return validate_ports_expression(value)


class ScanRequest(BaseModel):
    target: str = Field(..., min_length=1, max_length=253)
    options: ScanOptions = Field(default_factory=ScanOptions)

    @field_validator("target")
    @classmethod
    def validate_target(cls, value: str) -> str:
        parsed = validate_target_syntax(value, max_scan_hosts=256)
        return parsed.value


class PortFinding(BaseModel):
    port: int
    protocol: str = "tcp"
    state: str
    service: str | None = None
    product: str | None = None
    version: str | None = None
    extra_info: str | None = None
    scripts: dict[str, str] = Field(default_factory=dict)


class HostFinding(BaseModel):
    address: str
    hostname: str | None = None
    state: str
    os_matches: list[str] = Field(default_factory=list)
    ports: list[PortFinding] = Field(default_factory=list)


class Vulnerability(BaseModel):
    id: str
    title: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    description: str
    host: str
    port: int | None = None
    service: str | None = None
    evidence: str | None = None
    references: list[str] = Field(default_factory=list)
    cve_enrichment_status: str = "not_enriched"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScanResult(BaseModel):
    scan_id: str
    target: str
    status: ScanStatus = ScanStatus.completed
    started_at: datetime
    finished_at: datetime
    command_profile: str
    hosts: list[HostFinding] = Field(default_factory=list)
    vulnerabilities: list[Vulnerability] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


class ScanRecord(BaseModel):
    scan_id: str
    target: str
    status: ScanStatus
    created_at: datetime
    updated_at: datetime
    options: ScanOptions
    result: ScanResult | None = None
    error: str | None = None


class ScanAcceptedResponse(BaseModel):
    scan_id: str
    status: ScanStatus
    target: str
    websocket_url: str
    message: str


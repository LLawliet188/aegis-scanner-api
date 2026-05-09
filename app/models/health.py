from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    environment: str
    scan_engine: str
    nmap_available: bool
    allowed_target_mode: str


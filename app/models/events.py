from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal["queued", "log", "progress", "finding", "completed", "error"]


class ScanEvent(BaseModel):
    type: EventType
    scan_id: str
    timestamp: datetime
    message: str
    progress: int | None = Field(default=None, ge=0, le=100)
    data: dict[str, Any] | None = None


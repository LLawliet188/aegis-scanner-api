import asyncio
from datetime import UTC, datetime

from app.models.scan import ScanRecord, ScanResult, ScanStatus


class ScanStore:
    def __init__(self) -> None:
        self._records: dict[str, ScanRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, record: ScanRecord) -> None:
        async with self._lock:
            self._records[record.scan_id] = record

    async def get(self, scan_id: str) -> ScanRecord | None:
        async with self._lock:
            record = self._records.get(scan_id)
            return record.model_copy(deep=True) if record else None

    async def update(
        self,
        scan_id: str,
        status: ScanStatus | None = None,
        result: ScanResult | None = None,
        error: str | None = None,
    ) -> ScanRecord | None:
        async with self._lock:
            record = self._records.get(scan_id)
            if record is None:
                return None
            updates = {"updated_at": datetime.now(UTC)}
            if status is not None:
                updates["status"] = status
            if result is not None:
                updates["result"] = result
            if error is not None:
                updates["error"] = error
            updated = record.model_copy(update=updates)
            self._records[scan_id] = updated
            return updated.model_copy(deep=True)


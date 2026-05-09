import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import Settings
from app.core.targeting import enforce_target_policy
from app.models.events import ScanEvent
from app.models.scan import ScanRecord, ScanRequest, ScanStatus
from app.services.cve_service import CveEnrichmentService
from app.services.errors import ScanNotFoundError, ScannerExecutionError, ScannerUnavailableError
from app.services.event_bus import EventBus
from app.services.scan_store import ScanStore

logger = logging.getLogger(__name__)


class ScanManager:
    """Coordinate scan records, scanner execution, enrichment, and event streaming."""

    def __init__(
        self,
        store: ScanStore,
        event_bus: EventBus,
        scanner,
        cve_service: CveEnrichmentService,
        settings: Settings,
    ) -> None:
        self.store = store
        self.event_bus = event_bus
        self.scanner = scanner
        self.cve_service = cve_service
        self.settings = settings

    async def create_scan(self, request: ScanRequest) -> ScanRecord:
        parsed_target = enforce_target_policy(request.target, self.settings)
        request.target = parsed_target.value

        now = datetime.now(UTC)
        record = ScanRecord(
            scan_id=uuid4().hex,
            target=request.target,
            status=ScanStatus.queued,
            created_at=now,
            updated_at=now,
            options=request.options,
        )
        await self.store.create(record)
        await self._publish(record.scan_id, "queued", "Scan queued.", 0, {"target": request.target})
        logger.info(
            "scan_queued",
            extra={"scan_id": record.scan_id, "target": request.target, "engine": self.settings.scan_engine},
        )
        asyncio.create_task(self._run_scan(record.scan_id, request))
        return record

    async def get_scan(self, scan_id: str) -> ScanRecord:
        record = await self.store.get(scan_id)
        if record is None:
            raise ScanNotFoundError(f"Scan '{scan_id}' was not found.")
        return record

    async def _run_scan(self, scan_id: str, request: ScanRequest) -> None:
        await self.store.update(scan_id, status=ScanStatus.running)
        await self._publish(scan_id, "progress", "Scan started.", 1, None)
        logger.info("scan_started", extra={"scan_id": scan_id, "target": request.target})

        async def emit(event_type: str, message: str, progress: int | None = None, data: dict | None = None) -> None:
            await self._publish(scan_id, event_type, message, progress, data)

        try:
            result = await self.scanner.run(scan_id, request, emit)
            result = await self.cve_service.enrich(result)
            await self.store.update(scan_id, status=ScanStatus.completed, result=result)

            for vulnerability in result.vulnerabilities:
                await self._publish(
                    scan_id,
                    "finding",
                    vulnerability.title,
                    None,
                    vulnerability.model_dump(mode="json"),
                )

            await self._publish(
                scan_id,
                "completed",
                "Scan completed.",
                100,
                {"summary": result.summary, "result": result.model_dump(mode="json")},
            )
            logger.info("scan_completed", extra={"scan_id": scan_id, "target": request.target, "summary": result.summary})
        except (ScannerUnavailableError, ScannerExecutionError) as exc:
            await self.store.update(scan_id, status=ScanStatus.failed, error=str(exc))
            await self._publish(scan_id, "error", str(exc), None, None)
            logger.error("scan_failed", extra={"scan_id": scan_id, "target": request.target, "error": str(exc)})
        except Exception as exc:
            await self.store.update(scan_id, status=ScanStatus.failed, error="Unexpected scan failure.")
            await self._publish(scan_id, "error", f"Unexpected scan failure: {exc}", None, None)
            logger.exception("scan_unexpected_failure", extra={"scan_id": scan_id, "target": request.target})

    async def _publish(
        self,
        scan_id: str,
        event_type: str,
        message: str,
        progress: int | None,
        data: dict | None,
    ) -> None:
        await self.event_bus.publish(
            ScanEvent(
                type=event_type,
                scan_id=scan_id,
                timestamp=datetime.now(UTC),
                message=message,
                progress=progress,
                data=data,
            )
        )

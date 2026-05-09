import platform
import sys
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.models.health import (
    DependencyStatus,
    DetailedHealthResponse,
    HealthResponse,
    MetricsResponse,
)
from app.models.scan import ScanAcceptedResponse, ScanRecord, ScanRequest
from app.services.errors import ScanNotFoundError, TargetPolicyError
from app.services.health import is_nmap_available
from app.services.scan_manager import ScanManager

router = APIRouter(tags=["scanner"])


def get_scan_manager(request: Request) -> ScanManager:
    return request.app.state.scan_manager


def _websocket_path(request: Request, scan_id: str) -> str:
    prefix = "/v1" if request.url.path.startswith("/v1/") else ""
    return f"{prefix}/ws/scan/{scan_id}"


def _health_payload(request: Request) -> HealthResponse:
    """Build the lightweight readiness payload shared by both health endpoints."""
    settings = request.app.state.settings
    nmap_available = is_nmap_available()
    ready = settings.scan_engine == "mock" or nmap_available

    return HealthResponse(
        status="ok" if ready else "degraded",
        ready=ready,
        version=settings.app_version,
        environment=settings.environment,
        scan_engine=settings.scan_engine,
        nmap_available=nmap_available,
        allowed_target_mode=settings.allowed_target_mode,
    )


def _get_memory_info() -> dict:
    try:
        import psutil

        proc = psutil.Process()
        mem = proc.memory_info()
        return {
            "rss_mb": round(mem.rss / 1024 / 1024, 2),
            "vms_mb": round(mem.vms / 1024 / 1024, 2),
            "percent": round(proc.memory_percent(), 3),
        }
    except Exception:
        return {"rss_mb": None, "vms_mb": None, "percent": None}


def _get_cpu_percent() -> float | None:
    try:
        import psutil

        return round(psutil.Process().cpu_percent(interval=0.05), 2)
    except Exception:
        return None


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    return _health_payload(request)


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health(request: Request) -> DetailedHealthResponse:
    base = _health_payload(request)
    settings = request.app.state.settings
    started_at = request.app.state.started_at
    uptime = (datetime.now(UTC) - started_at).total_seconds()

    dependency_checks = {
        "nmap": DependencyStatus(
            ok=base.nmap_available,
            detail="available" if base.nmap_available else "missing or not configured",
        ),
        "configuration": DependencyStatus(ok=True, detail="settings loaded and validated"),
    }

    return DetailedHealthResponse(
        **base.model_dump(),
        uptime_seconds=uptime,
        environment_valid=True,
        dependencies=dependency_checks,
        system={
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "allowed_origins_count": len(settings.allowed_origins),
        },
        memory=_get_memory_info(),
        cpu_percent=_get_cpu_percent(),
    )


@router.get("/metrics", response_model=MetricsResponse)
async def metrics(request: Request, accept: str = "") -> Response:
    """Expose operational metrics. Returns Prometheus text when Accept: text/plain."""
    collector = getattr(request.app.state, "metrics", None)
    accept_header = request.headers.get("accept", accept)

    if collector is None:
        raise HTTPException(status_code=503, detail="Metrics collector not initialized.")

    if "text/plain" in accept_header:
        return Response(
            content=collector.prometheus_text(),
            media_type="text/plain; version=0.0.4",
        )

    return Response(
        content=MetricsResponse(**collector.snapshot()).model_dump_json(),
        media_type="application/json",
    )


@router.post("/scan", response_model=ScanAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_scan(payload: ScanRequest, request: Request) -> ScanAcceptedResponse:
    manager = get_scan_manager(request)
    try:
        record = await manager.create_scan(payload)
    except TargetPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ScanAcceptedResponse(
        scan_id=record.scan_id,
        status=record.status,
        target=record.target,
        websocket_url=_websocket_path(request, record.scan_id),
        message="Scan accepted and queued.",
    )


@router.get("/scan/{scan_id}", response_model=ScanRecord)
async def get_scan(scan_id: str, request: Request) -> ScanRecord:
    manager = get_scan_manager(request)
    try:
        return await manager.get_scan(scan_id)
    except ScanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

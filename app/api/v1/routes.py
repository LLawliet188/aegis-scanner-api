import platform
import sys
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status

from app.models.health import DependencyStatus, DetailedHealthResponse, HealthResponse
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

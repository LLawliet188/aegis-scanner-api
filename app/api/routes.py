from fastapi import APIRouter, HTTPException, Request, status

from app.models.health import HealthResponse
from app.models.scan import ScanAcceptedResponse, ScanRecord, ScanRequest
from app.services.errors import ScanNotFoundError, TargetPolicyError
from app.services.health import is_nmap_available
from app.services.scan_manager import ScanManager

router = APIRouter(tags=["scanner"])


def get_scan_manager(request: Request) -> ScanManager:
    return request.app.state.scan_manager


@router.get("/")
async def root(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "service": settings.app_name,
        "health": "/health",
        "docs": "/docs",
    }


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        scan_engine=settings.scan_engine,
        nmap_available=is_nmap_available(),
        allowed_target_mode=settings.allowed_target_mode,
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
        websocket_url=f"/ws/scan/{record.scan_id}",
        message="Scan accepted and queued.",
    )


@router.get("/scan/{scan_id}", response_model=ScanRecord)
async def get_scan(scan_id: str, request: Request) -> ScanRecord:
    manager = get_scan_manager(request)
    try:
        return await manager.get_scan(scan_id)
    except ScanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

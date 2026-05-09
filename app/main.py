from contextlib import asynccontextmanager
import logging
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as root_router
from app.api.v1.routes import router as v1_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.middleware.request_id import RequestIDMiddleware
from app.services.cve_service import CveEnrichmentService
from app.services.event_bus import EventBus
from app.services.metrics import MetricsCollector
from app.services.mock_scanner import MockScanner
from app.services.nmap_runner import NmapScanner
from app.services.scan_manager import ScanManager
from app.services.scan_store import ScanStore
from app.websocket.routes import router as websocket_router

logger = logging.getLogger(__name__)


def build_scanner(settings: Settings):
    if settings.scan_engine == "mock":
        return MockScanner()
    return NmapScanner(settings=settings)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    event_bus = EventBus()
    store = ScanStore()
    scanner = build_scanner(settings)
    cve_service = CveEnrichmentService()

    metrics = MetricsCollector()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.started_at = datetime.now(UTC)
        app.state.event_bus = event_bus
        app.state.scan_store = store
        app.state.metrics = metrics
        app.state.scan_manager = ScanManager(
            store=store,
            event_bus=event_bus,
            scanner=scanner,
            cve_service=cve_service,
            settings=settings,
            metrics=metrics,
        )
        logger.info(
            "app_started",
            extra={
                "environment": settings.environment,
                "scan_engine": settings.scan_engine,
                "allowed_origins": settings.allowed_origins,
            },
        )
        yield
        logger.info("app_stopped", extra={"environment": settings.environment})

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Safe Nmap-backed vulnerability scanning API for the Aegis dashboard.",
        lifespan=lifespan,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(root_router)
    app.include_router(v1_router, prefix="/v1")
    app.include_router(v1_router, include_in_schema=False)
    app.include_router(websocket_router, prefix="/v1")
    app.include_router(websocket_router, include_in_schema=False)
    return app


app = create_app()

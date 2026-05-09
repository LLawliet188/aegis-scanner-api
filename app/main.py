from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import Settings, get_settings
from app.services.cve_service import CveEnrichmentService
from app.services.event_bus import EventBus
from app.services.mock_scanner import MockScanner
from app.services.nmap_runner import NmapScanner
from app.services.scan_manager import ScanManager
from app.services.scan_store import ScanStore
from app.websocket.routes import router as websocket_router


def build_scanner(settings: Settings):
    if settings.scan_engine == "mock":
        return MockScanner()
    return NmapScanner(settings=settings)


def create_app() -> FastAPI:
    settings = get_settings()
    event_bus = EventBus()
    store = ScanStore()
    scanner = build_scanner(settings)
    cve_service = CveEnrichmentService()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.event_bus = event_bus
        app.state.scan_store = store
        app.state.scan_manager = ScanManager(
            store=store,
            event_bus=event_bus,
            scanner=scanner,
            cve_service=cve_service,
            settings=settings,
        )
        yield

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Safe Nmap-backed vulnerability scanning API for the Aegis dashboard.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.include_router(websocket_router)
    return app


app = create_app()


from fastapi import APIRouter, Request


router = APIRouter(tags=["root"])


@router.get("/")
async def root(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "health": "/v1/health",
        "docs": "/docs",
    }

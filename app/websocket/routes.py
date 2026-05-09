from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.services.errors import ScanNotFoundError

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/scan/{scan_id}")
async def scan_events(websocket: WebSocket, scan_id: str) -> None:
    await websocket.accept()
    manager = websocket.app.state.scan_manager
    event_bus = websocket.app.state.event_bus

    try:
        await manager.get_scan(scan_id)
    except ScanNotFoundError:
        await websocket.send_json({"type": "error", "scan_id": scan_id, "message": "Scan not found."})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        async for event in event_bus.subscribe(scan_id):
            await websocket.send_json(event.model_dump(mode="json"))
    except WebSocketDisconnect:
        return


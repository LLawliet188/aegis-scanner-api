import asyncio
from datetime import UTC, datetime
from typing import Awaitable, Callable

from app.models.scan import HostFinding, PortFinding, ScanRequest, ScanResult, Vulnerability

EmitCallback = Callable[[str, str, int | None, dict | None], Awaitable[None]]


class MockScanner:
    async def run(self, scan_id: str, request: ScanRequest, emit: EmitCallback) -> ScanResult:
        started_at = datetime.now(UTC)
        await emit("log", f"Preparing safe mock scan for {request.target}", 5, None)
        await asyncio.sleep(0.05)
        await emit("progress", "Resolving target and validating scan profile", 20, None)
        await asyncio.sleep(0.05)
        await emit("log", "Starting service detection pass", 35, None)
        await asyncio.sleep(0.05)
        await emit("progress", "Parsing scan results", 75, None)
        await asyncio.sleep(0.05)

        host = HostFinding(
            address=request.target,
            hostname="localhost" if request.target in {"127.0.0.1", "localhost"} else None,
            state="up",
            ports=[
                PortFinding(port=22, state="open", service="ssh", product="OpenSSH", version="8.x"),
                PortFinding(port=8000, state="open", service="http", product="Uvicorn", version="0.x"),
            ],
        )
        vulnerability = Vulnerability(
            id="AEGIS-DEMO-OPEN-SSH",
            title="SSH service exposed",
            severity="low",
            description="SSH is reachable. Verify key-only auth, patching, and access restrictions.",
            host=request.target,
            port=22,
            service="ssh",
            evidence="Port 22/tcp open",
        )

        finished_at = datetime.now(UTC)
        return ScanResult(
            scan_id=scan_id,
            target=request.target,
            started_at=started_at,
            finished_at=finished_at,
            command_profile="mock",
            hosts=[host],
            vulnerabilities=[vulnerability],
            summary={
                "hosts_total": 1,
                "hosts_up": 1,
                "open_ports": 2,
                "vulnerabilities": 1,
            },
        )


import asyncio
import logging
import os
import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Awaitable, Callable

from app.core.config import Settings
from app.models.scan import ScanRequest, ScanResult
from app.services.errors import ScannerExecutionError, ScannerUnavailableError
from app.utils.nmap_resolver import NMAP_NOT_INSTALLED_MESSAGE, get_nmap_path
from app.utils.nmap_parser import parse_nmap_xml

EmitCallback = Callable[[str, str, int | None, dict | None], Awaitable[None]]
PROGRESS_RE = re.compile(r"About\s+([0-9.]+)%\s+done", re.IGNORECASE)
logger = logging.getLogger(__name__)


class NmapScanner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def run(self, scan_id: str, request: ScanRequest, emit: EmitCallback) -> ScanResult:
        try:
            nmap_executable = get_nmap_path()
        except RuntimeError as exc:
            logger.error("nmap_unavailable", extra={"scan_id": scan_id, "target": request.target})
            raise ScannerUnavailableError(NMAP_NOT_INSTALLED_MESSAGE) from exc

        started_at = datetime.now(UTC)
        with tempfile.TemporaryDirectory(prefix="aegis-nmap-") as tmpdir:
            output_path = Path(tmpdir) / f"{scan_id}.xml"
            command = self._build_command(request, output_path, nmap_executable)
            await emit("log", f"Starting Nmap scan for {request.target}", 5, {"profile": self._profile_name(request)})
            logger.info(
                "nmap_scan_started",
                extra={"scan_id": scan_id, "target": request.target, "nmap_path": nmap_executable},
            )
            if request.options.os_detection and not self.settings.enable_os_detection:
                await emit("log", "OS detection requested but disabled by server policy.", None, None)
            if request.options.vuln_scripts and not self.settings.enable_vuln_scripts:
                await emit("log", "Vulnerability scripts requested but disabled by server policy.", None, None)
            await emit("log", self._summarize_command(command), None, None)
            logger.info("nmap_command_built", extra={"scan_id": scan_id, "command": self._summarize_command(command)})

            process_options = {}
            if os.name == "nt":
                process_options["creationflags"] = subprocess.CREATE_NO_WINDOW

            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    **process_options,
                )
            except OSError as exc:
                logger.exception("nmap_start_failed", extra={"scan_id": scan_id, "target": request.target})
                raise ScannerExecutionError(f"Failed to start Nmap: {exc}") from exc

            stdout_lines, stderr_lines = await asyncio.gather(
                self._stream_output(process.stdout, emit, "stdout"),
                self._stream_output(process.stderr, emit, "stderr"),
            )
            return_code = await process.wait()

            if return_code != 0:
                detail = self._tail_error(stderr_lines or stdout_lines)
                message = f"Nmap exited with code {return_code}."
                if detail:
                    message = f"{message} Last output: {detail}"
                logger.error(
                    "nmap_scan_failed",
                    extra={"scan_id": scan_id, "target": request.target, "return_code": return_code, "detail": detail},
                )
                raise ScannerExecutionError(message)

            if not output_path.exists():
                raise ScannerExecutionError("Nmap completed but did not produce XML output.")

            await emit("progress", "Parsing Nmap XML results", 95, None)
            xml_text = output_path.read_text(encoding="utf-8", errors="replace")
            result = parse_nmap_xml(
                scan_id=scan_id,
                target=request.target,
                xml_text=xml_text,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                command_profile=self._profile_name(request),
            )
            logger.info(
                "nmap_scan_completed",
                extra={"scan_id": scan_id, "target": request.target, "summary": result.summary},
            )
            return result

    def _build_command(self, request: ScanRequest, output_path: Path, nmap_executable: str) -> list[str]:
        options = request.options
        command = [
            nmap_executable,
            "-oX",
            str(output_path),
            "--stats-every",
            f"{self.settings.nmap_stats_interval_seconds}s",
            "-T3",
            "--max-retries",
            str(self.settings.nmap_max_retries),
            "--host-timeout",
            f"{self.settings.nmap_host_timeout_seconds}s",
        ]

        if options.ports:
            command.extend(["-p", options.ports])
        else:
            command.extend(["--top-ports", str(options.top_ports)])

        if options.service_detection:
            command.extend(["-sV", "--version-light"])

        if options.os_detection:
            if self.settings.enable_os_detection:
                command.extend(["-O", "--osscan-limit"])

        if options.vuln_scripts:
            if self.settings.enable_vuln_scripts:
                command.extend(
                    [
                        "--script",
                        self.settings.nmap_vuln_script_selector,
                        "--script-timeout",
                        f"{self.settings.nmap_script_timeout_seconds}s",
                    ]
                )

        command.append(request.target)
        return command

    def _profile_name(self, request: ScanRequest) -> str:
        enabled = ["service" if request.options.service_detection else "no-service"]
        if request.options.os_detection and self.settings.enable_os_detection:
            enabled.append("os")
        if request.options.vuln_scripts and self.settings.enable_vuln_scripts:
            enabled.append("vuln-scripts")
        return f"{request.options.intensity}:{'+'.join(enabled)}"

    async def _stream_output(self, stream: asyncio.StreamReader | None, emit: EmitCallback, source: str) -> list[str]:
        lines: list[str] = []
        if stream is None:
            return lines
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").strip()
            if not text:
                continue
            lines.append(text)
            progress = self._parse_progress(text)
            if progress is not None:
                await emit("progress", text, min(progress, 94), {"source": source})
                logger.info("nmap_progress", extra={"source": source, "line": text, "progress": min(progress, 94)})
            else:
                await emit("log", text, None, {"source": source})
                logger.info("nmap_output", extra={"source": source, "line": text})
        return lines

    @staticmethod
    def _parse_progress(line: str) -> int | None:
        match = PROGRESS_RE.search(line)
        if not match:
            return None
        return int(float(match.group(1)))

    @staticmethod
    def _summarize_command(command: list[str]) -> str:
        safe_parts = command.copy()
        if "-oX" in safe_parts:
            output_index = safe_parts.index("-oX") + 1
            if output_index < len(safe_parts):
                safe_parts[output_index] = "<xml-output>"
        return "Command profile: " + " ".join(safe_parts)

    @staticmethod
    def _tail_error(lines: list[str]) -> str:
        return " | ".join(lines[-3:])

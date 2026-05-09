import time
from threading import Lock


class MetricsCollector:
    """Thread-safe in-memory counters exposed at /v1/metrics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._requests_total: int = 0
        self._errors_total: int = 0
        self._active_scans: int = 0
        self._scans_total: int = 0
        self._started_at: float = time.monotonic()

    def record_request(self, *, is_error: bool = False) -> None:
        with self._lock:
            self._requests_total += 1
            if is_error:
                self._errors_total += 1

    def scan_started(self) -> None:
        with self._lock:
            self._active_scans += 1
            self._scans_total += 1

    def scan_finished(self) -> None:
        with self._lock:
            self._active_scans = max(0, self._active_scans - 1)

    def snapshot(self) -> dict:
        with self._lock:
            uptime = time.monotonic() - self._started_at
            requests = self._requests_total
            errors = self._errors_total
            return {
                "uptime_seconds": round(uptime, 3),
                "requests_total": requests,
                "errors_total": errors,
                "error_rate": round(errors / max(1, requests), 6),
                "active_scans": self._active_scans,
                "scans_total": self._scans_total,
            }

    def prometheus_text(self) -> str:
        snap = self.snapshot()
        lines = [
            "# HELP aegis_uptime_seconds Seconds since the process started",
            "# TYPE aegis_uptime_seconds gauge",
            f"aegis_uptime_seconds {snap['uptime_seconds']}",
            "# HELP aegis_requests_total Total HTTP requests handled",
            "# TYPE aegis_requests_total counter",
            f"aegis_requests_total {snap['requests_total']}",
            "# HELP aegis_errors_total Total HTTP 5xx responses",
            "# TYPE aegis_errors_total counter",
            f"aegis_errors_total {snap['errors_total']}",
            "# HELP aegis_active_scans Currently running scans",
            "# TYPE aegis_active_scans gauge",
            f"aegis_active_scans {snap['active_scans']}",
            "# HELP aegis_scans_total Total scans submitted since startup",
            "# TYPE aegis_scans_total counter",
            f"aegis_scans_total {snap['scans_total']}",
        ]
        return "\n".join(lines) + "\n"

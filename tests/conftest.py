import os

import pytest
from fastapi.testclient import TestClient

os.environ["AEGIS_SCAN_ENGINE"] = "mock"
os.environ["AEGIS_ALLOWED_TARGET_MODE"] = "private"
os.environ["AEGIS_CORS_ORIGINS"] = "http://localhost:5173,http://127.0.0.1:5173"

from app.core.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


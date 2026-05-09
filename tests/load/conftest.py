"""Shared fixtures for load and resilience tests.

All tests in this package run against a mock scanner so they work without
nmap installed and complete deterministically within milliseconds.
"""
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AEGIS_SCAN_ENGINE", "mock")
os.environ.setdefault("AEGIS_ALLOWED_TARGET_MODE", "private")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

from app.core.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture()
def load_app():
    get_settings.cache_clear()
    return create_app()


@pytest.fixture()
def sync_client(load_app):
    with TestClient(load_app) as client:
        yield client

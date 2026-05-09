import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_allowed_origins_reads_unprefixed_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://aegis.example,https://dashboard.example")

    settings = Settings(_env_file=None)

    assert settings.allowed_origins == ["https://aegis.example", "https://dashboard.example"]


def test_production_rejects_wildcard_cors(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("AEGIS_CORS_ORIGINS", raising=False)

    with pytest.raises(ValidationError, match="Wildcard CORS origins"):
        Settings(_env_file=None, environment="production", allowed_origins=["*"])


def test_production_requires_explicit_allowed_origins(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("AEGIS_CORS_ORIGINS", raising=False)

    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS"):
        Settings(_env_file=None, environment="production")

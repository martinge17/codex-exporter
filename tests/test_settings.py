import pytest

from app.settings import DEFAULT_HOST, DEFAULT_ISSUER_URL, DEFAULT_TOKEN_STATE_PATH, load_settings


def test_load_settings_uses_defaults_for_blank_env(monkeypatch):
    monkeypatch.setenv("HOST", "")
    monkeypatch.setenv("CODEX_TOKEN_STATE_PATH", "")
    monkeypatch.setenv("CODEX_ISSUER_URL", "")

    settings = load_settings()

    assert settings.host == DEFAULT_HOST
    assert settings.token_state_path == DEFAULT_TOKEN_STATE_PATH
    assert settings.issuer_url == DEFAULT_ISSUER_URL


def test_load_settings_reads_env_overrides(monkeypatch):
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "9999")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "5")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "6")
    monkeypatch.setenv("TOKEN_REFRESH_MARGIN_SECONDS", "7")
    monkeypatch.setenv("CODEX_ISSUER_URL", "https://example.com/")
    monkeypatch.setenv("CODEX_ACCESS_TOKEN", " access ")
    monkeypatch.setenv("CODEX_REFRESH_TOKEN", " refresh ")
    monkeypatch.setenv("CODEX_ID_TOKEN", " id ")

    settings = load_settings()

    assert settings.host == "127.0.0.1"
    assert settings.port == 9999
    assert settings.log_level == "debug"
    assert settings.cache_ttl_seconds == 5
    assert settings.request_timeout_seconds == 6
    assert settings.token_refresh_margin_seconds == 7
    assert settings.issuer_url == "https://example.com"
    assert settings.access_token == "access"
    assert settings.refresh_token == "refresh"
    assert settings.id_token == "id"


def test_load_settings_rejects_invalid_integer(monkeypatch):
    monkeypatch.setenv("PORT", "invalid")

    with pytest.raises(ValueError, match="PORT must be an integer"):
        load_settings()

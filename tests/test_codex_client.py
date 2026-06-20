import pytest

from app.codex import AuthError, CodexClient, CodexError, RefreshError, parse_usage
from app.settings import Settings
from app.token_store import TokenState


def test_codex_client_initial_state_prefers_store(jwt, memory_token_store):
    stored = TokenState(access_token="stored", refresh_token="refresh", expires_at=999)
    client = CodexClient(Settings(access_token=jwt({"exp": 1234})), memory_token_store(stored))

    assert client.token_state == stored


def test_codex_client_initial_state_uses_settings_tokens(jwt, memory_token_store):
    client = CodexClient(Settings(access_token=jwt({"exp": 1234}), id_token=jwt({"exp": 5678})), memory_token_store())

    assert client.token_state.access_token
    assert client.token_state.expires_at == 1234.0


def test_codex_client_update_token_state_saves_tokens(jwt, memory_token_store):
    store = memory_token_store()
    client = CodexClient(Settings(), store)

    client._update_token_state({"access_token": jwt({"exp": 2000}), "refresh_token": "refresh"})

    assert client.token_state.refresh_token == "refresh"
    assert client.token_state.expires_at == 2000.0
    assert store.saved == client.token_state


def test_codex_client_update_token_state_requires_access_token(memory_token_store):
    client = CodexClient(Settings(), memory_token_store())

    with pytest.raises(RefreshError, match="missing access token"):
        client._update_token_state({})


@pytest.mark.asyncio
async def test_fetch_usage_retries_after_auth_error(memory_token_store):
    client = CodexClient(Settings(), memory_token_store())
    calls = 0
    refreshed = False

    async def fetch_current():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise AuthError("expired")
        return parse_usage({"plan_type": "plus"})

    async def refresh():
        nonlocal refreshed
        refreshed = True

    client.ensure_token = refresh
    client.refresh_or_device_auth = refresh
    client._fetch_usage_with_current_token = fetch_current

    usage = await client.fetch_usage()

    assert usage.plan_type == "plus"
    assert refreshed is True
    assert calls == 2


@pytest.mark.asyncio
async def test_fetch_usage_with_current_token_success_and_fallback(monkeypatch, json_response, memory_token_store, patch_async_client):
    calls = []

    def handler(method, url, **_kwargs):
        calls.append((method, url))
        if url == "https://primary.example/usage":
            return json_response(404, {"error": "missing"})
        return json_response(200, {"plan_type": "plus"})

    patch_async_client(monkeypatch, handler)
    client = CodexClient(
        Settings(usage_url="https://primary.example/usage", usage_fallback_url="https://fallback.example/usage"),
        memory_token_store(TokenState(access_token="access")),
    )

    usage = await client._fetch_usage_with_current_token()

    assert usage.plan_type == "plus"
    assert calls == [("GET", "https://primary.example/usage"), ("GET", "https://fallback.example/usage")]
    assert client.auth_state == 1


@pytest.mark.asyncio
async def test_fetch_usage_with_current_token_errors(monkeypatch, json_response, memory_token_store, patch_async_client):
    patch_async_client(monkeypatch, lambda *_args, **_kwargs: json_response(401, {}))
    client = CodexClient(Settings(), memory_token_store(TokenState(access_token="access")))

    with pytest.raises(AuthError):
        await client._fetch_usage_with_current_token()
    assert client.auth_state == 0

    patch_async_client(monkeypatch, lambda *_args, **_kwargs: json_response(500, {}))
    with pytest.raises(CodexError, match="HTTP 500"):
        await client._fetch_usage_with_current_token()


@pytest.mark.asyncio
async def test_refresh_token_locked_success(monkeypatch, jwt, json_response, memory_token_store, patch_async_client):
    store = memory_token_store()
    client = CodexClient(Settings(), store)
    client.token_state = TokenState(refresh_token="refresh")
    patch_async_client(monkeypatch, lambda *_args, **_kwargs: json_response(200, {"access_token": jwt({"exp": 3000})}))

    await client._refresh_token_locked()

    assert client.auth_state == 1
    assert client.last_refresh_at > 0
    assert store.saved == client.token_state

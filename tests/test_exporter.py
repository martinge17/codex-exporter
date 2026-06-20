import pytest

from app.codex import CodexError, CodexUsage, CodexWindow, DeviceAuthError, RefreshError
from app.exporter import METRICS_MEDIA_TYPE, ExporterState
from app.settings import Settings


class FakeClient:
    auth_state = 1
    last_refresh_at = 0.0

    def __init__(self, usage=None, exc=None, auth_exc=None):
        self.usage = usage or CodexUsage(plan_type="plus", windows=[], captured_at=1)
        self.exc = exc
        self.auth_exc = auth_exc
        self.fetch_calls = 0

    async def fetch_usage(self):
        self.fetch_calls += 1
        if self.exc is not None:
            raise self.exc
        return self.usage

    async def ensure_token(self):
        if self.auth_exc is not None:
            raise self.auth_exc


@pytest.mark.asyncio
async def test_exporter_refresh_usage_success_updates_cache():
    usage = CodexUsage(
        plan_type="plus",
        windows=[CodexWindow(quota="five_hour", used_percent=10, reset_at=100, window_seconds=18000)],
        captured_at=1,
    )
    state = ExporterState(FakeClient(usage=usage), Settings())

    await state.refresh_usage()

    assert state.cached_usage == usage
    assert state.cached_at > 0
    assert state.last_success_at > 0


@pytest.mark.asyncio
async def test_exporter_refresh_usage_records_errors():
    auth_state = ExporterState(FakeClient(exc=RefreshError("refresh failed")), Settings())
    scrape_state = ExporterState(FakeClient(exc=CodexError("upstream failed")), Settings())

    await auth_state.refresh_usage()
    await scrape_state.refresh_usage()

    assert auth_state.refresh_errors["refresh_failed"] == 1
    assert scrape_state.scrape_errors["error"] == 1


@pytest.mark.asyncio
async def test_exporter_startup_auth_records_errors():
    auth_state = ExporterState(FakeClient(auth_exc=DeviceAuthError("auth failed")), Settings())
    scrape_state = ExporterState(FakeClient(auth_exc=CodexError("startup failed")), Settings())

    await auth_state.ensure_auth_on_startup()
    await scrape_state.ensure_auth_on_startup()

    assert auth_state.refresh_errors["device_auth_failed"] == 1
    assert scrape_state.scrape_errors["error"] == 1


@pytest.mark.asyncio
async def test_metrics_response_uses_fresh_cache_without_refresh():
    client = FakeClient()
    state = ExporterState(client, Settings(cache_ttl_seconds=120))
    state.cached_usage = CodexUsage(plan_type="plus", windows=[], captured_at=1)
    state.cached_at = 9999999999

    response = await state.metrics_response()

    assert response.status_code == 200
    assert response.media_type == METRICS_MEDIA_TYPE
    assert b"codex_exporter_up 1" in response.body
    assert client.fetch_calls == 0
    assert state.refresh_task is None

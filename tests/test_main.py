import asyncio
from dataclasses import replace

from app import main
from app.exporter import ExporterState


class BlockingClient:
    auth_state = 3
    last_refresh_at = 0.0

    def __init__(self):
        self.started = asyncio.Event()

    async def fetch_usage(self):
        self.started.set()
        await asyncio.sleep(60)


def test_metrics_returns_while_auth_refresh_is_pending():
    asyncio.run(_check_metrics_returns_while_auth_refresh_is_pending())


def test_lifespan_keeps_and_cleans_background_tasks(monkeypatch):
    asyncio.run(_check_lifespan_keeps_and_cleans_background_tasks(monkeypatch))


async def _check_metrics_returns_while_auth_refresh_is_pending():
    blocking_client = BlockingClient()
    state = ExporterState(blocking_client, replace(main.settings, cache_ttl_seconds=0))

    try:
        response = await asyncio.wait_for(state.metrics_response(), timeout=0.25)
        await asyncio.wait_for(blocking_client.started.wait(), timeout=0.25)
        second_response = await asyncio.wait_for(state.metrics_response(), timeout=0.25)
    finally:
        await state.shutdown()

    assert response.status_code == 200
    assert second_response.status_code == 200
    assert b"codex_exporter_up 0" in response.body
    assert b"codex_exporter_auth_state 3" in response.body


async def _check_lifespan_keeps_and_cleans_background_tasks(monkeypatch):
    startup_started = asyncio.Event()
    refresh_started = asyncio.Event()

    async def wait_forever(started):
        started.set()
        await asyncio.sleep(60)

    class FakeExporterState:
        def __init__(self):
            self.refresh_task = None

        async def ensure_auth_on_startup(self):
            await wait_forever(startup_started)

        async def shutdown(self, startup_task):
            startup_task.cancel()
            tasks = [startup_task]
            if self.refresh_task is not None:
                self.refresh_task.cancel()
                tasks.append(self.refresh_task)
            await asyncio.gather(*tasks, return_exceptions=True)
            self.refresh_task = None

    fake_state = FakeExporterState()

    monkeypatch.setattr(main, "exporter_state", fake_state)

    async with main.lifespan(main.app):
        fake_state.refresh_task = asyncio.create_task(wait_forever(refresh_started))
        await asyncio.wait_for(startup_started.wait(), timeout=0.25)
        await asyncio.wait_for(refresh_started.wait(), timeout=0.25)
        assert fake_state.refresh_task is not None
        assert not fake_state.refresh_task.done()

    assert fake_state.refresh_task is None

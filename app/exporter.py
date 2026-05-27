from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter

from fastapi import Response

from .codex import CodexClient, CodexError, CodexUsage, DeviceAuthError, RefreshError
from .metrics import render_metrics
from .settings import Settings

LOG = logging.getLogger("codex_exporter")
METRICS_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"


class ExporterState:
    def __init__(self, client: CodexClient, settings: Settings):
        self.client = client
        self.settings = settings
        self.cache_lock = asyncio.Lock()
        self.cached_usage: CodexUsage | None = None
        self.cached_at = 0.0
        self.last_success_at = 0.0
        self.refresh_task: asyncio.Task[None] | None = None
        self.scrape_errors: Counter[str] = Counter()
        self.refresh_errors: Counter[str] = Counter()

    async def ensure_auth_on_startup(self) -> None:
        try:
            await self.client.ensure_token()
        except (RefreshError, DeviceAuthError) as exc:
            reason = getattr(exc, "reason", "auth_failed")
            self.refresh_errors[reason] += 1
            LOG.warning("Codex startup auth did not complete", extra={"reason": reason})
        except CodexError as exc:
            reason = getattr(exc, "reason", "codex_error")
            self.scrape_errors[reason] += 1
            LOG.warning("Codex startup auth failed", extra={"reason": reason})

    async def metrics_response(self) -> Response:
        now = time.time()
        async with self.cache_lock:
            usage = self.cached_usage
            exporter_up = usage is not None
            cache_fresh = usage is not None and now - self.cached_at < self.settings.cache_ttl_seconds
            if not cache_fresh and (self.refresh_task is None or self.refresh_task.done()):
                self.refresh_task = asyncio.create_task(self.refresh_usage())
            body = self.render_current_metrics(usage, exporter_up=exporter_up)
        return Response(body, media_type=METRICS_MEDIA_TYPE)

    async def refresh_usage(self) -> None:
        try:
            usage = await self.client.fetch_usage()
            now = time.time()
            async with self.cache_lock:
                self.cached_usage = usage
                self.cached_at = now
                self.last_success_at = now
        except (RefreshError, DeviceAuthError) as exc:
            reason = getattr(exc, "reason", "auth_failed")
            async with self.cache_lock:
                self.refresh_errors[reason] += 1
            LOG.warning("Codex auth flow failed", extra={"reason": reason})
        except CodexError as exc:
            reason = getattr(exc, "reason", "codex_error")
            async with self.cache_lock:
                self.scrape_errors[reason] += 1
            LOG.warning("Codex usage scrape failed", extra={"reason": reason})

    async def shutdown(self, startup_task: asyncio.Task[None] | None = None) -> None:
        tasks = []
        if startup_task is not None and not startup_task.done():
            startup_task.cancel()
            tasks.append(startup_task)
        if self.refresh_task is not None and not self.refresh_task.done():
            self.refresh_task.cancel()
            tasks.append(self.refresh_task)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.refresh_task = None

    def render_current_metrics(self, usage: CodexUsage | None, *, exporter_up: bool) -> str:
        return render_metrics(
            usage,
            exporter_up=exporter_up,
            auth_state=self.client.auth_state,
            last_success_at=self.last_success_at,
            last_refresh_at=self.client.last_refresh_at,
            scrape_errors=dict(self.scrape_errors),
            refresh_errors=dict(self.refresh_errors),
        )

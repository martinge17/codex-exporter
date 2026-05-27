from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Response

from .codex import CodexClient
from .exporter import ExporterState
from .settings import load_settings
from .token_store import TokenStore

settings = load_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
LOG = logging.getLogger("codex_exporter")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    LOG.info(
        "Codex exporter auth endpoints configured",
        extra={
            "issuer_url": settings.issuer_url,
            "device_usercode_url": settings.device_usercode_url or f"{settings.issuer_url}/api/accounts/deviceauth/usercode",
            "device_token_url": settings.device_token_url or f"{settings.issuer_url}/api/accounts/deviceauth/token",
            "token_url": settings.token_url,
            "usage_url": settings.usage_url,
        },
    )
    startup_task = asyncio.create_task(exporter_state.ensure_auth_on_startup())
    try:
        yield
    finally:
        await exporter_state.shutdown(startup_task)


app = FastAPI(title="Codex Prometheus Exporter", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
client = CodexClient(settings, TokenStore(settings.token_state_path))
exporter_state = ExporterState(client, settings)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Response:
    return await exporter_state.metrics_response()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, log_level=settings.log_level, proxy_headers=True)

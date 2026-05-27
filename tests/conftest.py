import base64
import json

import httpx
import pytest

import app.codex as codex_module


class MemoryTokenStore:
    def __init__(self, state=None):
        self.state = state
        self.saved = None

    def load(self):
        return self.state

    def save(self, state):
        self.saved = state


def _jwt(claims):
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode("utf-8")).decode("ascii").rstrip("=")
    return f"header.{payload}.signature"


def _json_response(status_code, data):
    return httpx.Response(status_code, content=json.dumps(data).encode("utf-8"))


def _patch_async_client(monkeypatch, handler):
    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, **kwargs):
            return handler("GET", url, **kwargs)

        async def post(self, url, **kwargs):
            return handler("POST", url, **kwargs)

    monkeypatch.setattr(codex_module.httpx, "AsyncClient", FakeAsyncClient)


@pytest.fixture
def memory_token_store():
    return MemoryTokenStore


@pytest.fixture
def jwt():
    return _jwt


@pytest.fixture
def json_response():
    return _json_response


@pytest.fixture
def patch_async_client():
    return _patch_async_client

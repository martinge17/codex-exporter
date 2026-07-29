import stat
import time

from app.token_store import TokenState, TokenStore


def test_token_store_round_trip_permissions(tmp_path):
    path = tmp_path / "state" / "tokens.json"
    store = TokenStore(str(path))
    state = TokenState(access_token="access", refresh_token="refresh", id_token="id", expires_at=123.0)

    store.save(state)
    loaded = store.load()

    assert loaded == state
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_token_store_missing_returns_none(tmp_path):
    assert TokenStore(str(tmp_path / "missing.json")).load() is None


def test_token_store_invalid_content_returns_none(tmp_path):
    path = tmp_path / "tokens.json"
    store = TokenStore(str(path))

    path.write_text("not-json", encoding="utf-8")
    assert store.load() is None

    path.write_text("[]", encoding="utf-8")
    assert store.load() is None

    path.write_text('{"expires_at": "invalid"}', encoding="utf-8")
    assert store.load() is None


def test_token_state_valid_access_token_states():
    assert not TokenState().valid_access_token()
    assert TokenState(access_token="access").valid_access_token()
    assert not TokenState(access_token="access", expires_at=time.time() - 1).valid_access_token()
    assert not TokenState(access_token="access", expires_at=time.time() + 10).valid_access_token(20)
    assert TokenState(access_token="access", expires_at=time.time() + 20).valid_access_token(1)

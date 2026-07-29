import httpx
import pytest

from app.codex import CodexError, parse_jwt_expiry, parse_usage, safe_json_response


def test_parse_usage_paid_plan_windows():
    usage = parse_usage(
        {
            "plan_type": "plus",
            "rate_limit": {
                "primary_window": {"used_percent": 25.5, "reset_at": 1000, "limit_window_seconds": 18000},
                "secondary_window": {"used_percent": 11, "reset_at": 2000, "limit_window_seconds": 604800},
            },
            "code_review_rate_limit": {"primary_window": {"used_percent": 2, "reset_at": 3000, "limit_window_seconds": 604800}},
        }
    )

    assert usage.plan_type == "plus"
    assert [w.quota for w in usage.windows] == ["five_hour", "seven_day", "code_review"]
    assert usage.windows[0].used_percent == 25.5
    assert usage.windows[1].window_seconds == 604800


def test_parse_usage_free_primary_as_weekly():
    usage = parse_usage(
        {
            "plan_type": "free",
            "rate_limit": {"primary_window": {"used_percent": "60", "reset_at": "4000", "limit_window_seconds": 604800}},
        }
    )

    assert [w.quota for w in usage.windows] == ["seven_day"]
    assert usage.windows[0].used_percent == 60.0
    assert usage.windows[0].reset_at == 4000


def test_safe_json_response_requires_json_object():
    assert safe_json_response(httpx.Response(200, content=b'{"ok": true}')) == {"ok": True}

    with pytest.raises(CodexError, match="invalid json response"):
        safe_json_response(httpx.Response(200, content=b"not-json"))

    with pytest.raises(CodexError, match="json response is not an object"):
        safe_json_response(httpx.Response(200, content=b"[]"))


def test_safe_json_response_rejects_large_body():
    with pytest.raises(CodexError, match="response too large"):
        safe_json_response(httpx.Response(200, content=b"{" + (b" " * (128 * 1024)) + b"}"))


def test_parse_jwt_expiry(jwt):
    assert parse_jwt_expiry(jwt({"exp": 1234})) == 1234.0
    assert parse_jwt_expiry(jwt({})) == 0.0
    assert parse_jwt_expiry("not-a-jwt") == 0.0
    assert parse_jwt_expiry("header.invalid.signature") == 0.0

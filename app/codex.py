import asyncio
import base64
import json
import logging
import sys
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .settings import Settings
from .token_store import TokenState, TokenStore

LOG = logging.getLogger("codex_exporter.codex")
MAX_RESPONSE_BYTES = 128 * 1024
CODEX_CLI_USER_AGENT = "codex-cli/1.0.0"
EXPORTER_USER_AGENT = "codex-prometheus-exporter/1.0"


class CodexError(Exception):
    reason = "error"


class AuthError(CodexError):
    reason = "unauthorized"


class RefreshError(CodexError):
    reason = "refresh_failed"


class DeviceAuthError(CodexError):
    reason = "device_auth_failed"


@dataclass
class CodexWindow:
    quota: str
    used_percent: float
    reset_at: int
    window_seconds: int


@dataclass
class CodexUsage:
    plan_type: str
    windows: list[CodexWindow]


class CodexClient:
    def __init__(self, settings: Settings, token_store: TokenStore):
        self.settings = settings
        self.token_store = token_store
        self.token_state = self._initial_token_state()
        self.last_refresh_at = 0.0
        self.auth_state = 1 if self.token_state.valid_access_token() else 0
        self._auth_lock = asyncio.Lock()

    def _initial_token_state(self) -> TokenState:
        stored = self.token_store.load()
        if stored is not None and (stored.access_token or stored.refresh_token):
            return stored
        return TokenState(
            access_token=self.settings.access_token,
            refresh_token=self.settings.refresh_token,
            id_token=self.settings.id_token,
            expires_at=parse_jwt_expiry(self.settings.access_token) or parse_jwt_expiry(self.settings.id_token),
        )

    async def fetch_usage(self) -> CodexUsage:
        await self.ensure_token()
        try:
            return await self._fetch_usage_with_current_token()
        except AuthError:
            await self.refresh_or_device_auth()
            return await self._fetch_usage_with_current_token()

    async def ensure_token(self) -> None:
        async with self._auth_lock:
            if self.token_state.valid_access_token(self.settings.token_refresh_margin_seconds):
                self.auth_state = 1
                return
            if self.token_state.refresh_token:
                try:
                    await self._refresh_token_locked()
                    return
                except RefreshError as exc:
                    LOG.warning("Codex token refresh failed; starting device auth", extra={"reason": exc.reason})
            await self._device_auth_locked()

    async def refresh_or_device_auth(self) -> None:
        async with self._auth_lock:
            if self.token_state.refresh_token:
                try:
                    await self._refresh_token_locked()
                    return
                except RefreshError:
                    LOG.warning("Codex refresh after auth error failed; starting device auth")
            await self._device_auth_locked()

    async def _fetch_usage_with_current_token(self) -> CodexUsage:
        headers = {
            "Authorization": f"Bearer {self.token_state.access_token}",
            "Accept": "application/json",
            "User-Agent": EXPORTER_USER_AGENT,
        }
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, follow_redirects=False) as client:
            resp = await client.get(self.settings.usage_url, headers=headers)
            if resp.status_code == 404 and self.settings.usage_fallback_url:
                resp = await client.get(self.settings.usage_fallback_url, headers=headers)
            if resp.status_code in (401, 403):
                self.auth_state = 0
                raise AuthError("codex usage unauthorized")
            if resp.status_code >= 400:
                raise CodexError(f"codex usage returned HTTP {resp.status_code}")
            data = safe_json_response(resp)
        self.auth_state = 1
        return parse_usage(data)

    async def _refresh_token_locked(self) -> None:
        form = {
            "grant_type": "refresh_token",
            "refresh_token": self.token_state.refresh_token,
            "client_id": self.settings.client_id,
            "scope": self.settings.scope,
        }
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, follow_redirects=False) as client:
            resp = await client.post(self.settings.token_url, data=form, headers={"User-Agent": CODEX_CLI_USER_AGENT})
        if resp.status_code != 200:
            self.auth_state = 2
            raise RefreshError(f"refresh returned HTTP {resp.status_code}")
        data = safe_json_response(resp)
        self._update_token_state(data)
        self.last_refresh_at = time.time()
        self.auth_state = 1
        LOG.info("Codex OAuth token refreshed")

    async def _device_auth_locked(self) -> None:
        device = await self._request_device_code()
        verification_uri = device.get("verification_uri_complete") or device.get("verification_uri") or device.get("verification_url")
        user_code = device.get("user_code") or ""
        device_auth_id = device.get("device_auth_id") or device.get("device_code") or ""
        interval = int(device.get("interval") or 5)
        expires_in = int(device.get("expires_in") or 900)
        if not device_auth_id or not verification_uri or not user_code:
            self.auth_state = 2
            raise DeviceAuthError("device auth response missing required fields")

        self.auth_state = 3
        _emit_login_prompt(str(verification_uri), str(user_code), expires_in)
        LOG.warning("Codex login required: open %s and enter code %s; expires in %ss", verification_uri, user_code, expires_in)

        deadline = time.monotonic() + expires_in
        while time.monotonic() < deadline:
            await asyncio.sleep(interval)
            token_data, wait_longer = await self._poll_device_token(device_auth_id, str(user_code))
            if token_data is not None:
                if "authorization_code" in token_data:
                    token_data = await self._exchange_authorization_code(token_data)
                self._update_token_state(token_data)
                self.auth_state = 1
                LOG.info("Codex device login completed")
                return
            if wait_longer:
                interval += 5
        self.auth_state = 2
        raise DeviceAuthError("device auth expired")

    async def _request_device_code(self) -> dict[str, Any]:
        url = self.settings.device_usercode_url or f"{self.settings.issuer_url}/api/accounts/deviceauth/usercode"
        LOG.info("Requesting Codex device user code", extra={"url": url})
        payload = {"client_id": self.settings.client_id}
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, follow_redirects=False) as client:
            resp = await client.post(url, json=payload, headers={"User-Agent": CODEX_CLI_USER_AGENT})
        if resp.status_code != 200:
            raise DeviceAuthError(f"device code returned HTTP {resp.status_code}")
        data = safe_json_response(resp)
        data.setdefault("verification_url", f"{self.settings.issuer_url}/codex/device")
        data.setdefault("expires_in", 900)
        return data

    async def _poll_device_token(self, device_auth_id: str, user_code: str) -> tuple[dict[str, Any] | None, bool]:
        url = self.settings.device_token_url or f"{self.settings.issuer_url}/api/accounts/deviceauth/token"
        payload = {"device_auth_id": device_auth_id, "user_code": user_code}
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, follow_redirects=False) as client:
            resp = await client.post(url, json=payload, headers={"User-Agent": CODEX_CLI_USER_AGENT})
        data = safe_json_response(resp) if resp.content else {}
        if resp.status_code == 200:
            return data, False
        if resp.status_code in (403, 404):
            return None, False
        err = str(data.get("error") or resp.status_code)
        raise DeviceAuthError(f"device token polling failed: {err}")

    async def _exchange_authorization_code(self, code_data: dict[str, Any]) -> dict[str, Any]:
        authorization_code = str(code_data.get("authorization_code") or "")
        code_verifier = str(code_data.get("code_verifier") or "")
        if not authorization_code or not code_verifier:
            raise DeviceAuthError("device token response missing authorization code or verifier")
        redirect_uri = f"{self.settings.issuer_url}/deviceauth/callback"
        form = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "client_id": self.settings.client_id,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, follow_redirects=False) as client:
            resp = await client.post(
                self.settings.token_url,
                data=form,
                headers={"User-Agent": CODEX_CLI_USER_AGENT},
            )
        if resp.status_code != 200:
            raise DeviceAuthError(f"authorization code exchange returned HTTP {resp.status_code}")
        return safe_json_response(resp)

    def _update_token_state(self, data: dict[str, Any]) -> None:
        access_token = str(data.get("access_token") or "")
        if not access_token:
            raise RefreshError("token response missing access token")
        refresh_token = str(data.get("refresh_token") or self.token_state.refresh_token or "")
        id_token = str(data.get("id_token") or self.token_state.id_token or "")
        expires_in = int(data.get("expires_in") or 0)
        expires_at = time.time() + expires_in if expires_in > 0 else parse_jwt_expiry(access_token) or parse_jwt_expiry(id_token)
        self.token_state = TokenState(
            access_token=access_token,
            refresh_token=refresh_token,
            id_token=id_token,
            expires_at=expires_at or 0.0,
        )
        self.token_store.save(self.token_state)


def safe_json_response(resp: httpx.Response) -> dict[str, Any]:
    body = resp.content[: MAX_RESPONSE_BYTES + 1]
    if len(body) > MAX_RESPONSE_BYTES:
        raise CodexError("response too large")
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CodexError("invalid json response") from exc
    if not isinstance(parsed, dict):
        raise CodexError("json response is not an object")
    return parsed


def parse_usage(data: dict[str, Any]) -> CodexUsage:
    plan = str(data.get("plan_type") or "unknown")
    rate_limit = data.get("rate_limit") if isinstance(data.get("rate_limit"), dict) else {}
    code_review_limit = data.get("code_review_rate_limit") if isinstance(data.get("code_review_rate_limit"), dict) else {}
    windows: list[CodexWindow] = []
    primary = rate_limit.get("primary_window") if isinstance(rate_limit.get("primary_window"), dict) else None
    secondary = rate_limit.get("secondary_window") if isinstance(rate_limit.get("secondary_window"), dict) else None
    if primary:
        quota = "five_hour" if secondary or _window_seconds(primary) <= 5 * 60 * 60 else "seven_day"
        windows.append(_parse_window(quota, primary))
    if secondary:
        windows.append(_parse_window("seven_day", secondary))
    review = code_review_limit.get("primary_window") if isinstance(code_review_limit.get("primary_window"), dict) else None
    if review:
        windows.append(_parse_window("code_review", review))
    return CodexUsage(plan_type=plan, windows=windows)


def _window_seconds(window: dict[str, Any]) -> int:
    try:
        return int(window.get("limit_window_seconds") or 0)
    except TypeError, ValueError:
        return 0


def _parse_window(quota: str, window: dict[str, Any]) -> CodexWindow:
    return CodexWindow(
        quota=quota,
        used_percent=_float(window.get("used_percent")),
        reset_at=_int(window.get("reset_at")),
        window_seconds=_window_seconds(window),
    )


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except TypeError, ValueError:
        return 0.0


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except TypeError, ValueError:
        return 0


def _emit_login_prompt(verification_uri: str, user_code: str, expires_in: int) -> None:
    msg = f"\nCodex login required\nOpen: {verification_uri}\nCode: {user_code}\nExpires in: {expires_in} seconds\n"
    print(msg, file=sys.stderr, flush=True)


def parse_jwt_expiry(token: str) -> float:
    if not token or token.count(".") != 2:
        return 0.0
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
        claims = json.loads(decoded.decode("utf-8"))
        return float(claims.get("exp") or 0)
    except ValueError:
        return 0.0

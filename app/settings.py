import os
from dataclasses import dataclass

DEFAULT_HOST = "0.0.0.0"
DEFAULT_TOKEN_STATE_PATH = "/data/codex-token-state.json"
DEFAULT_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
DEFAULT_SCOPE = "openid profile email offline_access api.connectors.read api.connectors.invoke"
DEFAULT_ISSUER_URL = "https://auth.openai.com"
DEFAULT_TOKEN_URL = f"{DEFAULT_ISSUER_URL}/oauth/token"
DEFAULT_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
DEFAULT_USAGE_FALLBACK_URL = "https://chatgpt.com/api/codex/usage"


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class Settings:
    host: str = DEFAULT_HOST
    port: int = 9212
    log_level: str = "info"
    cache_ttl_seconds: int = 120
    request_timeout_seconds: int = 15
    token_refresh_margin_seconds: int = 300
    token_state_path: str = DEFAULT_TOKEN_STATE_PATH
    client_id: str = DEFAULT_CLIENT_ID
    scope: str = DEFAULT_SCOPE
    issuer_url: str = DEFAULT_ISSUER_URL
    device_usercode_url: str = ""
    device_token_url: str = ""
    token_url: str = DEFAULT_TOKEN_URL
    usage_url: str = DEFAULT_USAGE_URL
    usage_fallback_url: str = DEFAULT_USAGE_FALLBACK_URL
    access_token: str = ""
    refresh_token: str = ""
    id_token: str = ""


def load_settings() -> Settings:
    return Settings(
        host=os.getenv("HOST", DEFAULT_HOST).strip() or DEFAULT_HOST,
        port=_int_env("PORT", 9212),
        log_level=os.getenv("LOG_LEVEL", "info").strip().lower() or "info",
        cache_ttl_seconds=_int_env("CACHE_TTL_SECONDS", 120),
        request_timeout_seconds=_int_env("REQUEST_TIMEOUT_SECONDS", 15),
        token_refresh_margin_seconds=_int_env("TOKEN_REFRESH_MARGIN_SECONDS", 300),
        token_state_path=os.getenv("CODEX_TOKEN_STATE_PATH", DEFAULT_TOKEN_STATE_PATH).strip() or DEFAULT_TOKEN_STATE_PATH,
        client_id=os.getenv("CODEX_CLIENT_ID", DEFAULT_CLIENT_ID).strip() or DEFAULT_CLIENT_ID,
        scope=os.getenv("CODEX_SCOPE", DEFAULT_SCOPE).strip() or DEFAULT_SCOPE,
        issuer_url=os.getenv("CODEX_ISSUER_URL", DEFAULT_ISSUER_URL).strip().rstrip("/") or DEFAULT_ISSUER_URL,
        device_usercode_url=os.getenv("CODEX_DEVICE_USERCODE_URL", "").strip(),
        device_token_url=os.getenv("CODEX_DEVICE_TOKEN_URL", "").strip(),
        token_url=os.getenv("CODEX_TOKEN_URL", DEFAULT_TOKEN_URL).strip() or DEFAULT_TOKEN_URL,
        usage_url=os.getenv("CODEX_USAGE_URL", DEFAULT_USAGE_URL).strip() or DEFAULT_USAGE_URL,
        usage_fallback_url=os.getenv("CODEX_USAGE_FALLBACK_URL", DEFAULT_USAGE_FALLBACK_URL).strip() or DEFAULT_USAGE_FALLBACK_URL,
        access_token=os.getenv("CODEX_ACCESS_TOKEN", "").strip(),
        refresh_token=os.getenv("CODEX_REFRESH_TOKEN", "").strip(),
        id_token=os.getenv("CODEX_ID_TOKEN", "").strip(),
    )

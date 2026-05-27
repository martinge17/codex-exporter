from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TokenState:
    access_token: str = ""
    refresh_token: str = ""
    id_token: str = ""
    expires_at: float = 0.0

    def valid_access_token(self, margin_seconds: int = 0) -> bool:
        if not self.access_token:
            return False
        if self.expires_at <= 0:
            return True
        return time.time() + margin_seconds < self.expires_at

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenState:
        return cls(
            access_token=str(data.get("access_token") or ""),
            refresh_token=str(data.get("refresh_token") or ""),
            id_token=str(data.get("id_token") or ""),
            expires_at=float(data.get("expires_at") or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "id_token": self.id_token,
            "expires_at": self.expires_at,
        }


class TokenStore:
    def __init__(self, path: str):
        self.path = Path(path)

    def load(self) -> TokenState | None:
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return None
        except (OSError, TypeError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        try:
            return TokenState.from_dict(data)
        except (TypeError, ValueError):
            return None

    def save(self, state: TokenState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, tmp_name = tempfile.mkstemp(prefix=self.path.name + ".", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(state.to_dict(), fh, separators=(",", ":"))
                fh.write("\n")
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, self.path)
        except Exception:
            with suppress(OSError):
                os.unlink(tmp_name)
            raise

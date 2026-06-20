from __future__ import annotations

import math
from collections import defaultdict

from .codex import CodexUsage


def render_metrics(
    usage: CodexUsage | None,
    *,
    exporter_up: bool,
    auth_state: int,
    last_success_at: float,
    last_refresh_at: float,
    scrape_errors: dict[str, int] | None = None,
    refresh_errors: dict[str, int] | None = None,
) -> str:
    scrape_errors = scrape_errors or {}
    refresh_errors = refresh_errors or {}
    lines = [
        "# HELP codex_exporter_up 1 if the latest upstream usage scrape succeeded or stale cached data is available, 0 otherwise.",
        "# TYPE codex_exporter_up gauge",
        f"codex_exporter_up {1 if exporter_up else 0}",
        "# HELP codex_exporter_auth_state Authentication state: 0 unauthenticated, 1 authenticated, 2 auth failed, 3 device auth pending.",
        "# TYPE codex_exporter_auth_state gauge",
        f"codex_exporter_auth_state {auth_state}",
        "# HELP codex_exporter_last_success_timestamp_seconds Unix timestamp of the last successful Codex usage scrape.",
        "# TYPE codex_exporter_last_success_timestamp_seconds gauge",
        f"codex_exporter_last_success_timestamp_seconds {_num(last_success_at)}",
        "# HELP codex_exporter_last_refresh_timestamp_seconds Unix timestamp of the last successful OAuth token refresh.",
        "# TYPE codex_exporter_last_refresh_timestamp_seconds gauge",
        f"codex_exporter_last_refresh_timestamp_seconds {_num(last_refresh_at)}",
        "# HELP codex_exporter_scrape_errors_total Total Codex usage scrape errors by reason.",
        "# TYPE codex_exporter_scrape_errors_total counter",
    ]
    for reason, count in sorted(scrape_errors.items()):
        lines.append(f'codex_exporter_scrape_errors_total{{reason="{_label(reason)}"}} {int(count)}')
    lines.extend(
        [
            "# HELP codex_exporter_token_refresh_errors_total Total OAuth token refresh or login errors by reason.",
            "# TYPE codex_exporter_token_refresh_errors_total counter",
        ]
    )
    for reason, count in sorted(refresh_errors.items()):
        lines.append(f'codex_exporter_token_refresh_errors_total{{reason="{_label(reason)}"}} {int(count)}')

    lines.extend(
        [
            "# HELP codex_usage_used_percent Codex usage consumed as a percentage of the quota window.",
            "# TYPE codex_usage_used_percent gauge",
            "# HELP codex_usage_remaining_percent Codex usage remaining as a percentage of the quota window.",
            "# TYPE codex_usage_remaining_percent gauge",
            "# HELP codex_usage_reset_timestamp_seconds Unix timestamp when the Codex quota window resets.",
            "# TYPE codex_usage_reset_timestamp_seconds gauge",
            "# HELP codex_usage_window_seconds Codex quota window size in seconds.",
            "# TYPE codex_usage_window_seconds gauge",
        ]
    )
    if usage is not None:
        plan = _label(usage.plan_type)
        seen = defaultdict(int)
        for window in usage.windows:
            seen[window.quota] += 1
            quota = _label(window.quota)
            labels = f'quota="{quota}",plan="{plan}"'
            used = max(0.0, min(100.0, window.used_percent))
            remaining = max(0.0, 100.0 - used)
            lines.append(f"codex_usage_used_percent{{{labels}}} {_num(used)}")
            lines.append(f"codex_usage_remaining_percent{{{labels}}} {_num(remaining)}")
            lines.append(f"codex_usage_reset_timestamp_seconds{{{labels}}} {int(window.reset_at)}")
            lines.append(f"codex_usage_window_seconds{{{labels}}} {int(window.window_seconds)}")

    lines.append("")
    return "\n".join(lines)


def _label(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _num(value: float) -> str:
    if not math.isfinite(float(value)):
        return "0"
    return f"{float(value):.6f}".rstrip("0").rstrip(".")

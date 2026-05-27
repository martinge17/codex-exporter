from app.codex import CodexUsage, CodexWindow
from app.metrics import empty_metrics, now, render_metrics


def test_render_metrics_escapes_labels_and_remaining():
    body = render_metrics(
        CodexUsage(
            plan_type='plus"team',
            captured_at=10,
            windows=[CodexWindow(quota="five_hour", used_percent=33.25, reset_at=123, window_seconds=18000)],
        ),
        exporter_up=True,
        auth_state=1,
        last_success_at=20,
        last_refresh_at=30,
        scrape_errors={"network": 2},
        refresh_errors={"refresh_failed": 1},
    )

    assert "codex_exporter_up 1" in body
    assert 'codex_exporter_scrape_errors_total{reason="network"} 2' in body
    assert 'plan="plus\\"team"' in body
    assert 'codex_usage_used_percent{quota="five_hour",plan="plus\\"team"} 33.25' in body
    assert 'codex_usage_remaining_percent{quota="five_hour",plan="plus\\"team"} 66.75' in body


def test_render_metrics_clamps_percentages():
    body = render_metrics(
        CodexUsage(
            plan_type="plus",
            captured_at=10,
            windows=[CodexWindow(quota="five_hour", used_percent=150, reset_at=123, window_seconds=18000)],
        ),
        exporter_up=True,
        auth_state=1,
        last_success_at=20,
        last_refresh_at=30,
    )

    assert 'codex_usage_used_percent{quota="five_hour",plan="plus"} 100' in body
    assert 'codex_usage_remaining_percent{quota="five_hour",plan="plus"} 0' in body


def test_empty_metrics_and_non_finite_timestamps():
    body = render_metrics(None, exporter_up=False, auth_state=0, last_success_at=float("nan"), last_refresh_at=float("inf"))

    assert "codex_exporter_up 0" in empty_metrics()
    assert "codex_exporter_last_success_timestamp_seconds 0" in body
    assert "codex_exporter_last_refresh_timestamp_seconds 0" in body
    assert now() > 0

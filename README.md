# Codex Prometheus Exporter

Small Prometheus exporter for OpenAI Codex subscription usage. It exposes only `/metrics` and `/healthz` on port `9212`.

## Security Model

- Runs as a non-root user in Docker.
- Uses a read-only root filesystem.
- Drops all Linux capabilities.
- Enables `no-new-privileges`.
- Stores OAuth token state only in `/data/codex-token-state.json`.
- Does not log access tokens, refresh tokens, ID tokens, device codes, or usage response bodies.

## First Run

```bash
cp .env.example .env
docker compose up --build
```

On first scrape, or when no valid token state exists, the logs will print a Codex login prompt:

```text
Codex login required: open <verification-url> and enter code <code>; expires in 900s
```

Open the URL, complete login, and the exporter will save rotated tokens to `/data/codex-token-state.json` in the `test-codex` Docker volume.

The device-login implementation follows the official Codex CLI flow:

- `POST https://auth.openai.com/api/accounts/deviceauth/usercode`
- open `https://auth.openai.com/codex/device`
- poll `POST https://auth.openai.com/api/accounts/deviceauth/token`
- exchange the returned authorization code at `POST https://auth.openai.com/oauth/token`

## Network Binding

The default compose file publishes the exporter on the host port from `PORT`, defaulting to `9212`:

```yaml
ports:
  - "${PORT:-9212}:9212"
```

For a local-only deployment, bind explicitly to localhost:

```yaml
ports:
  - "127.0.0.1:9212:9212"
```

For a VPN-only VPS, bind to the VPN interface IP:

```yaml
ports:
  - "10.8.0.10:9212:9212"
```

Also enforce this with the host firewall.

## Prometheus

```yaml
scrape_configs:
  - job_name: codex-exporter
    metrics_path: /metrics
    static_configs:
      - targets:
          - 10.8.0.10:9212
```

## GitHub Actions

This repository includes GitHub Actions workflows under `.github/workflows/`:

- `test.yml` runs separate jobs for Ruff formatting/lint checks, Python tests, coverage, SonarQube analysis, Trivy filesystem/secret scans, and Trivy IaC scans.
- `build.yml` builds and pushes the Docker image to GitHub Container Registry.
- `renovate.yml` runs Renovate against the current GitHub repository.

Required GitHub variables:

- `SONAR_URL` - SonarQube server URL, if SonarQube analysis is enabled.

Required GitHub secrets:

- `SONAR_TOKEN` - token for SonarQube analysis.
- `RENOVATE_TOKEN` - GitHub token used by Renovate.

Renovate rules are in `renovate.json`.

## Local Quality Checks

Install development dependencies:

```bash
make install-dev
```

Format and auto-fix local code before committing:

```bash
make format
```

Run the same core checks used by CI:

```bash
make check
```

## Metrics

- `codex_exporter_up`
- `codex_exporter_auth_state`
- `codex_exporter_last_success_timestamp_seconds`
- `codex_exporter_last_refresh_timestamp_seconds`
- `codex_exporter_scrape_errors_total{reason="..."}`
- `codex_exporter_token_refresh_errors_total{reason="..."}`
- `codex_usage_used_percent{quota="five_hour|seven_day|code_review",plan="..."}`
- `codex_usage_remaining_percent{quota="five_hour|seven_day|code_review",plan="..."}`
- `codex_usage_reset_timestamp_seconds{quota="...",plan="..."}`
- `codex_usage_window_seconds{quota="...",plan="..."}`

`codex_exporter_auth_state` values:

- `0` unauthenticated
- `1` authenticated
- `2` auth failed
- `3` device auth pending

## Notes

This exporter relies on ChatGPT/Codex OAuth-backed internal usage endpoints. They are not a stable public OpenAI API and may change without notice.

# Codex Prometheus Exporter

Small Prometheus exporter for OpenAI Codex subscription usage. It exposes only `/metrics` and `/healthz` on port `9212`.

## Security Model

- Runs as a non-root user in Docker.
- Uses a read-only root filesystem.
- Drops all Linux capabilities.
- Enables `no-new-privileges`.
- Stores OAuth token state only in `/data/codex-token-state.json`.
- Does not log access tokens, refresh tokens, ID tokens, device codes, or usage response bodies.

## Container Images and Releases

Images are published to `ghcr.io/martinge17/codex-exporter` after tests and security scans pass:

- Every published image has a commit-addressable `sha-<12-character-commit>` tag.
- Successful builds from `main` update `edge`.
- A release tag such as `v1.2.3` publishes `1.2.3`, `1.2`, `1`, and `latest`.
- Release tags must use the exact `vMAJOR.MINOR.PATCH` format.

Use an exact version or digest for production deployments. The moving `latest`, major, minor, and `edge` tags are intended for convenient updates.

The Git tag is the source of truth; there is no separate application version file. To publish a release after merging to `main`:

```bash
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
gh release create v1.0.0 --verify-tag --generate-notes
```

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

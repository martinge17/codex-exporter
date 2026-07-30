# Codex Prometheus Exporter

[![CI](https://github.com/martinge17/codex-exporter/actions/workflows/ci.yml/badge.svg)](https://github.com/martinge17/codex-exporter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/martinge17/codex-exporter)](LICENSE)

A small Prometheus exporter for OpenAI Codex subscription usage. It exposes `/metrics` and `/healthz` and has been used in production with Prometheus and Grafana, both personally and in a company.

## Features

- Reports consumed and remaining quota for 5-hour, 7-day, and code-review windows.
- Reports quota reset timestamps and window durations.
- Uses the same OAuth device-code flow as the OpenAI Codex CLI.
- Caches usage data for two minutes by default to avoid unnecessary upstream requests.
- Runs as a non-root user in a minimal Docker image.

## Quick Start

```bash
curl -fsSLO https://github.com/martinge17/codex-exporter/blob/main/docker-compose.yml?raw=true
docker compose up -d
curl http://localhost:9212/metrics
docker compose logs -f codex-exporter
```

The first scrape starts authentication when no valid token is stored. Follow the prompt in the container logs:

```text
Codex login required
Open: <verification-url>
Code: <code>
Expires in: 900 seconds
```

Open the URL and enter the code. Rotated OAuth tokens are then stored in the named volume mounted at `/data`.

## Configuration

No configuration is required for the default deployment. To override settings use the following env variables:


| Variable | Default | Description |
| --- | --- | --- |
| `LOG_LEVEL` | `info` | Application log level. |
| `CACHE_TTL_SECONDS` | `120` | Minimum interval between upstream usage requests. |
| `REQUEST_TIMEOUT_SECONDS` | `15` | Upstream HTTP timeout. |
| `TOKEN_REFRESH_MARGIN_SECONDS` | `300` | Refresh tokens this many seconds before expiry. |
| `CODEX_TOKEN_STATE_PATH` | `/data/codex-token-state.json` | Persistent OAuth token-state path. |

See [`.env.example`](.env.example) for advanced OAuth and endpoint overrides.

## Security

- Runs as the unprivileged user `65532`.
- Drops all Linux capabilities and enables `no-new-privileges`.
- Uses a restricted temporary filesystem and container resource limits.
- Persists OAuth state only in the volume mounted at `/data`.
- Does not log access tokens, refresh tokens, ID tokens, device codes, or usage response bodies.

The metrics endpoint has no authentication or TLS. Bind it only to a trusted interface and enforce access with the host firewall or a reverse proxy.

## Network Binding

The default Compose file publishes port `9212` on every host interface:

```yaml
ports:
  - "9212:9212"
```

For local-only access:

```yaml
ports:
  - "127.0.0.1:9212:9212"
```

For a VPN-only deployment, bind to the VPN interface address:

```yaml
ports:
  - "10.8.0.10:9212:9212"
```

## Prometheus

```yaml
scrape_configs:
  - job_name: codex-exporter
    metrics_path: /metrics
    static_configs:
      - targets:
          - "10.8.0.10:9212"
```

Use `codex-exporter:9212` instead when Prometheus shares a Docker network with the exporter.

## Metrics

| Metric | Description |
| --- | --- |
| `codex_exporter_up` | `1` when current or cached usage data is available. |
| `codex_exporter_auth_state` | Current authentication state. |
| `codex_exporter_last_success_timestamp_seconds` | Last successful usage scrape. |
| `codex_exporter_last_refresh_timestamp_seconds` | Last successful token refresh. |
| `codex_exporter_scrape_errors_total{reason}` | Usage scrape failures by reason. |
| `codex_exporter_token_refresh_errors_total{reason}` | Token refresh and login failures by reason. |
| `codex_usage_used_percent{quota,plan}` | Consumed quota percentage. |
| `codex_usage_remaining_percent{quota,plan}` | Remaining quota percentage. |
| `codex_usage_reset_timestamp_seconds{quota,plan}` | Quota reset time. |
| `codex_usage_window_seconds{quota,plan}` | Quota window duration. |

Authentication states are `0` unauthenticated, `1` authenticated, `2` failed, and `3` device authentication pending.

## Images and Releases

Images are published to `ghcr.io/martinge17/codex-exporter` after tests and security scans pass.
Notable release changes are listed in the [changelog](CHANGELOG.md).

- Every published image receives a commit-addressable `sha-<12-character-commit>` tag.
- Successful `main` builds update `edge`.
- A release such as `v1.2.3` publishes `1.2.3`, `1.2`, `1`, and `latest`.
- Production deployments should use an exact version or digest.

Starting with `v1.1.0`, published images are signed keylessly with Cosign and GitHub Actions OIDC. Install [Cosign](https://docs.sigstore.dev/cosign/system_config/installation/) and verify a release with:

```bash
VERSION=1.1.0

cosign verify \
  --certificate-identity "https://github.com/martinge17/codex-exporter/.github/workflows/ci.yml@refs/tags/v${VERSION}" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  "ghcr.io/martinge17/codex-exporter:${VERSION}"
```

The signature covers the image digest, so it also verifies through the corresponding major, minor, `latest`, and commit tags. The existing `v1.0.0` image predates image signing.

## Limitations

This exporter relies on OAuth-backed internal ChatGPT/Codex usage endpoints. They are not a stable public OpenAI API and may change without notice.

## License

[MIT](LICENSE)

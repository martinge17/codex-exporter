# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-07-30

### Changed

- Use Chainguard distroless Python images for build and runtime stages.
- Allow the default Docker Compose deployment to run without configuration.

### Security

- Sign published container images keylessly with Cosign and GitHub Actions OIDC.
- Verify each signature in CI immediately after publishing.

## [1.0.0] - 2026-07-29

### Added

- Export Codex subscription quota usage, remaining capacity, reset times, and window durations as Prometheus metrics.
- Authenticate through the OpenAI Codex OAuth device-code flow and persist rotated tokens.
- Provide a non-root container deployment with capability dropping and resource limits.
- Test, scan, and publish container images through GitHub Actions.

[Unreleased]: https://github.com/martinge17/codex-exporter/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/martinge17/codex-exporter/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/martinge17/codex-exporter/releases/tag/v1.0.0

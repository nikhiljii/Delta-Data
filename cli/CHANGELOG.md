# Changelog

All notable changes to the `deltadata` CLI are documented here. This file
covers the CLI package only (`cli/`) — the hosted engine and API are a
separate, independently versioned service.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the CLI follows [Semantic Versioning](https://semver.org/): breaking
changes to flags, output shapes, or exit codes bump the major version once
the CLI reaches 1.0.0.

## [Unreleased]

## [0.1.1] - 2026-08-31

### Fixed

- Updated the package description after publication so PyPI leads with the
  working `pip install deltadata` command.

## [0.1.0] - 2026-08-27

Initial public release on PyPI as `deltadata`.

### Added

- `deltadata compare` command — calls a running DeltaData API's
  `POST /api/v1/compare` and prints a formatted terminal summary (change
  detected, risk level, findings, recommendation).
- `--json` flag for machine-readable output matching the API response shape.
- `--data` may be repeated once per source table a comparison needs.
- `--fail-on {none,low,medium,high,critical}` (default `high`) with
  CI-friendly exit codes: `0` OK, `1` risk threshold met/exceeded,
  `2` execution error, `3` usage error.
- `--api-url` / `--api-key`, defaulting to `$DELTADATA_API_URL` /
  `$DELTADATA_API_KEY`.

[Unreleased]: https://github.com/nikhiljii/Delta-Data/compare/cli-v0.1.0...HEAD
[0.1.0]: https://github.com/nikhiljii/Delta-Data/releases/tag/cli-v0.1.0

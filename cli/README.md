# deltadata-cli

Command-line interface for [DeltaData](../README.md) — behavioral
regression testing for SQL. This package is a thin HTTP client: every
`deltadata compare` call hits a running DeltaData API's
`POST /api/v1/compare` endpoint; it never reimplements the analysis engine.

See the [repository README](../README.md#cli-usage) for full usage, exit
codes, and CI examples.

## Install

The first PyPI release is pending. Until the
[`deltadata` project is live](https://pypi.org/project/deltadata/), install
the packaged CLI from GitHub:

```bash
pip install "git+https://github.com/nikhiljii/Delta-Data.git#subdirectory=cli"
```

Once the release succeeds, use:

```bash
pip install deltadata
```

See [`RELEASING.md`](RELEASING.md) for the release status and process.

## Quick start

```bash
deltadata compare \
  --before before.sql \
  --after after.sql \
  --data orders.csv \
  --api-url "$DELTADATA_API_URL" \
  --api-key "$DELTADATA_API_KEY"
```

## Develop

```bash
cd cli
pip install -e .
pytest tests/
```

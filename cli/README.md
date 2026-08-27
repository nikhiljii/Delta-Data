# deltadata-cli

Command-line interface for [DeltaData](../README.md) — behavioral
regression testing for SQL. This package is a thin HTTP client: every
`deltadata compare` call hits a running DeltaData API's
`POST /api/v1/compare` endpoint; it never reimplements the analysis engine.

See the [repository README](../README.md#cli-usage) for full usage, exit
codes, and CI examples.

## Install (local / CI)

```bash
pip install -e ./cli
```

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

# Contributing to DeltaData

Thanks for your interest in DeltaData! This repository contains the
**CLI**, worked **examples**, and **documentation** for DeltaData's public
API contract. The analysis engine and web app run as a separate hosted
service and are not part of this repository (see
[README.md](README.md#whats-in-this-repository) for the public/hosted
split).

## What you can contribute here

- Bug fixes and improvements to the `deltadata` CLI (`cli/`)
- New worked examples under `examples/` (a new SQL behavioral-change
  scenario with `before.sql`, `after.sql`, sample CSV data, and a README
  describing the expected finding)
- Documentation fixes and clarifications
- The GitHub Action workflow (`.github/workflows/`)

## Local setup

The CLI is a small, dependency-light Python package that talks to a running
DeltaData API over HTTP — it does not need the engine or a database to
develop against. (Just want to *use* the CLI, not modify it? `pip install
deltadata` from [PyPI](https://pypi.org/project/deltadata/) — no clone
needed; see [README.md#cli-usage](README.md#cli-usage).)

```bash
git clone https://github.com/nikhiljii/Delta-Data.git
cd Delta-Data
pip install -e ./cli
```

Point it at a running DeltaData API (the hosted demo, or your own instance)
via `--api-url`/`--api-key` or the `DELTADATA_API_URL`/`DELTADATA_API_KEY`
environment variables.

## Running tests

```bash
cd cli
pip install -e .
pytest tests/
```

## Releasing the CLI

Maintainers cutting a new `deltadata` release should follow
[`cli/RELEASING.md`](cli/RELEASING.md) — it covers versioning, the
CHANGELOG, and the tag-triggered PyPI publish workflow.

## Adding an example

Each folder under `examples/` should contain:

- `before.sql` / `after.sql` — the two versions of the query being compared
- One or more CSV files with small, synthetic sample data (no real/customer
  data — see [SECURITY.md](SECURITY.md))
- A `README.md` describing what changes and the expected finding

Verify the finding by actually running it against a live DeltaData API
before submitting — do not hand-write expected output.

```bash
deltadata compare \
  --before examples/your-example/before.sql \
  --after  examples/your-example/after.sql \
  --data   examples/your-example/orders.csv
```

## Submitting changes

1. Fork the repository and create a branch for your change.
2. Make your change and ensure `pytest tests/` (in `cli/`) passes.
3. Open a pull request describing what changed and why.
4. For anything touching the CLI's argument parsing, exit codes, or output
   format, call out any documentation (`README.md`, `cli/README.md`) that
   needs updating alongside the code.

## Reporting bugs / requesting features

Use the issue templates in this repository. For security issues, see
[SECURITY.md](SECURITY.md) instead of opening a public issue.

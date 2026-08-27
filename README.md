# DeltaData — Behavioral Regression Testing for SQL

**Catch SQL changes that still run, but no longer mean the same thing.**

```sql
-- BEFORE
SELECT COUNT(DISTINCT customer_id)
FROM orders;

-- AFTER
SELECT COUNT(customer_id)
FROM orders;
```

Both queries execute without error. Both return a single number. But if any
customer placed more than one order, they no longer return the *same*
number — and nothing in a normal SQL review, linter, or test suite would
catch that. DeltaData runs both queries against representative data, detects
that the behavior diverged, and explains why:

```
$ deltadata compare --before before.sql --after after.sql --data orders.csv

DeltaData Behavioral Regression Analysis

Change types: AGGREGATION_CHANGED
Classification: BREAKING_CHANGE
Risk: HIGH
Change detected: Yes

Findings:
  - [HIGH] COUNT vs COUNT(DISTINCT) — customer_id
    COUNT(customer_id) = 10, COUNT(DISTINCT customer_id) = 6 — difference: 4 (66.7% inflation)
  - [HIGH] Metric definition — customer_count
    METRIC DEFINITION CHANGED — customer_count: COUNT(DISTINCT customer_id) AS customer_count -> COUNT(customer_id) AS customer_count; observed total: 6 -> 10 (+66.7%)

Recommendation:
High-risk change detected. Investigate before deploying.
```

See [`examples/count-distinct-vs-count`](examples/count-distinct-vs-count/)
to run this exact scenario yourself, and [`examples/`](examples/) for four
more worked scenarios (join type changes, filter removal, GROUP BY changes,
metric formula changes).

## What DeltaData does

DeltaData compares a BEFORE and AFTER version of a SQL query, classifies the
semantic change (join type, filter, aggregation, grouping, metric formula,
...), executes a battery of deterministic behavioral tests against
representative sample data, and reports whether the change altered what the
query actually *means* — not just whether it still runs. Every number in a
DeltaData report (before/after values, row counts, percentage deltas) is
computed by executing SQL against real data, never inferred or guessed; an
AI review layer explains and prioritizes the *evidence*, but never invents
it.

DeltaData deliberately does **not** treat every behavioral difference as a
regression. It distinguishes:

- no behavioral change,
- a benign/low-risk change,
- a behavioral change worth reviewing,
- a likely breaking change,

so you can tell "this SQL rewrite is safe" from "this SQL rewrite quietly
changed the numbers" without drowning in false positives.

## What's in this repository

This repository is DeltaData's **developer preview**: the CLI, worked
examples, and documentation for the public API contract. The analysis
engine and web app are a separately operated, closed-source service — you
call them over HTTP (via the CLI or `curl`), the same way any DeltaData user
does; their source isn't published here.

| | |
|---|---|
| **Published here** | `cli/` (the `deltadata` command), `examples/`, this documentation, the GitHub Action |
| **Hosted, not published** | The analysis engine, the web UI, `/api/v1/compare`'s implementation |

You need a running DeltaData API (the [hosted demo](https://delta-data.replit.app/)
or your own instance) and an API key to run anything below — the CLI is a
thin client, not a standalone tool.

## Architecture

One shared analysis engine backs every way of using DeltaData — the Web UI,
the versioned API, and the CLI all call the same code path, so results never
drift between surfaces:

```text
                    DeltaData Engine
              (SQL diff -> classify -> generate
               tests -> execute -> risk -> review)
                           |
             +-------------+-------------+
             |             |             |
            Web           API           CLI
      (existing UI)  /api/v1/compare  deltadata compare
                                          |
                                    CI / GitHub Actions
                                    (see below)
```

- **Web UI** — the existing DeltaData application; unchanged by the API/CLI
  work described here.
- **API** — `POST /api/v1/compare`, a stable, API-key gated HTTP endpoint
  for programmatic and CI use (see below).
- **CLI** — `deltadata compare`, a thin wrapper that calls the API; it never
  reimplements analysis logic locally.

## API usage

`POST /api/v1/compare` on a running DeltaData API server. Requires an
`X-API-Key` header (the server checks it against the `DELTADATA_API_KEY`
secret).

```bash
curl -X POST "$DELTADATA_API_URL/api/v1/compare" \
  -H "X-API-Key: $DELTADATA_API_KEY" \
  -F "old_sql=<before.sql" \
  -F "new_sql=<after.sql" \
  -F "files=@orders.csv;type=text/csv"
```

Response shape (stable — this is the external contract, independent from
the internal Web UI's response shape):

```json
{
  "status": "ok",
  "change_detected": true,
  "classification": "BREAKING_CHANGE",
  "risk_level": "HIGH",
  "change_types": ["AGGREGATION_CHANGED"],
  "summary": "...human-readable multi-section summary...",
  "tests": [
    {
      "name": "COUNT vs COUNT(DISTINCT) — customer_id",
      "type": "CountVsDistinctCountTest",
      "status": "CHANGE_DETECTED",
      "severity": "HIGH",
      "reason": "COUNT(customer_id) = 10, COUNT(DISTINCT customer_id) = 6 — difference: 4 (66.7% inflation)"
    }
  ],
  "recommendation": "High-risk change detected. Investigate before deploying.",
  "error": null
}
```

`classification` is one of `NO_CHANGE`, `BENIGN_CHANGE`, `BEHAVIORAL_CHANGE`,
`BREAKING_CHANGE`, or `EXECUTION_ERROR` (when the SQL itself failed to run,
`risk_level` is `null`). Repeat the `files` form field once per source CSV
for queries that join multiple tables. Error responses (4xx/5xx) always use
`{"status": "error", "error": "<message>"}` — never a raw stack trace or
backend error string.

## CLI usage

The CLI lives in [`cli/`](cli/) as an installable Python package that talks
to the API over HTTP — it never touches the analysis engine directly.

```bash
pip install -e ./cli
```

```bash
deltadata compare \
  --before before.sql \
  --after after.sql \
  --data orders.csv \
  --api-url "$DELTADATA_API_URL" \
  --api-key "$DELTADATA_API_KEY"
```

- `--data` may be repeated once per source table the queries need.
- `--api-url` defaults to `$DELTADATA_API_URL`, then `http://localhost:8000`.
- `--api-key` defaults to `$DELTADATA_API_KEY`.
- `--json` prints the raw API response instead of the formatted summary
  above, for scripting.
- `--fail-on {none,low,medium,high,critical}` (default `high`) controls
  which risk levels cause a non-zero exit — see exit codes below.

### Exit codes (CI-friendly)

| Code | Meaning |
|---|---|
| `0` | OK — no behavioral change, or detected risk stayed below `--fail-on` |
| `1` | Detected risk met or exceeded `--fail-on` |
| `2` | Execution error — the provided SQL failed to run against the data |
| `3` | Usage error — bad CLI arguments, a missing file, or the API could not be reached (auth/connection/timeout) |

```bash
deltadata compare --before before.sql --after after.sql --data orders.csv --fail-on high
echo "exit code: $?"
```

## CI usage (GitHub Actions)

The CLI is deliberately just a plain command — `deltadata compare ...` — so
wiring it into CI needs nothing DeltaData-specific beyond installing it and
setting two secrets.

**Try the shipped demo first.** This repo includes a working, manually
triggered workflow at `.github/workflows/deltadata.yml`. Open the Actions
tab → "DeltaData behavioral check (manual demo)" → "Run workflow" and it
installs the CLI and runs it against the bundled
`examples/count-distinct-vs-count` scenario against a live DeltaData API —
it deliberately fails, because that scenario is a real HIGH-risk change,
which is the point of running it. (Replit's GitHub connector isn't granted
the `workflow` OAuth scope, so this one file has to be added to your
fork/clone by hand — via GitHub's web editor, or a git push with a personal
access token that has the `workflow` scope.)

**Turn it into a real PR gate for your own project** by pointing the same
command at your own SQL/data instead of the bundled example, and switching
the trigger to `pull_request`:

```yaml
# .github/workflows/deltadata.yml -- adapt to your own files, not the demo above
name: DeltaData behavioral check
on:
  pull_request:
    paths:
      - "sql/**/*.sql" # narrow this to wherever your tracked SQL actually lives

jobs:
  deltadata:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install DeltaData CLI
        run: pip install -e ./cli

      - name: Run behavioral diff
        env:
          DELTADATA_API_URL: ${{ secrets.DELTADATA_API_URL }}
          DELTADATA_API_KEY: ${{ secrets.DELTADATA_API_KEY }}
        run: |
          deltadata compare \
            --before sql/before.sql \
            --after sql/after.sql \
            --data sql/sample_orders.csv \
            --fail-on high
```

`sql/before.sql`, `sql/after.sql`, and `sql/sample_orders.csv` are
placeholders for wherever your project keeps its old/new query and sample
data — DeltaData doesn't (yet) diff arbitrary changed files in a PR
automatically, so this template always compares two fixed paths that you
choose. Because `deltadata compare` exits non-zero when the risk threshold
is exceeded (or the SQL fails to execute), this step fails the pull request
check on its own once it points at real files — no extra scripting needed.
The eventual PR workflow this sets up for:

```text
Developer changes SQL -> opens PR -> DeltaData detects the SQL change
  -> runs BEFORE and AFTER -> compares behavior -> reports risk
  -> PR check PASS / REVIEW / FAIL
```

## Security & data-handling

- The API never returns stack traces, backend SQL engine error text,
  secrets, model credentials, internal prompts, or server configuration —
  every error response is a short, generic, stable message (details are
  logged server-side only).
- `/api/v1/compare` requires a constant-time-compared `X-API-Key`; requests
  without a valid key are rejected before any analysis runs.
- Request size is bounded (SQL text length, per-file and total upload size,
  file count) and analysis runs under an enforced timeout, so a single
  request cannot exhaust server resources or hang a CI job indefinitely.
- Uploaded CSV data is only ever used in-memory for the single analysis
  request that included it; it is not persisted, logged, or reused across
  requests.
- The CLI never writes your SQL or data anywhere but the target
  DeltaData API you point it at with `--api-url` — treat that URL and your
  `DELTADATA_API_KEY` the same as any other credential (e.g. via
  `DELTADATA_API_KEY` env var / CI secrets, not a command-line literal in
  shared shell history).

## Examples

See [`examples/`](examples/) for five worked scenarios — each with a
`before.sql`, `after.sql`, sample data, and the expected finding —
covering `COUNT(DISTINCT)` removal, join type changes, filter removal,
`GROUP BY` changes, and metric formula changes.

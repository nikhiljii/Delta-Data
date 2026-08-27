# DeltaData examples

Five worked scenarios, each with a `before.sql`, `after.sql`, sample CSV
data, and a `README.md` describing the expected finding. Every finding below
was verified by actually running the scenario against the live
`/api/v1/compare` API, not hand-written.

| Example | What silently changes | Risk |
|---|---|---|
| [`count-distinct-vs-count`](count-distinct-vs-count/) | `COUNT(DISTINCT x)` → `COUNT(x)` | HIGH |
| [`left-vs-inner-join`](left-vs-inner-join/) | `LEFT JOIN` → `INNER JOIN` | HIGH |
| [`filter-removal`](filter-removal/) | a `WHERE` clause is dropped | HIGH |
| [`group-by-change`](group-by-change/) | a `GROUP BY` dimension is dropped | HIGH |
| [`metric-formula-change`](metric-formula-change/) | a `SUM(...)` formula changes | MEDIUM |

Run any of them with the CLI, from the repository root. `--data` takes one
file per flag, so scenarios with more than one CSV repeat the flag (see each
example's own README for its exact command):

```bash
deltadata compare \
  --before examples/count-distinct-vs-count/before.sql \
  --after  examples/count-distinct-vs-count/after.sql \
  --data   examples/count-distinct-vs-count/orders.csv
```

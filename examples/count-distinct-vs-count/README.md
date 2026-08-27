# Example: `COUNT(DISTINCT)` silently becomes `COUNT`

This is DeltaData's flagship example -- a query that still runs, still
returns a single number, and now means something different.

```sql
-- BEFORE
SELECT COUNT(DISTINCT customer_id) AS customer_count
FROM orders;

-- AFTER
SELECT COUNT(customer_id) AS customer_count
FROM orders;
```

`orders.csv` has 10 order rows but only 6 distinct customers (several
customers placed more than one order).

## Run it

```bash
deltadata compare \
  --before examples/count-distinct-vs-count/before.sql \
  --after examples/count-distinct-vs-count/after.sql \
  --data examples/count-distinct-vs-count/orders.csv
```

## Expected finding (verified against the live API)

- **Classification:** `BREAKING_CHANGE` — **Risk:** `HIGH`
- **`customer_count`: 6 → 10 (+66.7%)** — duplicate `customer_id` occurrences
  that used to be collapsed by `DISTINCT` now each add to the count.
- DeltaData's deterministic tests confirm this is duplicate-driven, not a
  data change: `COUNT(customer_id) = 10, COUNT(DISTINCT customer_id) = 6`
  against the *same* dataset for *both* queries — a corroborated metric
  redefinition with a material (≥20%) swing in the observed value, which is
  exactly the pattern DeltaData escalates to `HIGH`.
- **Recommendation:** investigate before deploying — confirm whether the
  metric should count unique customers or total order rows.

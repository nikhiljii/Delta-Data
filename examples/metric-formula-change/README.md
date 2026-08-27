# Example: a metric formula silently changes

```sql
-- BEFORE
SELECT SUM(quantity * price) AS revenue
FROM orders;

-- AFTER
SELECT SUM(quantity * price * (1 - discount)) AS revenue
FROM orders;
```

`orders.csv` adds a `discount` column that the AFTER query now applies
per line item.

## Run it

```bash
deltadata compare \
  --before examples/metric-formula-change/before.sql \
  --after examples/metric-formula-change/after.sql \
  --data examples/metric-formula-change/orders.csv
```

## Expected finding (verified against the live API)

- **Classification:** `BEHAVIORAL_CHANGE` — **Risk:** `MEDIUM`
- **`revenue`: 240.22 → 215.43 (-10.3%)** — the new formula now nets out
  each line item's discount before summing.
- DeltaData flags this as a metric definition change (not just a value
  drift), because it can see the SQL expression itself changed:
  `SUM(quantity * price)` → `SUM(quantity * price * (1 - discount))`.
- **Recommendation:** review before deploying — confirm the discounted
  total is the intended definition of "revenue" going forward.

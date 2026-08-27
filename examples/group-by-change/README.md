# Example: a `GROUP BY` dimension is silently dropped

```sql
-- BEFORE
SELECT customer_id, region, SUM(quantity * price) AS revenue
FROM orders
GROUP BY customer_id, region;

-- AFTER
SELECT customer_id, SUM(quantity * price) AS revenue
FROM orders
GROUP BY customer_id;
```

`orders.csv` includes a customer (customer 1) who ordered from two
different regions, so dropping `region` from the grain collapses their
rows together.

## Run it

```bash
deltadata compare \
  --before examples/group-by-change/before.sql \
  --after examples/group-by-change/after.sql \
  --data examples/group-by-change/orders.csv
```

## Expected finding (verified against the live API)

- **Classification:** `BREAKING_CHANGE` — **Risk:** `HIGH`
- **Result grain changed:** `(customer_id, region)` → `(customer_id)`,
  removing the `region` dimension entirely from the output schema.
- **Result cardinality: 6 → 5 rows** while the overall `SUM(revenue)` is
  conserved (266.21 → 266.21) — the totals still add up, but per-region
  breakdowns for repeat customers are gone.
- **Recommendation:** investigate before deploying — confirm downstream
  consumers don't depend on the per-region rows that just disappeared.

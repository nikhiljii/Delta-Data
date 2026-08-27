# Example: a `WHERE` filter is silently removed

```sql
-- BEFORE
SELECT COUNT(*) AS order_count, SUM(quantity * price) AS revenue
FROM orders
WHERE status = 'completed';

-- AFTER
SELECT COUNT(*) AS order_count, SUM(quantity * price) AS revenue
FROM orders;
```

`orders.csv` has 10 orders: 6 `completed`, 2 `cancelled`, 2 `refunded`.

## Run it

```bash
deltadata compare \
  --before examples/filter-removal/before.sql \
  --after examples/filter-removal/after.sql \
  --data examples/filter-removal/orders.csv
```

## Expected finding (verified against the live API)

- **Classification:** `BREAKING_CHANGE` — **Risk:** `HIGH`
- **`order_count`: 6 → 10 (+66.7%)** and **`revenue`: 167.72 → 326.21
  (+94.5%)** — cancelled and refunded orders that used to be excluded now
  count toward both metrics.
- **Recommendation:** investigate before deploying — decide whether
  cancelled/refunded orders should really be included in these metrics.

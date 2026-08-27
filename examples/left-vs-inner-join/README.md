# Example: `LEFT JOIN` silently becomes `INNER JOIN`

```sql
-- BEFORE
SELECT o.order_id, o.customer_id, c.region
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id;

-- AFTER
SELECT o.order_id, o.customer_id, c.region
FROM orders o
INNER JOIN customers c ON o.customer_id = c.customer_id;
```

`orders.csv` has 7 orders; `customers.csv` only has records for customers
1-5, so orders from customers 6 and 7 have no match.

## Run it

```bash
deltadata compare \
  --before examples/left-vs-inner-join/before.sql \
  --after examples/left-vs-inner-join/after.sql \
  --data examples/left-vs-inner-join/orders.csv \
  --data examples/left-vs-inner-join/customers.csv
```

## Expected finding (verified against the live API)

- **Classification:** `BREAKING_CHANGE` — **Risk:** `HIGH`
- **Result cardinality: 7 → 5 rows.** Switching `LEFT JOIN` to `INNER JOIN`
  drops every order without a matching customer record.
- DeltaData identifies exactly which rows disappeared: `customer_id` values
  `6` and `7` are silently excluded from the output.
- **Recommendation:** investigate before deploying — confirm whether orders
  without a matching customer should really be dropped.

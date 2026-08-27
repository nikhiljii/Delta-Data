-- AFTER: INNER JOIN silently drops orders that have no matching customer record
SELECT o.order_id, o.customer_id, c.region
FROM orders o
INNER JOIN customers c ON o.customer_id = c.customer_id;

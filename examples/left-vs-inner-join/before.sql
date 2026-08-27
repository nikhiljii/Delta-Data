-- BEFORE: LEFT JOIN keeps every order, even ones without a matching customer record
SELECT o.order_id, o.customer_id, c.region
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id;

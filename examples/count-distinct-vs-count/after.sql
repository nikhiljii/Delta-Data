-- AFTER: silently switched to counting order rows, not unique customers
SELECT COUNT(customer_id) AS customer_count
FROM orders;

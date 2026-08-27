-- BEFORE: counts unique customers who placed an order
SELECT COUNT(DISTINCT customer_id) AS customer_count
FROM orders;

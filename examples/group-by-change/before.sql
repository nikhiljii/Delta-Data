-- BEFORE: revenue broken out by customer AND region
SELECT customer_id, region, SUM(quantity * price) AS revenue
FROM orders
GROUP BY customer_id, region;

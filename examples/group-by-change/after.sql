-- AFTER: region dimension silently dropped -- rows for a customer across regions now collapse into one
SELECT customer_id, SUM(quantity * price) AS revenue
FROM orders
GROUP BY customer_id;

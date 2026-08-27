-- AFTER: filter silently removed -- refunded and cancelled orders now count too
SELECT COUNT(*) AS order_count, SUM(quantity * price) AS revenue
FROM orders;

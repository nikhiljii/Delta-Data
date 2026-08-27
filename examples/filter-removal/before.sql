-- BEFORE: only counts completed orders toward revenue
SELECT COUNT(*) AS order_count, SUM(quantity * price) AS revenue
FROM orders
WHERE status = 'completed';

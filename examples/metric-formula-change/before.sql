-- BEFORE: revenue is quantity * price
SELECT SUM(quantity * price) AS revenue
FROM orders;

-- AFTER: formula silently changed to also apply a per-line discount
SELECT SUM(quantity * price * (1 - discount)) AS revenue
FROM orders;

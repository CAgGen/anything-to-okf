# Orders and Customers Relationship

## Overview

The orders and customers tables are linked by a foreign key relationship:
- `orders.customer_id` is a foreign key that references `customers.customer_id`
- This establishes a one-to-many relationship: one customer can have many orders

## Order Fulfillment Process

When a customer places an order, the system creates a row in the orders table with
their customer ID, links it to their customer record, and processes payment through
the revenue system. Each order's total_usd contributes to the daily revenue metrics,
which aggregate revenue across all orders by customer tier (free/plus/pro).

## Queries

To find all orders for a specific customer:

```sql
SELECT o.order_id, o.status, o.total_usd, o.placed_at
FROM orders o
WHERE o.customer_id = 'C-90'
ORDER BY o.placed_at DESC
```

To summarize revenue by customer tier:

```sql
SELECT c.tier, SUM(o.total_usd) as revenue
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.tier
```

## Column Meanings

- **orders.customer_id**: Foreign key; must exist in customers.customer_id. NULL not allowed.
- **customers.customer_id**: Primary key uniquely identifying a customer account.
- **orders.total_usd**: In-order monetary value; when status is 'refunded', this is reset to 0.00
- **customers.tier**: One of 'free', 'plus', 'pro'; determines SLA and features.

# Refund handling runbook

When an order's `status` becomes `refunded`, the `total_usd` is set to 0.00 and
a reversal is written to the ledger within 30 minutes.

## Trigger
A support agent marks an order refunded, or the fraud system auto-refunds.

## Steps
1. Verify the order exists in the orders table and is not already refunded.
2. Confirm the customer tier (free/plus/pro) — pro customers get priority SLA.
3. Issue the reversal; the orders row's total_usd drops to 0.00.
4. Notify the customer at their account email (skip if null / guest checkout).

## Escalation
If the reversal does not post within 30 minutes, page the payments on-call.

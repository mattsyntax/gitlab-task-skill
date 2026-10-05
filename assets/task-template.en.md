## Description
What is wrong or what needs to be done and why, in plain language, without class, method or table names (1-2 paragraphs). A tester and a manager should understand it.

## Goal
Why this is being done and how it affects the system as a whole.

## Implementation plan
**Technical details:** where the problem is in the code, how it works now, references to files, classes, methods, tables, routes, related issues. A paragraph of text is fine.

*What to change:*
- [ ] Add a migration for the new `orders` table.
- [ ] Update the order list query in `src/orders/service` to apply the status filter.
- [ ] Validate the request parameters and answer 422 on an unknown status.

## Acceptance criteria
*How to tell the task is done:*
1. `GET /api/orders?status=paid` returns only paid orders.
2. The response contains no internal fields.
3. The order list UI has a status filter.

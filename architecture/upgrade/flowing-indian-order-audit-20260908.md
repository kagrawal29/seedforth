# Flowing Indian order-system discovery

Date: 2026-09-08
Parent: GitHub issue #13
Repository: `kartiksahu/flowing-indian-website`

## Revision boundary

- GitHub `main` observed through the Delta credential: `49926b4ebd087936db31f230eccb50e12bf82b3b`
- Local checkout: branch `feature/bundle-landing-page`, commit `e470982`, dirty with test/tooling changes
- Server checkout: branch `main`, commit `2d07670`, ahead of `origin/main` by two local commits and dirty with an untracked Delta log

These revisions must not be treated as one implementation baseline. No reset,
pull, cleanup, merge, or deployment action was taken during discovery.

## Current behavior observed in the local implementation

1. `/api/order` validates email and SKU, then creates a Razorpay order using
   server-side product price and notes. It does not persist a first-party order.
2. `/api/verify` verifies the payment signature, fetches the Razorpay payment
   and order, validates product, amount, and captured status, then grants the
   course entitlement and sends buyer/team email effects.
3. `/api/razorpay/webhook` verifies the webhook signature, resolves the order,
   validates product/order/amount, grants entitlement on `payment.captured`,
   revokes it on `payment.refunded`, and emits operational alerts for failures.
4. Clerk user metadata currently acts as the entitlement store and contains
   payment dedupe flags. There is no durable first-party order, notification
   outbox, fulfillment state, or buyer order-history store.
5. Buyer email and bundle fulfillment email exist. WhatsApp confirmation is not
   implemented in the inspected path.
6. The browser verification path and webhook both perform fulfillment effects;
   the current implementation attempts idempotency through Clerk metadata but
   does not provide a durable order/event transaction boundary.

## Gaps to resolve

- canonical order and payment state model
- durable persistence and retention policy
- event idempotency and concurrent delivery behavior
- notification outbox, retries, and provider status
- fulfillment lifecycle and team operations
- buyer order history and account-linking behavior
- WhatsApp provider and message contract
- repository/revision reconciliation before implementation

## Proposed first implementation boundary

Implement and test durable order state and provider reconciliation first. Keep
real messaging and production effects behind explicit approval. Then add the
notification pipeline and authenticated order history as separate deliverables.

## Human decisions required

- database/provider and retention policy
- canonical status lifecycle and refund semantics
- WhatsApp provider and team recipients
- whether team operations begin in GitHub, an admin surface, or both
- production messaging and deployment approval

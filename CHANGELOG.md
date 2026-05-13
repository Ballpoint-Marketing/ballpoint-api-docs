# Changelog

## v1.3.1 — 2026-05-12

- **New: `edit_leads_requested` event (iframe → parent)** — Fired when the user clicks the "Edit Leads" button on the iframe's My Campaigns / Dashboard page. PropStream listens and opens its own Edit Leads modal overlay. Payload carries `listId`, `listName`, `recipientCount` (raw, not post-selection), `externalAccountId`, `externalUserId`. The button is rendered only when active list context exists. Per-status / per-mailDate lockout in V1 is enforced by the recipient upload endpoint and PropStream's modal; the iframe does not block clicks based on order state in this version.
- **New: `set_list` refresh contract** — `set_list` MAY now be sent a second time with the SAME `listId` to refresh `count`, `name`, and `piece_counts` after PropStream's Edit Leads modal saves. `externalAccountId`, `externalUserId`, and `tenantKey` are immutable post first-receipt — refresh attempts to change these are ignored (externalAccountId/externalUserId) or reject the entire message (tenantKey mismatch). Different-listId mid-flow set_list is still rejected as a list switch attempt (unchanged from prior behavior). Backward compatibility: partners that do not send a second `set_list` are unaffected.

## v1.3.0 — 2026-05-12

- **New: `set_list.piece_counts` input contract** — PropStream may now send pre-computed piece counts for all 6 combinations of `Deliver To` (property/mailing/both) × `Remove duplicates` (off/on). Iframe consumes via lookup, displays exact piece count + price, and surfaces 2 user-facing controls (Deliver To select + Remove duplicates checkbox) on the piece-selection page. Backward compat: when `piece_counts` absent, controls are hidden and behavior is identical to prior versions — existing partners unaffected.
- **New: `campaign_submitted.recipient_selection` output contract** — When `piece_counts` was provided, iframe now echoes the user's final selection back to the partner in the `campaign_submitted` event under `recipient_selection.{deliver_to, remove_duplicate_addresses, piece_count}`. `piece_count` is per-drop and matches each `orders[].pieces`. When `piece_counts` was not provided, `recipient_selection` is omitted from the payload (legacy shape preserved).
- **Also supported: `set_lists[].piece_counts`** — multi-list flow propagates per-list piece_counts. When the user picks a list from the selector, the iframe applies that list's piece_counts to the active selection state.

## v1.2.2 — 2026-05-01

- **New: API Kit §6l — Partner Dashboard Endpoints** — `GET /v1/billing/partner/stats` and `GET /v1/billing/partner/orders` now formally documented. Both accept the new `list_id` query parameter (echoes the same value passed when creating orders, combinable with `external_user_id` via AND). Stats response covers totals, status breakdown, SLA buckets, and RTS summary. Orders response is a paginated drill-down with computed `sla_status`. Unknown `list_id` returns the same shape with all counts zero.
- **API Kit §12 (Endpoint Quick Reference)** — added rows for `/confirm-payment`, `/partner/stats`, and `/partner/orders`.
- **Payment-flow reminder** — for charging the end-user, partner backends must refetch the relevant order from `GET /v1/billing/partner/orders` server-side; browser-side values like `campaign_submitted.total_dollars` remain UX/display only.

## v1.2.1 — 2026-04-29

- **API Kit §3 (How Billing Works) restructured** to document Ballpoint's two partner billing models side-by-side: standard invoiced partners (`billing_mode: none`) and partner-billed / payment-gated partners (`requires_payment_confirmation = TRUE`). Removes prior wording that assumed every reader was on `billing_mode: none`, which contradicted §6k Confirm Payment for payment-gated accounts.
- **API Kit §3 Cancellations** updated to differentiate refund behavior between invoiced and payment-gated partners.
- **API Kit §6a (Preview)** note generalized: "For accounts with `billing_mode: none`, `balance_cents` is null" instead of presuming the reader's account.
- **API Kit §6g (Cancel Order)** note expanded to describe cancellation behavior for both billing models, including the auto-refund behavior on payment-gated `accepted` orders.
- **API Kit §10 (Error Handling)** `402` row clarified: applies only to accounts with prepaid balance or spending-limit enforcement; `billing_mode: none` accounts always pass balance checks.

## v1.2.0 — 2026-04-29

- **New: [IFRAME_KIT.md](IFRAME_KIT.md)** — partner-facing iframe integration guide moved into the public docs repo so partners can track the latest version directly. Covers embed, bootstrap, parent ↔ iframe message contracts, recipient upload flow, URL parameters, and security notes.
- **API Kit §6j — Per-end-user attribution (`external_user_metadata`)** — opaque dict passed at order creation, echoed verbatim on every `order.status_changed` webhook. Limits: max 8 keys, 64-char keys, 256-char values, no nested structures, ≤2KB total. Subject to the partner-controlled retention window (same as recipient PII).
- **API Kit webhooks — `list_id` verbatim echo** — every `order.status_changed` payload now carries the `list_id` the partner originally passed at order creation, removing the need to derive it from the internal campaign id format.
- **API Kit §6k — Confirm Payment (Partner Payment Gate)** — full `/confirm-payment` endpoint contract inlined: request/response schemas, field tables, idempotency rules, error codes (`PAYMENT_ALREADY_CONFIRMED`, `PAYMENT_ALREADY_FAILED`, `PAYMENT_GATE_NOT_ACTIVE`, `ORDER_CANCELLED`, tenant-isolation 404), security boundary (server-to-server only, no card data on Ballpoint side, browser pricing is UX/display-only), retry/finalization V1 (partner-determined billing policy, Ballpoint receives only the final outcome).
- **API Kit §6k user-flow timing subsection** — 10-step end-to-end walkthrough showing where each iframe event (`campaign_created`, `campaign_submitted`, `campaign_complete`) and API call (`POST /orders`, `/confirm-payment`, `GET /partner/orders`) fits in the user journey for an iframe-driven partner-billed order, including the iframe-vs-payment lifecycle parallelism note.
- **API Kit webhooks — RTS Push-Back V1** — per-piece return-to-sender event documented as a dedicated server-to-server webhook. Cap 10K entries per call. Per-entry payload: `contact_id` + `reason` + `last_scan_date` (no name/address fields in V1). Reconciliation is by `contact_id` only; partners must populate `contact_id` on every eligible recipient at upload.
- **Iframe Kit — Partner Payment Gate Flow** — companion section to API Kit §6k giving the same 10-step walkthrough from the iframe-integration angle.
- **Iframe Kit — `campaign_submitted` field table** — expanded with `listId`, `listName`, `externalAccountId`, `externalUserId`, `mailDate`, `productIds` rows. `total_dollars` is explicitly marked UX/display only, with a pointer to refetch the authoritative amount from `GET /v1/billing/partner/orders` before charging the end-user.
- **Iframe Kit — `contact_id` requirement** — `contact_id` description on the `/recipients` upload now notes the V1 RTS push-back dependency: partners using the RTS push-back must populate `contact_id` on every recipient.

## v1.1.0 — 2026-03-10

- **Production pipeline updated to 8 stages**: added `prep` (data formatting) and `shipping` (manifest/labeling) stages
- Updated production sequences for all product types
- Updated order lifecycle diagram with new stages
- Updated webhook event descriptions and test lifecycle examples

## v1.0.1 — 2026-03-02

- Webhook docs: prominent at-least-once delivery statement
- Webhook docs: deduplication promoted to required, with examples
- Webhook docs: processing model recommendation
- Webhook docs: expanded event catalog with example payloads
- Lambda example: uncommented DynamoDB dedup, added base64 guidance
- Cloudflare Worker example: uncommented KV dedup

## v1.0.0 — 2026-03-02

- Initial public release of integration documentation
- API Kit: ordering, tracking, webhooks, billing
- OpenAPI v2 specification
- Postman collection + sandbox/production environments
- Webhook receiver templates: Express, Lambda, Cloudflare Worker

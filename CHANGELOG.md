# Changelog

## v1.5.1 — 2026-05-19

- **Clarified — same-order recipient dedupe rule (docs-only, no behavior change).** `IFRAME_KIT.md` now states explicitly that Ballpoint never auto-collapses recipients within an order — including the case where a lead's property and mailing addresses are identical. Same-order dedupe (including same-lead `property == mailing` collapse) happens **only** when the user explicitly selects "Remove duplicates" on the iframe's piece-selection page, in which case the partner provides the deduplicated count via `set_list.piece_counts.<scope>.dedup_on` and uploads the matching deduplicated recipient list. If the user selects `Deliver To = both` + `Remove duplicates = OFF` and a lead's property address equals its mailing address, the partner uploads two recipient records for that lead and Ballpoint mails two postcards.
- **Reframed `piece_counts.both.dedup_off` / `dedup_on` semantics as partner-defined.** Previous wording asserted Ballpoint-side semantics ("per-lead unique send-address count — if property == mailing, lead counts as 1, not 2") and instructed partners to collapse same-lead duplicates before uploading. That wording is **superseded**: the partner's product owns the count for both combinations, Ballpoint mails exactly what is uploaded, and `duplicate_in_campaign` (cross-order A/B-split guard-rail) must **not** be used to override the user's same-order selection. Updated the dedupe callout under the `piece_counts` shape table, the worked example (978/850 instead of 920/850), the "Same-order dedupe" note under §7 Recipient Upload Flow, and the "What this does NOT do" subsection under Campaign Dedup (automatic).
- **No code, contract, or API changes.** Behavior was already as documented here on staging; this release brings the docs in line with the rule confirmed with PropStream on 2026-05-19 (product-design decision, no implementation work). Source: Slack `#ballpoint-propstream` thread `1779213550.746299` (2026-05-19, Geo + Evren + Armstrong).

## v1.5.0 — 2026-05-16

- **BREAKING (semantically): `edit_leads_requested` postMessage is now campaign-level.** V1 list-level payload replaced with V2 campaign-level payload (`scope: "multi_month_campaign"`, `campaignId`, `ballpointCampaignId`, `affectedOrders[]`, `lockedOrders[]`). The list-level header button is replaced by per-campaign-card buttons that appear only on multi-month campaigns with at least one future/unbilled drop. Iframe is still staging-only — PropStream listener updates required before any iframe production rollout. See `IFRAME_KIT.md` `edit_leads_requested` section.
- **New: `PATCH /v1/billing/orders/{order_id}/recipients` endpoint** for Edit Leads V2 flow. Replaces recipients, resizes `piece_count`, recomputes display pricing fields via canonical `get_unit_price`. All-or-nothing Pydantic v2 validation (any invalid recipient → `422`, no DB mutation). Gates: account `requires_payment_confirmation=TRUE`, order `payment_confirmed=FALSE`, status ∈ `{scheduled, pending_payment, accepted, prep}`. New 409 codes: `PAYMENT_GATE_NOT_ACTIVE`, `PAID_LOCKED`, `RECIPIENTS_LOCKED`. No transactions/usage/balance writes — `/confirm-payment` recomputes price at charge time using the new piece_count, so it remains the sole billing source of truth. See `API_KIT.md §6n`.
- **New: `recipients_updated` parent→iframe postMessage.** Emitted by the partner app after successfully PATCHing each `affectedOrder`. Triggers iframe to re-fetch campaign history. Read-only `tenantKey` check (event cannot be used to establish or mutate tenant scope). See `IFRAME_KIT.md`.
- **Note on existing `POST /v1/billing/orders/{order_id}/recipients`:** unchanged. Still the canonical endpoint for initial recipient upload (and chunked append). NOT the Edit Leads V2 flow (use the new PATCH).

## v1.4.2 — 2026-05-16

- **New field: `payment_confirmed` exposed in `GET /v1/billing/orders` and `GET /v1/billing/orders/{order_id}` responses.** Tri-state nullable boolean (`true`/`false`/`null`). Returned as `true` once `POST /v1/billing/orders/{order_id}/confirm-payment` succeeds for partner-gated accounts (`requires_payment_confirmation = TRUE`); `false` while awaiting partner confirmation; `null` for accounts that do not use the payment gate. Backward compatible: existing partners ignoring the field are unaffected. See `API_KIT.md §6c` + `§6d`.
- **Why.** Iframe consumers need a reliable per-order payment-state signal that does not require parsing ambiguous `production_status` values (e.g. `scheduled` can be either pre- or post-confirmation). Foundation for future campaign-level features that distinguish billed vs unbilled drops.

## v1.4.1 — 2026-05-16

- **New: `sender_setup_requested` iframe postMessage (iframe → parent).** Emitted when the user clicks the "Set up now" CTA on the iframe's first-time setup page (`page-setup`) and no `set_sender` has been received yet. Payload: `{ source: "ballpoint-mailer", version: 1, type: "sender_setup_requested", reason, page, externalAccountId, externalUserId }`. See `IFRAME_KIT.md §6`.
- **Casing.** Payload keys are **camelCase** to match sibling iframe → parent postMessages (`edit_leads_requested`, `order_rescheduled`, `order_cancelled`, `list_selected`).
- **Enums.** `reason` is the V1 enum `"sender_info_missing"`. `page` is the V1 enum `"setup"` \| `"campaigns"` (V1 wires `"setup"`; `"campaigns"` is accepted today so the future my-info CTA wire requires no schema change). Future values for both fields are additive — partners should treat unknown values as "open the sender modal" and not hard-fail.
- **Empty identifiers allowed.** `externalAccountId` and `externalUserId` MAY be empty strings if the user reaches the CTA before any `set_list` or `set_tenant` has arrived (e.g., very first session before list selection).
- **Parent → iframe response unchanged.** The parent replies with the existing [`set_sender`](IFRAME_KIT.md#set_sender--pre-fill-sender-info-optional) postMessage on modal save. No new inbound contract; the iframe's existing locking flow takes over from there.
- **Pre-lock behavior.** Queued by the iframe until the parent origin lock completes, then delivered only to the locked parent origin. Identical treatment to `edit_leads_requested`. In standalone (non-embed) mode the iframe falls back to its built-in inline sender form and the CTA is suppressed.

## v1.4.0 — 2026-05-15

- **New: same-order reschedule endpoint.** `POST /v1/billing/orders/{order_id}/reschedule` allows partners to change `mail_date` on a scheduled, unpaid order without creating a replacement order. Recomputes `scheduled_production_date` from product SLA. Returns `{ order_id, previous_mail_date, new_mail_date, previous_scheduled_production_date, new_scheduled_production_date }`. See `API_KIT.md §6m`.
  - **Allowed states:** `production_status='scheduled'` AND `payment_confirmed=FALSE`.
  - **409 reason codes:** `PAID_LOCKED` (payment already processed), `SEND_NOW_PROCESSING` (send-now order awaiting `/confirm-payment`), `IN_PRODUCTION` (accepted/prep/printing/writing/inserting/stamping/shipping), `TERMINAL` (complete/cancelled/failed/payment_failed), `STATE_CHANGED` (concurrent modification — retry).
  - **400 reason codes:** `MAIL_DATE_INVALID_FORMAT` (not YYYY-MM-DD), `MAIL_DATE_TOO_SOON` (`mail_date − SLA_days` ≤ today + 1 day), `MAIL_DATE_TOO_FAR` (more than 365 days in future).
  - **Idempotent no-op:** if the supplied `mail_date` equals the order's current value, the endpoint returns `200` with `previous_mail_date == new_mail_date` and emits **no** webhook (no audit row written).
  - **Distinct from `payment_failed → new order`:** the existing terminal-failed-payment flow (`API_KIT.md §6k`) applies only **after** a terminal payment failure and requires creating a fresh order. Same-order reschedule applies **only before** payment is processed.
- **New: `order.rescheduled` webhook event.** Fires on successful reschedule (suppressed on no-op). Payload field set follows the existing `order.status_changed` envelope style (snake_case keys): `order_id`, `campaign_id`, `list_id`, `source`, `external_account_id`, `external_user_id`, `external_user_metadata`, `product_type`, `previous_mail_date`, `new_mail_date`. Routed only to webhook subscriptions whose `external_account_id` matches the order's. See `API_KIT.md §7`.
- **New: `order_rescheduled` iframe postMessage.** Emitted to the embedding parent (e.g., PropStream) on successful reschedule. Payload uses **camelCase** keys to match sibling postMessages (`order_cancelled`, `order_added`, `list_selected`): `{ type: "order_rescheduled", source: "ballpoint-mailer", version: 1, orderId, campaignId, previousMailDate, newMailDate }`. Suppressed on no-op. See `IFRAME_KIT.md §6`.
- **Note on casing.** Two consistent conventions, mirroring existing patterns:
  - **API requests + webhooks** use **snake_case** field keys (e.g., `mail_date`, `previous_mail_date`).
  - **Iframe → parent postMessage** payloads use **camelCase** keys (e.g., `newMailDate`).
  - Existing GET response field `orders[].mailDate` (camelCase, from v1.3.5/v1.3.6) is unchanged.
- **Internal — scheduled-orders cron race fix.** The expire-pass cron now re-checks `scheduled_production_date` (and `deleted_at`) inside the UPDATE WHERE clause so a concurrently-rescheduled order is no longer at risk of being incorrectly flipped to `payment_failed` by an in-flight cron snapshot.

## v1.3.9 — 2026-05-15

- **New: `open_create_direct_mail` iframe command (parent → iframe)** — lets PropStream open the same Create Direct Mail flow as the iframe's internal `+ Create Direct Mail` / `+ New Campaign` button. The command has no payload fields and reuses the iframe's existing `startNewCampaign()` path.
- **Guard:** the command requires a concrete active list context: an accepted first `set_list` with non-empty `listId` and positive `count`, or a selected `set_lists` item with non-empty `listId` and positive `count` after `list_selected`. This prevents opening a create flow against the iframe's built-in demo defaults.
- **New failure event:** `open_create_direct_mail_failed` emits instead of navigating when the command arrives before active list context exists, or if the create-flow handler is unavailable.
- **Schema alignment:** the inbound `set_lists.lists` schema now accepts the array shape already documented and consumed by the list-selector handler.

## v1.3.8 — 2026-05-14

- **New: `campaign_submitted.orders[].campaignInstanceId`** — opaque submit/split instance key surfaced on each entry of the `orders[]` array. `null` for `single` and `multi` (sequence) campaigns; opaque shared string value for `split` (A/B) sibling orders in the same `campaign_submitted` payload. Partners that ignore the field are unaffected.
- **Clarified — Campaign Dedup scope (cross-order, instance-gated)** — `IFRAME_KIT.md` Campaign Dedup section now states explicitly that cross-order `duplicate_in_campaign` dedup only fires when an order's `campaign_instance_id` is set and shared across sibling orders (the A/B split guard-rail). `single` campaigns, `multi`-send campaigns, list reuse across separate submissions, and edit-leads re-upload paths all leave `campaign_instance_id` NULL and no longer trigger cross-order dedup. Backend `campaign_id` remains list-level for tenant scoping and audit purposes, but is no longer the dedup gate by itself. New "Identifier reference — four distinct ids" subsection added to make the `campaign_id` (backend list-level) / `campaignId` (iframe-local postMessage) / `campaign_instance_id` (API/DB) / `campaignInstanceId` (iframe-emitted) distinction explicit, plus a one-line cross-tenant scoping note.
- **Clarified — `recipient_selection` worked example wording** — removed the parenthetical that said "multi-drop campaigns repeat the same per-drop count across orders in V1"; replaced with per-drop guidance making explicit that each drop in a sequence carries its own `orders[].pieces` derived from the same `recipient_selection`, and that Ballpoint does not dedupe across drops in a sequence (deferring to the Campaign Dedup section for the cross-order scope rules).

## v1.3.7 — 2026-05-14

- **Clarified — recipient dedupe scope (docs-only, no behavior change)** — `IFRAME_KIT.md` now states explicitly that Ballpoint does **not** perform intra-order recipient dedupe: duplicate recipient records uploaded to the same order are treated as separate recipient records unless another normal validation rule rejects the request (missing required fields, invalid address fields, or exceeding the order's `piece_count`). Ballpoint's automatic `duplicate_in_campaign` dedupe is cross-order, same-campaign only. `lead_id` and `type` (`mailing` / `property`) are not active recipient upload fields and are not used for dedupe — unknown fields are silently ignored; use `contact_id` for partner-side identifiers. Partners must collapse same-lead `property == mailing` to one recipient before count and upload for `Deliver To = both`. New explicit notes added to (1) the `piece_counts.both.dedup_off` semantics (per-lead unique send-address count, NOT `property_count + mailing_count`), (2) the top of Recipient Upload Flow, and (3) a new "What this does NOT do" subsection under Campaign Dedup (automatic).

## v1.3.6 — 2026-05-13

- **Correction: `campaign_submitted` scheduled mail date contract (supersedes v1.3.5 top-level multi-send fix)** — `orders[].mailDate` is now the canonical scheduled mail date field for each submitted order/drop. Removed the ambiguous top-level `campaign_submitted.mailDate` from this multi-order event shape during the staging contract-cleanup window. For multi-send campaigns, partners should read `orders[].mailDate` for each individual drop.

## v1.3.5 — 2026-05-13

- **New: `campaign_submitted.orders[].mailDate`** — additive per-drop field on each entry of the `orders[]` array. ISO date this specific drop is scheduled for. For `single` and `split` campaigns all entries share the same date (equal to top-level `mailDate`); for `multi` campaigns each entry carries its own per-drop date. Partners that ignore the field are unaffected.
- **Fix: `campaign_submitted.mailDate` (top-level) — multi-send** — previously emitted as `null` for `multi` campaigns; now resolves to the first drop's mail date when no campaign-level date is supplied. Use `orders[].mailDate` for the per-drop date.

## v1.3.4 — 2026-05-13

- **New: `GET /v1/billing/orders/{order_id}`** — retrieve a single order by ID. Tenant-scoped: partners only see their own orders; cross-tenant or unknown `order_id` both return `404` (never `403`) so order existence cannot be probed across tenants. Response shape matches each element of `GET /v1/billing/orders`. See `API_KIT.md §6c` for the field reference and example body. OpenAPI v2 spec updated with the `/v1/billing/orders/{order_id}` path, `401` and `404` responses declared. Postman collection: `Get order` request added to the `Orders` folder.

## v1.3.3 — 2026-05-13

- **Clarified — partner order-creation endpoint path** — `API_KIT.md §6k` step 5 and `IFRAME_KIT.md` payment-gate walkthrough step 5 now state the partner order-creation path as `POST /orders` on the API base URL (this is the live route; iframes have always called it there). `GET /v1/billing/partner/orders` (read-only dashboard/reconciliation) is unchanged. Also clarified the send-now (`pending_payment`) vs future-dated (`scheduled` + `payment_confirmed=false`) state split that was already implicit in the payment-gate behavior.

## v1.3.2 — 2026-05-12

Patch on top of v1.3.1 (edit_leads_requested + set_list refresh contracts):

- **Fix:** `set_lists` user-pick flow now caches the picked list's raw count so `edit_leads_requested.recipientCount` reflects the picked list, not the original first-receipt count.
- **Fix:** `set_list` refresh now preserves the currently-active `piece_counts` table when the refresh payload omits the key. Previously, an omitted `piece_counts` on refresh silently cleared the table and broke v1.3.0 pricing/dedup state. To explicitly clear or replace `piece_counts` on refresh, include the key in the refresh payload.
- **Fix:** When `piece_counts` is active, `set_list` refresh delegates the display + pricing update to the selection UI (Deliver To + Remove duplicates) instead of overriding with the raw count. Refresh no longer drops the user's combo selection.
- **Fix:** `set_lists` message schema now formally declares `externalAccountId` and `externalUserId`. These were already read by the handler but the schema gate previously stripped them. Affects partners using the `set_lists` multi-list flow with per-account / per-user attribution.

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

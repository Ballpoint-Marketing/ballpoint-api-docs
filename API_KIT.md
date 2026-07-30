# Ballpoint Marketing API — Partner Integration Kit

> **v1.7.28 · July 2026** · _deployed to staging; not yet deployed to production_
>
> Everything your dev team needs to integrate direct mail ordering, tracking,
> and real-time status updates into your platform.
>
> See [CHANGELOG.md](CHANGELOG.md) for revision history. For the embedded iframe pattern, see [IFRAME_KIT.md](IFRAME_KIT.md).

---

## Quick Start (30 seconds)

Verify your credentials work — paste this into a terminal:

```bash
curl -s -X POST https://api.ballpointmarketing.com/v1/billing/orders \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME" \
  -H "Idempotency-Key: ps-quickstart-$(date +%s)" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "camp_test",
    "product_type": "4x6_printed",
    "postage_type": "first_class",
    "piece_count": 10
  }'
```

You should get back `202 Accepted` with an `order_id`. That's a real test order — no mail is printed or sent with your test key.

**New here?** Start with [`START_HERE.md`](START_HERE.md) for a 5-minute quickstart.

### Additional Resources

| Resource | Location |
|----------|----------|
| 5-minute quickstart | [`START_HERE.md`](START_HERE.md) |
| Postman collection | [`examples/ballpoint.postman_collection.json`](examples/ballpoint.postman_collection.json) |
| Postman staging environment (PropStream integration testing) | [`examples/ballpoint-staging.postman_environment.json`](examples/ballpoint-staging.postman_environment.json) |
| Postman sandbox environment | [`examples/ballpoint-sandbox.postman_environment.json`](examples/ballpoint-sandbox.postman_environment.json) |
| Postman production environment | [`examples/ballpoint-production.postman_environment.json`](examples/ballpoint-production.postman_environment.json) |
| Express integration example | [`examples/express-integration/`](examples/express-integration/) |
| AWS Lambda webhook template | [`examples/lambda-webhook/`](examples/lambda-webhook/) |
| Cloudflare Worker webhook template | [`examples/cloudflare-worker-webhook/`](examples/cloudflare-worker-webhook/) |
| OpenAPI spec | [`docs/ballpoint-api-spec-v2.yaml`](docs/ballpoint-api-spec-v2.yaml) |
| Canonical webhook catalog, JSON Schemas, and golden fixtures | [`contracts/webhooks/`](contracts/webhooks/) |

---

## Table of Contents

1. [Your Credentials](#1-your-credentials)
2. [How It Works (End-to-End Flow)](#2-how-it-works-end-to-end-flow)
3. [How Billing Works](#3-how-billing-works)
4. [Integration Patterns](#4-integration-patterns)
5. [Product Catalog & Pricing](#5-product-catalog--pricing)
6. [API Reference](#6-api-reference)
   - [6a. Preview Cost](#6a-preview-cost)
   - [6a-ii. Preview Campaign Cost (Payment-Gate)](#6a-ii-preview-campaign-cost-payment-gate)
   - [6b. Create Order](#6b-create-order)
   - [6c. Get Order](#6c-get-order)
   - [6d. List Orders](#6d-list-orders)
   - [6e. Order Tracking](#6e-order-tracking)
   - [6f. Campaign Tracking](#6f-campaign-tracking)
   - [6g. Cancel Order](#6g-cancel-order)
   - [6h. Idempotency](#6h-idempotency)
   - [6i. User Attribution (X-External-User-ID)](#6i-user-attribution)
   - [6j. Per-end-user attribution (external_user_metadata)](#6j-per-end-user-attribution-external_user_metadata)
   - [6k. Confirm Payment (Partner Payment Gate)](#6k-confirm-payment-partner-payment-gate)
   - [6l. Partner Dashboard Endpoints](#6l-partner-dashboard-endpoints)
   - [6r. Partner Feature Configuration](#6r-partner-feature-configuration)
   - [6s. Search Recipients Across Direct Mail](#6s-search-recipients-across-direct-mail)
7. [Status Updates via Webhooks](#7-status-updates-via-webhooks)
   - [Per-piece RTS Push-Back (V1)](#per-piece-rts-push-back-v1)
8. [Real-Time UI via SSE (Optional)](#8-real-time-ui-via-sse-optional)
9. [Order Lifecycle Diagram](#9-order-lifecycle-diagram)
10. [Error Handling](#10-error-handling)
11. [Sandbox & Testing](#11-sandbox--testing)
12. [Endpoint Quick Reference](#12-endpoint-quick-reference)
13. [Sample Code: Express Webhook Handler](#13-sample-code-express-webhook-handler)
14. [Support](#14-support)

---

## 1. Your Credentials

| What | Value |
|------|-------|
| **Test API Key** | `pk_test_PARTNER_REPLACE_ME` |
| **Live API Key** | `pk_live_REPLACE_WITH_YOUR_LIVE_KEY` |
| **Base URL** | `https://api.ballpointmarketing.com` |
| **Webhook Secret** | Provisioned during onboarding — send us your endpoint URL |

### Authentication

Every request must include your API key in the `X-Partner-Key` header:

```
X-Partner-Key: pk_test_PARTNER_REPLACE_ME
```

- **Test key** (`pk_test_...`) — no real mail printed or sent. Use freely during development.
- **Live key** (`pk_live_...`) — real orders, real mail sent. Invoiced after completion.

Keys are provisioned by Ballpoint. Contact us if you need to rotate them.

---

## 2. How It Works (End-to-End Flow)

### Flow A — Embedded iframe

Your users select recipients in your platform, then the Ballpoint iframe handles product selection, copy editing, and order submission.

```
┌───────────────────────────────────────────────────────────────────────┐
│  EMBEDDED IFRAME FLOW                                                 │
│                                                                       │
│  1. User selects mailing list in your platform                           │
│         │                                                             │
│         ▼                                                             │
│  2. Recipient data flows into embedded Ballpoint iframe               │
│         │                                                             │
│         ▼                                                             │
│  3. User picks product, tweaks copy, submits                          │
│         │                                                             │
│         ▼                                                             │
│  4. POST /orders creates order ──────────────────────► Ballpoint API  │
│         │                                                             │
│         ▼                                                             │
│  5. Ballpoint team fulfills (prep → printing → stamping → shipping → complete) │
│         │                                                             │
│         ▼                                                             │
│  6. Status updates push to iframe via SSE                             │
│         │                                                             │
│         ▼                                                             │
│  7. USPS scans arrive 1-2 days later → tracking available             │
│         │                                                             │
│         ▼                                                             │
│  8. Check Tracking ───► GET /v1/orders/{id}/mail-tracking             │
│     (anytime)           GET /v1/campaigns/{id}/mail-tracking          │
└───────────────────────────────────────────────────────────────────────┘
```

### Flow B — API-Only (Future Partners)

> **Note:** No API-only clients exist yet. This pattern is documented for future partners.

```
Partner sends order via POST /orders with their own recipient data
  → Ballpoint fulfills
  → Status updates via webhooks
  → USPS tracking via GET endpoints
```

### What Ballpoint Handles

- **Campaign creation** — Ballpoint creates the campaign and provides you the `campaign_id`
- **Recipients** — **you provide the mailing list**. Your users select recipients in your platform; that data flows into the ordering process.
- **Fulfillment** — Ballpoint handles printing, handwriting, envelope stuffing, postage, and USPS drop-off

> **Note:** There is no `POST /campaigns` endpoint today. Campaign setup happens
> through the Ballpoint dashboard. Once a campaign is ready, you receive the
> `campaign_id` to reference when creating orders via the API.

### What Your Platform Calls via API

- **Preview cost** — show your users what they'll pay before ordering
- **Create order** — submit an order referencing an existing campaign
- **List orders** — query orders by user, status, with pagination
- **Check tracking** — get USPS delivery status for an order or campaign
- **Cancel order** — cancel before production starts
- **Receive webhooks / SSE** — get status updates pushed to your server or browser in real-time

---

## 3. How Billing Works

Ballpoint supports two partner billing models, set per-account during onboarding.

### Standard invoiced partners (`billing_mode: none`)

Orders are accepted immediately on `POST /orders` — no balance check, no upfront charge. Ballpoint invoices separately after orders are marked `complete`; payment happens outside the API on the partner's audit cycle. This is the default for new partners.

### Partner-billed / payment-gated partners (`requires_payment_confirmation = TRUE`)

For partners who collect the end-user payment on their side (for example, PropStream), orders are created without starting production until payment is confirmed. Send-now orders enter `pending_payment`; future-dated orders remain `scheduled` with `payment_confirmed = false`. The end-user pays through the partner's payment provider; the partner's backend then calls `/confirm-payment` to flip the order into the production lifecycle.

Ballpoint never receives card or payment-method data. The partner key required for `/confirm-payment` must stay server-side.

For the full endpoint contract, see [§6k Confirm Payment](#6k-confirm-payment-partner-payment-gate).

### Pricing

Cost = `unit_price_tcents × piece_count`. No minimums, no surcharges, no per-request fees. See [§5 Product Catalog & Pricing](#5-product-catalog--pricing) for the full price list.

### Cancellations

Cancelling an order before production `prep` begins removes it from the fulfillment queue.

- *Invoiced partners*: no upfront charge means no refund — the cancelled order simply won't appear on the next invoice.
- *Payment-gated partners*: cancelling from `pending_payment` or `payment_failed` is free (no debit ever happened). Cancelling from `accepted` (after `/confirm-payment success`) auto-refunds the partner-balance debit.

---

## 4. Integration Patterns

### Pattern A — Server-to-Server

> **Note:** No API-only clients exist yet. This pattern is documented for future partners who want direct API integration without an iframe.

Your backend creates orders and receives webhook status updates.

```
┌──────────────┐                    ┌──────────────────┐
│              │  POST /orders      │                  │
│  Partner     │───────────────────►│  Ballpoint API   │
│  Server      │                    │                  │
│              │◄───────────────────│                  │
│              │  webhook POST      │                  │
│              │  (status updates)  │                  │
└──────────────┘                    └──────────────────┘
```

### Pattern B — Embedded iframe

Your platform embeds a Ballpoint iframe. Your users select recipients in your platform, then the iframe handles product selection, copy editing, and order submission. SSE provides real-time status updates in the browser.

```
┌─────────────────┐
│  Partner UI      │  1. User selects mailing list
│                  │  2. Data passed to iframe
│  ┌─────────────┐ │
│  │ Ballpoint   │ │  3. User picks product, edits copy, submits
│  │ iframe      │ │        │
│  └──────┬──────┘ │        │
└─────────┼────────┘        │
          │                 ▼
          │        ┌──────────────────┐
          │        │  Ballpoint API   │  4. POST /orders
          │        │                  │  5. Team fulfills order
          │◄───────│  SSE stream      │  6. Status updates push to iframe
          │        └──────────────────┘
```

SSE requires cookie auth with `withCredentials: true`. The iframe must be served over HTTPS. CORS is configured per-partner — provide your production domain during onboarding.

Webhooks remain the backend source of truth — SSE is for browser-side real-time display only.

For the full iframe integration contract — embed setup, parent ↔ iframe message contracts, recipient upload flow, partner payment gate walkthrough — see [IFRAME_KIT.md](IFRAME_KIT.md).

---

## 5. Product Catalog & Pricing

### Products

Ballpoint produces 7 product types:

#### Postcards

No envelope. Handwriting is always blue ink.

| Product Type | Description | Postage Options |
|-------------|-------------|-----------------|
| `4x6_printed` | Standard 4x6 printed postcard | `first_class`, `standard` |
| `4x6_cursive` | 4x6 pen-written postcard (cursive) | `first_class` only |
| `6x9_printed` | Large 6x9 printed postcard | `first_class`, `standard` |
| `6x9_cursive` | 6x9 pen-written postcard (cursive) | `first_class` only |

#### Letters

Envelope + insert. Letter orders **require** an `envelope_style` field.

| Product Type | Envelope | Insert | Envelope Size | Postage Options |
|-------------|----------|--------|---------------|-----------------|
| `color_letter` | Printed | Full-color printed 8.5x11 (tri-folded to fit the envelope) | #10 | `first_class`, `standard` |
| `hybrid_letter` | Handwritten | Printed | 5x7 | `first_class`, `presort` |
| `greeting_letter` | Handwritten | Handwritten | 5x7 | `first_class`, `presort` |

#### Envelope Styles

Available styles: `candy`, `party`, `pastel`, `confetti`, `desert`, `floral`, `stone`, `retro`, `deco`, `doodle`, `plain_white`

- **`color_letter`** uses #10 envelopes — only `plain_white` is supported.
- **`color_letter` is full color only in V1.** There is no black-and-white print option; the end user chooses only between the supported postage classes.
- **`color_letter` canvas artwork is one-sided in V1.** Send `canvas_json.front`; `canvas_json.back` is not required and is ignored for the printed insert. Two-sided canvas products continue sending both `front` and `back`.
- The Color Letter editor stores the 11 V1 dynamic fields as canonical `#Token#` values. Ballpoint resolves sender fields from the saved sender profile and owner/property fields from each recipient's `placeHolders`; absent values print blank.
- **`color_letter` V1 accepts at most 500 pieces per order.** Its complete `canvas_json` must be at most 20 MiB, 50 levels deep, 10,000 JSON nodes, and 1,000 Fabric objects. Embedded image sources must be base64 PNG, JPEG, or WebP and no more than 14 MiB encoded. Remote image sources must be HTTPS assets under Ballpoint's approved `/images/` or `/assets/` paths, or PropStream's approved `/direct-mail/` S3 prefix. Relative Ballpoint asset paths are also accepted. Other hosts, URL fragments, unsupported query parameters, and merge tokens inside image URLs are rejected before order creation. These request-validation limits do not change existing two-sided products.
- **`hybrid_letter`** and **`greeting_letter`** use 5x7 envelopes — all decorative styles available.
- **Postcards** — do not include `envelope_style` (the API will reject it).

### Pricing Table

The table below is the Ballpoint **base-price schedule effective July 12, 2026**.
Prices are in **tenth-cents** (tcents). Divide by 10,000 for dollars:
`5388 tcents = $0.5388/piece`. Partner-authenticated pricing and preview
responses apply that account's configured markup to the primary display-price
fields; `partner_cost_*` preview fields retain the base price.

| Product | Postage | Per Piece (tcents) | Per Piece ($) | 500 pieces |
|---------|---------|-------------------|---------------|------------|
| 4x6 Printed Postcard | First Class | 5,388 | $0.5388 | $269.40 |
| 4x6 Printed Postcard | Standard | 5,144 | $0.5144 | $257.20 |
| 4x6 Cursive Postcard | First Class | 7,888 | $0.7888 | $394.40 |
| 6x9 Printed Postcard | First Class | 6,142 | $0.6142 | $307.10 |
| 6x9 Printed Postcard | Standard | 5,742 | $0.5742 | $287.10 |
| 6x9 Cursive Postcard | First Class | 8,642 | $0.8642 | $432.10 |
| Color Letter (#10) | First Class | 8,620 | $0.8620 | $431.00 |
| Color Letter (#10) | Standard | 5,970 | $0.5970 | $298.50 |
| Hybrid Letter (5x7) | First Class | 10,900 | $1.0900 | $545.00 |
| Hybrid Letter (5x7) | Standard Class (API: `presort`) | 8,037 | $0.8037 | $401.85 |
| Greeting Letter (5x7) | First Class | 14,907 | $1.4907 | $745.35 |
| Greeting Letter (5x7) | Standard Class (API: `presort`) | 9,737 | $0.9737 | $486.85 |

Total cost = `unit_price_tcents × piece_count`. No minimums, no surcharges.

**PropStream label mapping:** for `hybrid_letter` and `greeting_letter`, the
customer-facing iframe and pricing dashboard label is **Standard Class**, while
the API value remains `postage_type: "presort"`. Do not send `standard` for
those two products. The `standard` API value continues to identify Standard
Class postage for supported postcards and `color_letter`.

You can also fetch pricing programmatically:

```bash
curl -s https://api.ballpointmarketing.com/v1/billing/pricing \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME"
```

Filter by product:

```bash
curl -s "https://api.ballpointmarketing.com/v1/billing/pricing?product_type=4x6_printed" \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME"
```

Response when no partner markup is configured (partner markup changes only
`unit_price_tcents`, not the underlying base schedule):

```json
[
  {
    "product_type": "4x6_printed",
    "postage_type": "first_class",
    "unit_price_tcents": 5388,
    "min_quantity": 1,
    "max_quantity": null,
    "description": "4x6 printed postcard - 1st class",
    "sla_business_days": 3
  },
  {
    "product_type": "4x6_printed",
    "postage_type": "standard",
    "unit_price_tcents": 5144,
    "min_quantity": 1,
    "max_quantity": null,
    "description": "4x6 printed postcard - standard",
    "sla_business_days": 3
  }
]
```

#### `sla_business_days` (integer, additive since v1.7.7)

Business days of production lead time between the scheduled production start date and `mail_date` for the row's `product_type`. Range: **1–15** (practically **3–6** today). Identical across all postage variants of the same product type.

Current values per partner-sendable product type:

| Product | `sla_business_days` |
|---------|---------------------|
| `4x6_printed`, `6x9_printed` | **3** |
| `4x6_cursive`, `6x9_cursive` | **4** |
| `color_letter`, `hybrid_letter`, `greeting_letter` | **6** |

This value is a UX affordance so partners can render an accurate date-picker minimum (earliest selectable `mail_date` = today + `sla_business_days` business days, skipping Saturday/Sunday). It is not currently enforced server-side at order creation — server-side enforcement is planned separately. Read this field per row and pass it into your date-picker instead of hard-coding a uniform lead time.

---

## 6. API Reference

All endpoints use `https://api.ballpointmarketing.com` as the base URL.

Every request must include:

```
X-Partner-Key: pk_test_PARTNER_REPLACE_ME
```

Write requests (`POST`, `PATCH`) must also include `Content-Type: application/json`. Read requests (`GET`) do not need it.

---

### 6a. Preview Cost

Show your user what they'll pay before creating an order.

```
POST /v1/billing/orders/preview
```

**Request:**

```bash
curl -X POST https://api.ballpointmarketing.com/v1/billing/orders/preview \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME" \
  -H "X-External-User-ID: user_789" \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "4x6_printed",
    "postage_type": "first_class",
    "piece_count": 500
  }'
```

**Response (`200`):**

```json
{
  "product_type": "4x6_printed",
  "postage_type": "first_class",
  "piece_count": 500,
  "unit_price_tcents": 5388,
  "total_tcents": 2694000,
  "total_dollars": "$269.4000",
  "partner_cost_unit_price_tcents": 5388,
  "partner_cost_total_tcents": 2694000,
  "partner_cost_total_dollars": "$269.4000",
  "billing_mode": "none",
  "balance_cents": null,
  "balance_after_cents": null,
  "limits": {
    "passed": true,
    "checks": [
      {"type": "order_limit", "passed": true, "order_cost_cents": 26940, "limit_cents": 500000}
    ]
  }
}
```

The preview runs the same limit checks as real order creation but reports results as warnings. If `limits.passed` is `false`, the real order would fail — show the user why before they submit.

> **Note:** For accounts with `billing_mode: none`, `balance_cents` and
> `balance_after_cents` are `null` and no balance check is added. The preview
> still validates product type, postage, and piece count. If a partner markup
> is configured, the primary price fields show the marked-up value while the
> `partner_cost_*` fields remain the Ballpoint base price.

> **Payment-gate amount source (legacy single-order path):** This endpoint still works for single-order previews and pre-submission UX. For payment-gated submissions with one or more drops, prefer the campaign-level endpoint [§6a-ii](#6a-ii-preview-campaign-cost-payment-gate) — one call returns the selected-order breakdown plus a chargeable-now total. On both endpoints `partner_cost_total_tcents` is the raw wholesale tenth-cent math and `total_tcents` / `total_dollars` are display-only. Only the campaign endpoint exposes the exact successful-confirmation cents via `partner_debit_cents` / `campaign_partner_debit_cents`.

---

### 6a-ii. Preview Campaign Cost (Payment-Gate)

One call prices a **caller-selected set of order IDs from one campaign** and returns, per order and campaign-wide, both the raw wholesale amount in tenth-cents and the **exact `/confirm-payment` ledger result in whole cents**. This is the canonical pricing endpoint for the payment gate — it **replaces** the legacy pattern of calling `POST /v1/billing/orders/preview` once per order/drop after `campaign_submitted`.

The endpoint prices exactly the set it is given. It does **not** compute billing windows or decide which drops are due — the caller selects the intended set of orders (for example, only the drops inside its own billing window) and is responsible for that selection until a future contract decision changes this. After previewing, call `/confirm-payment` only for response rows where `excluded_from_totals=false`; rows marked excluded are not part of the quoted campaign debit.

```
POST /v1/billing/campaigns/preview
X-Partner-Key: pk_live_...
Content-Type: application/json
```

**Auth.** Partner-only. `X-Partner-Key` required; non-partner keys (e.g. `X-API-Key`) get `401 Unauthorized`.

**When to call.** Server-to-server, after the iframe emits `campaign_submitted` and every selected order has a non-null `ballpointOrderId`. Recipient upload must be complete for each order selected for this payment event; for every selected [`POST /v1/billing/orders/{order_id}/recipients`](#6n-upload-recipients-initial-upload) response, verify `ready === true` and `piece_count > 0` before previewing. For A/B Split, upload a different recipient slice to each selected variant; do not reuse the full list for both orders. Pass the **subset you intend to charge in this payment event** (any subset of one campaign is accepted — from a single drop to the full submission). If any selected id is still `null` or any selected order's recipient upload is incomplete/zeroed, do not open the payment step or call this endpoint yet.

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `order_ids` | string[] | Yes | The `ballpointOrderId`s from `campaign_submitted.orders[]`. Must all belong to the **same** backend campaign. Order matters — the response `orders[]` preserves this order. Min 1, max 100. |
| `expected_order_count` | integer | Yes | Must equal `len(order_ids)`. A safety check to catch client-side miscounts before pricing runs. |

**Example**

```bash
curl -X POST https://api.ballpointmarketing.com/v1/billing/campaigns/preview \
  -H "X-Partner-Key: $PARTNER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "order_ids": ["ord_7f3a2b", "ord_8a4b1c", "ord_9b5c2d"],
    "expected_order_count": 3
  }'
```

**Response (`200`)**

```json
{
  "campaign_id": "camp_2026_q2",
  "currency": "USD",
  "order_ids": ["ord_7f3a2b", "ord_8a4b1c", "ord_9b5c2d"],
  "orders": [
    {
      "order_id": "ord_7f3a2b",
      "production_status": "pending_payment",
      "payment_confirmed": false,
      "product_type": "4x6_printed",
      "postage_type": "first_class",
      "piece_count": 500,
      "unit_price_tcents": 5388,
      "total_tcents": 2694000,
      "partner_cost_unit_price_tcents": 5388,
      "partner_cost_total_tcents": 2694000,
      "partner_debit_cents": 26940,
      "price_source": "computed_from_persisted_order_inputs",
      "excluded_from_totals": false,
      "exclusion_reason": null
    },
    {
      "order_id": "ord_8a4b1c",
      "production_status": "scheduled",
      "payment_confirmed": false,
      "product_type": "4x6_printed",
      "postage_type": "first_class",
      "piece_count": 97,
      "unit_price_tcents": 5388,
      "total_tcents": 522636,
      "partner_cost_unit_price_tcents": 5388,
      "partner_cost_total_tcents": 522636,
      "partner_debit_cents": 5227,
      "price_source": "computed_from_persisted_order_inputs",
      "excluded_from_totals": false,
      "exclusion_reason": null
    },
    {
      "order_id": "ord_9b5c2d",
      "production_status": "accepted",
      "payment_confirmed": true,
      "product_type": "4x6_printed",
      "postage_type": "first_class",
      "piece_count": 500,
      "unit_price_tcents": 5388,
      "total_tcents": 2694000,
      "partner_cost_unit_price_tcents": 5388,
      "partner_cost_total_tcents": 2694000,
      "partner_debit_cents": null,
      "price_source": "computed_from_persisted_order_inputs",
      "excluded_from_totals": true,
      "exclusion_reason": "already_confirmed"
    }
  ],
  "campaign_partner_cost_total_tcents": 3216636,
  "campaign_partner_debit_cents": 32167
}
```

**Response fields**

| Field | Type | Notes |
|---|---|---|
| `campaign_id` | string | The Ballpoint backend campaign id all `order_ids` belong to. |
| `currency` | string | Always `"USD"` for V1. |
| `order_ids` | string[] | Echo of the request `order_ids`, in the same order. |
| `orders[]` | array | Per-order pricing, **same order as `order_ids`**. |
| `orders[].order_id` | string | Ballpoint order id. |
| `orders[].production_status` | string | Current production status (`scheduled`, `pending_payment`, `accepted`, `prep`, `printing`, `complete`, `cancelled`, `payment_failed`, etc.). |
| `orders[].payment_confirmed` | boolean | Whether `/confirm-payment` has already succeeded for this order. |
| `orders[].product_type` | string | Persisted product type at order creation. |
| `orders[].postage_type` | string | Persisted postage type. |
| `orders[].piece_count` | integer | Persisted piece count. |
| `orders[].unit_price_tcents` | integer | **Display/retail** per-piece price (may include markup). Not the debit amount. |
| `orders[].total_tcents` | integer | **Display/retail** total for this order (`unit_price_tcents × piece_count`). Not the debit amount. UX/display only. |
| `orders[].partner_cost_unit_price_tcents` | integer | **Wholesale** per-piece price. |
| `orders[].partner_cost_total_tcents` | integer | **Raw wholesale total in tenth-cents** (`partner_cost_unit_price_tcents × piece_count`). May contain a fractional cent (e.g. `522636` = $52.2636). **Not the exact ledger debit** — the ledger settles whole cents; see `partner_debit_cents`. Returned even for excluded orders (for reconciliation), but only chargeable-now orders contribute to the campaign totals. |
| `orders[].partner_debit_cents` | integer \| null | **Exact whole-cent ledger amount recorded when `/confirm-payment` succeeds, provided the pricing tier, billing mode, and persisted product/postage/piece-count inputs remain unchanged.** For `stripe` / `manual` billing it is `ceil(partner_cost_total_tcents / 100)`: a fractional cent rounds **up, never down** (`522636` tcents → `5227` cents). It is `0` when the account has billing disabled (`billing_mode=none`, which records no charge or usage), and `null` when `excluded_from_totals=true`. The field is always present. Do **not** call `/confirm-payment` for an excluded row as part of this quoted payment event. This is an amount quote, not authorization: confirmation can still fail account, balance, piece-cap, or spending-limit checks. |
| `orders[].price_source` | string | Always `"computed_from_persisted_order_inputs"` for this endpoint as of PROPS-3087 — pricing is recomputed live from the persisted `product_type` / `postage_type` / `piece_count` via the **current** pricing tables (no raw client inputs accepted), so the preview equals the `/confirm-payment` charge. `"frozen"` (a price snapshot reused as-is) is retained in the enum for backward compatibility but is **no longer emitted** by this endpoint. |
| `orders[].excluded_from_totals` | boolean | `true` if this order is **not** added into `campaign_partner_cost_total_tcents` (see "Chargeable-now semantics" below). |
| `orders[].exclusion_reason` | string \| null | One of `"already_confirmed"`, `"cancelled"`, `"failed"`, `"payment_failed"`, `"not_chargeable_status"`. `null` when `excluded_from_totals=false`. |
| `campaign_partner_cost_total_tcents` | integer | **Raw wholesale sum in tenth-cents** of `partner_cost_total_tcents` across **chargeable-now orders only** (see below). May contain fractional cents; **not the exact ledger amount** — use `campaign_partner_debit_cents` for that. Excludes already-confirmed and terminal/failed orders. tcents → dollars: divide by 10000. |
| `campaign_partner_debit_cents` | integer | **Exact total ledger amount in whole cents when `/confirm-payment` succeeds, provided the pricing tier, billing mode, and persisted product/postage/piece-count inputs remain unchanged.** Sum of the per-order `partner_debit_cents` — each stripe/manual order settles **independently**, so this is the sum of per-order ceilings, **not** one ceiling of the summed raw tcents (two orders of `5001` tcents debit `51 + 51 = 102` cents, not `101`). Returns `0` for `billing_mode=none`. This does not guarantee that confirmation will pass account, balance, piece-cap, or spending-limit checks. |

**Chargeable-now semantics — IMPORTANT**

`campaign_partner_cost_total_tcents` is the sum of `partner_cost_total_tcents` for orders that satisfy **both**:

- `production_status` is one of `{scheduled, pending_payment, accepted}`, **AND**
- `payment_confirmed === false`

Every other order is reported per-order (so you can audit) but **excluded** from the campaign total via `excluded_from_totals: true` with an `exclusion_reason`:

| `exclusion_reason` | Meaning |
|---|---|
| `already_confirmed` | `payment_confirmed === true`. The payment outcome was already confirmed and the account's billing policy already ran for this order. Do not collect or confirm it again. |
| `cancelled` | Order is cancelled — no charge is due. |
| `failed` | Order is in a non-recoverable failed state. |
| `payment_failed` | `/confirm-payment` was previously called with `status:failed` and the order is in `payment_failed` (terminal). |
| `not_chargeable_status` | `production_status` is outside `{scheduled, pending_payment, accepted}` (e.g. already in `prep`/`printing`/`complete`). |

This is by design — calling `POST /v1/billing/campaigns/preview` twice in a row (e.g. after one drop's `/confirm-payment` has succeeded) will return a lower total the second time, never re-billing the confirmed drop.

**Three price layers — do not mix them**

| Layer | Fields | Unit | Use for |
|---|---|---|---|
| Customer display/retail | `unit_price_tcents`, `total_tcents` | tenth-cents | What the end customer sees/pays (includes partner markup). Never the partner debit. |
| Raw Ballpoint wholesale | `partner_cost_unit_price_tcents`, `partner_cost_total_tcents`, `campaign_partner_cost_total_tcents` | tenth-cents | Reconciliation and audit of exact per-piece wholesale math (may carry fractional cents). |
| Exact ledger result | `partner_debit_cents`, `campaign_partner_debit_cents` | whole cents | The amount Ballpoint records on `/confirm-payment` success (`0` when billing is disabled). Use it for stripe balance forecasting and for manual-billing statement/usage reconciliation. |

The debit-cents values equal the amount recorded on successful `/confirm-payment` **provided the pricing tier, billing mode, and persisted `product_type` / `postage_type` / `piece_count` inputs do not change between preview and confirm** (pricing is resolved live from those inputs at both moments — see `price_source`). For `stripe` and `manual`, each chargeable order is ceilinged independently to whole cents; for `billing_mode=none`, the result is `0` because no charge or usage entry is recorded. This preview quotes the amount but does not run every confirmation-time eligibility/limit/balance check. Re-preview after any order/recipient edit or if the tier or billing mode changes.

**tcents convention.** All `*_tcents` fields are integer **tenth-cents**. Dollars = `tcents / 10000`. Example: `2694000` tcents = `$269.40`.

**Errors**

| HTTP | `code` | When |
|---|---|---|
| `401` | (auth-layer error) | Missing `X-Partner-Key`, or an `X-API-Key` was sent instead. |
| `409` | `PAYMENT_GATE_NOT_ACTIVE` | Account does not have `requires_payment_confirmation = TRUE`. Mirrors the same error on [`/confirm-payment`](#6k-confirm-payment-partner-payment-gate). |
| `422` | `ORDER_IDS_EMPTY` | `order_ids` is missing or `[]`. |
| `422` | `ORDER_IDS_DUPLICATE` | Same `order_id` appears more than once in `order_ids`. |
| `422` | `ORDER_IDS_LIMIT_EXCEEDED` | More than 100 ids in `order_ids`. |
| `400` | `ORDER_COUNT_MISMATCH` | `expected_order_count !== len(order_ids)`. |
| `404` | `ORDER_NOT_FOUND` | Any id in `order_ids` is missing **or** belongs to a different tenant. The whole request is rejected — there is **no partial response**. |
| `400` | `MIXED_CAMPAIGN_IDS` | The provided `order_ids` do not all belong to the same backend campaign. |
| `409` | `INVALID_PIECE_COUNT` | At least one persisted order has `piece_count <= 0`. The order cannot be priced or confirmed; correct its recipient slice before collecting payment. This is distinct from `NO_PRICING`: the product/postage price may exist, but zero pieces are not billable. |

**Why a campaign-level endpoint (vs N calls to `/v1/billing/orders/preview`)**

- **One round-trip** per campaign instead of N — simpler partner code, fewer rate-limit concerns, atomic snapshot of all orders' pricing at one instant.
- **Server-computed totals** — Ballpoint applies the chargeable-now filter and the exact whole-cent ledger settlement (`campaign_partner_debit_cents`) server-side; partners do not have to re-implement either.
- **No double-charge risk on retries** — re-previewing after partial success drops already-confirmed orders out of the total automatically.

For pre-submission per-product previews (e.g. "show the user a price for a 500-piece postcard before they click Submit"), the single-order `POST /v1/billing/orders/preview` endpoint ([§6a](#6a-preview-cost)) remains the right tool — it doesn't require created orders.

---

### 6b. Create Order

```
POST /v1/billing/orders
```

**Required headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-Partner-Key` | Yes | Your API key |
| `Idempotency-Key` | Yes | Unique UUID per order (see [6h. Idempotency](#6h-idempotency)) |
| `Content-Type` | Yes | `application/json` |
| `X-External-User-ID` | Recommended | Attributes the order to a specific platform user (see [6i](#6i-user-attribution)) |

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `campaign_id` | string | Yes | Campaign to fulfill (provided by Ballpoint) |
| `product_type` | string | Yes | One of the 7 product types |
| `postage_type` | string | Yes | `first_class`, `standard`, or `presort` |
| `piece_count` | integer | Yes | Number of mail pieces |
| `envelope_style` | string | Letters only | Required for letter products, rejected for postcards |
| `external_id` | string | No | Your internal reference ID (flows back in webhooks) |
| `campaign_instance_id` | string | No | Optional submit/split instance key (1–64 chars, `[A-Za-z0-9_-]`). When shared across orders in the same campaign it enables cross-order recipient dedup as a guard-rail (A/B split disjoint slices). `null`/omitted bypasses cross-order dedup. Populate on A/B split sibling orders only; single-send, multi-send, and edit-leads paths leave it `null`. Round-tripped on GET responses. |
| `variant` | string | No | A/B split variant identifier; one of `"a"` \| `"b"`. Case-insensitive (server normalizes to lowercase + trims whitespace). Required only on A/B split sibling orders so they can be reconstructed after reload. Persisted to `metadata.variant` server-side and round-tripped on GET responses. Single-send, multi-send, and edit-leads paths leave it `null`. |
| `deliver_to` | string | No | Optional, additive. Recipient address routing the user selected on the iframe's piece-selection page when a `piece_counts` table was active. One of `"mailing"` \| `"property"` \| `"both"`. Case-insensitive and trimmed server-side (`"MAILING"`, `" both "` → `"mailing"`, `"both"`); any other value is rejected with 422. Sent only when a validated recipient selection exists; paths without `piece_counts` leave it `null`. Persisted to `metadata.deliver_to` and round-tripped on GET responses. Iframe-driven persistence — no partner-side action required. |
| `remove_duplicate_addresses` | boolean | No | Optional, additive. Whether the user enabled the "Remove duplicates" checkbox on the iframe's piece-selection page (paired with `deliver_to`). Persisted to `metadata.remove_duplicate_addresses` and round-tripped on GET responses **even when `false`**, so partners can read back the user's exact selection. `null`/absent when no recipient-selection UI was shown. Iframe-driven persistence — no partner-side action required. |

**Partner iframe compatibility sender (`POST /orders`):**

The partner/iframe request shape may include an optional `sender` object. Empty or `null` contact fields remain optional for partial Marketing Profiles. Invalid non-empty contact values return `422` before idempotency or order creation.

| `sender` field | Accepted format |
|----------------|-----------------|
| `zip` | 5 digits (`12345`), 9 digits (`123456789`), or ZIP+4 (`12345-6789`); maximum 10 characters. |
| `phone` | 10 digits, or 11 digits beginning with `1`; `+`, parentheses, spaces, periods, and hyphens are accepted formatting. Letters and extensions are rejected; maximum 20 characters. |

Valid formatted values are persisted as supplied by the API client. The embedded iframe may normalize a valid phone to `AAA-BBB-CCCC` before sending it.

**Example — postcard:**

```bash
curl -X POST https://api.ballpointmarketing.com/v1/billing/orders \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME" \
  -H "X-External-User-ID: user_789" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "camp_test",
    "product_type": "4x6_printed",
    "postage_type": "first_class",
    "piece_count": 500,
    "external_id": "ps_order_12345"
  }'
```

**Response (`202 Accepted`):**

```json
{
  "order_id": "ord_7f3a2b",
  "status": "accepted",
  "campaign_id": "camp_test",
  "product_type": "4x6_printed",
  "piece_count": 500,
  "unit_price_tcents": 5388,
  "total_price_tcents": 2694000,
  "external_id": "ps_order_12345",
  "external_user_id": "user_789",
  "created_at": "2026-07-18T14:00:00Z"
}
```

The `unit_price_tcents` / `total_price_tcents` above are a **creation-time
estimate** persisted on the order row for display — they are **not** the amount
debited. As of PROPS-3087 the wholesale charge is resolved against the
**current** pricing tier at [`/confirm-payment`](#6k-confirm-payment-partner-payment-gate),
and [`POST /v1/billing/campaigns/preview`](#6a-ii-preview-campaign-cost-payment-gate)
recomputes the same way — always refetch that preview immediately before
charging. Because these estimate columns are captured at creation, an order
created before the July 12, 2026 cutover may still show the prior base price in
these fields, but the debit uses the pricing tier in effect at confirmation.

**Example — letter (requires `envelope_style`):**

```bash
curl -X POST https://api.ballpointmarketing.com/v1/billing/orders \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME" \
  -H "Idempotency-Key: 660f9500-f30c-52e5-b827-557766551111" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "camp_test",
    "product_type": "hybrid_letter",
    "postage_type": "presort",
    "piece_count": 200,
    "envelope_style": "confetti"
  }'
```

---

### 6c. Get Order

Fetch a single order by ID — use this to check current status.

> **Not a mid-flow drop-discovery API.** `GET /v1/billing/orders/{order_id}` (and the List variant in §6d) return **persisted Ballpoint orders only**. For iframe-driven campaigns — Single Send, Multi Send, and A/B Split — individual drops do **not** exist server-side until the end-user clicks **Continue to Payment** and the iframe emits `campaign_submitted` (see [IFRAME_KIT.md `campaign_created` timing note](IFRAME_KIT.md#campaign_created--campaign-created-before-submission)). Use `campaign_submitted.orders[].ballpointOrderId` as the reconciliation trigger; **do not poll `GET /v1/billing/orders` for individual drops during scheduling / mid-flow** — the ids carried on `campaign_created.orderIds` and `order_added.orderId` are local pre-API ids and have no server-side row to fetch yet.

```
GET /v1/billing/orders/{order_id}
```

**Example:**

```bash
curl -s https://api.ballpointmarketing.com/v1/billing/orders/ord_7f3a2b \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME"
```

**Response (`200`):**

```json
{
  "id": "ord_7f3a2b",
  "campaign_id": "cmp_abc123",
  "account_id": "acct_partner_propstream",
  "source": "propstream",
  "external_account_id": "ps_acct_42",
  "external_user_id": "user_789",
  "product_type": "4x6_printed",
  "postage_type": "first_class",
  "piece_count": 500,
  "unit_price_tcents": 5054,
  "total_price_tcents": 2527000,
  "production_status": "printing",
  "usps_status": null,
  "display_status": "printing",
  "payment_confirmed": true,
  "envelope_style": null,
  "print_font": null,
  "shipping_option": null,
  "proof_approval_status": null,
  "metadata": "{\"campaign_ref\": \"abc123\"}",
  "customer_info": null,
  "sla_due_at": "2026-03-09T14:00:00Z",
  "priority": "normal",
  "render_status": "complete",
  "status_changed_at": "2026-03-02T09:00:00Z",
  "created_at": "2026-03-01T14:00:00Z"
}
```

`display_status` is the single field to show your users. `usps_status` is `null` until USPS scans arrive (1–2 days after production completes).

Tenant scoping: partners only see their own orders. Both cross-tenant and unknown `order_id` return `404` (never `403`) so existence cannot be probed across tenants.

`customer_info` is `null` unless populated (object with `name`, `website`, `rma`, `phone`, `shipping_address` — only present keys returned). `envelope_style`, `print_font`, `shipping_option`, `proof_approval_status` are `null` for products that do not use them. `metadata` is returned as a JSON-encoded string; call `JSON.parse(body.metadata)` if you need nested fields. Response shape matches each element of `GET /v1/billing/orders` (§6d).

**`campaign_instance_id`** (string or null): Surfaced verbatim from the stored column (previously persisted but not exposed; now round-tripped on GET). Set only on A/B split sibling orders so the iframe can reconstruct split groupings after a reload; `null` on single-send, multi-send, and edit-leads orders.

**`metadata.variant`** (string `"a"` | `"b"`, or absent): Present only on A/B split sibling orders, paired with `campaign_instance_id`. To read it: `JSON.parse(body.metadata).variant`. Absent on single-send, multi-send, and edit-leads orders.

**`metadata.deliver_to`** (string `"mailing"` | `"property"` | `"both"`, or absent) and **`metadata.remove_duplicate_addresses`** (boolean, or absent): Round-tripped from the corresponding optional POST `/orders` fields (see §6b request body). Present when the iframe submitted the order with a recipient selection resolved from a `piece_counts` table; absent otherwise. `remove_duplicate_addresses` is persisted even when `false`, so partners can read back the user's exact selection. To read: `JSON.parse(body.metadata).deliver_to` / `JSON.parse(body.metadata).remove_duplicate_addresses`. Additive — partners that don't consume them are unaffected. Same shape on each element of `GET /v1/billing/orders` (§6d).

**`payment_confirmed`** (boolean or null): For accounts with partner-side payment confirmation gating (`requires_payment_confirmation = TRUE`, e.g. PropStream): `true` once `POST /v1/billing/orders/{order_id}/confirm-payment` has fired with `status: success`; `false` while the order is still awaiting partner confirmation. For accounts that do not use the payment gate, the value is always `null` and the field should be ignored — their billing lifecycle does not use partner-side payment confirmation.

**ID reconciliation.** The `campaign_id` returned here (and on `GET /v1/billing/orders`, §6d) is Ballpoint's backend **grouping key**, derived from your account + `list_id` — one Ballpoint campaign per `list_id`. It is **not** the iframe `campaignId` from `campaign_created`/`campaign_submitted` (that one is an iframe-local, per-Direct-Mail id with no backend relationship). For **per-order** reconciliation, use **`campaign_submitted.orders[].ballpointOrderId`**, which equals the `id` on this response. Note: Get Orders does not return a standalone `list_id` field — it is encoded in `campaign_id`.

> **Reminder — `campaign_submitted` is the discovery trigger, not a poll loop.** For Multi Send and A/B Split, do not call `GET /v1/billing/orders` or `GET /v1/billing/orders/{order_id}` per drop during the scheduling step looking for orders to appear — they won't, because no Ballpoint order is created until the end-user clicks **Continue to Payment**. Consume `campaign_submitted.orders[].ballpointOrderId` for each drop's authoritative id (one event covers all drops in the submission). If `orders[].ballpointOrderId` is `null` on an entry, that single drop is pending retry — only then is it appropriate to poll `GET /v1/billing/orders` (scoped to the same `external_user_id` / campaign) to discover the server-assigned id once the retry succeeds. See [IFRAME_KIT.md `campaign_submitted` field notes](IFRAME_KIT.md#campaign_submitted--campaign-submitted-to-ballpoint).

---

### 6d. List Orders

```
GET /v1/billing/orders
```

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `external_user_id` | string | — | Filter to a specific platform user |
| `list_id` | string (repeatable) | — | Filter to one or more campaign lists. **Repeat the param** to span several: `?list_id=a&list_id=b`. A single `?list_id=a` is unchanged (backward compatible). These are the same `list_id` values you pass when creating orders; each maps to one `campaign_id` server-side. **Max 100 per request** — more returns `422 LIST_ID_LIMIT_EXCEEDED` (no truncation). Omit for all lists. A **present-but-empty** `?list_id=` returns **zero results** (never account-wide). |
| `status` | string | — | Filter by order status (e.g., `accepted`, `printing`, `complete`, `delivered`) |
| `limit` | integer | 20 | Results per page (1–100) |
| `offset` | integer | 0 | Pagination offset |

> The same repeated `list_id` filter (1–100 values, `422 LIST_ID_LIMIT_EXCEEDED` over the cap, present-but-empty = zero results) is also accepted on the partner dashboard reads `GET /v1/billing/partner/stats`, `GET /v1/billing/partner/orders`, and the insights endpoint `GET /v1/mail-tracking/account-summary`. The iframe's `set_dashboard_filter` postMessage drives these under the hood (see [IFRAME_KIT.md](IFRAME_KIT.md)).

> **`total_pieces_mailed` counts every order in scope — cancelled and failed included.** The `GET /v1/mail-tracking/account-summary` piece total sums `piece_count` across all orders matching the account/tenant, `list_id`, and date scope, without excluding terminal orders. Read it as "pieces ordered", not "pieces handed to USPS". This is deliberate parity with the partner's own campaign totals (PROPS-3082), so the same campaign reports the same piece count on both surfaces. `active_campaigns`, `completed_campaigns`, and `total_rts` are unaffected and keep their existing definitions.

**Example:**

```bash
curl -s "https://api.ballpointmarketing.com/v1/billing/orders?external_user_id=user_789&limit=10" \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME"
```

**Response (`200`):**

```json
{
  "orders": [
    {
      "id": "ord_7f3a2b",
      "campaign_id": "camp_test",
      "product_type": "4x6_printed",
      "postage_type": "first_class",
      "piece_count": 500,
      "unit_price_tcents": 5054,
      "total_price_tcents": 2527000,
      "production_status": "complete",
      "usps_status": "delivered",
      "display_status": "delivered",
      "payment_confirmed": true,
      "external_user_id": "user_789",
      "status_changed_at": "2026-03-05T10:00:00Z",
      "created_at": "2026-03-01T14:00:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

**Notes:**
- Results are scoped to your partner account automatically — you only see your own orders.
- `display_status` is the single field to show users. It equals `usps_status` when USPS tracking is available, otherwise `production_status`.
- Use `total` for pagination: if `total > limit + offset`, there are more pages.

Each element has the same shape as §6c, including the `payment_confirmed` field.

---

### 6e. Order Tracking

Get USPS delivery tracking for a specific order.

```
GET /v1/orders/{order_id}/mail-tracking
```

**Example:**

```bash
curl -s https://api.ballpointmarketing.com/v1/orders/ord_7f3a2b/mail-tracking \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME"
```

**Response (`200`):**

```json
{
  "campaign_id": "camp_test",
  "mail_status": "delivered",
  "mail_status_label": "Delivered",
  "total_pieces": 500,
  "scanned_pieces": 480,
  "scan_coverage": 0.96,
  "delivered": 420,
  "in_transit": 30,
  "out_for_delivery": 25,
  "rts": 5,
  "forwarded": 0,
  "delivered_rate": 0.84,
  "delivered_or_ofd_rate": 0.89,
  "rts_rate": 0.01,
  "first_scan_at": "2026-03-03T08:15:00Z",
  "last_scan_at": "2026-03-06T14:30:00Z",
  "last_delivered_at": "2026-03-06T12:00:00Z",
  "last_rts_at": "2026-03-05T09:45:00Z",
  "last_updated_at": "2026-03-06T14:30:00Z",
  "status_version": "2026-02-01",
  "derived_from": "piece_scan_events"
}
```

**Key fields:**

| Field | Description |
|-------|-------------|
| `mail_status` | Overall status: `shipped`, `in_transit`, `out_for_delivery`, `delivered` |
| `total_pieces` | Total pieces in the order |
| `scanned_pieces` | How many have at least one USPS scan |
| `scan_coverage` | `scanned_pieces / total_pieces` (0.0–1.0) |
| `delivered` | Pieces with delivery confirmation scans |
| `delivered_rate` | `delivered / total_pieces` |
| `rts` | Return-to-sender pieces (bad addresses) |
| `rts_rate` | `rts / total_pieces` |

**Note:** Tracking data appears 1–2 business days after Ballpoint drops the mail at USPS. Before the first scan, this endpoint returns a summary with zero counts.

---

### 6f. Campaign Tracking

Get aggregate USPS tracking for an entire campaign (across all orders).

```
GET /v1/campaigns/{campaign_id}/mail-tracking
```

**Example:**

```bash
curl -s https://api.ballpointmarketing.com/v1/campaigns/camp_test/mail-tracking \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME"
```

Response has the same shape as [Order Tracking](#6e-order-tracking) but aggregated across all orders in the campaign.

---

### 6g. Cancel Order

Cancel is allowed only before production prep begins: `scheduled`, `pending_payment`, `payment_failed`, or `accepted`.

```
POST /orders/{order_id}/cancel
```

**Example:**

```bash
curl -X POST https://api.ballpointmarketing.com/orders/ord_7f3a2b/cancel \
  -H "X-Partner-Key: <PARTNER_KEY>"
```

**Response (`200`):**

```json
{
  "id": "ord_7f3a2b",
  "status": "cancelled"
}
```

**Note:** Cancellation behavior depends on the account's billing model. For invoiced partners (`billing_mode: none`), there is no charge to reverse and the cancelled order will not appear on the next invoice. For payment-gated partners, cancelling from `pending_payment` or `payment_failed` is free (no debit happened); cancelling from `accepted` after payment confirmation auto-refunds the partner-balance debit. The dedicated `order.drop_cancelled` webhook carries `ballpoint_billed` and `ballpoint_billed_amount_tcents` for reconciliation.

Once an order moves to `prep` or beyond, it cannot be cancelled — staff time and (later) materials are being spent on the order. Contact Ballpoint support for production-stage issues.

---

### 6h. Idempotency

Every `POST /v1/billing/orders` **must** include an `Idempotency-Key` header with a unique UUID.

**Why:** Network failures happen. Idempotency keys let you safely retry without double-creating orders or double-charging.

**How it works:**

| Scenario | Result |
|----------|--------|
| First request with key `abc123` | Order created, `202` returned |
| Retry with same key `abc123` + same body | Cached `202` returned (no new order) |
| Same key `abc123` + **different** body | `422 IDEMPOTENCY_KEY_REUSE` error |
| New order | Generate a new UUID |

**On failure:** If a request fails with `5xx` or times out, retry with the **same `Idempotency-Key` and same body**. If the original succeeded, you'll get the cached response. If it didn't, you'll get a fresh attempt. You will never create duplicate orders.

---

### 6i. User Attribution

Pass `X-External-User-ID` on any request to attribute it to a specific end-user:

```
X-External-User-ID: user_789
```

This ID:
- Is stored on orders created during that request
- Is included in webhook payloads sent back to you
- Can be used to filter `GET /v1/billing/orders?external_user_id=user_789`
- Routes tracking data back to the correct user's dashboard

This is optional but recommended — it lets you show each platform user only their own orders and track per-user activity.

### 6j. Per-end-user attribution (`external_user_metadata`)

For partners that need to attribute orders to richer end-user records (display name, plan tier, internal billing id, etc.) without making a separate lookup, pass `external_user_metadata` at order creation:

```json
POST /v1/billing/orders
{
  "campaign_id": "camp_2025_q1",
  "product_type": "4x6_printed",
  "postage_type": "first_class",
  "piece_count": 250,
  "external_user_id": "user_789",
  "external_user_metadata": {
    "display_name": "Alice Cooper",
    "internal_user_id": "u_42",
    "plan": "pro",
    "team_id": "t_17"
  }
}
```

We do not read or interpret the contents. Whatever you send is echoed verbatim on every `order.status_changed` webhook for that order, so you can reconcile to your own per-end-user records without an additional API call.

**Limits (validated at the API boundary):**

| Limit | Value |
|---|---|
| Max top-level keys | 8 |
| Key character set | `A-Z a-z 0-9 _ . -` |
| Max key length | 64 chars |
| Max value length | 256 chars (after string conversion) |
| Nested objects/arrays | Not allowed (flat dict only) |
| Max total size | 2,048 bytes (compact JSON) |

Validator violations return `422 Unprocessable Entity` with a descriptive error message.

**Lifecycle:**

- Captured **only at order creation** — represents the end-user who placed the order. Subsequent `PATCH /v1/billing/orders/{order_id}` calls cannot mutate it.
- Echoed on every `order.status_changed` event (covers status changes, cancel, complete, payment_failed).
- Subject to the same retention window as recipient PII — when an order ages past the partner-controlled retention threshold, this field is scrubbed from our storage automatically.

**Sample webhook payload with the field present** (flat envelope — see [§7 Envelope Shape on the Wire](#envelope-shape-on-the-wire)):

```json
{
  "order_id": "ord_7f3a2b",
  "campaign_id": "camp_2025_q1",
  "previous_production_status": "accepted",
  "production_status": "printing",
  "external_user_id": "user_789",
  "external_user_metadata": {
    "display_name": "Alice Cooper",
    "internal_user_id": "u_42",
    "plan": "pro",
    "team_id": "t_17"
  },
  "event_id": "7d8e9f0a-1b2c-4d3e-8f4a-5b6c7d8e9f0a",
  "event_type": "order.status_changed",
  "timestamp": "2026-03-01T16:30:00Z"
}
```

If you didn't send the field at creation, it is omitted from the payload (or set to `null`).

---

### 6k. Confirm Payment (Partner Payment Gate)

For accounts where Ballpoint waits for the partner to debit the end-user before producing the order (currently PropStream — flagged via `accounts.requires_payment_confirmation = TRUE`), use this endpoint to report the result of the end-user payment attempt.

**Security boundary**

- The end-user payment is captured **on the partner side** using the partner's own payment provider. Ballpoint never sees card data, payment-method data, or any PCI-relevant payload.
- `/confirm-payment` is a **server-to-server** call by integration contract. It must be issued from the partner backend after the partner has confirmed the payment outcome with its payment provider. The customer browser must **not** call this endpoint directly — the partner key would be exposed.
- **Principal enforcement (v1.7.27):** only a **partner principal** (`X-Partner-Key`, matched on the full tenant identity `account_id + source + external_account_id` — the same triple the campaign preview enforces) or Ballpoint's internal ops key may call this endpoint. Same-account `live`/`test` Bearer tokens are rejected with `401 PARTNER_KEY_REQUIRED`; a malformed partner principal missing `source`/`external_account_id` gets `401 MISSING_PARTNER_CONTEXT` (defensive — real partner keys always carry both). Like `INVALID_PIECE_COUNT` below, these `401`s use the `detail`-wrapped envelope rather than the endpoint's top-level `error` object. A partner key whose tenant identity does not match the order returns `404 ORDER_NOT_FOUND` (never `403` — no cross-tenant existence disclosure).
- Pricing values shown in the iframe or carried on browser-side events (e.g. `campaign_submitted.total_dollars`) are **for UX/display only**. After `campaign_submitted`, the partner backend must upload and validate recipients for each order it intends to charge in the current payment event. Only after every selected upload reports `ready === true` with `piece_count > 0` may it call [`POST /v1/billing/campaigns/preview`](#6a-ii-preview-campaign-cost-payment-gate) once with that selected set of `ballpointOrderId`s. Read `campaign_partner_debit_cents` as the exact whole-cent amount Ballpoint records when confirmation succeeds (already excludes any already-confirmed drops), and use the `partner_cost_*_tcents` fields only for raw wholesale reconciliation. Browser-provided values must never be treated as authoritative.

**User-flow timing**

Where this call sits in the end-user journey for an iframe-driven order:

1. iframe loads. Parent app sends `set_api_config` + `set_list`.
2. End-user creates the campaign locally inside the iframe (picks list, product, drop type).
3. iframe emits `campaign_created` to the parent. `orderIds` in this event are local iframe IDs only — no Ballpoint order exists yet.
4. End-user customizes the campaign and clicks Submit.
5. iframe calls `POST /orders` on the API base URL and sends the selected `postage_type` (`first_class`, `standard`, or `presort`). Ballpoint validates and persists that value, then records a creation-time price **estimate** on the order for payment-gated accounts (the wholesale debit is resolved against the current pricing tier at [`/confirm-payment`](#6k-confirm-payment-partner-payment-gate) — refetch [§6a-ii](#6a-ii-preview-campaign-cost-payment-gate) before charging). Only legacy requests that omit `postage_type` default to `first_class`. The order is created in `pending_payment` (send-now) or `scheduled` with `payment_confirmed=false` (future-dated); no charge occurs yet.
6. iframe emits `campaign_submitted` to the parent (carries `orders[].ballpointOrderId` and `total_dollars` for UX/display). Use this as the trigger for the backend handoff, not as authorization to collect payment yet. For partners that sent `piece_counts` on `set_list`, this event also carries `recipient_selection.piece_count`; for A/B Split, each `orders[].pieces` is the size of that variant's slice. See [IFRAME_KIT.md](IFRAME_KIT.md#recipient-selection-contract-piece-count--dedup) for the full input/output contract.
7. Partner backend selects the orders due in the current payment event, waits until each selected `ballpointOrderId` is non-null, uploads the matching recipient slice with [`POST /v1/billing/orders/{order_id}/recipients`](#6n-upload-recipients-initial-upload), and verifies every selected response has `ready === true` and `piece_count > 0`. For A/B Split, the slices must be address-disjoint.
8. Partner backend calls [`POST /v1/billing/campaigns/preview`](#6a-ii-preview-campaign-cost-payment-gate) **once** with that selected order-id set. Read `campaign_partner_debit_cents` as the exact successful-confirmation ledger amount; the `partner_cost_*_tcents` fields remain the raw wholesale math for reconciliation. Call `/confirm-payment` only for response rows where `excluded_from_totals=false`; do not confirm rows excluded from the quoted total. The legacy per-order `POST /v1/billing/orders/preview` loop is no longer required for this step.
9. Partner shows the payment popup; end-user pays via the partner's payment provider.
10. Partner backend calls `POST /v1/billing/orders/{order_id}/confirm-payment` with `status: success` (or `failed`).
11. On success, Ballpoint applies the account billing policy (stripe debits balance; manual records usage without moving balance; none records no charge/usage) and moves the order from `pending_payment` to `accepted`. Production proceeds.

After step 6, the iframe lifecycle and the payment lifecycle run in parallel: the iframe may emit `campaign_complete` / `done` once its own submission flow finishes, independent of the payment popup. Production status continues separately through `order.status_changed` webhooks (`accepted` → `prep` → ... → `complete`).

For payment, reconciliation, or backend workflows, key off `campaign_submitted.orders[].ballpointOrderId` — not `campaign_created.orderIds` (those are pre-API local IDs).

**Endpoint**

```
POST /v1/billing/orders/{order_id}/confirm-payment
X-Partner-Key: pk_live_...
Content-Type: application/json
```

**Request body — success**

```json
{
  "status": "success",
  "payment_date": "2026-04-27T15:30:00Z",
  "transaction_id": "ps_txn_8f2a1d",
  "amount_charged_to_user_cents": 12500
}
```

**Request body — failed**

```json
{
  "status": "failed",
  "transaction_id": "ps_txn_8f2a1d",
  "failure_reason": "card declined",
  "failure_code": "CARD_DECLINED"
}
```

**Fields**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | string | yes | `"success"` or `"failed"`. |
| `payment_date` | string | no | ISO 8601 timestamp of the partner-side debit. Audit only. |
| `transaction_id` | string | no | Partner-side transaction id. Used for audit and idempotency dedup. Stored verbatim. |
| `amount_charged_to_user_cents` | integer | no | What the partner charged the end-user, in cents. Audit only — Ballpoint does not validate this against the wholesale price. |
| `failure_reason` | string | yes (when `status:failed`) | Free-form description stored on the order for audit. |
| `failure_code` | string | no | Optional partner-side code (e.g. `CARD_DECLINED`). |

**Behavior**

- **`status:success`** — the account billing policy runs: `stripe` debits balance, `manual` records usage without moving balance, and `none` records neither charge nor usage. `payment_confirmed` flips to `TRUE`; send-now orders advance from `pending_payment` to `accepted`, while scheduled orders stay `scheduled` until the production date hits.
- **`status:failed`** — order moves to `payment_failed` (terminal) and `failure_reason` is stored. No partner balance debit happens.
- **Idempotency** — repeating the same status is a no-op (last call wins for `transaction_id` and `failure_reason`). Repeating with the **opposite** status is rejected with `409` — payment outcome is unidirectional once recorded.
- **Cancelled orders** — calling `/confirm-payment` against a cancelled order returns `409 ORDER_CANCELLED`.
- **Chargeable-status parity (v1.7.27)** — a **first** `status:success` is accepted only from the same chargeable allowlist the campaign preview quotes: `production_status ∈ {scheduled, pending_payment, accepted}` with `payment_confirmed = false`. Any other unconfirmed state (`failed`, `prep`, `printing`, `complete`, …) returns `409 ORDER_NOT_CHARGEABLE` with **no** ledger movement, usage entry, or payment-state change — you can never charge a row the preview excluded from its totals. Already-confirmed orders keep the idempotent no-op behavior above.
- **Late confirmation** — if the order's `scheduled_production_date` passes without a `success` call, a Ballpoint cron flips it to `payment_failed` automatically. A subsequent `/confirm-payment` returns `409 PAYMENT_ALREADY_FAILED`.
- **No-gate accounts** — calling `/confirm-payment` against an account where `requires_payment_confirmation = FALSE` returns `409 PAYMENT_GATE_NOT_ACTIVE` (the order was already debited at creation).
- **Zero-piece orders** — `status:success` returns `409 INVALID_PIECE_COUNT` before any debit or payment-state mutation when the persisted `piece_count <= 0`. Correct the recipient slice and re-preview before collecting or confirming payment. Unlike the other `409`s on this endpoint (top-level `error` object), this error uses the `detail`-wrapped envelope — the same shape [`POST /v1/billing/campaigns/preview`](#6a-ii-preview-campaign-cost-payment-gate) returns:

  ```json
  {
    "detail": {
      "error": {
        "type": "conflict",
        "code": "INVALID_PIECE_COUNT",
        "message": "Order ord_... must have piece_count greater than zero before billing.",
        "trace_id": "tr_...",
        "order_id": "ord_...",
        "piece_count": 0
      }
    }
  }
  ```
- **Tenant isolation** — orders owned by a different account return `404 ORDER_NOT_FOUND`. Never `403`, to avoid leaking which order ids exist on other accounts.

**Response — success**

```json
{
  "order_id": "ord_7f3a2b",
  "status": "success",
  "previous_status": "pending_payment",
  "production_status": "accepted",
  "payment_confirmed": true,
  "billing": {
    "charged": true,
    "amount_cents": 12300,
    "total_tcents": 123000,
    "balance_after_cents": 4500000,
    "billing_mode": "stripe",
    "transaction_id": "txn_a1b2c3"
  },
  "idempotent": false
}
```

`billing.amount_cents` is the whole-cent wholesale settlement amount: debited from balance in `stripe`, recorded as usage in `manual`, and `0` in `none`. The corresponding billed amount is carried on the cancellation webhook as `ballpoint_billed_amount_tcents` if the order is later cancelled (`0` / `ballpoint_billed=false` for `none`). It is **not** the same as `amount_charged_to_user_cents`, which is what the partner billed the end-user.

**Response — failed**

```json
{
  "order_id": "ord_7f3a2b",
  "status": "failed",
  "previous_status": "pending_payment",
  "production_status": "payment_failed",
  "payment_confirmed": false,
  "failure_reason": "card declined",
  "idempotent": false
}
```

**Retry & finalization (V1)**

Payment retry logic lives **on the partner side**. Ballpoint does not retry the partner debit and only records the final outcome.

- Handle retries internally with the partner payment provider. Only call `/confirm-payment` with the **final** outcome.
- The partner may retry payment internally according to its own billing policy, as long as Ballpoint only receives the final `success` or terminal `failed` result.
- Multi-send drops: if a drop fails, pause subsequent drops on the partner side (stop calling `/confirm-payment` for downstream drops).
- Once an order is in `payment_failed`, it stays there. To reschedule, submit a **new** order via `POST /orders` with the new `mail_date` — the failed order remains in `payment_failed` for audit.
- If the partner is still retrying with the end-user, **do not** send `status:failed` yet — only send it when payment is truly terminal.

---

### 6l. Partner Dashboard Endpoints

These endpoints power partner-side operational dashboards (per-account aggregate stats, paginated order list with SLA, drill-down by user or campaign list). Both require an `X-Partner-Key` header and are scoped to your `source` + `external_account_id`.

> **For payment-gate flows:** do not use these dashboard endpoints for pre-confirmation pricing. After `campaign_submitted`, call [`POST /v1/billing/campaigns/preview`](#6a-ii-preview-campaign-cost-payment-gate) **once** with the caller-selected set of `ballpointOrderId`s intended for the current payment event. Use `campaign_partner_debit_cents` as the exact whole-cent amount recorded when confirmation succeeds and the `partner_cost_*_tcents` fields only for raw wholesale reconciliation. Call `/confirm-payment` only for response rows where `excluded_from_totals=false`. Browser-side values like `campaign_submitted.total_dollars` are UX/display only. See [§6k](#6k-confirm-payment-partner-payment-gate) and [IFRAME_KIT.md](IFRAME_KIT.md) for the full payment-gate context.

#### `GET /v1/billing/partner/stats`

Aggregate counts for a dashboard top panel: order totals, status breakdown, SLA buckets, RTS summary.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | integer | 7 | Range of recent days to aggregate (1–365) |
| `external_user_id` | string | — | Narrow to a single end-user within the account. Omit for account-wide totals |
| `list_id` | string | — | Narrow to a single campaign list. Echoes the same `list_id` originally passed when creating orders. Combinable with `external_user_id` (AND) |

**Example:**

```bash
curl -s "https://api.ballpointmarketing.com/v1/billing/partner/stats?days=30&list_id=marketing_q1_2026" \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME"
```

**Response (`200`):**

```json
{
  "total_orders": 8,
  "total_pieces": 3000,
  "orders_by_status": {
    "pending": 0,
    "pending_payment": 0,
    "scheduled": 1,
    "accepted": 0,
    "prep": 0,
    "printing": 5,
    "writing": 0,
    "inserting": 0,
    "stamping": 0,
    "shipping": 0,
    "complete": 1,
    "cancelled": 1,
    "payment_failed": 0,
    "failed": 0
  },
  "sla_summary": {
    "on_time": 7,
    "at_risk": 0,
    "breached": 1
  },
  "rts_summary": {
    "total_rts": 20,
    "tracked_pieces": 1000,
    "rts_rate": 0.02
  },
  "date_range": { "from": "2026-04-01", "to": "2026-05-01" }
}
```

Unknown `list_id` (or one with no orders in the partner's scope) returns the same shape with all counts zero.

#### `GET /v1/billing/partner/orders`

Paginated, partner-scoped order list with computed `sla_status`. Use this to drill from a stats tile into the underlying orders.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `external_user_id` | string | — | Filter to a single end-user within the account |
| `list_id` | string | — | Filter to a single campaign list. Same value passed when creating orders |
| `status` | string | — | Filter by `production_status` (e.g. `accepted`, `printing`, `complete`) |
| `product_type` | string | — | Filter by product type |
| `sla` | string | — | One of `on_time`, `at_risk`, `breached` |
| `search` | string | — | Substring match on order id OR campaign id OR your `external_order_id` |
| `days` | integer | 30 | Range of recent days (1–365) |
| `limit` | integer | 100 | Page size (1–500) |
| `offset` | integer | 0 | Pagination offset |

**Example:**

```bash
curl -s "https://api.ballpointmarketing.com/v1/billing/partner/orders?days=30&list_id=marketing_q1_2026&status=printing" \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME"
```

**Response (`200`):**

```json
{
  "orders": [
    {
      "id": "ord_abc123",
      "external_order_id": "ps_order_42",
      "product_type": "4x6_printed",
      "piece_count": 500,
      "production_status": "printing",
      "usps_status": null,
      "created_at": "2026-04-12T15:00:00Z",
      "scheduled_production_date": "2026-04-15",
      "sla_due_at": "2026-04-22T00:00:00Z",
      "sla_status": "on_time",
      "campaign_id": "camp_partner_marketing_q1_2026",
      "total_cost_cents": 28000
    }
  ],
  "total": 5,
  "limit": 100,
  "offset": 0,
  "has_more": false
}
```

Filters compose with AND. `total_cost_cents` may be `null` for unpriced orders or billing configurations where no partner-facing amount is set. For payment-gated accounts, this endpoint is for dashboard/post-confirmation reads, not for pre-confirmation charge authorization; use [`POST /v1/billing/campaigns/preview`](#6a-ii-preview-campaign-cost-payment-gate) (campaign-level, recommended) — or [`POST /v1/billing/orders/preview`](#6a-preview-cost) for single-order/pre-submission previews — for that flow. For payment-gated accounts, orders created on/after the 2026-06-23 price-freeze carry a non-null `total_cost_cents` as soon as they are created, but it remains a dashboard/display value and is **not** the authoritative current-price charge amount. Source the exact successful-confirmation cents from `partner_debit_cents` / `campaign_partner_debit_cents` in the campaign preview; use `partner_cost_*_tcents` only for raw wholesale reconciliation (see [§6a-ii](#6a-ii-preview-campaign-cost-payment-gate)).

#### `GET /v1/billing/partner/health`

Operational health snapshot scoped to your partner account. Use this to power a dashboard health tile (API status, last error within scope, current rate-limit headroom, daily piece cap) and to correlate the iframe build with the API build at a glance.

**Authentication:** `X-Partner-Key` (same as other partner endpoints).

**Example:** Set `PARTNER_KEY` to your staging or live partner key before running.

```bash
curl -s "https://api.ballpointmarketing.com/v1/billing/partner/health" \
  -H "X-Partner-Key: $PARTNER_KEY"
```

**Response (`200`):**

```json
{
  "api_status": "ok",
  "last_error": null,
  "rate_limit": {
    "rpm_limit": 60,
    "rpd_limit": 10000,
    "rpd_used_today": 142
  },
  "daily_piece_cap": {
    "used": 1850,
    "limit": 50000
  },
  "build": {
    "environment": "staging",
    "buildId": "3450452",
    "releaseTag": "",
    "deployedAt": "2026-06-16T21:01:49Z"
  },
  "contractVersions": {
    "iframe": "1",
    "api": "3.1",
    "partner": "1.6.7"
  }
}
```

- `api_status` — `"ok"` or `"degraded"`. Reflects the partner-scoped error state, not global API availability.
- `last_error` — `null` when there is no recent failure within your scope; otherwise `{code, action, at}` summarizing the most recent error logged for the account.
- `rate_limit` — current per-minute and per-day limits plus today's usage. `rpm_used` is intentionally omitted (process-local; not reliably aggregable across instances).
- `daily_piece_cap` — pieces accepted today vs. the configured daily cap.
- `build` and `contractVersions` (v1.6.7+) — same shape as the iframe `ready` event. See [IFRAME_KIT.md → `ready`](IFRAME_KIT.md#ready--iframe-is-loaded-and-ready-for-configuration) for field-level notes. Diagnostic and non-sensitive — partners may ignore them. The `build` values above are from a **staging** deploy (`environment: "staging"`, `releaseTag: ""`), the currently deployed environment; on production, `environment` is `"production"` and `releaseTag` carries the release tag (field shapes identical).

---

### 6m. Reschedule Order

Update an order's scheduled mail date without creating a replacement order. V1 contract: the same `order_id` is preserved and the backend recomputes `scheduled_production_date` from the product SLA.

```
POST /v1/billing/orders/{order_id}/reschedule
```

**Allowed when:** `production_status = 'scheduled'` AND `payment_confirmed = FALSE`. Any other state returns `409` with a reason code (see the table below).

**Request body:**

```json
{
  "mail_date": "2026-08-15"
}
```

**Response (`200`):**

```json
{
  "order_id": "ord_7f3a2b",
  "previous_mail_date": "2026-08-01",
  "new_mail_date": "2026-08-15",
  "previous_scheduled_production_date": "2026-07-30T00:00:00+00:00",
  "new_scheduled_production_date": "2026-08-13T00:00:00+00:00"
}
```

**Example:**

```bash
curl -X POST https://api.ballpointmarketing.com/v1/billing/orders/ord_7f3a2b/reschedule \
  -H "X-Partner-Key: <PARTNER_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"mail_date": "2026-08-15"}'
```

**Idempotent no-op.** If the supplied `mail_date` equals the order's current `metadata.mail_date`, the endpoint returns `200` with `previous_mail_date == new_mail_date`. **No** webhook is fired and **no** audit row is written. Safe to retry.

**Rejection reasons:**

| HTTP | `error.code` | When |
|------|------|------|
| 400 | `MAIL_DATE_INVALID_FORMAT` | Not `YYYY-MM-DD` (datetime strings, ISO-with-TZ, missing/null are all rejected) |
| 400 | `MAIL_DATE_TOO_SOON` | `mail_date − SLA_business_days(product_type)` is ≤ today + 1 day (same threshold as `create_order`'s scheduling branch). SLA is in **business days** (Mon–Fri); see §6q for the full table. |
| 400 | `MAIL_DATE_TOO_FAR` | `mail_date` is more than 365 days in the future |
| 409 | `PAID_LOCKED` | `payment_confirmed = TRUE` — order is locked, no reschedule |
| 409 | `SEND_NOW_PROCESSING` | Send-now order in `pending_payment` awaiting `/confirm-payment` |
| 409 | `IN_PRODUCTION` | Status is `accepted`, `prep`, `printing`, `writing`, `inserting`, `stamping`, or `shipping` |
| 409 | `TERMINAL` | Status is `complete`, `cancelled`, `failed`, or `payment_failed` |
| 409 | `STATE_CHANGED` | Concurrent state transition between read and write — retry once |
| 404 | `ORDER_NOT_FOUND` | Order does not exist OR belongs to a different tenant (404, never 403, to prevent existence probing) |

**Distinct from `payment_failed → new order`.** The existing terminal-failed-payment flow (`§6k Confirm Payment`) applies only **after** a terminal payment failure: the failed order is left in `payment_failed`, and partners create a fresh order to retry. Same-order reschedule (this endpoint) applies **only before** payment is processed.

**On success.** Ballpoint emits the `order.rescheduled` webhook (see §7 Payload Format) and — when initiated from the embedded iframe — an `order_rescheduled` postMessage to the parent (see `IFRAME_KIT.md §6`). Webhook endpoints are selected by the exact partner identity tuple `account_id + source + external_account_id`, then by the endpoint's optional `event_types[]` allowlist. Cross-tenant endpoints are not eligible (see [§7 Delivery Scope](#delivery-scope-shipping-behavior)).

### 6n. Upload Recipients (Initial Upload)

```
POST /v1/billing/orders/{order_id}/recipients
X-Partner-Key: pk_test_...
Content-Type: application/json
```

The PropStream flow is create the order first (with `piece_count`, via `POST /orders` or `POST /v1/billing/orders`), then upload the mailing addresses with this endpoint. This is the initial recipient-upload endpoint; it is distinct from the Edit Leads PATCH below.

**Request body:**

```json
{
  "recipients": [
    {
      "first_name": "Jane",
      "last_name": "Doe",
      "company": null,
      "address": "100 Main St",
      "address2": null,
      "city": "San Francisco",
      "state": "CA",
      "zip": "94103",
      "contact_id": "ps_contact_42",
      "address_type": "MAILING",
      "placeHolders": { "OwnerFirstName": "Jane" }
    }
  ],
  "append": false
}
```

- `recipients[]` — max 10,000 per request. For larger orders, chunk with multiple calls using `append=true`.
- Required per recipient: `address`, `city`, `state` (2-letter), `zip` (5 or 5+4).
- At least one of `first_name` / `last_name` (enforced per-row — see partial acceptance below).
- Optional: `company`, `address2`, `contact_id` (<=64; partner-side recipient id, stored verbatim and round-tripped, never interpreted by Ballpoint), `address_type` (`PROPERTY` | `MAILING`; optional for order-level upload), `placeHolders` (camelCase; PropStream V1 merge-tag values; used for render personalization only, never as the delivery address).
- `append` (default `false`): `false` REPLACES all existing recipients on the order (idempotent re-upload); `true` APPENDS to existing recipients (for chunked uploads of large orders).

**Response (`200`):**

```json
{
  "order_id": "ord_7f3a2b",
  "accepted": 499,
  "rejected": 1,
  "rejected_details": [ { "index": 12, "reason": "At least first_name or last_name is required" } ],
  "total_recipients": 499,
  "piece_count": 500,
  "ready": false
}
```

- `accepted` / `rejected` — counts of rows written vs soft-rejected. `rejected_details` — `[{index, reason}]`.
- `total_recipients` — existing (if `append`) + accepted. `piece_count` — the order's current piece_count.
- `ready` — `true` when `total_recipients == piece_count` (the order has all of its addresses).

Before opening the payment step, require both `ready === true` **and** `piece_count > 0` for every order, then call the campaign preview. A response with `piece_count: 0` is not billable even if `ready` is mathematically `true` after all submitted A/B recipients were rejected as cross-order duplicates.

If an initial A/B upload has already reduced an order to `piece_count: 0`, retrying this POST with a non-empty list cannot repair it because the new list would exceed the order's current piece count. For an eligible gated, unconfirmed order, use the [Edit Leads PATCH](#6o-edit-leads--replace--resize--reprice-recipients-patch) with a verified address-disjoint slice so the order is resized and repriced; otherwise cancel and recreate the order. If you cancel, drop the cancelled order's id from subsequent [`POST /v1/billing/campaigns/preview`](#6a-ii-preview-campaign-cost-payment-gate) calls — a cancelled order that still has `piece_count: 0` keeps returning `409 INVALID_PIECE_COUNT` and blocks the preview for its healthy siblings. The PATCH is a replacement operation and does not construct or validate the A/B split for the partner.

**Allowed order statuses:** `scheduled`, `pending_payment`, `accepted`, `prep`. Any other status → `409 RECIPIENTS_LOCKED`.

**Partial acceptance:** rows missing BOTH `first_name` and `last_name` are rejected per-row into `rejected_details`, and the request still succeeds with the valid rows. (Malformed REQUIRED fields — bad zip, non-2-letter state, missing address/city/state/zip — fail validation for the whole request: `422`.)

**Errors:**

| HTTP | `error.code` | When |
|------|------|------|
| 404 | `ORDER_NOT_FOUND` | Order does not exist OR belongs to another tenant (never 403, to prevent existence probing). |
| 409 | `RECIPIENTS_LOCKED` | Order status not in `{scheduled, pending_payment, accepted, prep}`. |
| 400 | `RECIPIENT_COUNT_EXCEEDS_PIECE_COUNT` | Existing (if `append`) + accepted exceeds the order's `piece_count`. |
| 422 | — | Malformed recipient fields. |

**Distinction from Edit Leads (`PATCH /v1/billing/orders/{order_id}/recipients`, the next section):** this POST is the INITIAL (and chunked) upload — it does NOT resize `piece_count` and does NOT reprice, and it works on ANY account when the order is in `scheduled` / `pending_payment` / `accepted` / `prep`. The Edit Leads PATCH replaces recipients on GATED future/unbilled drops and additionally RESIZES `piece_count` and REPRICES.

### 6o. Edit Leads — Replace + Resize + Reprice (Recipients PATCH)

```
PATCH /v1/billing/orders/{order_id}/recipients
X-Partner-Key: pk_test_...
Content-Type: application/json
```

For Edit Leads recipient replacement on future/unbilled drops. Replaces all recipients on the order, resizes `piece_count` to match the new count, and recomputes display pricing fields (`unit_price_tcents`, `total_price_tcents`) via the canonical pricing helper. Backend gate is order-level and campaign-type-neutral — applies to single send, A/B split, and multi-month equally.

**Distinction from `POST /v1/billing/orders/{order_id}/recipients`:** the POST endpoint is for **initial recipient upload** (or chunked append). It does NOT resize `piece_count` and is NOT the Edit Leads PATCH flow. Use this PATCH instead for Edit Leads.

**Request body:**

```json
{
  "recipients": [
    {
      "first_name": "Jane",
      "last_name": "Doe",
      "company": null,
      "address": "100 Main St",
      "address2": null,
      "city": "San Francisco",
      "state": "CA",
      "zip": "94103",
      "contact_id": "ps_contact_42"
    }
  ]
}
```

**All-or-nothing.** Each recipient must satisfy:
- `first_name` OR `last_name` populated (at least one)
- `address`, `city`, `state` (2-letter), `zip` (5 or 5+4)

Any invalid recipient → `422` with FastAPI's default Pydantic error envelope, **no DB mutation**.

**Gate (fail-fast):**
1. Pydantic validation → `422` (no handler execution if any recipient invalid)
2. Tenant scoping → `404` if order belongs to another tenant
3. Order not found → `404 ORDER_NOT_FOUND`
4. Status ∉ `{scheduled, pending_payment}` → `409 RECIPIENTS_LOCKED`
5. Account `requires_payment_confirmation = FALSE` → `409 PAYMENT_GATE_NOT_ACTIVE`
6. Order `payment_confirmed = TRUE` → `409 PAID_LOCKED`

**Response 200:**

```json
{
  "order_id": "ord_abc123",
  "accepted": 499,
  "previous_piece_count": 500,
  "new_piece_count": 499,
  "previous_unit_price_tcents": 5050,
  "new_unit_price_tcents": 5050,
  "previous_total_price_tcents": 2525000,
  "new_total_price_tcents": 2519950,
  "payment_confirmed": false
}
```

| Field | Description |
|---|---|
| `accepted` | Count of recipients successfully written (equals `new_piece_count`). |
| `previous_piece_count` / `new_piece_count` | Order `piece_count` before/after this PATCH. |
| `previous_unit_price_tcents` | integer or null. Wholesale unit price (tenth-cents) before this PATCH. **Populated for gated orders created on/after the gated price-freeze (2026-06-23)** — `POST /orders` freezes `unit_price_tcents` / `total_price_tcents` on the order row at creation (no debit; the wholesale debit still happens only at `/confirm-payment`). `null` only for **legacy** gated orders created before that change. Tier-aware: shrinking past a volume tier boundary changes the per-piece rate. |
| `new_unit_price_tcents` | integer. Wholesale unit price after this PATCH. Always populated because this PATCH recomputes via the canonical `get_unit_price` helper. |
| `previous_total_price_tcents` | integer or null. Display total before this PATCH (unit × count). **Populated for gated orders created on/after 2026-06-23** (price frozen at creation); `null` only for legacy gated orders created before that change — same as `previous_unit_price_tcents`. |
| `new_total_price_tcents` | integer. Display total after this PATCH (`new_unit_price_tcents` × `new_piece_count`). Always populated. |
| `payment_confirmed` | Always `false` (endpoint gate rejects `true`). |

**409 error codes:**

| Code | Meaning |
|---|---|
| `RECIPIENTS_LOCKED` | Order status is outside the Edit Leads allowlist (`scheduled`, `pending_payment`). `accepted`, `prep`, and production statuses are locked. |
| `PAYMENT_GATE_NOT_ACTIVE` | Account does not use the partner payment confirmation gate. Edit Leads only applies to gated accounts. |
| `PAID_LOCKED` | Order has already been confirmed (`payment_confirmed=TRUE`). Recipients are locked. |

**Billing semantics:**

This endpoint does NOT debit, charge, or hold balance. It updates `unit_price_tcents` and `total_price_tcents` on the order row for display, but `/confirm-payment` recomputes pricing at charge time using the (newly-updated) `piece_count` via the canonical pricing helper, so this PATCH cannot cause incorrect billing. `/confirm-payment` remains the sole billing source of truth.

**Audit log:** every successful PATCH writes an `audit_log` row with `action="recipients_edit_leads"` and `detail` containing previous/new piece_count, unit_price_tcents, and total_price_tcents.

### 6p. Campaign Delta Recipients — Add/Remove Across Editable Drops

```
PATCH /v1/billing/campaigns/{campaign_id}/recipients
X-Partner-Key: pk_test_...
Content-Type: application/json
```

Campaign-level delta add/remove endpoint. One call applies recipient changes across all editable drops in a campaign. Editable = status ∈ `{scheduled, pending_payment}` with `payment_confirmed=false`. Locked drops (accepted, in production, mailed, delivered, terminal) are skipped and reported in the response.

**Gated accounts only.** Account must have `requires_payment_confirmation = TRUE`. Non-gated accounts → `409 PAYMENT_GATE_NOT_ACTIVE`.

**Distinction from §6o (order-level PATCH):** §6o replaces ALL recipients on ONE order. This endpoint applies a delta (add/remove) across ALL editable orders in a campaign in one call. Use §6o for variant-specific A/B split edits; use §6p for campaign-wide multi-month changes.

**Request body:**

```json
{
  "added": [
    {
      "contact_id": "ps_lead_42",
      "address_type": "PROPERTY",
      "first_name": "Jane",
      "last_name": "Doe",
      "company": null,
      "address": "100 Main St",
      "address2": null,
      "city": "San Francisco",
      "state": "CA",
      "zip": "94103"
    }
  ],
  "removed": [
    { "contact_id": "ps_lead_17", "address_type": "MAILING" }
  ],
  "remove_all": false
}
```

**Request fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `added` | array | No (default `[]`) | Recipients to add/upsert on each editable drop. Max 10,000 items. |
| `added[].contact_id` | string (max 64) | Yes | Partner-side unique recipient identifier. |
| `added[].address_type` | string | Yes | `"PROPERTY"` or `"MAILING"`. Combined with `contact_id`, forms the unique key. |
| `added[].first_name` | string | At least one of first/last | Recipient first name. |
| `added[].last_name` | string | At least one of first/last | Recipient last name. |
| `added[].company` | string | No | Company name. |
| `added[].address` | string | Yes | Street address line 1. |
| `added[].address2` | string | No | Street address line 2. |
| `added[].city` | string | Yes | City. |
| `added[].state` | string (2-letter) | Yes | State code (uppercase). |
| `added[].zip` | string | Yes | ZIP code (5 or 5+4 digit). |
| `removed` | array | No (default `[]`) | Recipients to remove from each editable drop by unique key. Max 10,000 items. |
| `removed[].contact_id` | string | Yes | Partner-side recipient identifier to remove. |
| `removed[].address_type` | string | Yes | `"PROPERTY"` or `"MAILING"`. |
| `remove_all` | boolean | No (default `false`) | If `true`, clears all recipients from editable drops before applying `added[]`. Cannot be combined with `removed[]` (→ 422). |

**Unique key:** `contact_id + address_type`. If `added[]` includes a key that already exists on an editable drop, the recipient is updated (upsert), not duplicated.

**Validation (422, no DB mutation):**
- Empty request (no `added`, no `removed`, `remove_all=false`)
- `remove_all=true` combined with non-empty `removed[]`
- Duplicate `(contact_id, address_type)` pairs within `added[]`
- Duplicate `(contact_id, address_type)` pairs within `removed[]`
- Invalid recipient fields (missing name, bad zip/state, invalid `address_type`)

**Gate (fail-fast):**
1. Campaign not found → `404 CAMPAIGN_NOT_FOUND`
2. Account `requires_payment_confirmation = FALSE` → `409 PAYMENT_GATE_NOT_ACTIVE`
3. No editable drops in campaign → `409 NO_EDITABLE_DROPS`
4. No pricing for product/postage at new count → `400 NO_PRICING`

**Editable drops:** status ∈ `{scheduled, pending_payment}` AND `payment_confirmed = false`.

**Locked drops:** all other orders in the campaign. Reported in `drops_locked[]` with reason.

**Response 200:**

```json
{
  "campaign_id": "camp_abc123",
  "added_count": 25,
  "removed_count": 8,
  "removed_not_found_count": 1,
  "drops_affected": [
    {
      "order_id": "ord_a",
      "previous_piece_count": 500,
      "new_piece_count": 517,
      "previous_total_price_tcents": 2525000,
      "new_total_price_tcents": 2610858,
      "payment_confirmed": false
    }
  ],
  "drops_locked": [
    {
      "order_id": "ord_c",
      "locked_reason": "paid_or_accepted",
      "current_status": "accepted"
    }
  ]
}
```

**Response fields:**

| Field | Type | Description |
|---|---|---|
| `campaign_id` | string | The campaign that was modified. |
| `added_count` | integer | Number of recipient keys in the `added[]` request (includes upserts). |
| `removed_count` | integer | Number of unique keys from `removed[]` that matched at least one recipient across editable drops. |
| `removed_not_found_count` | integer | Keys from `removed[]` that matched zero recipients on any editable drop. `removed_count + removed_not_found_count = len(removed[])`. |
| `drops_affected` | array | Drops that were successfully mutated. |
| `drops_affected[].order_id` | string | Ballpoint order ID. |
| `drops_affected[].previous_piece_count` | integer | Piece count before this mutation. |
| `drops_affected[].new_piece_count` | integer | Piece count after this mutation. **Per-drop source of truth.** |
| `drops_affected[].previous_total_price_tcents` | integer or null | Total price before mutation (tenth-cents). Populated for gated orders created on/after 2026-06-23 (price frozen at creation); `null` only for legacy gated orders created before that change. |
| `drops_affected[].new_total_price_tcents` | integer | Total price after mutation (tenth-cents). Always computed from the same pricing path used at `/confirm-payment`. |
| `drops_affected[].payment_confirmed` | boolean | Always `false` (editable drops are by definition unconfirmed). |
| `drops_locked` | array | Drops skipped because they are past the editable window. |
| `drops_locked[].order_id` | string | Ballpoint order ID. |
| `drops_locked[].locked_reason` | string | Why this drop was not modified. See enum below. |
| `drops_locked[].current_status` | string | The drop's current production status. |

**`locked_reason` enum:**

| Value | Meaning |
|---|---|
| `paid_or_accepted` | `payment_confirmed=true` OR status is `accepted`. |
| `in_production` | Status in `{prep, printing, writing, inserting, stamping, shipping}`. |
| `mailed` | Status `complete`. |
| `delivered` | Status in `{shipped, in_transit, out_for_delivery, delivered}`. |
| `terminal` | Status in `{cancelled, failed, payment_failed}`. |

**Idempotency:** Naturally idempotent. A repeated call: `added[]` upserts same values (no-op), `removed[]` finds nothing → all reported as `removed_not_found_count`. Response reflects current state.

**Billing semantics:** Same as §6o — this endpoint does NOT charge. It recomputes `unit_price_tcents` and `total_price_tcents` on each affected order for display. `/confirm-payment` recomputes at charge time using the updated `piece_count`.

**Audit log:** `action="recipients_campaign_delta"` with detail containing counts and affected/locked order IDs.

### 6q. Product SLA Lead Times (Business Days)

Ballpoint computes `scheduled_production_date` by subtracting the product's SLA lead time (in **business days**, Mon–Fri) from `mail_date`. Weekends are skipped; no holiday calendar is applied.

**Partner-contract product types:**

| `product_type` | SLA (business days) |
|---|---|
| `4x6_printed` | 3 |
| `6x9_printed` | 3 |
| `4x6_cursive` | 4 |
| `6x9_cursive` | 4 |
| `color_letter` | 6 |
| `hybrid_letter` | 6 |
| `greeting_letter` | 6 |

**Example:** `mail_date = 2026-07-13` (Monday) with `product_type = 4x6_printed` (3 business days) → `scheduled_production_date = 2026-07-08` (previous Wednesday, skipping Sat+Sun).

Unknown product types are rejected by validation (`INVALID_PRODUCT_CONFIG`). If an unrecognized type reaches the scheduler through a legacy path, the conservative default is 6 business days.

The 3/4/6 policy applies when Ballpoint computes a schedule for a new order or a rescheduled order. Existing orders keep their persisted `scheduled_production_date`; this release does not backfill them automatically.

The `MAIL_DATE_TOO_SOON` rejection (§6m) fires when `scheduled_production_date ≤ today + 1 day`.

### 6r. Partner Feature Configuration

`GET /v1/config` resolves the current partner feature flags for the requesting
user. The embedded iframe calls this automatically; partners normally do not
need to call it themselves.

```bash
curl https://api.ballpointmarketing.com/v1/config \
  -H "X-Partner-Key: ${BALLPOINT_PARTNER_KEY}" \
  -H "X-External-User-ID: user_456"
```

```json
{
  "flags": { "propstream_send_mail_enabled": false },
  "evaluated_at": "2026-07-14T16:00:00Z",
  "evaluation_context": {
    "principal_type": "partner",
    "source": "propstream",
    "kill_switch_engaged": false
  },
  "cache_ttl_seconds": 60
}
```

The response contains boolean flags only and never returns raw or hashed user
or account identifiers. Cache it in memory for 60 seconds (`Cache-Control:
private, max-age=60`). Do not persist it to browser storage. `X-External-User-ID`
is optional; without it, evaluation uses the partner/account context only.

Rate limits are 10 requests/minute per partner-key + external-user pair and
3,000 requests/minute per partner key. Headerless requests skip the per-user
tier. Standard `401`, `403`, and `429` errors apply.

For PropStream, `propstream_send_mail_enabled` authoritatively gates both
`POST /orders` and `POST /v1/billing/orders`. A disabled evaluation returns
`403 FEATURE_DISABLED` before idempotency, order creation, or billing. Other
partner sources and internal flows are unchanged. This flag is a rollout
control, not strong user authorization: the external user ID is asserted by
the partner holding the shared partner key.

### 6s. Search Recipients Across Direct Mail

`GET /v1/mail-tracking/recipients/search` searches recipient names and mailing
addresses across the authenticated tenant's direct-mail campaigns. The embedded
iframe calls this endpoint automatically; partners do not need to add a new
postMessage handler.

```bash
curl --get https://api.ballpointmarketing.com/v1/mail-tracking/recipients/search \
  -H "X-Partner-Key: ${BALLPOINT_PARTNER_KEY}" \
  -H "X-External-User-ID: user_456" \
  --data-urlencode "q=Gregory, Debra" \
  --data-urlencode "limit=20" \
  --data-urlencode "offset=0"
```

| Parameter / header | Required | Behavior |
|---|---|---|
| `q` | Yes | 2–200 characters. Punctuation and whitespace split the query into tokens; every token must match the combined recipient name/address text in any order. For example, `Gregory, Debra` matches `Debra Gregory`. |
| `limit` | No | 1–100, default `20`. |
| `offset` | No | Zero-based result offset, default `0`. |
| `X-Partner-Key` | Yes | Authenticates and tenant-scopes the request. |
| `X-External-User-ID` | No | When present, limits partner results to campaigns attributed to that user. Omit only for an authorized tenant-wide search. |

The search reads both accepted/uploaded order recipients and USPS piece-tracking
rows. A newly accepted campaign is therefore searchable before USPS tracking is
indexed. Duplicate records for the same normalized address and campaign are
collapsed; once tracking exists, the tracking row supplies the authoritative
piece status and opt-out state.

```json
{
  "results": [
    {
      "recipient_name": "Debra Gregory",
      "recipient_address": "123 Main St",
      "recipient_city": "Austin",
      "recipient_state": "TX",
      "recipient_zip": "78701",
      "campaign_count": 1,
      "is_opted_out": false,
      "campaigns": [
        {
          "campaign_id": "camp_new_fc",
          "campaign_name": "New_FC",
          "status": "accepted",
          "mail_date": "2026-07-18",
          "last_scan_at": null,
          "piece_status": null
        }
      ]
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0,
  "query": "Gregory, Debra"
}
```

Results are grouped by normalized street address, city, state, and ZIP5. For an
order-only result, `last_scan_at` and `piece_status` are `null`; this means USPS
tracking is not available yet, not that the search failed. Principals with full
PII access receive all recipient fields. Limited PII access omits
`recipient_address`; principals with no PII access receive `403`.

---

## 7. Status Updates via Webhooks

> **Ballpoint delivers webhooks at least once. Your integration must handle duplicates, delays, and out-of-order delivery.**

> Ballpoint emits two webhook event families: order lifecycle events (`order.drop_completed`, `order.drop_cancelled`, `order.status_changed`, `order.usps_update`, and `order.rescheduled`) and the per-piece RTS push-back (`campaign.mail_tracking.rts_update` — see [§7b](#7b-per-piece-rts-push-back-v1)).

The partner-facing source of truth is the [canonical webhook catalog](contracts/webhooks/catalog.json). Each emitted event has a Draft 2020-12 logical schema, wire schema, exact raw-body fixture, parsed fixture, and header fixture under [`contracts/webhooks/`](contracts/webhooks/). The fixture HMAC is independently recalculated in CI. If a prose example and a wire schema ever disagree, the wire schema and its raw-body fixture win.

### Registration

Send us your webhook endpoint URL — Ballpoint will configure it on our side. There is no self-service webhook registration endpoint today. *(Contact details provided during onboarding.)*

**Requirements for your endpoint:**
- Must accept `POST` requests with `Content-Type: application/json`
- Must be HTTPS (HTTP is rejected)
- Must respond with `2xx` within 10 seconds
- Must be publicly reachable from the internet

### <a id="delivery-scope-shipping-behavior"></a>Delivery Scope (as currently shipped)

Ballpoint snapshots eligible endpoints once per logical event using an exact, null-safe match on all three partner identity fields:

- `account_id`
- `source`
- `external_account_id`

The endpoint must also be active and, when it has an `event_types[]` allowlist, the event type must be present. An endpoint from another source or external account is never selected, even when it shares the same Ballpoint `account_id`. Delivery state and retry exhaustion are tracked independently per endpoint, so one endpoint's success cannot suppress another endpoint's retry.

### <a id="envelope-shape-on-the-wire"></a>Envelope Shape on the Wire

There are **two envelope shapes** depending on the event type. Code against the shape of the event you subscribe to — the two do not converge.

**Flat envelope — `order.*` events (`order.drop_completed`, `order.drop_cancelled`, `order.status_changed`, `order.usps_update`, `order.rescheduled`).** Only `event_id` / `event_type` / `timestamp` are added at the top level at delivery time. There is **no** `id` / `version` / `data` wrapper on the wire. All payload fields sit directly at the top of the JSON object alongside `event_id` / `event_type` / `timestamp`; the dedicated drop events also carry their logical `type` field.

**Wrapped envelope — `campaign.mail_tracking.rts_update`.** Uses `{ id, type, version, created_at, data }` with the actual payload nested inside `data`. In addition, `event_id` / `event_type` / `timestamp` are **also** added at the top level at delivery time (so the wire object has both forms). See the [`campaign.mail_tracking.rts_update` example](#campaign-level-mail-tracking-events) for the concrete shape.

Match on the appropriate top-level key. `X-Ballpoint-Event` and `X-Ballpoint-Event-Id` headers are always present and are the recommended dispatch/dedup surfaces regardless of envelope shape.

### Payload Format

When an order's status changes, we send an `order.status_changed` event. **Flat envelope** (see [Envelope Shape on the Wire](#envelope-shape-on-the-wire) above) — no `data` wrapper on the wire:

```json
{
  "order_id": "ord_7f3a2b",
  "campaign_id": "camp_test",
  "previous_production_status": "accepted",
  "production_status": "printing",
  "usps_status": null,
  "display_status": "printing",
  "product_type": "4x6_printed",
  "note": null,
  "external_user_id": "user_789",
  "external_user_metadata": { "agent_id": "a-123" },
  "list_id": "marketing_q1_2026",
  "source": "your_source",
  "external_account_id": "acct_partner",
  "event_id": "b6c3f9d1-2e4a-4d7b-9c1a-5f8e2b3d4c6e",
  "event_type": "order.status_changed",
  "timestamp": "2026-03-01T16:30:00Z"
}
```

`list_id` echoes back verbatim the value you originally passed when creating the order (or `null` for orders not created via the partner endpoint). Use it as the join key on your side for reconciliation.

#### <a id="d1-order-status_changed-field-name-pairs"></a>Two field-name pairs by trigger

`order.status_changed` is enqueued by **four** code paths (internal-staff status change, partner-initiated cancel, scheduler expiring an unconfirmed payment, and order-job dead-letter). They share the same event type but **use two different field-name pairs** to describe the transition:

| Trigger path | Transition field pair | Also carried |
|---|---|---|
| Internal-staff status change | `previous_production_status` → `production_status` | `usps_status`, `display_status`, `note`, `refund` (object, only when a refund was executed on a cancel) |
| Partner-initiated cancel | `previous_status` → `new_status` (values `scheduled`/`accepted` → `cancelled`) | — |
| Scheduler expires an unconfirmed payment | `previous_status` → `new_status` (values `scheduled` → `payment_failed`) | `trigger` (`payment_confirmation_expired`), `failure_reason` (`expired_no_payment_confirmation`) |
| Order-job dead-letter (terminal failure) | `previous_production_status` → `production_status` (`failed` terminal) | `error_message` |

**A robust consumer reads either field-name pair.** The `production_status` / `new_status` value string set is identical across paths (`scheduled | accepted | prep | printing | writing | inserting | stamping | shipping | complete | cancelled | failed | payment_failed`); only the field name carrying the value changes. Fields present on all four triggers: `order_id`, `campaign_id`, `external_user_id`. Fields present on staff-path, partner-cancel, and scheduler-expire (not dead-letter): `list_id`, `external_user_metadata`. Fields present only on staff-path and dead-letter — not on partner-cancel or scheduler-expire, since those two pass `source`/`external_account_id` to `enqueue_webhook_event` for outbox routing only and neither key appears in the delivered JSON on those two paths: `source`, `external_account_id`.

### `order.rescheduled` Payload Format (v1.4.0+)

Fired on a successful `POST /v1/billing/orders/{order_id}/reschedule` (see [§6m](#6m-reschedule-order)). Suppressed on idempotent no-op (when the requested `mail_date` equals the order's current value).

```json
{
  "order_id": "ord_7f3a2b",
  "campaign_id": "camp_test",
  "list_id": "marketing_q1_2026",
  "source": "your_source",
  "external_account_id": "acct_partner",
  "external_user_id": "user_789",
  "external_user_metadata": { "agent_id": "a-123" },
  "product_type": "4x6_printed",
  "previous_mail_date": "2026-08-01",
  "new_mail_date": "2026-08-15",
  "event_id": "7d8e9f0a-1b2c-4d3e-8f4a-5b6c7d8e9f0a",
  "event_type": "order.rescheduled",
  "timestamp": "2026-03-15T16:30:00Z"
}
```

Field notes:

- **`previous_mail_date`** / **`new_mail_date`** are `YYYY-MM-DD` strings (no time, no timezone) — same shape as the API request body in §6m.
- The webhook intentionally does **NOT** carry `previous_scheduled_production_date` / `new_scheduled_production_date`. Those are returned only in the synchronous reschedule API response (§6m). Partners rarely need the production-date directly; consume the API response if you do.
- **Flat envelope, same shape as `order.status_changed`.** Only `event_id` / `event_type` / `timestamp` are added at the top level at delivery time — no `id` / `type` / `version` / `data` wrapper (see [Envelope Shape on the Wire](#envelope-shape-on-the-wire)). Re-use your existing webhook deduplication, retry logic, and signature verification — no changes required.
- **Delivery scope.** Endpoint selection uses the exact `account_id + source + external_account_id` tuple and the endpoint's optional `event_types[]` allowlist (see [§7 Delivery Scope](#delivery-scope-shipping-behavior)).

### Webhook Headers

Every webhook includes these headers:

```
X-Ballpoint-Signature: sha256=<hex>
X-Ballpoint-Timestamp: 2026-03-01T16:30:00Z
X-Ballpoint-Event: order.drop_completed
X-Ballpoint-Event-Id: b6c3f9d1-2e4a-4d7b-9c1a-5f8e2b3d4c6e
X-Ballpoint-Delivery: d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a
```

`X-Ballpoint-Event-Id` is the transport deduplication key and stays stable across endpoints, inline retries, and later outbox rounds. `X-Ballpoint-Delivery` identifies one concrete HTTP request and changes on every attempt. On the wrapped RTS event, the legacy payload `id` has separate semantics; do not use it in place of `X-Ballpoint-Event-Id`. The complete signed/unsigned header contract is [`contracts/webhooks/headers/contract.json`](contracts/webhooks/headers/contract.json).

During the endpoint-secret migration grace period, an endpoint provisioned without a secret receives `X-Ballpoint-Insecure: true` instead of `X-Ballpoint-Signature`. That marker means the request is **not authenticated**; it is not a substitute for verification. New integrations must provision a webhook secret, and existing unsigned endpoints should migrate to signed delivery.

### Signature Verification

Verify every webhook to ensure it came from Ballpoint and wasn't tampered with.

**Python:**

```python
import hmac, hashlib

def verify_signature(body_bytes, timestamp, signature, secret):
    expected = hmac.new(
        secret.encode(),
        timestamp.encode() + body_bytes,
        hashlib.sha256
    ).hexdigest()
    received = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)

# In your handler:
#   1. Reject if signature doesn't match
#   2. Reject timestamps > 5 min old or > 2 min in the future
#   3. Deduplicate on X-Ballpoint-Event-Id (you may receive retries)
```

**Node.js:**

```javascript
const crypto = require("crypto");

function verifySignature(bodyBuffer, timestamp, signature, secret) {
  const expected = crypto
    .createHmac("sha256", secret)
    .update(timestamp, "utf8")
    .update(bodyBuffer)
    .digest();
  const received = signature.replace("sha256=", "");
  const receivedBytes = Buffer.from(received, "hex");
  return receivedBytes.length === expected.length &&
    crypto.timingSafeEqual(expected, receivedBytes);
}
```

### Validation Checklist

| Step | Rule |
|------|------|
| 1 | Verify `sha256=<hex>` signature using `HMAC-SHA256(secret, timestamp + raw_body)` |
| 2 | Use constant-time comparison |
| 3 | Reject timestamps older than 5 minutes |
| 4 | Reject timestamps more than 2 minutes in the future (clock skew) |
| 5 | Reject duplicate `X-Ballpoint-Event-Id` values (store processed IDs with TTL) |
| 6 | Return `2xx` quickly — do heavy processing asynchronously |

### Processing Model

- **Return `2xx` immediately** — do heavy processing asynchronously. We time out after 10 seconds.
- **Queue events** for background processing (SQS, Bull, Durable Objects, etc.).
- **If you need strict ordering**, use a single-threaded consumer keyed on `order_id`.

### Delivery Semantics

Webhook delivery is **at-least-once**. Your handler must be idempotent:

- Deduplicate on `X-Ballpoint-Event-Id` — you may receive the same event more than once
- If you enqueue downstream jobs, deduplicate there too
- Failed deliveries (non-2xx or timeout) are retried with exponential backoff

### Deduplication (Required)

Store `X-Ballpoint-Event-Id` values for at least 24 hours. Reject any event ID you have already processed. This is not optional — at-least-once delivery means duplicates **will** occur during retries and deploys.

- **Lambda:** DynamoDB conditional put with TTL — see the [Lambda example](examples/lambda-webhook/)
- **Cloudflare Workers:** KV with `expirationTtl` — see the [Worker example](examples/cloudflare-worker-webhook/)
- **Express/Node:** Redis `SETNX` with `EX 86400`
- **Any platform:** a SQL `UNIQUE` constraint on `event_id` works too

If you fan out to downstream queues, deduplicate there as well — the event ID is stable across retries.

### Production Status Lifecycle

Production status is set by Ballpoint operations staff. It moves forward only.

| Status | Meaning | Your UX |
|--------|---------|---------|
| `scheduled` | Order created with a future drop date. Waiting for the production date to arrive — a cron auto-transitions to `accepted` when the date hits. Send-now orders skip this state. | "Scheduled" |
| `accepted` | Payment cleared and the order is queued for production. Cancellation allowed up to (and including) this state. | "Order placed" |
| `prep` | Data formatting and pre-production setup (list cleanup, NCOA, address validation). Cancellation no longer possible — staff time is being spent. | "In production" |
| `printing` | In the physical print queue. | "In production" |
| `writing` | Handwritten content being applied by pen plotters. *Handwritten products only.* | "In production" |
| `inserting` | Printed materials being folded into envelopes. *Letter products only.* | "In production" |
| `stamping` | Postage applied, pieces trayed for USPS induction. | "In production" |
| `shipping` | Manifesting and labeling for USPS drop-off. Final production step. | "In production" |
| `complete` | All pieces dropped at USPS. First scans arrive 1–2 business days later. | "Shipped" |
| `cancelled` | Cancelled before production began (only from `scheduled` or `accepted`). Charge auto-refunded. Removed from fulfillment queue. | "Cancelled" |
| `failed` | Terminal error from unrecoverable processing failure after the order was created (e.g., dead-lettered fulfillment job). Pre-creation payment failures return `402 INSUFFICIENT_BALANCE` instead of creating a `failed` order. Non-editable. | "Failed" |

> **Naming heads-up:** `shipping` (production status — staff is manifesting for USPS drop-off) is distinct from `shipped` (USPS status — first scans received from the postal network). Both can appear in the same order's lifecycle on different fields.

**Production sequences by product:**

```
Printed postcards (4x6/6x9):  [scheduled →] accepted → prep → printing → stamping → shipping → complete
Handwritten postcards:         [scheduled →] accepted → prep → printing → writing → stamping → shipping → complete
Color letters:                 [scheduled →] accepted → prep → printing → inserting → stamping → shipping → complete
Hybrid letters:                [scheduled →] accepted → prep → printing → writing → inserting → stamping → shipping → complete
Handwritten letters:           [scheduled →] accepted → prep → printing → writing → inserting → stamping → shipping → complete
```

The `[scheduled →]` prefix only applies to orders with a future drop date. Send-now orders start at `accepted`.

### USPS Tracking Lifecycle

USPS status is set automatically by the scan ingest pipeline. Also forward-only.

| Status | Meaning | Threshold | Your UX |
|--------|---------|-----------|---------|
| `shipped` | At least one piece has any USPS scan. Mail entered the postal network. | ≥1 piece scanned | "Shipped" |
| `out_for_delivery` | Mail is at the recipients' local postal facilities. | ≥51% of pieces at destination | "Out for delivery" |
| `delivered` | ≥80% of pieces resolved (delivered + RTS combined). RTS counts toward the threshold so a campaign with high return rates does not get stuck below `delivered` forever; the RTS detail surfaces separately on the `campaign.mail_tracking.rts_update` event. | ≥80% of pieces resolved | "Delivered" |

#### How USPS data really works

USPS Informed Visibility (IV-MTR) provides **facility-level processing scans**, not carrier-level tracking. For marketing mail there is no "out for delivery" or "delivered to mailbox" event from USPS itself. What IV emits per piece is a raw **Operation Code** (e.g., `015` for AFCS cancellation, `246` for DPS sort), each tagged with:

- `mail_phase` — Phase 0 (origin cancellation) → Phase 1 (origin sort) → Transportation → Phase 2 (destination arrival) → Phase 3 (destination secondary / DPS sort) → Phase 4 (logical delivery — geofence-based, no physical scan)
- `stop_the_clock` (Yes/No) — USPS's official flag indicating whether this scan stops the service-clock for SLA purposes
- Plus PARS scans (separate phase) for return-to-sender and forwarding

The three `usps_status` values above are **Ballpoint rollups** computed from those raw scans using the percentage thresholds. The names are our convention; the underlying signal is real USPS IV data. `delivered` is the industry-standard delivery indicator for flat marketing mail (DPS sort = mail sorted for carrier delivery on the next route).

#### Return-to-sender (RTS) details

RTS pieces count toward the `delivered` threshold above so the badge progresses normally even on campaigns with returns. The **per-piece RTS detail** is delivered on a separate webhook event: `campaign.mail_tracking.rts_update`, which carries the address payload so you can suppress bad addresses on your side. Do not expect RTS information on `usps_status` itself — subscribe to the dedicated event.

### USPS Update Webhook

When USPS tracking status changes, you receive an `order.usps_update` event with piece-level breakdown. Envelope is **flat on the wire** (`event_id` / `event_type` / `timestamp` at the top level, no `data` wrapper) — see [Envelope Shape on the Wire](#envelope-shape-on-the-wire).

```json
{
  "order_id": "ord_7f3a2b",
  "campaign_id": "camp_test",
  "previous_usps_status": "shipped",
  "usps_status": "out_for_delivery",
  "production_status": "shipping",
  "display_status": "out_for_delivery",
  "product_type": "4x6_printed",
  "external_user_id": "user_789",
  "source": "your_source",
  "external_account_id": "acct_partner",
  "piece_count": 500,
  "pieces_delivered": 50,
  "pieces_at_destination": 200,
  "pieces_rts": 3,
  "pieces_scanned": 380,
  "event_id": "b6c3f9d1-2e4a-4d7b-9c1a-5f8e2b3d4c6e",
  "event_type": "order.usps_update",
  "timestamp": "2026-03-05T18:30:00Z"
}
```

**Full field set (15 payload fields + 3 delivery-time fields):**

- `order_id`, `campaign_id` — always present.
- `previous_usps_status`, `usps_status` — string, one of `shipped` / `out_for_delivery` / `delivered`. Forward-only; never fires on regression.
- `production_status`, `display_status`, `product_type` — always present.
- `external_user_id`, `source`, `external_account_id` — always present (echo of the values you passed on order creation, per your partner-side scoping).
- `piece_count`, `pieces_delivered`, `pieces_at_destination`, `pieces_rts`, `pieces_scanned` — integer piece-level counters.
- `event_id`, `event_type`, `timestamp` — delivery-time envelope fields (see [Envelope Shape on the Wire](#envelope-shape-on-the-wire)).

**Fields NOT on this event.** Unlike `order.status_changed` and `order.rescheduled`, `order.usps_update` does **not** carry `list_id` or `external_user_metadata`. For reconciliation on your side, key this event on `order_id` (join back to the original order's `list_id` / `external_user_metadata` from your own store, or from the order-detail GET endpoint).

### Campaign-Level Mail Tracking Events

In addition to order-level updates, you may receive campaign-level tracking events. Only `campaign.mail_tracking.rts_update` is emitted today. The other four campaign-level types are documented historically but no code path enqueues them — see the "not emitted" rows below.

| Event Type | Status | When |
|------------|--------|------|
| `order.drop_completed` | Emitted | A drop reaches `complete`; carries the canonical mailed/suppressed counts and a deprecated suppression-count alias. |
| `order.drop_cancelled` | Emitted | A partner or staff cancellation succeeds before production prevents cancellation. |
| `order.status_changed` | Emitted | Production status changes (scheduled → accepted → prep → printing → ... → shipping → complete; also `cancelled` and `failed`). |
| `order.rescheduled` | Emitted | A same-order reschedule succeeds and changes the mail date. |
| `order.usps_update` | Emitted | USPS scan data changes the order's delivery status. |
| `campaign.mail_tracking.rts_update` | Emitted | Return-to-sender pieces found (per-piece payload with recipient PII for suppression + `contact_id`/`contact_type` for CRM reconciliation). |
| `campaign.mail_tracking.in_transit` | **Not emitted — pending joint decision.** | Historically documented as "first USPS scans detected for the campaign"; no code path emits this event today. Decision needed on whether to ship the emitter or remove from the public docs (framed as a decision, not a promise). Consume the per-order `order.usps_update` in the meantime. |
| `campaign.mail_tracking.out_for_delivery` | **Not emitted — pending joint decision.** | Historically documented as "≥51% of campaign pieces at destination"; no code path emits this event today. Same decision framing as above. Consume the per-order `order.usps_update` (with `usps_status == "out_for_delivery"`) in the meantime. |
| `campaign.mail_tracking.delivered` | **Not emitted — pending joint decision.** | Historically documented as "≥80% of campaign pieces delivered"; no code path emits this event today. Same decision framing. Consume the per-order `order.usps_update` (with `usps_status == "delivered"`) in the meantime. |
| `campaign.mail_tracking.stalled` | **Not emitted — pending joint decision.** | Historically documented as "no scans in 72+ hours with pieces still in transit"; no code path emits this event today. Same decision framing. No consumption surface today. |

> **Do not code against the four "not emitted" rows.** Ballpoint makes no implicit promise to ship any of them — decision is joint. Their example payload shapes have been removed from this document to avoid confusion; if the decision goes toward shipping, the payload contracts will be published then.

#### Dedicated terminal-drop events (v1.7.13+)

`order.drop_completed` and `order.drop_cancelled` are optional, dedicated flat-wire events emitted in addition to the existing `order.status_changed` transition. A consumer that already handles terminal outcomes through `order.status_changed` does not need to consume them.

An existing integration that handles terminal outcomes through `order.status_changed` remains valid and does not need to migrate. The status transition and its dedicated terminal event use independent durable deliveries and may arrive in either order. If you consume both surfaces, choose one as the authoritative trigger for each terminal business action or make that action idempotent on the terminal outcome (for example, `order_id + complete` or `order_id + cancelled`) so the same completion or cancellation is not applied twice. Continue to deduplicate transport retries by `event_id` as described below; transport deduplication alone does not merge the two distinct event types.

`order.drop_completed` fields are `type`, `order_id`, `campaign_id`, `billed_count`, `actual_mailed`, `rts_suppressed_count`, `suppressed_count`, `completed_at`, plus the transport fields. `rts_suppressed_count` is canonical. `suppressed_count` is a deprecated compatibility alias and is always equal to the canonical value during the migration window. Runtime enforces `billed_count = actual_mailed + rts_suppressed_count`.

`order.drop_cancelled` fields are `type`, `order_id`, `campaign_id`, `cancelled_at`, `drop_index`, `total_drops`, `ballpoint_billed`, `ballpoint_billed_amount_tcents`, `reason`, plus the transport fields. `reason` is `user_cancel` or `staff_cancel`; an unbilled cancellation carries amount `0`.

See the exact [completion fixture](contracts/webhooks/order.drop_completed/fixtures/wire.json), [cancellation fixture](contracts/webhooks/order.drop_cancelled/fixtures/wire.json), and their adjacent wire schemas. These events apply to transitions recorded after the runtime release; Ballpoint does not synthesize historical backfill for earlier terminal rows. A legacy transition whose terminal facts cannot be proved from persisted data can therefore remain represented only by `order.status_changed`.

#### Example Payloads

**`campaign.mail_tracking.rts_update`** — this is the only campaign-level event Ballpoint actually emits today. Wrapped envelope (`id`, `type`, `version`, `created_at`, `data`), plus the flat `event_id` / `event_type` / `timestamp` fields added at delivery time (see [Envelope Shape on the Wire](#envelope-shape-on-the-wire)).

```json
{
  "id": "evt_campaign.mail_tracking.rts_update_camp_spring_2026_2026030518_a1b2c3",
  "type": "campaign.mail_tracking.rts_update",
  "version": "2026-02-01",
  "created_at": "2026-03-05T18:30:00Z",
  "data": {
    "campaign_id": "camp_spring_2026",
    "mail_status": "in_transit",
    "total_pieces": 1000,
    "scanned_pieces": 620,
    "scan_coverage": 62.0,
    "delivered": 380,
    "in_transit": 210,
    "out_for_delivery": 30,
    "rts": 12,
    "forwarded": 0,
    "delivered_rate": 38.0,
    "rts_rate": 1.2,
    "first_scan_at": "2026-03-03T14:22:00Z",
    "last_scan_at": "2026-03-05T18:20:00Z",
    "integration": {
      "source": "your_source",
      "external_account_id": "acct_partner",
      "external_user_id": "user_789",
      "external_id": "ps_camp_ref_42"
    },
    "new_rts_pieces": [
      {
        "piece_id": "9f2a1c7b4e6d8a0f3b5c2e14",
        "status": "RTS",
        "recipient_name": "Jane Doe",
        "recipient_address": "123 Main St",
        "recipient_city": "Austin",
        "recipient_state": "TX",
        "recipient_zip": "78701",
        "last_scan_at": "2026-03-05T18:22:00Z",
        "contact_id": "ps_contact_42",
        "contact_type": "PROPERTY"
      }
    ],
    "new_rts_count": 1
  },
  "event_id": "b6c3f9d1-2e4a-4d7b-9c1a-5f8e2b3d4c6e",
  "event_type": "campaign.mail_tracking.rts_update",
  "timestamp": "2026-03-05T18:30:00Z"
}
```

**Field notes on the rollup counters.**

- `mail_status` — rolled-up campaign delivery status string.
- `total_pieces` / `scanned_pieces` / `delivered` / `in_transit` / `out_for_delivery` / `rts` / `forwarded` — integer campaign-wide counters.
- `scan_coverage` / `delivered_rate` / `rts_rate` — percentages on the inclusive `0`–`100` scale.
- `first_scan_at` / `last_scan_at` — ISO 8601 UTC or `null`.
- `integration.source` / `.external_account_id` / `.external_user_id` / `.external_id` — for tenant / user / campaign routing on your side.
- `new_rts_pieces[]` — per-piece objects (see below).
- `new_rts_count` — length of `new_rts_pieces[]`.

Per-piece fields:

- `piece_id` — string — Opaque hash of the IMb + campaign — stable per piece.
- `status` — string — Always `RTS` on this event.
- `recipient_name` / `recipient_address` / `recipient_city` / `recipient_state` / `recipient_zip` — string — Mailed PII, exactly as mailed. Retained for suppression.
- `last_scan_at` — string | null — ISO 8601 timestamp of the last scan associated with the returned piece.
- `contact_id` — string | null — Partner-side recipient identifier, echoed verbatim from the `/recipients` upload. `null` when none was supplied (Ballpoint-direct uploads).
- `contact_type` — string | null — `PROPERTY` or `MAILING`. Disambiguates two pieces with the same `contact_id` (one contact may have both a property and a mailing address mailed in the same campaign). `null` when no address-type was supplied.

Note: the unique recipient key is `(contact_id, contact_type)`. A single `contact_id` may appear twice in one payload (both PROPERTY and MAILING came back RTS). These are **pass-through** — Ballpoint does not address-match; the partner pre-resolves the key at manifest-upload time. The existing `recipient_*` PII is unchanged (kept for suppression).

### Retry Policy

Delivery is at-least-once. Retries run in two layers, back-to-back:

**Layer 1 — inline HTTP attempts within one endpoint round.**

- Up to **3 HTTP attempts** per outbox pass, with **1s / 2s** backoff between attempts (formula `2^(attempt-1)`, capped at 30s — the loop stops after attempt 3, so no 3rd sleep / no 4s ever occurs in this schedule).
- **10-second timeout** per HTTP attempt.
- **4xx responses (400–499) short-circuit the current inline round** (client/config problem). The durable endpoint target remains failed and is eligible for a later Layer-2 round until its round limit is exhausted.
- 5xx / timeout / connection error continues to the next inline attempt (and, if all fail, to Layer 2).

**Layer 2 — durable per-endpoint rounds.**

- Up to **5 total rounds per endpoint target** (each round is one Layer-1 pass above).
- Between eligible rounds the next retry is scheduled at `now + min(10 * 3^(round-1), 3600)` seconds: **10s → 30s → 90s → 270s** before rounds 2–5.
- After 5 failed rounds that endpoint target moves to `dead_letter`; another endpoint that already returned `2xx` stays delivered and is never re-emitted. There is no automatic dead-letter replay. The maximum is **15 HTTP POSTs per endpoint** for repeated 5xx/timeouts (3 inline attempts × 5 rounds), or **5** for repeated 4xx responses (one short-circuited request per round).

**Circuit breaker.** Sustained 5xx / timeout / connection errors open the `webhooks` circuit; queued events pause until the circuit half-opens or closes. 4xx does not trip the circuit.

**Endpoint auto-disable.** 10 consecutive failed deliveries across events on the same endpoint flip `active` to `false`; the partner is notified out-of-band. Contact us to re-enable.

**Your responsibilities:**
- Return `2xx` within 10 seconds.
- Deduplicate on `X-Ballpoint-Event-Id`, which is stable across all endpoints, inline retries, and durable outbox rounds for the same logical event.
- Reject payloads with `X-Ballpoint-Timestamp` older than 5 minutes or more than 2 minutes in the future.

---

### Per-piece RTS Push-Back (V1)

When the USPS scan pipeline detects a returned-to-sender piece, Ballpoint emits a per-piece RTS event server-to-server so the partner can reconcile each undeliverable mailing piece against its CRM contact directly.

> **Status:** Live today — fires whenever a webhook endpoint is configured for the account/source. The V1 contract described here is what Ballpoint emits.

**Delivery**

- HTTP `POST` to the partner-registered webhook endpoint (same endpoint configured at onboarding for `order.status_changed`).
- HMAC-signed using the same scheme as `order.status_changed` (see [Signature Verification](#signature-verification)).
- Server-to-server only.

**Batch limits**

- Max **100 `new_rts_pieces` entries per event**. Larger result sets are emitted as additional events.

**Per entry**

| Field | Type | Required | Description |
|---|---|---|---|
| `piece_id` | string | yes | Opaque hash of the IMb + campaign — stable per piece. |
| `status` | string | yes | Always `RTS` on this event. |
| `recipient_name` | string | yes | Mailed recipient name. |
| `recipient_address` | string | yes | Street address as mailed. |
| `recipient_city` | string | yes | City as mailed. |
| `recipient_state` | string | yes | 2-letter state as mailed. |
| `recipient_zip` | string | yes | 5 or 5+4 zip as mailed. |
| `last_scan_at` | string \| null | yes | ISO 8601 timestamp of the last scan associated with the returned piece. |
| `contact_id` | string \| null | yes | Opaque partner-side contact identifier (e.g. PropStream `contact_id`). Echoed verbatim from the `/recipients` upload. `null` when no partner contact was supplied (Ballpoint-direct uploads). |
| `contact_type` | string \| null | yes | `PROPERTY` or `MAILING` — disambiguates two pieces with the same `contact_id` (one contact may have both a property address and a separate mailing address mailed in the same campaign). `null` when no partner address-type was supplied. |

**Notes**

- The unique recipient key is `(contact_id, contact_type)`. A single `contact_id` may appear twice in a single payload when both a PROPERTY and a MAILING address for the same contact were mailed and both came back RTS.
- Recipient PII (`recipient_name`/`recipient_address`/`recipient_city`/`recipient_state`/`recipient_zip`) is included on every entry so partners can suppress by mailed address even when no CRM key is present.
- Both `contact_id` and `contact_type` are pass-through. Ballpoint does not interpret or address-match — the partner pre-resolves the recipient key at manifest-upload time. Manifests without these columns ingest cleanly — they just emit `null` for both fields on the RTS event.
- This event is distinct from `order.status_changed`. The two events use the same delivery channel but carry different payloads.

---

## 8. Real-Time UI via SSE (Optional)

If you're embedding order status in an iframe or dashboard, SSE gives instant updates without polling. **Webhooks are the primary integration path** — SSE is for display only.

### Step 1: Mint a Token (Server-Side)

```bash
curl -X POST https://api.ballpointmarketing.com/v1/billing/orders/ord_7f3a2b/sse-token \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME"
```

Response:

```json
{
  "order_id": "ord_7f3a2b",
  "expires_at": "2026-03-01T14:05:00Z",
  "ttl_seconds": 300
}
```

This sets an `HttpOnly; Secure; SameSite=None` cookie scoped to the SSE endpoint. The token expires in 5 minutes.

### Step 2: Connect from the Browser

```javascript
// Cookie was set by the sse-token call — sent automatically
const es = new EventSource(
  "https://api.ballpointmarketing.com/v1/billing/orders/ord_7f3a2b/events",
  { withCredentials: true }
);

es.onmessage = (event) => {
  const data = JSON.parse(event.data);
  updateStatusUI(data.display_status);
};

es.onerror = () => {
  // Token expired or connection dropped — mint a new token and reconnect
  es.close();
  // ... re-mint token, re-create EventSource
};
```

### CORS

CORS is configured per-partner. Provide your production domain (e.g., `your-app.example.com`) and we will add it. If you need additional origins, let us know.

---

## 9. Order Lifecycle Diagram

An order has two parallel status tracks. They are independent — USPS never overwrites production status, and vice versa.

```
              YOUR API CALL                             BALLPOINT PRODUCTION                                                            USPS SCANS
              ─────────────                             ────────────────────                                                            ──────────

           POST /v1/billing/orders
                    │
                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                                                                │
│  ┌───────────┐  ┌────────┐  ┌──────┐  ┌────────┐  ┌────────┐  ┌─────────┐  ┌────────┐  ┌────────┐  ┌────────┐                                 │
│  │[scheduled]│─►│accepted│─►│ prep │─►│printing│─►│writing │─►│inserting│─►│stamping│─►│shipping│─►│complete│                                 │
│  └───────────┘  └────────┘  └──────┘  └────────┘  └────────┘  └─────────┘  └────────┘  └────────┘  └────────┘                                 │
│                      │                                                                                  │                                      │
│                      │ POST /orders/{id}/cancel                                                         │ 1-2 days                             │
│                      ▼                                                                                  ▼                                      │
│                 ┌──────────┐                                                  ┌─────────┐   ┌───────────┐   ┌──────────┐                       │
│                 │cancelled │                                                  │ shipped │──►│out_for_   │──►│delivered │                       │
│                 └──────────┘                                                  │         │   │delivery   │   │          │                       │
│                                                                               └─────────┘   └───────────┘   └──────────┘                       │
│                                                                                                                                                │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

    PRODUCTION TRACK (top)                                    USPS TRACK (bottom)
    Set by Ballpoint staff                                    Set automatically by scan pipeline
    Forward-only                                              Forward-only, starts 1-2 days after "complete"
    [scheduled] only for future-dated orders;                 Plus terminal `failed` for unrecoverable errors
    send-now orders start at `accepted`
```

**Not all products go through every step.** See [production sequences](#production-status-lifecycle) for which steps apply to each product type.

**Display status** = USPS status when available, otherwise production status. This is the single field you should show to end users — it's returned as `display_status` in API responses and webhooks.

### Partner-Billed Variant (Payment Gate)

Accounts where `requires_payment_confirmation = TRUE` (e.g. PropStream) take a slightly different entry path: the order is created without an immediate balance debit and waits on `POST /v1/billing/orders/{id}/confirm-payment`.

```
POST /orders (partner-billed)
       │
       ├── send-now ──────────► pending_payment ──/confirm-payment success──► accepted ──► prep ──► … ──► complete
       │                              │
       │                              └─/confirm-payment failed─► payment_failed (terminal)
       │
       └── future mail_date ──► scheduled, payment_confirmed=FALSE
                                       │
                                       ├── /confirm-payment success ──► payment_confirmed=TRUE, stays scheduled,
                                       │                                cron advances on production date
                                       │
                                       ├── /confirm-payment failed   ──► payment_failed (terminal)
                                       │
                                       └── production date passes
                                           with no /confirm-payment   ──► payment_failed (terminal, no debit)
```

The account billing policy runs on `/confirm-payment success` (same `charge_order` flow used for direct accounts at creation time): stripe debits balance, manual records usage, and none records no charge/usage. Cancelling from `pending_payment` or `payment_failed` is free — no debit ever happened. Cancelling from `accepted` (or `scheduled` after a successful confirmation) applies the mode-specific refund policy. See [§6k. Confirm Payment](#6k-confirm-payment-partner-payment-gate) for the full endpoint contract.

---

## 10. Error Handling

### Error Response Format

All error responses (4xx, 5xx) return a JSON object with this shape:

```json
{
  "error_code": "INVALID_PRODUCT_TYPE",
  "message": "Product type 'magic_letter' is not available",
  "detail": {}
}
```

| Field | Always present | Description |
|-------|---------------|-------------|
| `error_code` | Yes | Machine-readable code (e.g., `INVALID_PRODUCT_TYPE`, `MISSING_FIELD`, `IDEMPOTENCY_KEY_REUSE`) |
| `message` | Yes | Human-readable explanation |
| `detail` | No | Additional context (e.g., field-level validation details) |

Use `error_code` for programmatic handling. Use `message` for logging/display.

### Status Code Reference

| Code | Meaning | Retry? | What to Do |
|------|---------|--------|------------|
| `200` | Success | — | — |
| `202` | Order accepted | — | — |
| `400` | Bad request (malformed JSON, missing fields) | **No** | Fix your request payload |
| `401` | Authentication failed | **No** | Check your API key |
| `402` | Insufficient balance or spending limit hit | **No** | Applies only to accounts with prepaid balance or spending-limit enforcement; `billing_mode: none` accounts always pass balance checks |
| `403` | Account suspended | **No** | Contact Ballpoint |
| `404` | Resource not found | **No** | Check the ID |
| `409` | Conflict (idempotency key reuse with different body) | **No** | Use a new idempotency key |
| `422` | Validation error (bad product type, missing envelope_style) | **No** | Fix your request |
| `429` | Rate limited | **Yes** — after `Retry-After` | Wait, then retry |
| `500` | Server error | **Yes** — same idempotency key | Retry with exponential backoff |
| `502` | Gateway error | **Yes** — same idempotency key | Retry |
| `503` | Service unavailable | **Yes** — after `Retry-After` | Wait, then retry |
| `504` | Gateway timeout | **Yes** — same idempotency key | Request may have succeeded — retry with same key to find out |

### Retry Strategy

```
Attempt 1: immediate
Attempt 2: wait 1s
Attempt 3: wait 2s
Attempt 4: wait 4s
Attempt 5: wait 8s (give up)
```

For `POST /orders`, **always retry with the same `Idempotency-Key`**. You will never create duplicate orders.

### Rate Limits

- **120 requests per minute** per account
- **10,000 requests per day** per account

Every response includes:

```
X-RateLimit-Remaining: 118
X-RateLimit-Limit: 120
```

On `429` responses:

```
Retry-After: 12
```

### Client Error Telemetry (automatic)

`POST /v1/partner/client-errors` — the embedded iframe calls this endpoint **automatically** to log client-side JavaScript errors it catches during a partner session (`window.onerror` and `unhandledrejection`). **Partners do not need to integrate it**; it is documented here because the request is authenticated with `X-Partner-Key` and will appear in partner-side network monitoring as expected traffic.

Intake is **log-only** — every accepted event becomes a single structured log line on Ballpoint's side. No database row, no webhook fan-out, no state change, and no request-body echo in any response. PII (emails, phone numbers, ZIPs, long digit-runs) is scrubbed **client-side by the iframe** before send, and the iframe caps itself at 5 events per page-load (deduped).

**Caps.** Request body ≤ **4096 bytes**; per-partner-key rate limit **60 requests / minute** (sliding window, independent of the account-wide 120/min bucket above); per-field caps on the JSON payload — `name` ≤ 50, `message` ≤ 220, `source` ≤ 300, `pageId` ≤ 40, `buildId` ≤ 64, `lineno`/`colno` 0–10,000,000, `contractVersions` ≤ 6 keys of ≤ 20 chars each. Extra fields and control characters (`\r`, `\n`, `0x00`–`0x1F`) are rejected.

| Status | Meaning | Body |
|--------|---------|------|
| `204 No Content` | Accepted and logged. | empty |
| `401 Unauthorized` | Missing or invalid `X-Partner-Key`. | standard auth error envelope |
| `413 Payload Too Large` | Request body larger than 4096 bytes. | empty |
| `422 Unprocessable Entity` | Field cap exceeded, unknown field, or control character present. | empty |
| `429 Too Many Requests` | Over 60 requests/minute for this partner key. | empty |

413/422/429 responses have empty bodies by design (no payload echo, no field-name leak). 401 returns the standard auth error envelope used across `/v1/billing/partner/*`.

Payload example (fields the iframe sends):

```json
{"type":"error","name":"TypeError","message":"Cannot read properties of undefined","source":"https://mailer.ballpointmarketing.com/js/app.js","lineno":42,"colno":7,"pageId":"pg_01H8XYZ","buildId":"abc1234","contractVersions":{"iframe":"1","api":"3","partner":"1"}}
```

Available on staging now; production on the next API release.

### Iframe Funnel Analytics (automatic)

`POST /v1/partner/funnel-events` is prepared for the embedded iframe to send one
funnel milestone per request. **Partners do not need to call or integrate this
endpoint.** It is documented because the automatic request uses
`X-Partner-Key` plus `X-External-User-ID` and may appear in partner-side network
monitoring during staging validation.

The intake is **log-only**: an accepted event produces a structured Ballpoint
log entry and returns `204 No Content`. It does not create a database row, emit
a webhook, change campaign/order state, or echo the request. Delivery is
best-effort and never blocks or retries the user's campaign flow.

One request carries exactly one of these events:

- `campaign_started`
- `product_selected`
- `copy_edited`
- `proof_viewed`
- `submit_clicked`
- `campaign_submitted_confirmed`

`campaign_submitted_confirmed` is emitted only after a successful payment
result. `submit_clicked` may appear more than once for the same session when a
user reopens the payment handoff. Drop-off is not sent as a separate event; it
is derived from the last accepted event for a session.

```json
{
  "event": "product_selected",
  "session_id": "sfe_9f2a1c4b7e3d0a11",
  "sequence": 2,
  "elapsed_ms_client": 4230,
  "page_id": "products",
  "flow_type": "single"
}
```

The payload is capped at **2048 bytes**. `session_id` must match
`sfe_` followed by 16 lowercase hexadecimal characters; `sequence` is 1–50;
`elapsed_ms_client` is 0–86,400,000; `page_id` is a safe identifier up to 40
characters; and optional `flow_type` is `single`, `multi`, or `split`. Extra
fields are rejected. Account, tenant/source, and user attribution are not
accepted in the JSON body: account and tenant/source are derived from the
authenticated partner principal, and user context comes from the required
`X-External-User-ID` header. The event schema accepts no recipient PII or typed
copy.

This intake has an endpoint-specific ceiling of **1,000 attempts with valid
partner and user context per 60 seconds** for each
account/source/external-account tuple, enforced per API process. Its dedicated
empty `429` response does not include the general API rate-limit headers or
`Retry-After` described elsewhere in this kit.

| Status | Meaning | Body |
|--------|---------|------|
| `204 No Content` | Accepted and logged. | empty |
| `401 Unauthorized` | Missing/invalid partner identity headers. | standard auth error envelope |
| `413 Payload Too Large` | Request body larger than 2048 bytes. | empty |
| `422 Unprocessable Entity` | Invalid or extra field. | empty |
| `429 Too Many Requests` | Telemetry intake rate limit exceeded. | empty |

This contract is prepared for local and staging validation. Its inclusion here
does not assert staging runtime deployment or production availability.

---

## 11. Sandbox & Testing

### Test vs. Live

| | Test Key (`pk_test_...`) | Live Key (`pk_live_...`) |
|---|---|---|
| Orders created | Yes | Yes |
| Real mail printed & sent | **No** | **Yes** |
| USPS tracking | No (no physical mail) | Yes (1-2 days after drop) |
| Billing | Invoiced (same as live) | Invoiced |
| Validation & error responses | Identical | Identical |

### Test Key Behavior

Your test key (`pk_test_PARTNER_REPLACE_ME`):

- All orders succeed immediately (`billing_mode: none`)
- No real mail is printed or sent
- Validation, status codes, and error responses are identical to production
- Use `camp_test` as the campaign ID for testing

**What happens to test orders?** Test orders are created with status `accepted` and stay there — production status does not auto-advance because there is no physical fulfillment. To test your webhook handler, ask us to trigger test events against your endpoint. We can simulate the full lifecycle (`accepted` → `prep` → `printing` → ... → `shipping` → `complete` → `shipped` → `delivered`) so you can verify your handler end-to-end without waiting for real mail.

### Webhook Testing

Once you've given us your webhook URL, we can:
- Trigger test events against your endpoint
- Help you verify your signature verification logic
- Replay dead-lettered events

### Going Live Checklist

Before switching to your live key:

```
[ ] Orders create successfully with test key (202 response)
[ ] Preview endpoint returns expected pricing
[ ] Webhook handler receives events and verifies signature
[ ] Webhook handler deduplicates on X-Ballpoint-Event-Id
[ ] Webhook handler rejects timestamps older than 5 min or more than 2 min in the future
[ ] Retry logic handles 429 (waits for Retry-After) and 5xx (retries with same idempotency key)
[ ] Cancel works from accepted status
[ ] List orders with external_user_id filter returns correct results
[ ] Order tracking endpoint returns delivery data (will be empty until real mail is sent)
[ ] Switch to live key and create one small real order to verify end-to-end
```

---

## 12. Endpoint Quick Reference

| Action | Method | Path | Key Headers |
|--------|--------|------|-------------|
| Preview cost (single order) | `POST` | `/v1/billing/orders/preview` | `X-Partner-Key` |
| Resolve partner feature flags (iframe automatic) | `GET` | `/v1/config` | `X-Partner-Key`, optional `X-External-User-ID` |
| Preview campaign cost (payment-gate) | `POST` | `/v1/billing/campaigns/preview` | `X-Partner-Key` (server-to-server) |
| Create order | `POST` | `/v1/billing/orders` | `X-Partner-Key`, `Idempotency-Key`, `X-External-User-ID` |
| Get order | `GET` | `/v1/billing/orders/{id}` | `X-Partner-Key` |
| List orders | `GET` | `/v1/billing/orders?external_user_id=...&status=...&limit=20&offset=0` | `X-Partner-Key` |
| Cancel order | `POST` | `/orders/{id}/cancel` | `X-Partner-Key` |
| Confirm payment | `POST` | `/v1/billing/orders/{id}/confirm-payment` | `X-Partner-Key` (server-to-server only) |
| Partner dashboard stats | `GET` | `/v1/billing/partner/stats?days=30&list_id=...&external_user_id=...` | `X-Partner-Key` |
| Partner dashboard orders | `GET` | `/v1/billing/partner/orders?days=30&list_id=...&status=...` | `X-Partner-Key` |
| Recipient/direct-mail search (iframe automatic) | `GET` | `/v1/mail-tracking/recipients/search?q=...&limit=20&offset=0` | `X-Partner-Key`, optional `X-External-User-ID` |
| Order tracking | `GET` | `/v1/orders/{id}/mail-tracking` | `X-Partner-Key` |
| Campaign tracking | `GET` | `/v1/campaigns/{id}/mail-tracking` | `X-Partner-Key` |
| Pricing catalog | `GET` | `/v1/billing/pricing?product_type=...` | `X-Partner-Key` |
| Mint SSE token | `POST` | `/v1/billing/orders/{id}/sse-token` | `X-Partner-Key` |
| SSE stream | `GET` | `/v1/billing/orders/{id}/events` | *(cookie auth via sse-token)* |
| Client-error telemetry (iframe, automatic — no partner action needed) | `POST` | `/v1/partner/client-errors` | `X-Partner-Key` |
| Funnel analytics (iframe, automatic — no partner action needed) | `POST` | `/v1/partner/funnel-events` | `X-Partner-Key`, `X-External-User-ID` |
| Health check | `GET` | `/health` | *(none)* |

---

## 13. Sample Code & Templates

### Webhook Receiver Templates

| Platform | Location |
|----------|----------|
| Express (Node.js) | [`examples/express-integration/`](examples/express-integration/) — full integration app with order creation, webhook handling, and dashboard |
| AWS Lambda | [`examples/lambda-webhook/`](examples/lambda-webhook/) — minimal Lambda handler with API Gateway setup instructions |
| Cloudflare Workers | [`examples/cloudflare-worker-webhook/`](examples/cloudflare-worker-webhook/) — Worker using Web Crypto API |

All templates implement the same verification logic: HMAC-SHA256 signature check, 5-minute replay protection, and event deduplication.

### Inline Example: Express Webhook Handler

A minimal Node.js webhook handler with signature verification, replay protection, and deduplication:

```javascript
const express = require("express");
const crypto = require("crypto");

const app = express();
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || "";

// IMPORTANT: Use raw body for signature verification (not parsed JSON)
app.post(
  "/webhooks/ballpoint",
  express.raw({ type: "application/json" }),
  (req, res) => {
    const signature = req.headers["x-ballpoint-signature"] || "";
    const timestamp = req.headers["x-ballpoint-timestamp"] || "";
    const eventId = req.headers["x-ballpoint-event-id"] || "";

    // 1. Verify signature
    if (!verifySignature(req.body, timestamp, signature, WEBHOOK_SECRET)) {
      console.warn(`Rejected: invalid signature (event ${eventId})`);
      return res.status(400).json({ error: "Invalid signature" });
    }

    // 2. Reject stale timestamps (replay protection)
    //    Also reject timestamps more than 2 minutes in the future (clock skew)
    const age = Date.now() - new Date(timestamp).getTime();
    if (age > 5 * 60 * 1000 || age < -2 * 60 * 1000) {
      console.warn(`Rejected: timestamp out of range (${timestamp})`);
      return res.status(400).json({ error: "Timestamp out of range" });
    }

    // 3. Parse payload
    const event = JSON.parse(req.body.toString());
    const eventType = event.event_type || event.type;
    console.log(`Received: ${eventType} (${eventId})`);

    // 4. Deduplicate on eventId (check your database)
    // if (await alreadyProcessed(eventId)) {
    //   return res.status(200).json({ received: true, duplicate: true });
    // }

    // 5. Process the event
    // order.* events are flat; the RTS event keeps its legacy data wrapper.
    const payload = eventType === "campaign.mail_tracking.rts_update" ? event.data : event;
    const { order_id, display_status, production_status, new_status, external_user_id } = payload;
    const status = display_status || production_status || new_status || eventType;
    console.log(`Order ${order_id || "n/a"} → ${status} (user: ${external_user_id || "n/a"})`);

    // TODO: Update your database, notify the user, etc.

    // 6. Return 200 quickly — do heavy processing async
    res.status(200).json({ received: true });
  }
);

function verifySignature(bodyBuffer, timestamp, signature, secret) {
  const expected = crypto
    .createHmac("sha256", secret)
    .update(timestamp, "utf8")
    .update(bodyBuffer)
    .digest();
  const received = signature.replace("sha256=", "");
  const receivedBytes = Buffer.from(received, "hex");
  return receivedBytes.length === expected.length &&
    crypto.timingSafeEqual(expected, receivedBytes);
}

app.listen(3000, () => console.log("Webhook handler on :3000"));
```

---

## 14. Support

Contact details will be shared during onboarding (Slack channel, email, escalation path).

### Health Check

```bash
curl https://api.ballpointmarketing.com/health
# → {"status": "ok", ...}
```

### What Counts as Urgent (P1)

- `POST /orders` returning 500 for multiple requests
- Webhook delivery completely stopped
- All requests returning 401

---

*Questions? Contact your Ballpoint point-of-contact — we're here to get this running smoothly.*

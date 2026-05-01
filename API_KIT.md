# Ballpoint Marketing API — Partner Integration Kit

> **v1.2.2 · May 2026**
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
| Postman sandbox environment | [`examples/ballpoint-sandbox.postman_environment.json`](examples/ballpoint-sandbox.postman_environment.json) |
| Postman production environment | [`examples/ballpoint-production.postman_environment.json`](examples/ballpoint-production.postman_environment.json) |
| Express integration example | [`examples/express-integration/`](examples/express-integration/) |
| AWS Lambda webhook template | [`examples/lambda-webhook/`](examples/lambda-webhook/) |
| Cloudflare Worker webhook template | [`examples/cloudflare-worker-webhook/`](examples/cloudflare-worker-webhook/) |
| OpenAPI spec | [`docs/ballpoint-api-spec-v2.yaml`](docs/ballpoint-api-spec-v2.yaml) |

---

## Table of Contents

1. [Your Credentials](#1-your-credentials)
2. [How It Works (End-to-End Flow)](#2-how-it-works-end-to-end-flow)
3. [How Billing Works](#3-how-billing-works)
4. [Integration Patterns](#4-integration-patterns)
5. [Product Catalog & Pricing](#5-product-catalog--pricing)
6. [API Reference](#6-api-reference)
   - [6a. Preview Cost](#6a-preview-cost)
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
│  8. Check Tracking ───► GET /orders/{id}/mail-tracking                │
│     (anytime)           GET /campaigns/{id}/mail-tracking             │
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
| `4x6_handwritten` | 4x6 pen-plotted postcard | `first_class` only |
| `6x9_printed` | Large 6x9 printed postcard | `first_class`, `standard` |
| `6x9_handwritten` | 6x9 pen-plotted postcard | `first_class` only |

#### Letters

Envelope + insert. Letter orders **require** an `envelope_style` field.

| Product Type | Envelope | Insert | Envelope Size | Postage Options |
|-------------|----------|--------|---------------|-----------------|
| `color_letter` | Printed | Printed 8.5x11 (folded) | #10 | `first_class`, `standard` |
| `hybrid_letter` | Handwritten | Printed | 5x7 | `first_class`, `presort` |
| `handwritten_letter` | Handwritten | Handwritten | 5x7 | `first_class`, `presort` |

#### Envelope Styles

Available styles: `candy`, `party`, `pastel`, `confetti`, `desert`, `floral`, `stone`, `retro`, `deco`, `doodle`, `plain_white`

- **`color_letter`** uses #10 envelopes — only `plain_white` is supported.
- **`hybrid_letter`** and **`handwritten_letter`** use 5x7 envelopes — all decorative styles available.
- **Postcards** — do not include `envelope_style` (the API will reject it).

### Pricing Table

Prices are in **tenth-cents** (tcents). Divide by 10,000 for dollars: `5054 tcents = $0.5054/piece`.

| Product | Postage | Per Piece (tcents) | Per Piece ($) | 500 pieces |
|---------|---------|-------------------|---------------|------------|
| 4x6 Printed Postcard | First Class | 5,054 | $0.5054 | $252.70 |
| 4x6 Printed Postcard | Standard | 4,910 | $0.4910 | $245.50 |
| 4x6 Handwritten Postcard | First Class | 7,554 | $0.7554 | $377.70 |
| 6x9 Printed Postcard | First Class | 5,810 | $0.5810 | $290.50 |
| 6x9 Printed Postcard | Standard | 5,510 | $0.5510 | $275.50 |
| 6x9 Handwritten Postcard | First Class | 8,310 | $0.8310 | $415.50 |
| Color Letter (#10) | First Class | 8,210 | $0.8210 | $410.50 |
| Color Letter (#10) | Standard | 5,730 | $0.5730 | $286.50 |
| Hybrid Letter (5x7) | First Class | 10,500 | $1.0500 | $525.00 |
| Hybrid Letter (5x7) | Presort | 7,800 | $0.7800 | $390.00 |
| Handwritten Letter (5x7) | First Class | 14,500 | $1.4500 | $725.00 |
| Handwritten Letter (5x7) | Presort | 9,500 | $0.9500 | $475.00 |

Total cost = `unit_price_tcents × piece_count`. No minimums, no surcharges.

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

Response:

```json
[
  {
    "product_type": "4x6_printed",
    "postage_type": "first_class",
    "unit_price_tcents": 5054,
    "min_quantity": 1,
    "max_quantity": null,
    "description": "4x6 printed postcard - 1st class"
  },
  {
    "product_type": "4x6_printed",
    "postage_type": "standard",
    "unit_price_tcents": 4910,
    "min_quantity": 1,
    "max_quantity": null,
    "description": "4x6 printed postcard - standard"
  }
]
```

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
  "unit_price_tcents": 5054,
  "total_tcents": 2527000,
  "piece_count": 500,
  "billing_mode": "none",
  "balance_cents": null,
  "limits": {
    "passed": true,
    "checks": [
      {"type": "order_limit", "passed": true, "order_cost_cents": 25270, "limit_cents": 500000},
      {"type": "balance", "passed": true, "required_cents": 25270, "available_cents": null}
    ]
  }
}
```

The preview runs the same limit checks as real order creation but reports results as warnings. If `limits.passed` is `false`, the real order would fail — show the user why before they submit.

> **Note:** For accounts with `billing_mode: none`, `balance_cents` is `null` and balance checks always pass. The preview still validates product type, postage, and piece count.

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
  "unit_price_tcents": 5054,
  "total_price_tcents": 2527000,
  "external_id": "ps_order_12345",
  "external_user_id": "user_789",
  "created_at": "2026-03-01T14:00:00Z"
}
```

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
  "campaign_id": "camp_test",
  "product_type": "4x6_printed",
  "postage_type": "first_class",
  "piece_count": 500,
  "unit_price_tcents": 5054,
  "total_price_tcents": 2527000,
  "production_status": "printing",
  "usps_status": null,
  "display_status": "printing",
  "external_id": "ps_order_12345",
  "external_user_id": "user_789",
  "status_changed_at": "2026-03-02T09:00:00Z",
  "created_at": "2026-03-01T14:00:00Z"
}
```

`display_status` is the single field to show your users. `usps_status` is `null` until USPS scans arrive (1–2 days after production completes).

---

### 6d. List Orders

```
GET /v1/billing/orders
```

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `external_user_id` | string | — | Filter to a specific platform user |
| `status` | string | — | Filter by order status (e.g., `accepted`, `printing`, `complete`, `delivered`) |
| `limit` | integer | 20 | Results per page (1–100) |
| `offset` | integer | 0 | Pagination offset |

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

Cancel is allowed **only while the order is in `scheduled` or `accepted` status** (before production prep begins).

```
PATCH /v1/billing/orders/{order_id}/status
```

**Example:**

```bash
curl -X PATCH https://api.ballpointmarketing.com/v1/billing/orders/ord_7f3a2b/status \
  -H "X-Partner-Key: pk_test_PARTNER_REPLACE_ME" \
  -H "Content-Type: application/json" \
  -d '{"status": "cancelled", "note": "Customer changed their mind"}'
```

**Response (`200`):**

```json
{
  "order_id": "ord_7f3a2b",
  "previous_production_status": "accepted",
  "production_status": "cancelled",
  "display_status": "cancelled",
  "refund": {
    "transaction_id": "txn_a1b2c3",
    "refund_cents": 25270,
    "balance_after_cents": 100000
  }
}
```

**Note:** Cancellation behavior depends on the account's billing model. For invoiced partners (`billing_mode: none`), the `refund` field will be `null` — there is no charge to reverse, and the cancelled order won't appear on the next invoice. For payment-gated partners, cancelling from `pending_payment` or `payment_failed` is free (no debit happened); cancelling from `accepted` (after `/confirm-payment success`) auto-refunds the partner-balance debit.

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

- Captured **only at order creation** — represents the end-user who placed the order. Subsequent `PATCH /orders/{id}` calls cannot mutate it.
- Echoed on every `order.status_changed` event (covers status changes, cancel, complete, payment_failed).
- Subject to the same retention window as recipient PII — when an order ages past the partner-controlled retention threshold, this field is scrubbed from our storage automatically.

**Sample webhook payload with the field present:**

```json
{
  "type": "order.status_changed",
  "data": {
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
    }
  }
}
```

If you didn't send the field at creation, it is omitted from the payload (or set to `null`).

---

### 6k. Confirm Payment (Partner Payment Gate)

For accounts where Ballpoint waits for the partner to debit the end-user before producing the order (currently PropStream — flagged via `accounts.requires_payment_confirmation = TRUE`), use this endpoint to report the result of the end-user payment attempt.

**Security boundary**

- The end-user payment is captured **on the partner side** using the partner's own payment provider. Ballpoint never sees card data, payment-method data, or any PCI-relevant payload.
- `/confirm-payment` is a **server-to-server** call by integration contract. It must be issued from the partner backend after the partner has confirmed the payment outcome with its payment provider. The customer browser must **not** call this endpoint directly — the partner key would be exposed.
- Pricing values shown in the iframe or carried on browser-side events (e.g. `campaign_submitted.total_dollars`) are **for UX/display only**. Before charging the end-user, the partner backend must call `GET /v1/billing/partner/orders` and use the server-side amount as the billing source of truth. Browser-provided values must never be treated as authoritative.

**User-flow timing**

Where this call sits in the end-user journey for an iframe-driven order:

1. iframe loads. Parent app sends `set_api_config` + `set_list`.
2. End-user creates the campaign locally inside the iframe (picks list, product, drop type).
3. iframe emits `campaign_created` to the parent. `orderIds` in this event are local iframe IDs only — no Ballpoint order exists yet.
4. End-user customizes the campaign and clicks Submit.
5. iframe calls `POST /v1/billing/partner/orders`. Ballpoint creates the order in `pending_payment` (no charge yet).
6. iframe emits `campaign_submitted` to the parent (carries `orders[].ballpointOrderId` and `total_dollars` for UX/display). Use this as the trigger to start the payment popup.
7. Partner backend refetches the authoritative amount from `GET /v1/billing/partner/orders` before charging.
8. Partner shows the payment popup; end-user pays via the partner's payment provider.
9. Partner backend calls `POST /v1/billing/orders/{order_id}/confirm-payment` with `status: success` (or `failed`).
10. On success, Ballpoint debits the partner balance and moves the order from `pending_payment` to `accepted`. Production proceeds.

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

- **`status:success`** — wholesale charge runs (debits the partner balance), `payment_confirmed` flips to `TRUE`. Send-now orders advance from `pending_payment` to `accepted`. Scheduled orders stay `scheduled` until the production date hits.
- **`status:failed`** — order moves to `payment_failed` (terminal) and `failure_reason` is stored. No partner balance debit happens.
- **Idempotency** — repeating the same status is a no-op (last call wins for `transaction_id` and `failure_reason`). Repeating with the **opposite** status is rejected with `409` — payment outcome is unidirectional once recorded.
- **Cancelled orders** — calling `/confirm-payment` against a cancelled order returns `409 ORDER_CANCELLED`.
- **Late confirmation** — if the order's `scheduled_production_date` passes without a `success` call, a Ballpoint cron flips it to `payment_failed` automatically. A subsequent `/confirm-payment` returns `409 PAYMENT_ALREADY_FAILED`.
- **No-gate accounts** — calling `/confirm-payment` against an account where `requires_payment_confirmation = FALSE` returns `409 PAYMENT_GATE_NOT_ACTIVE` (the order was already debited at creation).
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

`billing.amount_cents` is the wholesale amount Ballpoint debited from the partner balance — this is the value carried on the cancellation webhook as `ballpoint_billed_amount_tcents` if the order is later cancelled. It is **not** the same as `amount_charged_to_user_cents`, which is what the partner billed the end-user.

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

> **For payment flows:** refetch the relevant order from `GET /v1/billing/partner/orders` server-side before charging the end-user. Browser-side values like `campaign_submitted.total_dollars` are UX/display only. See [§6k](#6k-confirm-payment-partner-payment-gate) and [IFRAME_KIT.md](IFRAME_KIT.md) for the full payment-gate context.

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

Filters compose with AND. `total_cost_cents` may be `null` for unpriced orders or billing configurations where no partner-facing amount is set.

---

## 7. Status Updates via Webhooks

> **Ballpoint delivers webhooks at least once. Your integration must handle duplicates, delays, and out-of-order delivery.**

> Ballpoint emits two webhook event families: `order.status_changed` (this section, lifecycle of every order) and the per-piece RTS push-back (see [§7b](#7b-per-piece-rts-push-back-v1) below — V1 contract documented; live emission shipping in a future release).

### Registration

Send us your webhook endpoint URL — Ballpoint will configure it on our side. There is no self-service webhook registration endpoint today. *(Contact details provided during onboarding.)*

**Requirements for your endpoint:**
- Must accept `POST` requests with `Content-Type: application/json`
- Must be HTTPS (HTTP is rejected)
- Must respond with `2xx` within 10 seconds
- Must be publicly reachable from the internet

### Payload Format

When an order's status changes, we send an `order.status_changed` event:

```json
{
  "id": "evt_order.status_changed_ord_7f3a2b_20260301_a1b2c3",
  "type": "order.status_changed",
  "version": "2026-02-01",
  "timestamp": "2026-03-01T16:30:00Z",
  "data": {
    "order_id": "ord_7f3a2b",
    "campaign_id": "camp_test",
    "previous_production_status": "accepted",
    "production_status": "printing",
    "display_status": "printing",
    "product_type": "4x6_printed",
    "source": "your_source",
    "external_account_id": "acct_partner",
    "external_user_id": "user_789",
    "list_id": "marketing_q1_2026"
  }
}
```

`list_id` echoes back verbatim the value you originally passed when creating the order (or `null` for orders not created via the partner endpoint). Use it as the join key on your side for reconciliation.

### Webhook Headers

Every webhook includes these headers:

```
X-Ballpoint-Signature: sha256=<hex>
X-Ballpoint-Timestamp: 2026-03-01T16:30:00Z
X-Ballpoint-Event-Id: evt_order.status_changed_ord_7f3a2b_20260301_a1b2c3
X-Ballpoint-Delivery: d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a
```

### Signature Verification

Verify every webhook to ensure it came from Ballpoint and wasn't tampered with.

**Python:**

```python
import hmac, hashlib

def verify_signature(body_bytes, timestamp, signature, secret):
    expected = hmac.new(
        secret.encode(),
        f"{timestamp}{body_bytes.decode()}".encode(),
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
    .update(timestamp + bodyBuffer.toString())
    .digest("hex");
  const received = signature.replace("sha256=", "");
  return crypto.timingSafeEqual(
    Buffer.from(expected, "hex"),
    Buffer.from(received, "hex")
  );
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

When USPS tracking status changes, you receive an `order.usps_update` event with piece-level breakdown:

```json
{
  "type": "order.usps_update",
  "data": {
    "order_id": "ord_7f3a2b",
    "usps_status": "out_for_delivery",
    "previous_usps_status": "shipped",
    "piece_count": 500,
    "pieces_delivered": 50,
    "pieces_at_destination": 200,
    "pieces_scanned": 380
  }
}
```

### Campaign-Level Mail Tracking Events

In addition to order-level updates, you may receive campaign-level tracking events:

| Event Type | When |
|------------|------|
| `order.status_changed` | Production status changes (scheduled → accepted → prep → printing → ... → shipping → complete; also `cancelled` and `failed`) |
| `order.usps_update` | USPS scan data changes the order's delivery status |
| `campaign.mail_tracking.in_transit` | First USPS scans detected for the campaign |
| `campaign.mail_tracking.out_for_delivery` | ≥51% of campaign pieces at destination facility |
| `campaign.mail_tracking.delivered` | ≥80% of campaign pieces delivered |
| `campaign.mail_tracking.rts_update` | Return-to-sender pieces found (includes addresses for suppression) |
| `campaign.mail_tracking.stalled` | No scans in 72+ hours with pieces still in transit |

#### Example Payloads

**`campaign.mail_tracking.in_transit`**

```json
{
  "type": "campaign.mail_tracking.in_transit",
  "data": {
    "campaign_id": "camp_spring_2026",
    "order_ids": ["ord_7f3a2b", "ord_8c4d5e"],
    "pieces_total": 1000,
    "pieces_scanned": 120,
    "first_scan_at": "2026-03-03T14:22:00Z"
  }
}
```

**`campaign.mail_tracking.delivered`**

```json
{
  "type": "campaign.mail_tracking.delivered",
  "data": {
    "campaign_id": "camp_spring_2026",
    "order_ids": ["ord_7f3a2b", "ord_8c4d5e"],
    "pieces_total": 1000,
    "pieces_delivered": 812,
    "delivery_rate": 0.812,
    "delivered_at": "2026-03-06T09:15:00Z"
  }
}
```

**`campaign.mail_tracking.rts_update`**

```json
{
  "type": "campaign.mail_tracking.rts_update",
  "data": {
    "campaign_id": "camp_spring_2026",
    "rts_count": 14,
    "rts_addresses": [
      { "line1": "123 Main St", "city": "Austin", "state": "TX", "zip": "78701" },
      { "line1": "456 Oak Ave", "city": "Dallas", "state": "TX", "zip": "75201" }
    ],
    "suppression_recommended": true
  }
}
```

**`campaign.mail_tracking.stalled`**

```json
{
  "type": "campaign.mail_tracking.stalled",
  "data": {
    "campaign_id": "camp_spring_2026",
    "order_ids": ["ord_8c4d5e"],
    "pieces_total": 500,
    "pieces_scanned": 310,
    "pieces_stalled": 190,
    "last_scan_at": "2026-03-04T08:00:00Z",
    "hours_since_last_scan": 78
  }
}
```

### Retry Policy

Events are guaranteed to be delivered. If your endpoint is down, we retry with exponential backoff:

**Per-delivery attempt (immediate retries):**

| Attempt | Backoff |
|---------|---------|
| 1 | Immediate |
| 2 | 1 second |
| 3 | 2 seconds |
| 4 | 4 seconds |
| 5 | 8 seconds |

4xx responses (400, 401, 403, 404) are **not retried** — they indicate a problem with your endpoint.

**If all 5 attempts fail:** The event goes back to the queue with increasing delays (10s → 30s → 90s → up to 1 hour). After 15 total delivery attempts, the event moves to dead letter and Ballpoint support is notified.

**Auto-disable:** If your endpoint accumulates 10 consecutive failures across different events, we disable it and notify you. Contact us to re-enable.

**Your responsibilities:**
- Return `2xx` within 10 seconds
- Deduplicate on `X-Ballpoint-Event-Id` (you may receive the same event more than once)
- Reject payloads with `X-Ballpoint-Timestamp` older than 5 minutes or more than 2 minutes in the future

---

### Per-piece RTS Push-Back (V1)

When the USPS scan pipeline detects a returned-to-sender piece, Ballpoint emits a per-piece RTS event server-to-server so the partner can reconcile each undeliverable mailing piece against its CRM contact directly.

> **Status:** V1 contract finalized. Delivery will be enabled once the partner endpoint is configured and E2E testing is complete.

**Delivery**

- HTTP `POST` to the partner-registered webhook endpoint (same endpoint configured at onboarding for `order.status_changed`).
- HMAC-signed using the same scheme as `order.status_changed` (see [Signature Verification](#signature-verification)).
- Server-to-server only.

**Batch limits**

- Max **10,000 entries** per call.

**Per entry**

| Field | Type | Required | Description |
|---|---|---|---|
| `contact_id` | string | yes | The same `contact_id` the partner supplied in the original `POST /v1/billing/orders/{id}/recipients` upload. Echoed verbatim. |
| `reason` | string | yes | Return-to-sender reason (e.g. `vacant`, `moved_no_forwarding`, `insufficient_address`). |
| `last_scan_date` | string | yes | ISO 8601 date of the last scan associated with the returned piece. |

**Notes**

- `name`, `address`, `city`, `state`, `zip` are **not** included in the V1 payload. Reconciliation is by `contact_id` only.
- Every recipient that should be eligible for RTS push-back must include `contact_id` in the original `/recipients` upload. Ballpoint persists the value verbatim and echoes it back unchanged on the RTS event.
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
│                      │ PATCH /status                                                                    │ 1-2 days                             │
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

Wholesale charge runs on `/confirm-payment success` (same `charge_order` flow used for direct accounts at creation time). Cancelling from `pending_payment` or `payment_failed` is free — no debit ever happened. Cancelling from `accepted` (or `scheduled` after a successful confirmation) still triggers the auto-refund. See [§6k. Confirm Payment](#6k-confirm-payment-partner-payment-gate) for the full endpoint contract.

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
| Preview cost | `POST` | `/v1/billing/orders/preview` | `X-Partner-Key` |
| Create order | `POST` | `/v1/billing/orders` | `X-Partner-Key`, `Idempotency-Key`, `X-External-User-ID` |
| Get order | `GET` | `/v1/billing/orders/{id}` | `X-Partner-Key` |
| List orders | `GET` | `/v1/billing/orders?external_user_id=...&status=...&limit=20&offset=0` | `X-Partner-Key` |
| Cancel order | `PATCH` | `/v1/billing/orders/{id}/status` | `X-Partner-Key` |
| Confirm payment | `POST` | `/v1/billing/orders/{id}/confirm-payment` | `X-Partner-Key` (server-to-server only) |
| Partner dashboard stats | `GET` | `/v1/billing/partner/stats?days=30&list_id=...&external_user_id=...` | `X-Partner-Key` |
| Partner dashboard orders | `GET` | `/v1/billing/partner/orders?days=30&list_id=...&status=...` | `X-Partner-Key` |
| Order tracking | `GET` | `/v1/orders/{id}/mail-tracking` | `X-Partner-Key` |
| Campaign tracking | `GET` | `/v1/campaigns/{id}/mail-tracking` | `X-Partner-Key` |
| Pricing catalog | `GET` | `/v1/billing/pricing?product_type=...` | `X-Partner-Key` |
| Mint SSE token | `POST` | `/v1/billing/orders/{id}/sse-token` | `X-Partner-Key` |
| SSE stream | `GET` | `/v1/billing/orders/{id}/events` | *(cookie auth via sse-token)* |
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
    console.log(`Received: ${event.type} (${eventId})`);

    // 4. Deduplicate on eventId (check your database)
    // if (await alreadyProcessed(eventId)) {
    //   return res.status(200).json({ received: true, duplicate: true });
    // }

    // 5. Process the event
    const { order_id, display_status, external_user_id } = event.data;
    console.log(`Order ${order_id} → ${display_status} (user: ${external_user_id})`);

    // TODO: Update your database, notify the user, etc.

    // 6. Return 200 quickly — do heavy processing async
    res.status(200).json({ received: true });
  }
);

function verifySignature(bodyBuffer, timestamp, signature, secret) {
  const expected = crypto
    .createHmac("sha256", secret)
    .update(timestamp + bodyBuffer.toString())
    .digest("hex");
  const received = signature.replace("sha256=", "");
  return crypto.timingSafeEqual(
    Buffer.from(expected, "hex"),
    Buffer.from(received, "hex")
  );
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

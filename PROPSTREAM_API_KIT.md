# Ballpoint Marketing API — PropStream Integration Kit

> **v1.0 · March 2026**
>
> Everything your dev team needs to integrate direct mail ordering, tracking,
> and real-time status updates into PropStream.

---

## Quick Start (30 seconds)

Verify your credentials work — paste this into a terminal:

```bash
curl -s -X POST https://api.ballpointmarketing.com/v1/billing/orders \
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ" \
  -H "Idempotency-Key: ps-quickstart-$(date +%s)" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "camp_propstream_test",
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
7. [Status Updates via Webhooks](#7-status-updates-via-webhooks)
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
| **Test API Key** | `pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ` |
| **Live API Key** | `pk_live_propstream_REPLACE_WITH_YOUR_LIVE_KEY` |
| **Base URL** | `https://api.ballpointmarketing.com` |
| **Webhook Secret** | Provisioned during onboarding — send us your endpoint URL |

### Authentication

Every request must include your API key in the `X-Partner-Key` header:

```
X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ
```

- **Test key** (`pk_test_...`) — no real mail printed or sent. Use freely during development.
- **Live key** (`pk_live_...`) — real orders, real mail sent. Invoiced after completion.

Keys are provisioned by Ballpoint. Contact us if you need to rotate them.

---

## 2. How It Works (End-to-End Flow)

### Flow A — Embedded iframe (PropStream's Model)

Your users select recipients in PropStream, then the Ballpoint iframe handles product selection, copy editing, and order submission.

```
┌───────────────────────────────────────────────────────────────────────┐
│  PROPSTREAM IFRAME FLOW                                               │
│                                                                       │
│  1. User selects mailing list in PropStream                           │
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
│  5. Ballpoint team fulfills (printing → stamping → complete)          │
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

### What PropStream Calls via API

- **Preview cost** — show your users what they'll pay before ordering
- **Create order** — submit an order referencing an existing campaign
- **List orders** — query orders by user, status, with pagination
- **Check tracking** — get USPS delivery status for an order or campaign
- **Cancel order** — cancel before production starts
- **Receive webhooks / SSE** — get status updates pushed to your server or browser in real-time

---

## 3. How Billing Works

Your account (`acct_propstream`) uses `billing_mode: none`. This means:

- **All orders succeed immediately** — no balance checks, no upfront charges
- **Ballpoint invoices separately** — after orders are marked `complete`, Ballpoint sends an invoice for review
- **PropStream audits and pays** — payment happens outside the API, on your schedule

This billing mode applies to both your test key and live key. There are no changes needed when you go to production — the only difference between test and live is that live orders trigger real fulfillment and real mail.

### Pricing

Cost = `unit_price_tcents × piece_count`. No minimums, no surcharges, no per-request fees. See [Product Catalog & Pricing](#5-product-catalog--pricing) for the full price list.

### Cancellations

Cancelling an order (from `accepted` status only) removes it from the fulfillment queue. Since there is no upfront charge, there is no refund to process — the cancelled order simply won't appear on your next invoice.

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

### Pattern B — Embedded iframe (PropStream's Model)

Your platform embeds a Ballpoint iframe. Your users select recipients in PropStream, then the iframe handles product selection, copy editing, and order submission. SSE provides real-time status updates in the browser.

```
┌─────────────────┐
│  PropStream UI   │  1. User selects mailing list
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

SSE requires cookie auth with `withCredentials: true`. The iframe must be served over HTTPS. CORS is already configured to allow `app.propstream.com`.

Webhooks remain the backend source of truth — SSE is for browser-side real-time display only.

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
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ"
```

Filter by product:

```bash
curl -s "https://api.ballpointmarketing.com/v1/billing/pricing?product_type=4x6_printed" \
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ"
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
X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ
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
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ" \
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

> **Note:** Your account uses `billing_mode: none`, so `balance_cents` is `null` and balance checks always pass. The preview still validates product type, postage, and piece count.

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
| `X-External-User-ID` | Recommended | Attributes the order to a specific PropStream user (see [6i](#6i-user-attribution)) |

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
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ" \
  -H "X-External-User-ID: user_789" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "camp_propstream_test",
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
  "campaign_id": "camp_propstream_test",
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
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ" \
  -H "Idempotency-Key: 660f9500-f30c-52e5-b827-557766551111" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "camp_propstream_test",
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
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ"
```

**Response (`200`):**

```json
{
  "id": "ord_7f3a2b",
  "campaign_id": "camp_propstream_test",
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
| `external_user_id` | string | — | Filter to a specific PropStream user |
| `status` | string | — | Filter by order status (e.g., `accepted`, `printing`, `complete`, `delivered`) |
| `limit` | integer | 20 | Results per page (1–100) |
| `offset` | integer | 0 | Pagination offset |

**Example:**

```bash
curl -s "https://api.ballpointmarketing.com/v1/billing/orders?external_user_id=user_789&limit=10" \
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ"
```

**Response (`200`):**

```json
{
  "orders": [
    {
      "id": "ord_7f3a2b",
      "campaign_id": "camp_propstream_test",
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
- Results are scoped to your PropStream account automatically — you only see your own orders.
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
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ"
```

**Response (`200`):**

```json
{
  "campaign_id": "camp_propstream_test",
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
curl -s https://api.ballpointmarketing.com/v1/campaigns/camp_propstream_test/mail-tracking \
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ"
```

Response has the same shape as [Order Tracking](#6e-order-tracking) but aggregated across all orders in the campaign.

---

### 6g. Cancel Order

Cancel is allowed **only while the order is in `accepted` status** (before production begins).

```
PATCH /v1/billing/orders/{order_id}/status
```

**Example:**

```bash
curl -X PATCH https://api.ballpointmarketing.com/v1/billing/orders/ord_7f3a2b/status \
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ" \
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

**Note:** Since your account uses `billing_mode: none`, cancelling an order simply removes it from the fulfillment queue. The `refund` field will be `null` — there is no charge to reverse.

Once an order moves to `printing` or beyond, it cannot be cancelled — physical production has started. Contact Ballpoint support for production-stage issues.

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

Pass `X-External-User-ID` on any request to attribute it to a specific PropStream end-user:

```
X-External-User-ID: user_789
```

This ID:
- Is stored on orders created during that request
- Is included in webhook payloads sent back to you
- Can be used to filter `GET /v1/billing/orders?external_user_id=user_789`
- Routes tracking data back to the correct user's dashboard

This is optional but recommended — it lets you show each PropStream user only their own orders and track per-user activity.

---

## 7. Status Updates via Webhooks

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
    "campaign_id": "camp_propstream_test",
    "previous_production_status": "accepted",
    "production_status": "printing",
    "display_status": "printing",
    "product_type": "4x6_printed",
    "source": "propstream",
    "external_account_id": "acct_propstream",
    "external_user_id": "user_789"
  }
}
```

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

### Delivery Semantics

Webhook delivery is **at-least-once**. Your handler must be idempotent:

- Deduplicate on `X-Ballpoint-Event-Id` — you may receive the same event more than once
- If you enqueue downstream jobs, deduplicate there too
- Failed deliveries (non-2xx or timeout) are retried with exponential backoff

### Production Status Lifecycle

Production status is set by Ballpoint operations staff. It moves forward only.

| Status | Meaning | Your UX |
|--------|---------|---------|
| `accepted` | Order created. Only status where cancellation is allowed. | "Order placed" |
| `printing` | In the physical print queue. Cancellation no longer possible. | "In production" |
| `writing` | Handwritten content being applied by pen plotters. *Handwritten products only.* | "In production" |
| `inserting` | Printed materials being folded into envelopes. *Letter products only.* | "In production" |
| `stamping` | Postage applied, pieces trayed for USPS induction. | "In production" |
| `complete` | All pieces dropped at USPS. First scans arrive 1–2 business days later. | "Shipped" |
| `cancelled` | Cancelled before production. Removed from fulfillment queue. | "Cancelled" |

**Production sequences by product:**

```
Printed postcards:     accepted → printing → stamping → complete
Handwritten postcards: accepted → writing → stamping → complete
Color letters:         accepted → printing → inserting → stamping → complete
Hybrid letters:        accepted → printing → writing → inserting → stamping → complete
Handwritten letters:   accepted → writing → inserting → stamping → complete
```

### USPS Tracking Lifecycle

USPS status is set automatically by the scan ingest pipeline. Also forward-only.

| Status | Meaning | Threshold | Your UX |
|--------|---------|-----------|---------|
| `shipped` | At least one piece has a USPS scan. Mail entered the postal network. | ≥1 piece scanned | "Shipped" |
| `out_for_delivery` | Mail is at the recipients' local postal facilities. | ≥51% of pieces at destination | "Out for delivery" |
| `delivered` | Mail has been sorted into carrier walk order — final automated scan. | ≥80% of pieces have stop-the-clock scans | "Delivered" |

> **Note:** USPS Informed Visibility provides facility-level processing scans,
> not carrier-level "delivered to mailbox" tracking. `delivered` means the mail
> has been sorted for carrier delivery — the industry-standard delivery indicator
> for marketing mail.

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
| `order.status_changed` | Production status changes (accepted → printing → ... → complete) |
| `order.usps_update` | USPS scan data changes the order's delivery status |
| `campaign.mail_tracking.in_transit` | First USPS scans detected for the campaign |
| `campaign.mail_tracking.delivered` | ≥80% of campaign pieces delivered |
| `campaign.mail_tracking.rts_update` | Return-to-sender pieces found (includes addresses for suppression) |
| `campaign.mail_tracking.stalled` | No scans in 72+ hours with pieces still in transit |

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

## 8. Real-Time UI via SSE (Optional)

If you're embedding order status in an iframe or dashboard, SSE gives instant updates without polling. **Webhooks are the primary integration path** — SSE is for display only.

### Step 1: Mint a Token (Server-Side)

```bash
curl -X POST https://api.ballpointmarketing.com/v1/billing/orders/ord_7f3a2b/sse-token \
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ"
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

CORS is already configured to allow `app.propstream.com` with credentials. If you need additional origins, let us know.

---

## 9. Order Lifecycle Diagram

An order has two parallel status tracks. They are independent — USPS never overwrites production status, and vice versa.

```
                    YOUR API CALL                 BALLPOINT PRODUCTION                     USPS SCANS
                    ─────────────                 ────────────────────                     ──────────

                 POST /v1/billing/orders
                          │
                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│  │ accepted │───►│ printing │───►│ writing  │───►│inserting │───►│ stamping │───►│ complete │    │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    │
│       │                                                                               │           │
│       │ PATCH /status                                                                 │ 1-2 days  │
│       ▼                                                                               ▼           │
│  ┌──────────┐                                        ┌─────────┐   ┌───────────┐   ┌──────────┐ │
│  │cancelled │                                        │ shipped │──►│out_for_   │──►│delivered │ │
│  └──────────┘                                        │         │   │delivery   │   │          │ │
│                                                      └─────────┘   └───────────┘   └──────────┘ │
│                                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘

    PRODUCTION TRACK (top)                              USPS TRACK (bottom)
    Set by Ballpoint staff                              Set automatically by scan pipeline
    Forward-only                                        Forward-only, starts 1-2 days after "complete"
```

**Not all products go through every step.** See [production sequences](#production-status-lifecycle) for which steps apply to each product type.

**Display status** = USPS status when available, otherwise production status. This is the single field you should show to end users — it's returned as `display_status` in API responses and webhooks.

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
| `402` | Insufficient balance or spending limit hit | **No** | **Does not apply to your account** (`billing_mode: none`) |
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

Your test key (`pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ`):

- All orders succeed immediately (`billing_mode: none`)
- No real mail is printed or sent
- Validation, status codes, and error responses are identical to production
- Use `camp_propstream_test` as the campaign ID for testing

**What happens to test orders?** Test orders are created with status `accepted` and stay there — production status does not auto-advance because there is no physical fulfillment. To test your webhook handler, ask us to trigger test events against your endpoint. We can simulate the full lifecycle (`accepted` → `printing` → ... → `complete` → `shipped` → `delivered`) so you can verify your handler end-to-end without waiting for real mail.

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

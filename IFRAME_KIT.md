# Ballpoint Marketing Iframe — Partner Integration Kit

This guide explains how to embed the Ballpoint direct mail campaign builder into your application via the embedded iframe pattern. For server-to-server API integration (orders, webhooks, billing, payment gate), see the companion [API_KIT.md](API_KIT.md).

> See [CHANGELOG.md](CHANGELOG.md) for revision history.

## Table of Contents

1. [Before You Start](#1-before-you-start)
2. [Embedding the Iframe](#2-embedding-the-iframe)
3. [Environments](#3-environments)
4. [Bootstrap Flow](#4-bootstrap-flow)
5. [Messages You Send (Parent → Iframe)](#5-messages-you-send-parent--iframe)
6. [Messages You Receive (Iframe → Parent)](#6-messages-you-receive-iframe--parent)
7. [Recipient Upload Flow](#7-recipient-upload-flow)
8. [URL Parameters (Alternative Bootstrap)](#8-url-parameters-alternative-bootstrap)
9. [Security Notes](#9-security-notes)

---

## 1. Before You Start

### What Ballpoint provides to you

- [ ] **Iframe URL** — the embed URL for staging and production (see [Environments](#3-environments))
- [ ] **API key** (`pk_...`) — partner key for authenticating with the Ballpoint API
- [ ] **Origin allowlisting** — your domain(s) added to the iframe's parent origin allowlist and CSP `frame-ancestors` so the embed works in your app

### What you provide to Ballpoint

- [ ] **Your embed domain(s)** — the exact origin(s) where the iframe will be loaded (e.g. `https://app.yourdomain.com`). We need this to allowlist your origin. Include staging domains if applicable.

### What you implement on your side

- [ ] **Iframe embed** — add the `<iframe>` tag to your page (see [Section 2](#2-embedding-the-iframe))
- [ ] **postMessage handler** — listen for events from the iframe and send configuration on `ready` (see [Section 4](#4-bootstrap-flow))
- [ ] **Recipient upload** — after a campaign is submitted, POST the mailing addresses to the Ballpoint API (see [Section 7](#7-recipient-upload-flow))

> **Minimum viable integration:** embed the iframe, send `set_api_config` + `set_list` on ready, and handle recipient upload on `campaign_submitted`. Everything else is optional.

---

## 2. Embedding the Iframe

Add this to your page:

```html
<iframe
  id="ballpoint-mailer"
  src="https://mailer.ballpointmarketing.com/index.html"
  sandbox="allow-scripts allow-same-origin allow-forms allow-downloads"
  style="width: 100%; height: 100vh; border: none;">
</iframe>
```

### Sandbox Tokens

| Token | Required | Why |
|-------|----------|-----|
| `allow-scripts` | Yes | Iframe runs JavaScript |
| `allow-same-origin` | Yes | Iframe needs access to its own storage |
| `allow-forms` | Yes | Campaign builder uses form elements |
| `allow-downloads` | Yes | Users can export tracking data as CSV |

---

## 3. Environments

| Environment | Iframe URL | API URL |
|-------------|-----------|---------|
| **Production** | `https://mailer.ballpointmarketing.com/index.html` | `https://api.ballpointmarketing.com` |
| **Staging** | `https://staging-mailer.ballpointmarketing.com/index.html` | `https://staging-api.ballpointmarketing.com` |

Use the staging environment for development and testing.

**Staging API key:** `pk_test_PARTNER_REPLACE_ME`

Your partner-specific test key is provisioned by Ballpoint during onboarding and is pre-configured with test campaign data so you can see the full experience (campaign creation, tracking dashboard, etc.) right away.

> **QA / Dev domains:** If your organization uses separate domains for QA or dev environments (e.g. `app.qa.yourdomain.com`, `app.dev.yourdomain.com`), provide these to Ballpoint so we can add them to the origin allowlist and CSP `frame-ancestors`. The embed will not load in unlisted origins.

---

## 4. Bootstrap Flow

After the iframe loads, it sends a `ready` message. Your page then sends configuration messages via `postMessage`. Here is the recommended sequence:

```
1. Iframe loads
2. Iframe → Parent:  "ready"           (iframe is alive)
3. Parent → Iframe:  "set_api_config"  (API URL + auth token)
4. Parent → Iframe:  "set_list"        (recipient count, list info)
   — OR —            "set_lists"       (multiple lists for user to choose from)
5. Parent → Iframe:  "set_sender"      (optional — pre-fill sender info)
```

If the user performs an action before `set_api_config` arrives, the iframe queues it automatically and replays it once config is received. No action is lost.

### Listening for the Ready Event

```javascript
const iframe = document.getElementById('ballpoint-mailer');

window.addEventListener('message', function(event) {
  // Only accept messages from the Ballpoint iframe origin
  if (event.origin !== 'https://mailer.ballpointmarketing.com') return;

  const msg = event.data;
  if (!msg || msg.source !== 'ballpoint-mailer') return;

  if (msg.type === 'ready') {
    // Iframe is ready — send configuration
    sendConfig();
  }

  // Handle other events (see Section 5)
});
```

### Sending Configuration

```javascript
function sendConfig() {
  const iframe = document.getElementById('ballpoint-mailer');
  const origin = 'https://mailer.ballpointmarketing.com';

  // Required: API configuration
  iframe.contentWindow.postMessage({
    source: 'propstream',
    version: 1,
    type: 'set_api_config',
    apiBaseUrl: 'https://api.ballpointmarketing.com',
    apiToken: 'YOUR_API_TOKEN'
  }, origin);

  // Required: List/recipient information
  iframe.contentWindow.postMessage({
    source: 'propstream',
    version: 1,
    type: 'set_list',
    count: 847,
    name: 'Pre-Foreclosure Leads',
    listId: 'your_list_id',
    externalAccountId: 'your_account_id',
    externalUserId: 'your_user_id'
  }, origin);

  // Optional: Pre-fill sender information
  iframe.contentWindow.postMessage({
    source: 'propstream',
    version: 1,
    type: 'set_sender',
    fullName: 'John Smith',
    address: '123 Main St',
    city: 'Tampa',
    state: 'FL',
    zip: '33601',
    phone: '555-123-4567',
    website: 'www.example.com'
  }, origin);
}
```

---

## 5. Messages You Send (Parent → Iframe)

All messages must include these base fields:

```json
{
  "source": "propstream",
  "version": 1,
  "type": "message_type"
}
```

> The `source` field must be `"propstream"`. If you're a different partner, reach out and we'll set up your source identifier.

### `set_api_config` — API credentials (required)

| Field | Type | Description |
|-------|------|-------------|
| `apiBaseUrl` | string | Ballpoint API base URL |
| `apiToken` | string | Partner API key (`pk_...`) |
| `tenantKey` | string | Optional. Tenant scope key for storage isolation |

This is the only message that can be sent more than once (to refresh tokens). All other message types are accepted once per session.

### `set_list` — Recipient list info (required)

| Field | Type | Description |
|-------|------|-------------|
| `count` | number or string | Number of recipients in the list |
| `name` | string | Human-readable list name (shown in the UI) |
| `listId` | string | Your internal list identifier |
| `externalAccountId` | string | Your account/tenant identifier |
| `externalUserId` | string | Your user identifier |
| `piece_counts` | object | Optional. Pre-computed piece counts for the 6 combinations of `Deliver To` × `Remove duplicates`. When present, the iframe shows 2 user-facing controls on the piece-selection page (Deliver To select + Remove duplicates checkbox) and uses these values as the authoritative count + price input. When absent, the controls are hidden and the iframe falls back to `count` (legacy behavior — existing partners are unaffected). See [Recipient selection contract](#recipient-selection-contract-piece-count--dedup) for the full walkthrough. |
| `tenantKey` | string | Optional. Tenant scope key |

#### `piece_counts` shape

```json
"piece_counts": {
  "property": { "dedup_off": 480, "dedup_on": 440 },
  "mailing":  { "dedup_off": 498, "dedup_on": 472 },
  "both":     { "dedup_off": 920, "dedup_on": 850 }
}
```

| Path | Type | Description |
|------|------|-------------|
| `piece_counts.property.dedup_off` | number or null | Count of leads with a property address, no dedup applied. |
| `piece_counts.property.dedup_on` | number or null | Count of distinct normalized property addresses. |
| `piece_counts.mailing.dedup_off` | number or null | Count of leads with a mailing address, no dedup applied. |
| `piece_counts.mailing.dedup_on` | number or null | Count of distinct normalized mailing addresses. |
| `piece_counts.both.dedup_off` | number or null | Per-lead count of unique send addresses across property + mailing (if a lead's property and mailing addresses are equal, that lead counts as 1, not 2). Duplicate addresses across different leads are not collapsed. |
| `piece_counts.both.dedup_on` | number or null | Count of distinct normalized send addresses across the union of property + mailing. |

Semantics:

- **`0` is a valid value** for any combination. It means "no recipients available for this selection" (e.g. no leads have a mailing address). The iframe shows the option but with a 0-piece price.
- **Missing key vs `0`**: an omitted combination (e.g. no `property.dedup_off` key, or the entire `property` block missing) means "option unavailable for selection in iframe UI" — the iframe disables the corresponding option in the Deliver To select (user can see it but cannot pick it). This is distinct from `0`, which is selectable but disables the submit button with a "no recipients available" warning.
- **4 KB cap** on the serialized `piece_counts` JSON. Payloads exceeding the cap are silently rejected at the postMessage boundary — the iframe logs a console warning and falls back to legacy behavior (controls hidden, `count` used as the recipient total).
- Leads missing the relevant address contribute 0 for that option (e.g. a lead with no mailing address contributes 0 to `mailing.*`).

#### Full `set_list` example with `piece_counts`

```json
{
  "source": "propstream",
  "version": 1,
  "type": "set_list",
  "count": 500,
  "name": "Pre-Foreclosure Leads",
  "listId": "your_list_id",
  "externalAccountId": "your_account_id",
  "externalUserId": "your_user_id",
  "piece_counts": {
    "property": { "dedup_off": 480, "dedup_on": 440 },
    "mailing":  { "dedup_off": 498, "dedup_on": 472 },
    "both":     { "dedup_off": 920, "dedup_on": 850 }
  }
}
```

### `set_lists` — Multiple lists for user selection (alternative to `set_list`)

Use this instead of `set_list` when you want the user to choose from multiple lists before creating a campaign. The iframe shows a "Select Your List" page where the user picks one, then proceeds to the campaign builder.

```json
{
  "source": "propstream",
  "version": 1,
  "type": "set_lists",
  "lists": [
    { "name": "Pre-Foreclosure Leads", "count": 847, "listId": "list_001" },
    { "name": "Absentee Owners — Tampa", "count": 1203, "listId": "list_002" },
    { "name": "Expired Listings Q1", "count": 312, "listId": "list_003" }
  ],
  "externalAccountId": "your_account_id",
  "externalUserId": "your_user_id"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `lists` | array | Array of list objects |
| `lists[].name` | string | Human-readable list name |
| `lists[].count` | number | Number of recipients in this list |
| `lists[].listId` | string | Your internal list identifier |
| `lists[].piece_counts` | object | Optional. Per-list pre-computed piece counts. Same shape and semantics as `set_list.piece_counts` (see above). When the user picks a list from the selector, the iframe applies that list's `piece_counts` to the active selection state. Lists without `piece_counts` fall back to legacy behavior (controls hidden, count from `lists[].count`). |
| `externalAccountId` | string | Your account/tenant identifier |
| `externalUserId` | string | Your user identifier |
| `tenantKey` | string | Optional. Tenant scope key |

When the user selects a list, the iframe sends a `list_selected` event back to the parent (see [Section 6](#6-messages-you-receive-iframe--parent)).

> **Note:** Send either `set_list` (single list, user goes straight to campaign builder) or `set_lists` (multiple lists, user picks first). Do not send both.

### Recipient selection contract (piece count + dedup)

When `set_list.piece_counts` (or `set_lists[].piece_counts`) is present, the iframe surfaces two user-facing controls on the piece-selection page and emits the user's final choice back to the parent on `campaign_submitted`. End-to-end:

1. **Partner pre-computes** the 6 piece counts on its side (raw address availability + dedup math against its own normalized address index).
2. **Partner sends** `set_list.piece_counts` on bootstrap (alongside `count`, `name`, etc.).
3. **Iframe shows** two controls:
   - **Deliver To** — radio/select between `property`, `mailing`, `both` (only options present in `piece_counts` are offered).
   - **Remove duplicate addresses** — checkbox. Toggles `dedup_off` ↔ `dedup_on`.
4. **User selects** → iframe looks up the resolved count via `piece_counts[deliver_to][dedup_on ? "dedup_on" : "dedup_off"]` → displays the count and recomputes price.
5. **User submits** → iframe echoes the final selection on `campaign_submitted.recipient_selection` (see [Section 6](#6-messages-you-receive-iframe--parent)).
6. **Partner reconciles** `recipient_selection.piece_count` against each `orders[].pieces` for billing and recipient-upload sizing.

#### Worked example

Suppose a list of 500 leads has the following address availability and dedup math on the partner side:

- 20 leads have no property address → 480 leads have a property address.
- Among those 480 property addresses, 40 are duplicates → 440 distinct property addresses.
- 2 leads have no mailing address → 498 leads have a mailing address.
- Among those 498 mailing addresses, 26 are duplicates → 472 distinct mailing addresses.
- For `both`, per-lead unique address count summed across all 500 leads = 920 (leads where property == mailing count as 1).
- Distinct normalized send addresses across the union of property + mailing = 850.

The partner sends:

```json
"piece_counts": {
  "property": { "dedup_off": 480, "dedup_on": 440 },
  "mailing":  { "dedup_off": 498, "dedup_on": 472 },
  "both":     { "dedup_off": 920, "dedup_on": 850 }
}
```

If the user picks `Deliver To = both` + `Remove duplicates = on`, the iframe displays **850 pieces** and prices accordingly. On submit, `campaign_submitted.recipient_selection` carries `{ deliver_to: "both", remove_duplicate_addresses: true, piece_count: 850 }`, and each entry in `orders[].pieces` equals 850 for a single-drop campaign (multi-drop campaigns repeat the same per-drop count across orders in V1).

#### Backward compatibility

- `piece_counts` is **optional**. Partners not yet emitting it see no change.
- When `piece_counts` is absent: the two new UI controls are hidden, the iframe uses `count` as before, and `campaign_submitted` does **not** carry the `recipient_selection` block (the field is omitted, not set to `null`).
- Partners can adopt `piece_counts` per-list — emitting it on some lists and omitting it on others is supported via `set_lists[].piece_counts`.

### `set_sender` — Pre-fill sender info (optional)

If provided, the iframe pre-fills the sender form and locks it so the user cannot edit it.

| Field | Type | Description |
|-------|------|-------------|
| `fullName` | string | Sender name or company |
| `address` | string | Street address |
| `city` | string | City |
| `state` | string | Two-letter state code (e.g. `FL`) |
| `zip` | string or number | ZIP code |
| `phone` | string | Phone number |
| `website` | string | Website URL |
| `logo` | string | Optional. URL to sender logo image |
| `tenantKey` | string | Optional. Tenant scope key |

### `set_tenant` — Storage isolation (optional)

Only needed if you embed the iframe for multiple tenants in the same browser session.

| Field | Type | Description |
|-------|------|-------------|
| `tenantKey` | string | Unique key per tenant (e.g. account ID) |

> **Note:** `tenantKey` can also be included in any of the messages above instead of sending `set_tenant` separately.

---

## 6. Messages You Receive (Iframe → Parent)

All messages from the iframe have this shape:

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "event_type"
}
```

### Lifecycle Events

#### `ready` — Iframe is loaded and ready for configuration

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "ready",
  "iframeVersion": 1,
  "maxVersion": 1,
  "buildStamp": "20260318.1"
}
```

#### `resize` — Iframe content height changed

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "resize",
  "height": 1200
}
```

Use this to dynamically resize the iframe element to avoid internal scrollbars:

```javascript
if (msg.type === 'resize') {
  document.getElementById('ballpoint-mailer').style.height = msg.height + 'px';
}
```

#### `request_config` — Iframe is requesting configuration

Sent right after `ready` as a handshake. If you already sent config on `ready`, just ignore this one.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "request_config"
}
```

#### `list_selected` — User selected a list (multi-list flow)

Sent when the user picks a list from the `set_lists` selector. Just FYI — you don't need to do anything with this.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "list_selected",
  "listId": "list_001",
  "listName": "Pre-Foreclosure Leads",
  "recipientCount": 847
}
```

#### `page_changed` — User navigated to a different view

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "page_changed",
  "page": "products"
}
```

#### `cancelled` — User cancelled the flow

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "cancelled",
  "reason": "user_back"
}
```

Possible `reason` values: `user_back`, `user_cancel`.

#### `done` — Flow is complete

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "done"
}
```

### Campaign Events

#### `campaign_created` — Campaign created (before submission)

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "campaign_created",
  "campaignId": "camp_abc123",
  "orderIds": ["ord_001"],
  "campaignType": "single",
  "listId": "your_list_id",
  "listName": "Pre-Foreclosure Leads",
  "externalAccountId": "your_account_id",
  "externalUserId": "your_user_id",
  "recipients": 847,
  "productIds": ["printed_postcard_4x6"]
}
```

`campaignType` values: `single`, `multi`, `split`.

#### `campaign_submitted` — Campaign submitted to Ballpoint

This is the most important event. It confirms the order(s) were sent to Ballpoint for processing. It fires from two paths — the campaigns flow (single / split / multi-send) and the canvas builder (single ad-hoc order). Both emit the same field shape; the canvas builder sets `campaignId: null` because it does not own a multi-order campaign concept on the iframe side.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "campaign_submitted",
  "campaignId": "camp_abc123",
  "campaignType": "single",
  "orderIds": ["ord_001"],
  "listId": "your_list_id",
  "listName": "Pre-Foreclosure Leads",
  "externalAccountId": "ps_acc_42",
  "externalUserId": "ps_user_99",
  "mailDate": "2026-05-12",
  "productIds": ["product-21"],
  "pendingSubmissionCount": 0,
  "submittedNowCount": 1,
  "pendingOrderIds": [],
  "total_tcents": 8470000,
  "total_dollars": "847.00",
  "orders": [
    {
      "orderId": "ord_001",
      "ballpointOrderId": "ord_abc123",
      "pieces": 847,
      "unit_price_tcents": 10000,
      "total_tcents": 8470000,
      "total_dollars": "847.00",
      "recipientsEndpoint": "/v1/billing/orders/ord_abc123/recipients"
    }
  ],
  "recipient_selection": {
    "deliver_to": "both",
    "remove_duplicate_addresses": true,
    "piece_count": 850
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `campaignId` | string or null | Iframe-side campaign id; `null` when the canvas builder emits a single ad-hoc order. |
| `campaignType` | string | `"single"`, `"split"`, or `"multi"`. |
| `orderIds` | string[] | All iframe-side order ids in this submission batch. |
| `listId` | string or null | Verbatim echo of the `listId` the parent app passed via `set_list`. Use this as the join key when reconciling on the parent side — Ballpoint also echoes the same value as `list_id` on `order.status_changed` webhooks. |
| `listName` | string or null | Verbatim echo of the `listName` the parent app passed via `set_list` (display label only). |
| `externalAccountId` | string or null | Account id passed via `set_api_config`. |
| `externalUserId` | string or null | End-user id passed via `set_api_config`. |
| `mailDate` | string or null | ISO date the campaign is scheduled for, when applicable. |
| `productIds` | string[] | Product ids selected for this submission. |
| `orders[].orderId` | string | Local iframe order ID. |
| `orders[].ballpointOrderId` | string or null | Server-assigned order ID (null if submission still pending retry). |
| `orders[].pieces` | number | Recipient count for this order. |
| `orders[].unit_price_tcents` | number | Marked-up unit price in tenth-cents. |
| `orders[].total_tcents` | number | Marked-up total for this order in tenth-cents. |
| `orders[].recipientsEndpoint` | string or null | API path to POST recipients (null if pending). |
| `total_tcents` | number | Marked-up total across all orders, in tenth-cents — what the end user pays. |
| `total_dollars` | string | Same total as a fixed-2 dollar string. **UX/display only.** Before charging the end-user on the partner side, refetch the authoritative amount from Ballpoint server-side via `GET /v1/billing/partner/orders`. |
| `pendingSubmissionCount` | number | Orders still waiting to submit (usually 0). |
| `submittedNowCount` | number | Orders submitted in this batch. |
| `pendingOrderIds` | string[] | Iframe order ids still waiting to submit (empty in the happy path). |
| `recipient_selection` | object or omitted | Present only when the parent provided `piece_counts` on `set_list` / `set_lists[]`. Echoes the user's final selection from the iframe's Deliver To + Remove duplicates controls. See [Recipient selection contract](#recipient-selection-contract-piece-count--dedup). |
| `recipient_selection.deliver_to` | string | One of `"property"`, `"mailing"`, `"both"` — the address type the user chose. |
| `recipient_selection.remove_duplicate_addresses` | boolean | `true` when the user enabled the Remove duplicates checkbox. |
| `recipient_selection.piece_count` | number | Per-drop piece count resolved from `piece_counts[deliver_to][dedup_on ? "dedup_on" : "dedup_off"]`. Matches each `orders[].pieces` entry — in V1, all drops in a campaign use the same recipient selection, so summing `orders[].pieces` across drops equals `piece_count × number_of_drops`. |

> **Backward compatibility.** `recipient_selection` is **omitted from the payload** (not set to `null`) when the parent did not send `piece_counts` on `set_list`. Existing partners that don't yet emit `piece_counts` continue to receive the legacy `campaign_submitted` shape unchanged.

#### `order_added` — New order added (multi-month campaigns)

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "order_added",
  "campaignId": "camp_abc123",
  "orderId": "ord_002",
  "pieceIndex": 1
}
```

#### `order_cancelled` — User cancelled an order

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "order_cancelled",
  "orderId": "ord_001",
  "campaignId": "camp_abc123"
}
```

Only emitted after Ballpoint has confirmed the cancellation server-side. If the iframe attempted to cancel via the Ballpoint API and the call rejected (e.g. order is already in production and no longer cancellable), no `order_cancelled` event fires and the iframe surfaces the failure to the user instead. This guarantees parent-side state stays consistent with Ballpoint's record.

#### `campaign_complete` — Entire campaign flow finished

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "campaign_complete",
  "campaignId": "camp_abc123",
  "campaignType": "single",
  "listId": "your_list_id",
  "listName": "Pre-Foreclosure Leads"
}
```

Sent right before the `done` event. `campaignId` matches the value emitted on the corresponding `campaign_submitted`. For the canvas builder single-order path it can be `null` when no campaign id was generated client-side.

### Error / Retry Events

These events indicate submission issues. They are informational — the iframe handles retries automatically.

#### `order_submission_deferred` — Order queued for retry

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "order_submission_deferred",
  "campaignId": "camp_abc123",
  "orderId": "ord_001",
  "reason": "api_config_missing",
  "listId": "your_list_id",
  "listName": "Pre-Foreclosure Leads",
  "recipients": 847,
  "mailDate": "2026-03-20"
}
```

#### `campaign_submission_pending` — Some orders still pending

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "campaign_submission_pending",
  "campaignId": "camp_abc123",
  "orderIds": ["ord_002"],
  "pendingSubmissionCount": 1,
  "submittedNowCount": 1
}
```

#### `order_submission_stalled` — Order failed after all retries

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "order_submission_stalled",
  "campaignId": "camp_abc123",
  "orderId": "ord_001",
  "reason": "retry_window_exceeded",
  "listId": "your_list_id",
  "listName": "Pre-Foreclosure Leads"
}
```

---

## Partner Payment Gate Flow (Send-now Walkthrough)

For accounts where Ballpoint waits on a partner-side end-user debit before producing the order (`accounts.requires_payment_confirmation = TRUE`), the iframe and payment lifecycles are decoupled. The iframe submits the order and surfaces it via `campaign_submitted`; payment is collected on the partner side; the partner backend then calls `/confirm-payment` to release the order into production.

End-to-end timeline:

1. iframe loads. Parent app sends `set_api_config` + `set_list`.
2. End-user creates the campaign locally inside the iframe (picks list, product, drop type).
3. iframe emits `campaign_created` to the parent. `orderIds` in this event are local iframe IDs only — no Ballpoint order exists yet.
4. End-user customizes the campaign and clicks Submit.
5. iframe calls `POST /v1/billing/partner/orders`. Ballpoint creates the order in `pending_payment`. No charge yet.
6. iframe emits `campaign_submitted` to the parent (carries `orders[].ballpointOrderId` and `total_dollars` for UX). This is the trigger to start the payment popup on the parent side.
7. Parent backend refetches the authoritative amount from `GET /v1/billing/partner/orders` before charging. `total_dollars` from the iframe is UX/display only and must not be used as the billing source of truth.
8. Parent shows the payment popup; end-user pays via the parent's payment provider.
9. Parent backend calls `POST /v1/billing/orders/{order_id}/confirm-payment` with `status: success` (or `failed`).
10. On success, Ballpoint debits the partner balance and moves the order to `accepted`. Production proceeds.

**Important distinction.** After `campaign_submitted`, the iframe lifecycle and payment lifecycle are separate. The iframe may emit `campaign_complete` / `done` once the iframe submission flow finishes, independent of the payment popup. That does not mean production is complete and does not replace `/confirm-payment`. Production status continues separately through `order.status_changed` webhooks (`accepted` → `prep` → ... → `complete`).

For payment, reconciliation, or backend workflows, key off `campaign_submitted.orders[].ballpointOrderId` — not `campaign_created.orderIds` (those are pre-API local IDs).

For the full `/confirm-payment` endpoint contract (request/response, fields, behavior, error codes), see [API_KIT.md §6k](https://github.com/Ballpoint-Marketing/ballpoint-api-docs/blob/main/API_KIT.md#6k-confirm-payment-partner-payment-gate).

---

## 7. Recipient Upload Flow

After receiving `campaign_submitted`, upload the mailing addresses for each order.

### Request

```
POST {apiBaseUrl}/v1/billing/orders/{ballpointOrderId}/recipients
Header: X-Partner-Key: YOUR_API_TOKEN
Content-Type: application/json
```

```json
{
  "recipients": [
    {
      "first_name": "John",
      "last_name": "Smith",
      "company": "Acme LLC",
      "address": "123 Main St",
      "address2": "Suite 200",
      "city": "Phoenix",
      "state": "AZ",
      "zip": "85001",
      "contact_id": "ps_contact_8123"
    }
  ],
  "append": false
}
```

### Recipient Fields

| Field | Required | Description |
|-------|----------|-------------|
| `first_name` | Conditional | At least one of `first_name` or `last_name` is required |
| `last_name` | Conditional | At least one of `first_name` or `last_name` is required |
| `company` | No | Company name |
| `address` | Yes | Street address |
| `address2` | No | Suite, unit, etc. |
| `city` | Yes | City |
| `state` | Yes | Two-letter state code (e.g. `AZ`) |
| `zip` | Yes | ZIP code — 5-digit (`85001`) or ZIP+4 (`85001-1234`) |
| `contact_id` | No | Opaque partner-side identifier (e.g. PropStream contact id), max 64 chars. Stored verbatim, never interpreted by Ballpoint, round-tripped on the corresponding `GET .../recipients` response, and echoed verbatim on per-piece RTS push-back events so you can map returned pieces directly to the CRM contact. **For partners using the per-piece RTS push-back, `contact_id` must be populated on every recipient** — the V1 RTS payload carries `contact_id` only (no name/address fields). |

### Batching Large Lists

Each request accepts a maximum of **10,000 recipients**.

For lists larger than 10,000, send multiple requests using the `append` flag:

1. **First request** — `"append": false` (default). This replaces any existing recipients on the order.
2. **Subsequent requests** — `"append": true`. This adds to the existing recipient list.

```
POST .../recipients   { "recipients": [first 10k], "append": false }
POST .../recipients   { "recipients": [next 10k],  "append": true  }
POST .../recipients   { "recipients": [next 10k],  "append": true  }
```

### Response

```json
{
  "accepted": 845,
  "rejected": 2,
  "total_recipients": 845,
  "piece_count": 847,
  "ready": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `accepted` | number | Recipients accepted in this request |
| `rejected` | number | Recipients rejected (invalid name, duplicate address, etc.) |
| `rejected_details` | array | Per-recipient rejection reasons (see below) |
| `total_recipients` | number | Total recipients on the order so far |
| `piece_count` | number | Current piece count (may be auto-reduced — see Dedup below) |
| `ready` | boolean | `true` = all addresses received, order can enter production |

#### Rejection reasons

| Reason | Description |
|--------|-------------|
| `At least first_name or last_name is required` | Recipient is missing both name fields |
| `duplicate_in_campaign` | Address already exists in a previous order within the same campaign |

### Campaign Dedup (automatic)

If an order belongs to a campaign that already has recipients from previous drops, we check for duplicate addresses automatically. Matches get rejected with `duplicate_in_campaign` and the order's `piece_count` is adjusted down so it can still reach `ready: true`.

Dedup matches on `(address, city, state, zip)`, trimmed and case-insensitive. We only check against other orders in the same campaign — cancelled/deleted orders are ignored.

**Example:** Say a campaign already has 500 recipients from drop 1. You upload 847 for drop 2, and 47 of those match. You'd get back:
```json
{
  "accepted": 800,
  "rejected": 47,
  "rejected_details": [
    { "index": 3, "reason": "duplicate_in_campaign" },
    { "index": 12, "reason": "duplicate_in_campaign" }
  ],
  "total_recipients": 800,
  "piece_count": 800,
  "ready": true
}
```

The `piece_count` went from 847 → 800. Order enters production with 800 unique pieces.

You don't need to handle dedup on your end — the API takes care of it. Check `rejected_details` if you want to see which addresses were skipped.

### Timing

Recipient upload is accepted while the order is in any pre-production state: `scheduled`, `pending_payment`, `accepted`, or `prep`. You can attach recipients as soon as `campaign_submitted` carries the `ballpointOrderId` — no need to wait for the order to advance to `accepted`. Once the order moves into production (`printing`/`writing`/`inserting`/`stamping`/`shipping`/`complete`), the recipient list is locked.

### Pending Orders

For orders where `ballpointOrderId` is null in the `campaign_submitted` event (still pending server-side creation):
- Wait for the retry flow to complete, or
- Poll `GET /v1/billing/orders?external_user_id=...` to find the order once created

---

## 8. URL Parameters (Alternative Bootstrap)

Instead of (or in addition to) postMessage, you can pass non-sensitive config values as URL parameters on the iframe `src`:

```
https://mailer.ballpointmarketing.com/index.html?count=847&list=Pre-Foreclosure+Leads&listId=abc123
```

| Param | Type | Max Length | Description |
|-------|------|-----------|-------------|
| `tenantKey` | string | 80 | Tenant scope key |
| `apiBaseUrl` | string | 200 | API base URL (token must still come via postMessage) |
| `count` | number | — | Recipient count |
| `list` | string | 80 | List name |
| `listId` | string | 100 | Your list identifier |
| `externalAccountId` | string | 100 | Your account identifier |
| `externalUserId` | string | 100 | Your user identifier |
| `fullName` | string | 100 | Sender name |
| `address` | string | 200 | Sender street address |
| `city` | string | 100 | Sender city |
| `state` | string | 2 | Sender state (two-letter code) |
| `zip` | string | 10 | Sender ZIP |
| `phone` | string | 20 | Sender phone |
| `website` | string | 200 | Sender website |

> **Important:** The API token (`apiToken`) must **never** be passed as a URL parameter. It must always be sent via `postMessage` using `set_api_config`. URLs are visible in browser history, Referer headers, and server logs.

---

## 9. Security Notes

- **Origin validation:** The iframe only accepts `postMessage` from allowlisted parent origins. Contact Ballpoint to add your domain to the allowlist.
- **Token delivery:** `apiToken` is only accepted via `postMessage`, never via URL params.
- **First-write-wins:** `set_list`, `set_sender`, and `set_tenant` are accepted once per session. Duplicates are ignored. `set_api_config` can be resent to refresh the token.
- **Rate limiting:** Inbound messages are rate-limited to 20 messages per 5 seconds per origin.
- **CSP:** The iframe is served with a strict Content Security Policy. Your domain must be listed in the `frame-ancestors` directive. Contact Ballpoint if you receive CSP errors.

---

## Support

For iframe access, environment keys, and technical support, reach out to your partner technical contact at Ballpoint.

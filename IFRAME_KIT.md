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
10. [Troubleshooting](#10-troubleshooting)

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

> **Minimum viable integration:** embed the iframe, send `set_api_config` + `set_list` on ready, resolve sender info (either send `set_sender` directly, or include `externalUserIsAccountOwner: true` in `set_list` and handle the `sender_setup_requested` → `set_sender` flow), and handle recipient upload on `campaign_submitted`.

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
    externalUserId: 'your_user_id',
    externalUserIsAccountOwner: true  // Optional — gates sender-info setup CTA visibility
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
| `externalUserIsAccountOwner` | boolean | Optional. Gates the iframe's sender-info "Set up now" CTA for this user. `true` → CTA visible, user may set up / edit sender info. `false` or missing → CTA hidden, blocked-state copy shown instead. Default if absent or non-`true`: `false` (deny-by-default; partners who do not send the field see the same blocked state as a non-owner). Mutable on `set_list` refresh — see [Sender-info setup gate](#sender-info-setup-gate-externaluserisaccountowner). |
| `piece_counts` | object | Optional. Pre-computed piece counts for the 6 combinations of `Deliver To` × `Remove duplicates`. When present, the iframe shows 2 user-facing controls on the piece-selection page (Deliver To select + Remove duplicates checkbox) and uses these values as the authoritative count + price input. When absent, the controls are hidden and the iframe falls back to `count` (legacy behavior — existing partners are unaffected). See [Recipient selection contract](#recipient-selection-contract-piece-count--dedup) for the full walkthrough. |
| `tenantKey` | string | Optional. Tenant scope key |

#### `piece_counts` shape

```json
"piece_counts": {
  "property": { "dedup_off": 480, "dedup_on": 440 },
  "mailing":  { "dedup_off": 498, "dedup_on": 472 },
  "both":     { "dedup_off": 978, "dedup_on": 850 }
}
```

| Path | Type | Description |
|------|------|-------------|
| `piece_counts.property.dedup_off` | number or null | Count of leads with a property address, no dedup applied. |
| `piece_counts.property.dedup_on` | number or null | Count of distinct normalized property addresses. |
| `piece_counts.mailing.dedup_off` | number or null | Count of leads with a mailing address, no dedup applied. |
| `piece_counts.mailing.dedup_on` | number or null | Count of distinct normalized mailing addresses. |
| `piece_counts.both.dedup_off` | number or null | Partner-defined count for the `Deliver To = both` + `Remove duplicates = OFF` combination. Whatever number the partner sends here is the number of pieces Ballpoint mails when this combination is selected. Ballpoint does **not** auto-collapse same-lead `property == mailing` or any other intra-list duplicate when `dedup_off` is selected — see [Same-order dedupe](#7-recipient-upload-flow) below. |
| `piece_counts.both.dedup_on` | number or null | Partner-defined count for the `Deliver To = both` + `Remove duplicates = ON` combination. Typically the count of distinct normalized send addresses across the union of property + mailing, but the partner is the source of truth — whatever count is sent here is what Ballpoint mails when this combination is selected. |

Semantics:

- **`0` is a valid value** for any combination. It means "no recipients available for this selection" (e.g. no leads have a mailing address). The iframe shows the option but with a 0-piece price.
- **Missing key vs `0`**: an omitted combination (e.g. no `property.dedup_off` key, or the entire `property` block missing) means "option unavailable for selection in iframe UI" — the iframe disables the corresponding option in the Deliver To select (user can see it but cannot pick it). This is distinct from `0`, which is selectable but disables the submit button with a "no recipients available" warning.
- **4 KB cap** on the serialized `piece_counts` JSON. Payloads exceeding the cap are silently rejected at the postMessage boundary — the iframe logs a console warning and falls back to legacy behavior (controls hidden, `count` used as the recipient total).
- Leads missing the relevant address contribute 0 for that option (e.g. a lead with no mailing address contributes 0 to `mailing.*`).

> **`both.dedup_off` is partner-defined.** Ballpoint does **not** auto-collapse same-lead `property == mailing` (or any other intra-list duplicate) when `dedup_off` is selected. Whatever count the partner sends in `both.dedup_off` is the count Ballpoint mails, and the partner is expected to upload exactly that many recipient records to the order.
>
> Example: if `send to both = true`, `remove duplicates = false`, and a lead's property and mailing addresses are equal, the partner uploads **two** recipient records for that lead and Ballpoint mails **two** postcards. Collapsing same-lead `property == mailing` only happens when the user explicitly selects `Remove duplicates` (i.e. the partner sends a deduplicated count via `both.dedup_on` and uploads the deduplicated list).
>
> See [Campaign Dedup (automatic)](#campaign-dedup-automatic) for the only server-side dedupe Ballpoint performs (cross-order A/B-split guard-rail), and [Recipient Upload Flow](#7-recipient-upload-flow) for same-order behavior.

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
  "externalUserIsAccountOwner": true,
  "piece_counts": {
    "property": { "dedup_off": 480, "dedup_on": 440 },
    "mailing":  { "dedup_off": 498, "dedup_on": 472 },
    "both":     { "dedup_off": 978, "dedup_on": 850 }
  }
}
```

#### `set_list` refresh (post-modal sync)

After PropStream's Edit Leads modal saves changes to the recipient list, the parent SHOULD send `set_list` again to refresh the iframe's view of the list. Rules:

- **Same `listId` required.** The refresh `set_list` payload MUST carry the same `listId` as the original first-receipt `set_list`. Any other `listId` is treated as a list switch attempt and REJECTED.
- **Updatable fields on refresh:** `count`, `name`, `piece_counts`, `externalUserIsAccountOwner`. These are re-validated and re-applied. The iframe's count display, pricing UI, recipient selection state, and sender-info CTA visibility refresh in place.
- **Preserving vs clearing `piece_counts` on refresh:** if the refresh payload OMITS the `piece_counts` key entirely, the iframe preserves the currently-active `piece_counts` table (the user's combo selection and pricing continue working). To explicitly replace the table, include `piece_counts` in the refresh payload with the new values. To explicitly clear it back to legacy single-count behavior, include `piece_counts: null`. Omitting the key is NOT the same as clearing.
- **Pricing/display on refresh when `piece_counts` is active:** the refreshed count is applied to internal state, but the visible recipient count and price stay aligned with the user's current Deliver To + Remove duplicates selection (via the existing piece_counts lookup). If `piece_counts` is not active on the active list, the refreshed raw count drives display + price directly (legacy behavior).
- **Immutable fields on refresh:** `externalAccountId`, `externalUserId`, `tenantKey`. The values from the first-receipt set_list are authoritative for the session. Refresh payloads attempting to change these are:
  - `externalAccountId` / `externalUserId`: ignored (existing values preserved).
  - `tenantKey` mismatch: ENTIRE refresh message rejected, no state change applied.
- **Backward compatibility:** partners that do not send `set_list` a second time are unaffected. First-receipt behavior is unchanged. Partners that previously relied on second-receipt rejection still get the same rejection for *different-listId* attempts.

Example refresh payload (after Edit Leads modal save):

```json
{
  "source": "propstream",
  "version": 1,
  "type": "set_list",
  "listId": "ps_list_123",
  "name": "Pre-Foreclosure Leads (edited)",
  "count": 472,
  "piece_counts": {
    "property": { "dedup_off": 460, "dedup_on": 425 },
    "mailing":  { "dedup_off": 470, "dedup_on": 450 },
    "both":     { "dedup_off": 870, "dedup_on": 800 }
  }
}
```

See also the [`edit_leads_requested` event](#edit_leads_requested--user-clicked-edit-leads-on-a-campaign-card) for the iframe → parent trigger that opens the modal.

#### Sender-info setup gate (`externalUserIsAccountOwner`)

Optional boolean on `set_list` (singular). Controls **only** the iframe's sender-info "Set up now" CTA on the first-time setup page.

| Value sent on `set_list` | Iframe behavior |
|--------------------------|-----------------|
| `true` | "Set up now" CTA visible. User may complete sender-info setup and edit existing sender info. `sender_setup_requested` postMessage may be emitted on click. |
| `false`, missing, or any non-`true` value | "Set up now" CTA hidden. A blocked-state message ("Please contact your account owner to set up sender info") is shown in its place. `sender_setup_requested` postMessage emit is suppressed. |

Rules:

- **Default is `false`.** Partners who do not send the field see the same blocked state as a non-owner. This is intentional (deny-by-default for backward compatibility).
- **Mutable on `set_list` refresh.** Unlike `externalUserId` and `externalAccountId` (which are locked to the first-receipt values for the session), `externalUserIsAccountOwner` may be flipped on a same-`listId` refresh. The iframe re-applies CTA visibility immediately. PropStream should re-send `set_list` with the updated value whenever the user's account-owner status changes.
- **Singular `set_list` only.** The field is **not** part of the `set_lists` (plural) schema. If sent there, it is silently dropped.
- **Strict equality.** The iframe checks for `=== true`. String `"true"`, `1`, or any other truthy value is treated as `false`.

Scope (what this field does **not** do):

- Does **not** introduce broader RBAC, role gating, or permission sync between PropStream and the iframe.
- Does **not** affect dashboard, API, or webhook behavior. Ballpoint's API does not read or enforce this field.
- Does **not** change `externalUserId` semantics — `externalUserId` remains a technical identifier echoed back on outbound events; it is not used as a permission key.
- Does **not** display a username, role label, or owner indicator anywhere in the iframe UI.
- Does **not** affect any other CTA (Edit Leads, Reschedule, Cancel, etc.) — sender-info setup only.

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

### `open_create_direct_mail` — Open the Create Direct Mail flow (optional)

Use this when your parent app needs to programmatically open the same flow the iframe opens when the user clicks `+ Create Direct Mail` / `+ New Campaign`.

```json
{
  "source": "propstream",
  "version": 1,
  "type": "open_create_direct_mail"
}
```

This message has no required payload fields. On success, the iframe reuses its internal `startNewCampaign()` path and emits the normal `page_changed` event for the page it opens (`type` when sender info is already saved, otherwise `setup`).

**Required list context:** send this only after the iframe has a concrete active list context: either an accepted first `set_list` with a non-empty `listId` and positive `count`, or a user-selected `set_lists` item with a non-empty `listId` and positive `count` after the iframe has emitted `list_selected`. The iframe intentionally does not treat its built-in demo defaults (`Pre-Foreclosure Leads`, `847`) as usable context for this command. If the command arrives before active list context exists, the iframe does not navigate and emits `open_create_direct_mail_failed`.

`set_api_config` should still be sent during bootstrap. Missing API config does not block opening this screen because the iframe already queues submit actions until API config arrives, but partners should send `set_api_config` before the user submits.

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
- For `both` + `Remove duplicates = OFF` (`both.dedup_off`), the partner's product chooses to send to every available address on every lead without collapsing same-lead property == mailing → 978 pieces (480 property + 498 mailing). The partner could equally choose to collapse same-lead duplicates here and send a smaller number — `both.dedup_off` is whatever the partner sends, and Ballpoint mails that exact count.
- For `both` + `Remove duplicates = ON` (`both.dedup_on`), the partner collapses to distinct normalized send addresses across the union of property + mailing → 850.

The partner sends:

```json
"piece_counts": {
  "property": { "dedup_off": 480, "dedup_on": 440 },
  "mailing":  { "dedup_off": 498, "dedup_on": 472 },
  "both":     { "dedup_off": 978, "dedup_on": 850 }
}
```

If the user picks `Deliver To = both` + `Remove duplicates = on`, the iframe displays **850 pieces** and prices accordingly. On submit, `campaign_submitted.recipient_selection` carries `{ deliver_to: "both", remove_duplicate_addresses: true, piece_count: 850 }`, and each entry in `orders[].pieces` equals 850. The partner then uploads exactly 850 recipient records.

If the user instead picks `Deliver To = both` + `Remove duplicates = off`, the iframe displays **978 pieces** and the partner uploads 978 recipient records — including the second record for any lead whose property and mailing addresses happen to be identical, because the user opted out of dedupe. Ballpoint mails the 978 pieces as uploaded.

For multi-send (sequence) and A/B split campaigns each drop carries its own `orders[].pieces` value derived from the same `recipient_selection` — each drop's recipient set is the partner's full selection for that drop, and Ballpoint does not dedupe across drops in a sequence (see [Campaign Dedup (automatic)](#campaign-dedup-automatic) for the cross-order scope rules).

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

#### `edit_leads_requested` — User clicked "Edit Leads" on a campaign card

**Historical note (iframe staging-only):** the original list-level header button (`{listId, listName, recipientCount, externalAccountId, externalUserId}` emitted from a single global header button) has been replaced by per-campaign-card buttons. The header button is removed; each campaign card in My Campaigns — single send, A/B split, and multi-month — now has its own Edit Leads button when at least one of its orders is still pre-production and unbilled.

**When emitted:** the user clicks the Edit Leads button on any campaign card (single send, A/B split, or multi-month). Eligibility requires:
- All orders have `paymentConfirmed` not null (defense: campaigns with any null are skipped — typically non-gated accounts)
- At least one order is "affected" (see classification below)

**Eligibility (v1.6.0).** Edit Leads is available **only** for payment-gated campaigns/orders that are still `scheduled` or `pending_payment` and unbilled (`paymentConfirmed === false`) — i.e. pre-production and not yet paid. Once an order is paid, `accepted`, in production, mailed, delivered, or terminal, it is **locked** and its Edit Leads button is hidden (the underlying `PATCH .../recipients` returns `409 RECIPIENTS_LOCKED` / `PAID_LOCKED`). **Non-gated accounts do not expose Edit Leads** because the payment gate is not active. Full per-order classification is in "Affected allowlist" below; see also `API_KIT.md §6n/§6o`. Tightened in CHANGELOG v1.6.0.

**Payload:**

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "edit_leads_requested",
  "scope": "multi_month_campaign",
  "campaignId": "api_campaign_cmp_abc",
  "ballpointCampaignId": "cmp_abc",
  "campaignType": "multi",
  "campaignDeltaEndpoint": "/v1/billing/campaigns/cmp_abc/recipients",
  "campaignDeltaMethod": "PATCH",
  "listId": "ps_list_123",
  "listName": "Pre-Foreclosure Leads",
  "recipientCount": 500,
  "externalAccountId": "ps_acc_42",
  "externalUserId": "user_789",
  "affectedOrders": [
    {
      "orderId": "ord_local_or_api",
      "ballpointOrderId": "ord_abc123",
      "mailDate": "2026-07-15",
      "productionStatus": "scheduled",
      "paymentConfirmed": false,
      "pieces": 500,
      "variant": null,
      "campaignInstanceId": null,
      "editRecipientsEndpoint": "/v1/billing/orders/ord_abc123/recipients",
      "editRecipientsMethod": "PATCH"
    }
  ],
  "lockedOrders": [
    {
      "orderId": "ord_other",
      "ballpointOrderId": "ord_xyz",
      "mailDate": "2026-06-01",
      "productionStatus": "accepted",
      "paymentConfirmed": true,
      "pieces": 500,
      "variant": null,
      "campaignInstanceId": null,
      "lockedReason": "paid_or_accepted"
    }
  ]
}
```

**Single-send example:**

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "edit_leads_requested",
  "scope": "single_send",
  "campaignId": "api_campaign_cmp_single_1",
  "ballpointCampaignId": "cmp_single_1",
  "campaignType": "single",
  "campaignDeltaEndpoint": "/v1/billing/campaigns/cmp_single_1/recipients",
  "campaignDeltaMethod": "PATCH",
  "listId": "ps_list_321",
  "listName": "Absentee Owners",
  "recipientCount": 250,
  "externalAccountId": "ps_acc_42",
  "externalUserId": "user_789",
  "affectedOrders": [
    {
      "orderId": "ord_single_1",
      "ballpointOrderId": "ord_s1",
      "mailDate": "2026-08-01",
      "productionStatus": "scheduled",
      "paymentConfirmed": false,
      "pieces": 250,
      "variant": null,
      "campaignInstanceId": null,
      "editRecipientsEndpoint": "/v1/billing/orders/ord_s1/recipients",
      "editRecipientsMethod": "PATCH"
    }
  ],
  "lockedOrders": []
}
```

**A/B split example:** both sibling variants share the same `mailDate` and appear in `affectedOrders[]`, each tagged with its `variant` (`"a"` or `"b"`). For A/B split, PropStream's Edit Leads modal MUST allocate the new recipient list into variant-specific slices before PATCHing each variant's `editRecipientsEndpoint` separately. The `pieces` field on each item reflects the variant's current slice; preserving the original `a/b` ratio is the simplest allocation, but PropStream owns the split logic.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "edit_leads_requested",
  "scope": "ab_split",
  "campaignId": "api_campaign_cmp_split_1",
  "ballpointCampaignId": "cmp_split_1",
  "campaignType": "split",
  "campaignDeltaEndpoint": "/v1/billing/campaigns/cmp_split_1/recipients",
  "campaignDeltaMethod": "PATCH",
  "listId": "ps_list_654",
  "listName": "Probate Leads",
  "recipientCount": 400,
  "externalAccountId": "ps_acc_42",
  "externalUserId": "user_789",
  "affectedOrders": [
    {
      "orderId": "ord_split_a",
      "ballpointOrderId": "ord_sa",
      "mailDate": "2026-09-01",
      "productionStatus": "scheduled",
      "paymentConfirmed": false,
      "pieces": 200,
      "variant": "a",
      "campaignInstanceId": "ci_split_2026_09_01",
      "editRecipientsEndpoint": "/v1/billing/orders/ord_sa/recipients",
      "editRecipientsMethod": "PATCH"
    },
    {
      "orderId": "ord_split_b",
      "ballpointOrderId": "ord_sb",
      "mailDate": "2026-09-01",
      "productionStatus": "scheduled",
      "paymentConfirmed": false,
      "pieces": 200,
      "variant": "b",
      "campaignInstanceId": "ci_split_2026_09_01",
      "editRecipientsEndpoint": "/v1/billing/orders/ord_sb/recipients",
      "editRecipientsMethod": "PATCH"
    }
  ],
  "lockedOrders": []
}
```

| Field | Description |
|---|---|
| `scope` | One of `multi_month_campaign` \| `single_send` \| `ab_split`. Reflects the campaign type so the parent listener can route to the right modal. `multi_month_campaign` value unchanged from prior releases for backwards compatibility. |
| `campaignId` | Iframe-local group key (e.g. `api_campaign_<id>` for API-loaded campaigns; `cmp_<local>` for in-builder). Use `ballpointCampaignId` for cross-system reference. |
| `ballpointCampaignId` | Server-side Ballpoint campaign ID (from API `campaign_id`). May be `null` for campaigns not yet persisted server-side. |
| `campaignType` | `"single"` \| `"multi"` \| `"split"`. Mirrors `campaign.type` in the iframe. |
| `campaignDeltaEndpoint` | Campaign-level PATCH endpoint for delta add/remove (`/v1/billing/campaigns/{ballpointCampaignId}/recipients`). Preferred for multi-month campaigns. `null` if campaign not yet persisted server-side. See `API_KIT.md §6o`. |
| `campaignDeltaMethod` | Always `"PATCH"`. |
| `recipientCount` | Raw list recipient count at the time of click (not the affected/locked breakdown sum). |
| `affectedOrders[]` | Orders eligible for edit. Each has `editRecipientsEndpoint` + `editRecipientsMethod: "PATCH"`. PropStream's Edit Leads modal should PATCH each one with the new recipient list after the user saves. |
| `lockedOrders[]` | Orders that cannot be edited (paid/accepted, in production, mailed, delivered, terminal). Each has `lockedReason`. Use these to explain to the user which orders won't be affected. |
| `affectedOrders[].variant` / `lockedOrders[].variant` | For A/B split campaigns: `"a"` or `"b"` identifying the sibling. For single send and multi-month: `null`. Used by PropStream to allocate per-variant recipient slices before PATCH. |
| `affectedOrders[].campaignInstanceId` / `lockedOrders[].campaignInstanceId` | The order's split-instance key, surfaced verbatim from the Ballpoint `campaign_instance_id` column. For A/B split sibling orders: both variants share the SAME non-null string, letting the parent verify cross-variant identity before allocating per-variant slices. For single send and multi-month: `null`. Same value the partner sent on POST `/orders` and that round-trips on GET `/orders`. |
| `affectedOrders[].pieces` / `lockedOrders[].pieces` | The order's CURRENT piece count. For A/B split orders this is the variant's slice (e.g. 200 each on a 400-total 50/50 split), not the campaign-level total. Use the top-level `recipientCount` for the full campaign list size. |

**`lockedReason` enum:**

| Value | Meaning |
|---|---|
| `"paid_or_accepted"` | `paymentConfirmed === true` OR status is `accepted` (even if `paymentConfirmed === false`). Orders past the edit window. |
| `"in_production"` | Status in `{prep, processing, in_production, printing, quality_check, printed}`. |
| `"mailed"` | Status `complete`. |
| `"delivered"` | Status in `{shipped, in_transit, out_for_delivery, delivered}`. |
| `"terminal"` | Status in `{cancelled, failed, payment_failed}`. |
| `"unsupported_status"` | Status outside both the affected allowlist and known production states (e.g. `submitted`, `received`). |
| `"unknown"` | `paymentConfirmed` is `null` or missing (typically non-gated account; campaign should not have been eligible — defense-in-depth). |

**Affected allowlist** (mirrors the backend gate on `PATCH /v1/billing/orders/{id}/recipients`):

- Status ∈ `{scheduled, pending_payment}` AND
- `paymentConfirmed === false`

`accepted` and `prep` are now **locked** (moved to `lockedOrders` with reasons `paid_or_accepted` and `in_production` respectively).

`submitted` and `received` are NOT in the allowlist — they appear in `lockedOrders` with `lockedReason: "unsupported_status"`.

**Emit-only-when-affected:** the iframe does NOT emit this event when `affectedOrders.length === 0`. The button is hidden in that case.

**Expected PropStream behavior**

1. Listen for `edit_leads_requested`.
2. Open the Edit Leads modal (PropStream-hosted, on top of the iframe).
3. **Option A (campaign-level, preferred for multi-month):** PATCH `campaignDeltaEndpoint` with delta `{added, removed, remove_all}`. One call distributes to all editable drops. See `API_KIT.md §6o`.
4. **Option B (per-order, required for A/B split variant allocation):** PATCH each `affectedOrders[].editRecipientsEndpoint` with the full replacement list. See `API_KIT.md §6n`.
    - **A/B split:** the variant-specific slice goes to each variant's endpoint, not the full list. Use the `variant` field on each `affectedOrders[]` item to identify A vs B. PropStream's split allocation logic determines what slice goes to each.
5. After all PATCHes succeed, emit [`recipients_updated`](#recipients_updated--partner-finished-editing-recipients) back to the iframe so it can refresh the campaign card.
6. On modal close without changes, no postMessage required.

**Testing this flow.** Use a payment-gated staging account (`requires_payment_confirmation = true`). Create a campaign but **do not confirm payment** — the order stays `pending_payment` (send-now) or `scheduled` with `paymentConfirmed = false` (future-dated), and the **Edit Leads button is available** on the campaign card. After payment is confirmed (or the order moves to `accepted` / production), the button disappears and the order shows in `lockedOrders`.

#### `recipients_updated` — Partner finished editing recipients (parent → iframe)

Emitted by the parent app (e.g. PropStream) after successfully PATCHing each `affectedOrder`. Triggers the iframe to re-fetch campaign history and re-render My Campaigns.

```json
{
  "source": "propstream-app",
  "version": 1,
  "type": "recipients_updated",
  "tenantKey": "ps_acc_42",
  "campaignId": "api_campaign_cmp_abc",
  "ballpointCampaignId": "cmp_abc",
  "updatedBallpointOrderIds": ["ord_abc123", "ord_def456"]
}
```

| Field | Description |
|---|---|
| `tenantKey` | MUST match the iframe's active tenant scope. The iframe rejects mismatches without mutating tenant state — this event cannot be used to establish or change tenant scope. |
| `campaignId` | Iframe-local group key, echoed from the original `edit_leads_requested` event. |
| `ballpointCampaignId` | Server-side campaign ID. |
| `updatedBallpointOrderIds` | Array of `ballpointOrderId` strings that were PATCHed. Maximum 1000 IDs, each up to 256 chars. The iframe treats this as advisory (full refresh happens regardless). |

**Iframe behavior on receipt:**

1. Validate `tenantKey` against the active scope (read-only check; mismatch → rejected, no state mutation).
2. Validate `updatedBallpointOrderIds` array shape + per-element string + length caps.
3. Re-fetch campaign history (full refresh).
4. Re-render My Campaigns page so the user sees the new `piece_count` and price for the edited drops.

**Defense in depth:** the iframe does NOT trust `updatedBallpointOrderIds` for access control. The list is advisory; refresh is unconditional once tenant + shape validation pass. This prevents a malicious or buggy parent from selectively invalidating per-order state.

#### `sender_setup_requested` — User requested sender info setup

Sent when the user clicks the "Set up now" CTA on the iframe's first-time setup page because no sender info has been provided. PropStream's parent app should listen for this event and open its sender-setup modal overlay, then reply with the existing [`set_sender`](#set_sender--pre-fill-sender-info-optional) postMessage once the user saves.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "sender_setup_requested",
  "reason": "sender_info_missing",
  "page": "setup",
  "externalAccountId": "ps_acc_42",
  "externalUserId": "ps_user_99"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Always `ballpoint-mailer`. |
| `version` | number | Always `1`. |
| `type` | string | Always `sender_setup_requested`. |
| `reason` | string | V1 enum: `"sender_info_missing"`. Future values are additive — partners should treat unknown values as "open the sender modal" and not hard-fail. |
| `page` | string | V1 enum: `"setup"` \| `"campaigns"`. Identifies the iframe view the CTA was triggered from. V1 wires `"setup"` (first-time setup page); `"campaigns"` is reserved for a future my-info CTA on the My Campaigns / Dashboard page and is accepted by the contract today so a later wire requires no schema change. |
| `externalAccountId` | string | Partner account identifier echoed verbatim from the most recent `set_list` / `set_tenant`. **MAY be empty string** if the user reaches "Set up now" before any `set_list` or `set_tenant` has arrived (e.g., very first session before list selection). |
| `externalUserId` | string | Partner user identifier echoed verbatim from the most recent `set_list` / `set_tenant`. **MAY be empty string** under the same condition as `externalAccountId`. |

No sender PII (`fullName`, `address`, `city`, `state`, `zip`, `phone`, `email`, `website`) is ever included in this event. The parent already owns the sender data via the existing `set_sender` flow.

**Visibility / lifecycle**

- **Gated by `set_list.externalUserIsAccountOwner === true`.** When the field is `false`, missing, or any non-`true` value, the "Set up now" CTA is hidden and `sender_setup_requested` is not emitted. See [Sender-info setup gate](#sender-info-setup-gate-externaluserisaccountowner).
- Rendered on the iframe's first-time setup page (`page-setup`) only when no `set_sender` has been received yet. Once `set_sender` has been accepted, the CTA is suppressed and the sender form is locked per the existing `set_sender` behavior.
- In standalone (non-embed) mode the iframe falls back to its built-in inline sender form. The CTA is suppressed.
- **Pre-lock behavior:** queued by the iframe until the parent origin lock completes, then delivered only to the locked parent origin. Not broadcast to all allowlisted origins. Identical treatment to `edit_leads_requested`.

**Expected PropStream behavior**

1. Listen for the `sender_setup_requested` event.
2. Open the sender-setup modal overlay (PropStream-hosted, on top of the iframe).
3. On modal save, send the existing [`set_sender`](#set_sender--pre-fill-sender-info-optional) postMessage to the iframe with the user's sender data. The iframe's existing locking flow takes over from there.
4. On modal close without changes, no postMessage required.

#### `page_changed` — User navigated to a different view

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "page_changed",
  "page": "products"
}
```

#### `open_create_direct_mail_failed` — Create Direct Mail command rejected

Sent when the parent sends `open_create_direct_mail` before the iframe has the required active list context, or if the internal create-flow handler is unavailable. No navigation occurs when this event is emitted.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "open_create_direct_mail_failed",
  "reason": "list_context_missing",
  "message": "A concrete list context is required before opening Create Direct Mail.",
  "requiredContext": "accepted set_list with non-empty listId and positive count, or selected set_lists item with non-empty listId and positive count",
  "listId": null,
  "listName": "Pre-Foreclosure Leads",
  "recipientCount": null,
  "hasAcceptedSetList": false,
  "hasSelectedSetListsItem": false
}
```

Possible `reason` values: `list_context_missing`, `handler_unavailable`.

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

> **Timing (v1.6.6).** In the review-before-pay checkout flow, `campaign_created` now fires when the user clicks **Continue to Payment** on the Order Summary, not per-piece during scheduling. Payload shape is unchanged. `orderIds` continue to be local pre-API ids — no Ballpoint order exists at this point. Key off `campaign_submitted.orders[].ballpointOrderId` for the authoritative server-assigned id.

#### `campaign_submitted` — Campaign submitted to Ballpoint

This is the most important event. It confirms the order(s) were sent to Ballpoint for processing. It fires from two paths — the campaigns flow (single / split / multi-send) and the canvas builder (single ad-hoc order). Both emit the same field shape; the canvas builder sets `campaignId: null` because it does not own a multi-order campaign concept on the iframe side.

> **Terminal in a partner embed (v1.6.6).** After this event is emitted, the iframe shows a neutral hand-off ("Opening secure checkout…") and defers final completion to the partner's billing flow — there is no internal "Campaign Submitted!" confirmation page in a partner embed. The campaign is not "submitted/complete" until billing succeeds on the partner side. Event semantics are unchanged: `campaign_submitted` remains the authoritative billing trigger, and partners should continue to key off `orders[].ballpointOrderId` as the server-assigned order id.

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
      "mailDate": "2026-05-12",
      "unit_price_tcents": 10000,
      "total_tcents": 8470000,
      "total_dollars": "847.00",
      "recipientsEndpoint": "/v1/billing/orders/ord_abc123/recipients",
      "campaignInstanceId": null
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
| `productIds` | string[] | Product ids selected for this submission. |
| `orders[].orderId` | string | Local iframe order ID. |
| `orders[].ballpointOrderId` | string or null | Server-assigned order ID (null if submission still pending retry). |
| `orders[].pieces` | number | Recipient count for this order. |
| `orders[].mailDate` | string or null | ISO date this specific drop is scheduled for. Canonical scheduled-mail-date field for each submitted order. For `single` and `split` campaigns all entries carry the same date; for `multi` campaigns each entry carries its own per-drop date — partners reading multi-send schedules MUST iterate `orders[].mailDate`. |
| `orders[].unit_price_tcents` | number | Marked-up unit price in tenth-cents. |
| `orders[].total_tcents` | number | Marked-up total for this order in tenth-cents. |
| `orders[].recipientsEndpoint` | string or null | API path to POST recipients (null if pending). |
| `orders[].campaignInstanceId` | string or null | Opaque submit/split instance key. `null` for `single` and `multi` campaigns (no cross-order dedup expected). For `split` campaigns, all sibling orders in the same `campaign_submitted` payload share the same opaque string value — Ballpoint uses this server-side as a guard-rail to enforce disjoint slices across A/B variants (see [Campaign Dedup (automatic)](#campaign-dedup-automatic)). Treat as opaque on the partner side; do not parse, mutate, or echo back. |
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

> **This event ONLY fires during the creation of Multi-Month campaigns. It does not fire for Single Send or A/B Split campaigns.**

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

> **Timing (v1.6.6).** `order_added` fires **only for multi-month campaigns** — once per drop, at the user's **Continue to Payment** click on the Order Summary (not per-piece during scheduling). For *all* campaign types `campaign_created` also fires at that same click; **Single Send and A/B Split create their orders via `campaign_created` only and never emit `order_added`.** Payload shape is unchanged. `orderId` is still a local pre-API id; key off `campaign_submitted.orders[].ballpointOrderId` for the authoritative server-assigned id.

**How to Test.** Create a Multi-Month campaign with 2+ drops, schedule the drops, then click **Continue to Payment** on the Order Summary — you'll observe one `order_added` per drop. Single Send and A/B Split campaigns emit `campaign_created` + `campaign_submitted` but **never** `order_added`.

**Ownership.** Ballpoint emits this iframe postMessage; PropStream (the embedding parent) consumes it.

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

#### `order_rescheduled` — Drop mail date changed (v1.4.0+)

Emitted after a successful **Reschedule** operation initiated from the iframe UI on a `scheduled` order whose payment has not yet been processed (`payment_confirmed=false` server-side). The same `orderId` is preserved — Ballpoint does **not** create a replacement order for V1 same-order reschedule. The Reschedule button is hidden by the iframe on paid / terminal / in-production rows; if the partner triggers the underlying API directly on a blocked state, the backend rejects with a `409` (see `API_KIT.md §6m`) and no postMessage is emitted.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "order_rescheduled",
  "orderId": "ord_7f3a2b",
  "campaignId": "camp_abc123",
  "previousMailDate": "2026-08-01",
  "newMailDate": "2026-08-15"
}
```

Notes:

- **Suppressed on no-op.** If the user re-submits the same `newMailDate` as the order's current value, the event is **not** re-emitted (the underlying API treats it as idempotent and writes no audit row).
- **Casing.** Payload keys are camelCase to match sibling events (`order_cancelled`, `order_added`, `list_selected`). The corresponding **webhook** event (`order.rescheduled` — see `API_KIT.md §7`) uses **snake_case** keys (`previous_mail_date`/`new_mail_date`) to match the existing `order.status_changed` envelope. This snake-vs-camel split is intentional — consume the channel that matches your client style.
- `campaignId` is the local iframe campaign identifier captured at campaign creation time. It can be `null` for single-order canvas-builder paths where no campaign id was generated client-side.
- The Ballpoint webhook (`order.rescheduled`) carries the canonical `previous_scheduled_production_date` / `new_scheduled_production_date` recomputed from the product SLA (in business days, Mon–Fri; see `API_KIT.md §6p`). The iframe postMessage intentionally omits these (the parent app rarely needs them; if you do, consume the webhook).

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
5. iframe calls `POST /orders` on the API base URL. For payment-gated accounts, Ballpoint creates the order in `pending_payment` (send-now) or `scheduled` with `payment_confirmed=false` (future-dated). No charge yet in either case.
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

> **Same-order dedupe is the partner's responsibility — Ballpoint never auto-collapses within an order.** If duplicate recipient records are uploaded to the same order, Ballpoint treats them as separate recipient records and mails each one (subject only to the normal validation rules: missing required fields, invalid address fields, exceeding the order's `piece_count`). Same-order dedupe — including collapsing a lead's `property == mailing` to one piece — happens only when the user explicitly selects the partner's "Remove duplicates" control (i.e. the partner sent the deduplicated count via `set_list.piece_counts.<scope>.dedup_on` and uploads a deduplicated recipient list to match). Ballpoint's automatic [Campaign Dedup](#campaign-dedup-automatic) (`duplicate_in_campaign`) is **cross-order, same-campaign only** (A/B-split guard-rail) and must **not** be relied on to override the user's same-order selection.

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
      "contact_id": "ps_contact_8123",
      "address_type": "PROPERTY"
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
| `contact_id` | No | Stable partner-side contact/lead identifier (e.g. PropStream contact id), max 64 chars. Stored verbatim, never interpreted by Ballpoint, round-tripped on the corresponding `GET .../recipients` response, and echoed verbatim on per-piece RTS push-back events so you can map returned pieces directly to the CRM contact. **For partners using the per-piece RTS push-back, `contact_id` must be populated on every recipient** — the V1 RTS payload carries `contact_id` only (no name/address fields). |
| `address_type` | No | `PROPERTY` or `MAILING`. Optional for order-level upload; pair with `contact_id` when you need to distinguish a contact's property vs mailing address records. On the campaign-level Edit Leads / delta endpoint it is **required** and, together with `contact_id`, forms the upsert/remove key. |

> For campaign-level Edit Leads / delta (`PATCH /v1/billing/campaigns/{campaign_id}/recipients`), `contact_id` + `address_type` are required and together form the unique upsert/remove key. See [`API_KIT.md §6o`](API_KIT.md#6o-campaign-delta-recipients--addremove-across-editable-drops).

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

**Scope: cross-order dedup is opt-in via `campaign_instance_id`.** Ballpoint groups orders internally by a list-level backend `campaign_id` (a stable key derived from your account + `list_id`), but cross-order recipient dedup only runs when an order also carries a non-null `campaign_instance_id` shared with its sibling orders. The iframe surfaces this as `orders[].campaignInstanceId` on `campaign_submitted`:

- **`single` campaigns** — `campaignInstanceId` is `null`. No cross-order dedup.
- **`multi` (sequence) campaigns** — `campaignInstanceId` is `null` on every drop. Each drop's recipient set is the partner's full selection for that drop — Ballpoint does **not** dedupe across drops, matching the product intent that a sequence repeatedly reaches the same individuals. List reuse across separate submissions is also not deduped.
- **`split` (A/B) campaigns** — `campaignInstanceId` is the same opaque string on every sibling order in the same `campaign_submitted` payload. Cross-order dedup runs against the sibling orders only; partners must upload disjoint recipient slices per variant, and any overlap that slips through is rejected with `duplicate_in_campaign` on the second-uploaded variant. This is a guard-rail so no recipient receives both variants.

When `campaignInstanceId` is `null` on every order in a campaign, the "If an order belongs to a campaign..." behavior below does **not** fire, regardless of whether the orders share a backend `campaign_id`.

If an order belongs to a campaign that already has recipients from previous drops, we check for duplicate addresses automatically. Matches get rejected with `duplicate_in_campaign` and the order's `piece_count` is adjusted down so it can still reach `ready: true`.

Dedup matches on `(address, city, state, zip)`, trimmed and case-insensitive. We only check against other orders in the same campaign **with the same non-null `campaign_instance_id`** — cancelled/deleted orders are ignored.

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

For cross-order duplicates within the same campaign, you don't need to handle dedup on your end — the API takes care of it. Check `rejected_details` if you want to see which addresses were skipped. For same-order (intra-payload) duplicates, see below.

#### What this does NOT do

`duplicate_in_campaign` is **cross-order, same-campaign only** (the A/B-split guard-rail). Ballpoint does **not** perform intra-order recipient dedupe and does **not** use `duplicate_in_campaign` (or any other server-side logic) to override the user's same-order "Remove duplicates" selection. Same-order behavior is partner-driven:

- **Duplicate recipient records in the same order are treated as separate recipient records and mailed as separate pieces** — unless another normal validation rule rejects the request, such as missing required fields, invalid address fields, or exceeding the order's `piece_count`. This also applies to records split across an `append: true` chain on the same order.
- **`lead_id` and `type` (`mailing` / `property`) are not active recipient upload fields and are not used for dedupe.** Unknown fields are silently ignored at parse time and are not stored. Use [`contact_id` and `address_type`](#recipient-fields) instead — `contact_id` for the partner-side identifier that needs to round-trip, and `address_type` (`PROPERTY` / `MAILING`) when you need to distinguish a contact's property vs mailing record.
- **Same-lead `property == mailing` collapse is the partner's decision, expressed via the user's `Remove duplicates` selection.** If the user picks `Deliver To = both` + `Remove duplicates = OFF`, the partner uploads two recipient records for each lead whose property and mailing addresses are equal and Ballpoint mails two pieces. If the user picks `Remove duplicates = ON`, the partner uploads the deduplicated list and Ballpoint mails that. The uploaded recipient count must match the `piece_count` that the partner provided for the selected `(deliver_to, remove_duplicates)` combination in [`set_list.piece_counts`](#recipient-selection-contract-piece-count--dedup).

#### Identifier reference — four distinct ids

Four distinct identifiers. Confusing any two of them is a docs/code bug. Doc copy must reflect this map exactly:

- **backend `campaign_id`** — existing DB column. List-level grouping, deterministically derived as `f"camp_{account_id}_{list_id}"` (billing_router.py:3767). Stable across all submissions touching the same list_id within an account. **NOT exposed in postMessage payloads as-is.**
- **postMessage `campaignId`** (camelCase) — iframe-local id, `generateId('camp')` from campaign-store.js. Emitted in `campaign_created` / `campaign_submitted` / `order_added`. Has **no relationship** to backend `campaign_id`. Doc must never describe `campaign_submitted.campaignId` as "the backend campaign". Treat it as an opaque iframe handle.
- **`campaign_instance_id`** (snake_case) — **NEW** DB/API field on `orders`. Optional submit/split instance key. NULL = bypass cross-order dedup; shared value across siblings = enable dedup.
- **`campaignInstanceId`** (camelCase) — same value as the new DB field, surfaced into iframe→partner `campaign_submitted.orders[].campaignInstanceId`. Opaque string for partners.
- **`sequence_instance_id`** — appears in api-docs Q2.a/Q2.b for payment-recovery clone-forward. **Different concept**. Do not touch, rename, or conflate with `campaign_instance_id` in this plan.

Cross-tenant scoping is preserved by `campaign_id`'s `acct_{account_id}` prefix. `campaign_instance_id` cannot bridge accounts.

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
- **First-write-wins:** `set_sender` and `set_tenant` are accepted once per session. Duplicates are ignored. `set_api_config` can be resent to refresh the token. `set_list` may be resent with the SAME `listId` to refresh `count` / `name` / `piece_counts` after PropStream's Edit Leads modal saves (see [`set_list` refresh](#set_list-refresh-post-modal-sync)); a different `listId` is still rejected as a list-switch attempt.
- **Rate limiting:** Inbound messages are rate-limited to 20 messages per 5 seconds per origin.
- **CSP:** The iframe is served with a strict Content Security Policy. Your domain must be listed in the `frame-ancestors` directive. Contact Ballpoint if you receive CSP errors.

---

## 10. Troubleshooting

### "Classic templates unavailable (API not configured)"

**Cause:** `set_api_config` was not sent, or the `apiToken` value is empty/invalid.

**Fix:** Ensure the parent sends `set_api_config` with a valid `apiBaseUrl` and `apiToken` before the user reaches the product selection page. The iframe queues actions until config arrives, but the Classic tab requires a configured API client to fetch templates. Verify the token is a valid `pk_...` key and that `apiBaseUrl` points to the correct [environment](#3-environments).

### "Please contact your account owner to set up sender information"

**Cause:** The iframe is in embed (iframe) mode, sender information has not been resolved (`set_sender` not received), and `externalUserIsAccountOwner` is missing or `false` in the `set_list` payload.

**Fix:** Either send [`set_sender`](#set_sender--pre-fill-sender-info-optional) with the user's sender data (which skips the setup page entirely), or include `externalUserIsAccountOwner: true` in [`set_list`](#set_list--recipient-list-info-required) so the user sees the "Set up now" CTA and can request setup via [`sender_setup_requested`](#sender_setup_requested--user-requested-sender-info-setup). Once `set_sender` is received, the owner flag no longer matters. See [Sender-info setup gate](#sender-info-setup-gate-externaluserisaccountowner) for full details.

---

## Support

For iframe access, environment keys, and technical support, reach out to your partner technical contact at Ballpoint.

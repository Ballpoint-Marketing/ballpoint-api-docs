# Ballpoint Marketing Iframe — Partner Integration Kit

Partner contract version: **v1.7.29** (prepared for staging validation; not yet deployed to production)

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

The exact four-token value above remains required in the parent page. In a normal cross-origin embed, browser same-origin policy may prevent the Ballpoint iframe from reading its parent `<iframe>` element, so Ballpoint cannot inspect the `sandbox` attribute directly. That inspection limitation does **not** mean the attribute is missing or incorrect. When the parent element is inspectable, Ballpoint warns only if the attribute or one of the four documented tokens is missing.

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

For a PropStream embed, the iframe uses this configuration plus the
`externalUserId` from `set_list` to fetch `GET /v1/config`. The response is
cached in memory for the API-provided TTL (currently 60 seconds), coalesces
concurrent fetches, refreshes after expiry/visibility wake, and is invalidated
when API credentials or list context are refreshed. It is never written to
`localStorage` or `sessionStorage`.

`propstream_send_mail_enabled` is a preventive submit gate. If configuration
cannot be fetched or the flag is false, the iframe does not call `POST /orders`.
The API independently re-evaluates the flag on both order-creation routes, so
the browser check is not the security boundary. The flag introduces **no new
button, checkbox, copy, or layout**. PropStream continues to own visibility of
its Send Mail entry point; Ballpoint owns the submit decision after the user
enters the iframe. Non-PropStream embeds are unchanged.

### Automatic funnel analytics traffic (no partner action)

During a staging campaign flow after this contract is deployed, the iframe is
prepared to send one best-effort `POST /v1/partner/funnel-events` request per
observed milestone:
`campaign_started`, `product_selected`, `copy_edited`, `proof_viewed`,
`submit_clicked`, and `campaign_submitted_confirmed`. These requests use the
`apiToken` from `set_api_config` as `X-Partner-Key` and the active
`externalUserId` as `X-External-User-ID`.

This is Ballpoint-owned, log-only product telemetry. Partners do not need to
call the endpoint, handle a response, add a listener, or change their
integration. Telemetry failures never block or retry the campaign flow. The
payload contains only a short-lived campaign session ID, sequence, client
elapsed time, safe page ID, optional `single`/`multi`/`split` flow type, and the
event name. It contains no account/tenant/user identity in the body, recipient
PII, or copy entered by the user.

The intake accepts up to 1,000 attempts with valid partner and user context per
60 seconds for each account/source/external-account tuple, enforced per API
process. A throttled telemetry request is dropped with an empty `429` and no
retry.

The same session may emit `submit_clicked` more than once if the payment handoff
is reopened. `campaign_submitted_confirmed` is emitted only after payment
success. Drop-off is derived by Ballpoint from the last event received; the
iframe does not send a separate abandonment event.

This contract is prepared for local and staging validation only. Its inclusion
does not assert staging deployment or production availability.

### `set_list` — Recipient list info (required)

| Field | Type | Description |
|-------|------|-------------|
| `count` | number or string | Number of recipients in the list |
| `name` | string | Human-readable list name (shown in the UI) |
| `listId` | string | Your internal list identifier |
| `externalAccountId` | string | Your account/tenant identifier |
| `externalUserId` | string | Your user identifier |
| `externalUserIsAccountOwner` | boolean | Optional. Gates the iframe's sender-info "Set up now" CTA for this user. `true` → CTA visible, user may set up / edit sender info. `false` or missing → CTA hidden; the Sender Information step shows the blocked-state copy when setup is incomplete, and the Direct Mail Dashboard hides the Sender Information card entirely in every sender state. Default if absent or non-`true`: `false` (deny-by-default; partners who do not send the field get the same non-owner presentation). Mutable on `set_list` refresh — see [Sender-info setup gate](#sender-info-setup-gate-externaluserisaccountowner). |
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
- **Preserving vs clearing `piece_counts` on refresh:** if the refresh payload OMITS the `piece_counts` key entirely, the iframe preserves the currently-active `piece_counts` table AND the user's combo selection (pricing continues working). To explicitly replace the table, include `piece_counts` in the refresh payload with the new values — this resets the Deliver To / Remove duplicates selection to the [default](#default-selection). To explicitly clear it back to legacy single-count behavior, include `piece_counts: null`. Omitting the key is NOT the same as clearing.
- **Pricing/display on refresh when `piece_counts` is active:** on a refresh that OMITS `piece_counts`, the refreshed count is applied to internal state while the visible recipient count and price stay aligned with the user's current Deliver To + Remove duplicates selection (via the existing piece_counts lookup). A refresh that INCLUDES `piece_counts` resets the selection to the default first, so the displayed count and price follow the default combination, not the user's prior choice. If `piece_counts` is not active on the active list, the refreshed raw count drives display + price directly (legacy behavior).
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

Optional boolean on singular `set_list` and on `set_sender`. It controls the embedded setup/edit actions on both the Sender Information step and the Direct Mail Dashboard.

| Effective value | Iframe behavior |
|-----------------|-----------------|
| `true` | An incomplete profile shows **Set up now** or **Complete in Marketing Profile**. A profile with any sender data shows **Edit** on the Dashboard. Clicking any of these actions may emit `sender_setup_requested`. |
| `false`, missing, or any non-`true` value | Setup/edit actions are hidden. On the Sender Information step, an incomplete profile shows the blocked-state message ("Please contact your account owner to set up sender info"). On the Direct Mail Dashboard, the Sender Information card is hidden entirely whether the sender profile is empty, partial, or complete. `sender_setup_requested` is suppressed. |

Rules:

- **Default is `false`.** Partners who do not send the field get the same non-owner presentation (blocked message on the step; hidden Dashboard card). This is intentional (deny-by-default for backward compatibility).
- **Dashboard-first bootstrap:** before any singular `set_list` has been accepted, `set_sender.externalUserIsAccountOwner` may establish the owner state. This lets the Dashboard render the correct setup/edit action before a campaign list exists.
- **`set_list` becomes authoritative:** once a singular `set_list` has been accepted, its `externalUserIsAccountOwner` value overrides the bootstrap value and later `set_sender` messages cannot change it.
- **Mutable on `set_list` refresh.** Unlike `externalUserId` and `externalAccountId` (which are locked to the first-receipt values for the session), `externalUserIsAccountOwner` may be flipped on a same-`listId` refresh. The iframe re-applies setup/edit visibility immediately. PropStream should re-send `set_list` with the updated value whenever the user's account-owner status changes.
- **Singular `set_list` only.** The field is **not** part of the `set_lists` (plural) schema. If sent there, it is silently dropped.
- **Strict equality.** The iframe checks for `=== true`. String `"true"`, `1`, or any other truthy value is treated as `false`.

Scope (what this field does **not** do):

- Does **not** introduce broader RBAC, role gating, or permission sync between PropStream and the iframe.
- Does **not** introduce API or webhook authorization. Ballpoint's API does not read or enforce this field.
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

**Idempotent while a create flow is active:** after the first valid command starts a create flow, replayed `open_create_direct_mail` messages are ignored until that flow explicitly ends (the user returns to the Direct Mail Dashboard, cancels/abandons the flow, or completes it). An ignored replay does not navigate, reset selections or form state, call `startNewCampaign()` again, or emit another `page_changed`. After the flow ends, a later valid command may start a new campaign in the same iframe load, including for the same list. Parent apps should still avoid sending duplicate commands; this iframe behavior is a defense against effect/retry replays.

**Required list context:** send this only after the iframe has a concrete active list context: either an accepted first `set_list` with a non-empty `listId` and positive `count`, or a user-selected `set_lists` item with a non-empty `listId` and positive `count` after the iframe has emitted `list_selected`. The iframe intentionally does not treat its built-in demo defaults (`Pre-Foreclosure Leads`, `847`) as usable context for this command. If the command arrives before active list context exists, the iframe does not navigate and emits `open_create_direct_mail_failed`.

`set_api_config` should still be sent during bootstrap. Missing API config does not block opening this screen because the iframe already queues submit actions until API config arrives, but partners should send `set_api_config` before the user submits.

### `set_dashboard_filter` — Scope the My Campaigns dashboard to a marketing group (parent → iframe)

> **Current staging contract — pending PropStream wiring.** A **view-only** filter for the iframe's **My Campaigns** dashboard (the campaign list, the insights header, and the status tab counts). It is **separate from** `set_list` (which locks the active list for *creating* an order) and `set_lists` (the deprecated list-selector): sending it never changes the active creation list and never opens the selector.

Use this when your app wants the user to see, in My Campaigns, only the direct-mail campaigns belonging to a specific marketing group they clicked in your UI. Your app stays the source of truth for which list IDs belong to a group; the iframe applies them as a view filter and asks the API to return the matching subset (no `group_id` is stored Ballpoint-side).

```json
{
  "source": "propstream",
  "version": 1,
  "type": "set_dashboard_filter",
  "listIds": ["list_abc", "list_def"],
  "tenantKey": "ps_acc_42"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | Yes | Must be `"propstream"`. |
| `version` | number | Yes | Must be `1`. |
| `type` | string | Yes | Always `"set_dashboard_filter"`. |
| `listIds` | array of strings \| null | No | The list IDs of the marketing group to scope the dashboard to (the same `listId` values you pass on `set_list`). **Optional** — omitting the field (or sending `null`) is the explicit *clear* signal (full account-wide view). See the semantics table below. |
| `tenantKey` | string | Optional | If present, must match the active tenant scope — a mismatch **rejects** the whole message (no filter applied, no tenant state changed). If omitted, the filter is applied. Real security is still enforced server-side by your partner/account scope; `listIds` are an **advisory view filter, not an authorization grant**. |

**`listIds` semantics:**

| Value | Meaning |
|-------|---------|
| `["a", "b", …]` (1–100 ids) | Scope the dashboard to those lists. The campaign list, insights header, **and** tab counts all narrow together. Ids are sanitized + de-duplicated. |
| `[]` (empty array) | **Zero-results** — the dashboard renders empty (empty list, zeroed insights, all tab counts `0`). This is **not** "show all"; use it when the selected group has no lists. |
| `null` or field omitted | **Clear** the filter — the dashboard returns to the full account-wide view. |
| more than 100 ids | **Rejected** with no truncation — the whole message is ignored (a warning is logged). Send ≤ 100. |

**Re-appliable:** unlike `set_list` (which locks on first receipt), `set_dashboard_filter` is a live view filter — send it again any time (e.g. when the user clicks a different group) and it **replaces** the prior `listIds` wholesale.

Backed by the repeated `list_id` query parameter on the dashboard read endpoints — see [`GET /v1/billing/orders` in API_KIT.md](API_KIT.md).

### `open_direct_mail_dashboard` — Open the Direct Mail dashboard (parent → iframe)

Explicit navigation command. Sends the iframe to its **My Campaigns / Direct Mail Dashboard** view and enters **dashboard-first mode**.

```json
{
  "source": "propstream",
  "version": 1,
  "type": "open_direct_mail_dashboard"
}
```

This message has **no payload fields** beyond the standard envelope (`source`, `version`, `type`). Send it once during bootstrap to land the iframe on the Dashboard.

**This is the only way to land the iframe on the Dashboard.** Sibling messages do not navigate:

- [`set_dashboard_filter`](#set_dashboard_filter--scope-the-my-campaigns-dashboard-to-a-marketing-group-parent--iframe) is **view-only** — it scopes what is displayed on the Dashboard (campaign list, insights header, tab counts) but never changes the active page.
- [`set_list`](#set_list--recipient-list-info-required) (and [`set_lists`](#set_lists--multiple-lists-for-user-selection-alternative-to-set_list)) set context only — they never navigate by themselves.
- [`open_create_direct_mail`](#open_create_direct_mail--open-the-create-direct-mail-flow-optional) opens the **Create Direct Mail** flow (and is gated on an active list context). It does not open the Dashboard.

**Session-sticky — no "exit dashboard-first" command in V1.** Once `open_direct_mail_dashboard` lands, dashboard-first mode persists for the iframe's lifetime. There is intentionally no inverse message. To return the iframe to the legacy `set_list`-first behavior (list context is supplied up front, and create navigation remains driven by the existing CTA/flow), remount the iframe element (or reload its `src`) and re-bootstrap without `open_direct_mail_dashboard`.

#### Dashboard-first handshake (worked example)

Recommended bootstrap order in dashboard-first mode:

1. On `ready`, send these four messages — **in this order**:
   1. `set_api_config`
   2. `set_dashboard_filter` *(optional — scopes the Dashboard view)*
   3. `open_direct_mail_dashboard`
   4. `set_sender` *(optional — pre-fills sender info)*

   The iframe is **order-robust** and always ends on the Dashboard regardless of the actual arrival order. The recommended order above avoids a brief one-frame flash of the create page — sending `open_direct_mail_dashboard` **before** `set_sender` prevents the iframe from momentarily composing the post-`set_sender` create view before the Dashboard navigation lands.

2. The iframe shows the Dashboard.

3. User clicks **+ Create Direct Mail** on the Dashboard. The iframe emits a **no-context** [`create_direct_mail_requested`](#create_direct_mail_requested--user-clicked-create-direct-mail) with payload `{ entryPoint: "campaign_home" }` only — `listId`, `listName`, and `recipientCount` are omitted because no active list context exists in dashboard-first mode. The iframe **stays on the Dashboard**; it does not open the create flow on its own in this mode.

4. The parent creates its own list / record on its backend.

5. On success, the parent sends — **in this order**:
   1. `set_list` *(context for the newly created list)*
   2. `open_create_direct_mail` *(navigation)*

   Order matters: `open_create_direct_mail` is gated on an active list context (see its [required list context note](#open_create_direct_mail--open-the-create-direct-mail-flow-optional)). If `open_create_direct_mail` arrives before `set_list`, the iframe emits [`open_create_direct_mail_failed`](#open_create_direct_mail_failed--create-direct-mail-command-rejected) and does not navigate.

6. The iframe opens the **Create Direct Mail** page with the new list context.

7. On parent-side failure, the parent sends nothing. The iframe stays on the Dashboard with **no iframe-side toast, error banner, or status message** — error UX is entirely the parent's responsibility.

> **Compatibility with the existing `set_list`-first flow.** Partners that do **not** send `open_direct_mail_dashboard` see the legacy bootstrap behavior unchanged: partners provide concrete list context up front via `set_list` or `set_lists`; when the iframe-owned Create Direct Mail CTA runs, [`create_direct_mail_requested`](#create_direct_mail_requested--user-clicked-create-direct-mail) includes `listId` / `listName` / `recipientCount` and the iframe opens the create flow locally, as before.

#### Dashboard direct-mail, recipient, and address search

The Dashboard search box combines locally loaded campaign matches with a
tenant-scoped recipient/address search performed by the iframe. Campaigns are
searchable as soon as their order recipients are accepted/uploaded; the user
does not have to wait for USPS piece tracking to be indexed. Recipient name
tokens are order-independent, so `Gregory, Debra` can find `Debra Gregory`.

The iframe sends the active `X-External-User-ID` when one was supplied by the
parent, merges campaign and recipient results, and shows an empty state only
when neither source matched. Clearing the query restores the normal campaign
list. An order-only recipient match can show its campaign, but does not expose
an **Opt Out** action until a piece-tracking record exists. This behavior is
automatic: there is no new parent → iframe command, iframe → parent event, or
partner-side listener to implement.

### `payment_result` — Payment popup outcome (parent → iframe)

> **Current staging contract — pending PropStream wiring.** This is the iframe-side contract for the in-iframe Payment Successful / Payment Failed result screens. The payment popup and the charge itself remain partner-owned (see [Partner Payment Gate Flow](#partner-payment-gate-flow-send-now-walkthrough)); after the partner's popup resolves, the partner should send `payment_result` to the iframe so the iframe can render the matching result screen. PropStream's listener / sender is not yet wired — this section documents what the iframe expects today on staging.

The iframe does **not** observe the payment popup directly. The parent app owns the popup lifecycle and is responsible for telling the iframe whether the charge succeeded, failed, or was cancelled.

```json
{
  "source": "propstream",
  "version": 1,
  "type": "payment_result",
  "tenantKey": "ps_acc_42",
  "status": "success",
  "campaignId": "camp_abc123",
  "ballpointCampaignId": "cmp_abc",
  "orderIds": ["ord_local_001"],
  "ballpointOrderIds": ["ord_abc123"],
  "reason": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | Yes | Must be `"propstream"` (the same source identifier required on all parent → iframe messages). |
| `version` | number | Yes | Must be `1`. The iframe supports the version set `[1]`; other values are ignored. |
| `type` | string | Yes | Always `"payment_result"`. |
| `tenantKey` | string | Yes | Must match the active tenant the iframe was scoped to. Mismatched or missing `tenantKey` causes the entire message to be **rejected and ignored** — no result screen is rendered and **no tenant state is mutated** by this message. The check is read-only (this event cannot be used to establish or change tenant scope). |
| `status` | string | Yes | One of `"success"`, `"failed"`, `"failure"`, `"cancelled"`. The iframe normalizes `"failure"` → `"failed"`. `"success"` → **Payment Successful** screen; `"failed"`/`"failure"` → **Payment Failed** screen; `"cancelled"` → **Payment Not Completed** screen (its own copy variant on the same visual shell — **not** "Payment Failed"). Any other value is ignored (no screen change). |
| `campaignId` | string | Optional | Iframe-local campaign handle (the same `campaignId` previously emitted on `campaign_created` / `campaign_submitted`). Echoed back on `payment_retry_requested` if present. |
| `ballpointCampaignId` | string | Optional | Server-side campaign id. Send only if the parent has it from its own API / order-history reconciliation state — note that `campaign_submitted` does **not** expose `ballpointCampaignId` (only `campaignId` and `orders[].ballpointOrderId`). Echoed back on `payment_retry_requested` if present. |
| `orderIds` | array of strings | Optional | Iframe-local order ids (e.g. those returned in `campaign_created.orderIds`). Echoed back on `payment_retry_requested` if present. |
| `ballpointOrderIds` | array of strings | Optional | Server-side `ballpointOrderId` values (from `campaign_submitted.orders[].ballpointOrderId`). Echoed back on `payment_retry_requested` if present. |
| `reason` | string | Optional | Decline context for an actual **failure** (e.g. card-decline reason), surfaced inline on the **Payment Failed** screen (plain text, ~300-char cap). Ignored on `status: "success"` **and on `"cancelled"`** (a cancellation has no failure reason). |

#### Status normalization and ignore behavior

- `"failure"` is normalized to `"failed"` internally — partners may send either; the iframe treats them identically.
- Any `status` value outside `{success, failed, failure, cancelled}` is ignored: the iframe does not change screens and does not emit a follow-up event. This is intentional, so an unknown future-status string (or a partner typo) cannot put the user on the wrong screen.
- Missing `tenantKey`, or `tenantKey` that does not match the active scope, also causes the entire message to be ignored before any other field is read.

#### Iframe behavior on receipt

- **`status: "success"`** — iframe shows the in-iframe **Payment Successful** screen and treats the campaign's payment as resolved on the iframe side. Production status continues to be driven by `order.status_changed` webhooks (see [API_KIT.md](API_KIT.md)) — this message only updates the iframe UI.
- **`status: "failed"` / `"failure"`** — iframe shows the in-iframe **Payment Failed** screen (an actual payment failure, e.g. card declined). The optional `reason` is surfaced inline. Offers a **Try Again** action that emits [`payment_retry_requested`](#payment_retry_requested--user-clicked-try-again-on-the-failure-screen) back to the parent.
- **`status: "cancelled"`** — iframe shows a distinct **Payment Not Completed** screen (same visual shell as Payment Failed, different copy: *"Your payment was not completed. You can try again when you're ready."*). This represents the user **closing / not completing** the payment flow — it is **not** a card/payment failure, and no `reason` is shown. Also offers **Try Again** → emits [`payment_retry_requested`](#payment_retry_requested--user-clicked-try-again-on-the-failure-screen). **Do not send `cancelled` on a plain Payment Preview modal close** — it ends the [`campaign_submitted` reopen flow](#campaign_submitted--campaign-submitted-to-ballpoint) by dead-ending the user on this result screen. Reserve `cancelled` for genuinely abandoned payment outcomes; on a plain modal close, send nothing and let the iframe's re-emit path handle a second **Continue to Payment** click.
- The iframe does **not** retry the payment itself, does **not** call `POST /orders` again, and does **not** call `/confirm-payment`. The parent owns the charge — this contract is UI handoff only.

> **Backend distinction (important).** `status: "cancelled"` is a **UI signal to the iframe only** — the user closed or did not complete the payment flow. It does **not** imply a card/payment failure. Reserve the backend `POST /v1/billing/orders/{order_id}/confirm-payment` with `status: "failed"` for an **actual** failed payment outcome (e.g. a declined charge), not for a user cancellation — unless that is your deliberate billing policy. A cancellation usually means no charge was attempted, so the order can remain `pending_payment` (the user retries later) or be cancelled via the canonical partner endpoint `POST /orders/{order_id}/cancel`.

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

#### Default selection

The controls open on **`Deliver To = mailing`** with **`Remove duplicate addresses = off`**.

This default is applied on first render and re-applied every time a new `piece_counts` table is received — a first-receipt `set_list`, a `set_lists` payload, the user picking a different list in the selector, **and a same-`listId` refresh that carries the `piece_counts` key** (the [Edit Leads sync](#set_list-refresh-post-modal-sync)). In every one of these the user's prior Deliver To / Remove duplicates choice is discarded and reset to the default. A refresh that OMITS the `piece_counts` key preserves both the table and the user's selection — the only case in which a prior choice survives.

A user who submits without touching either control emits the default selection. Using the worked example below (where `piece_counts.mailing.dedup_off` is 498):

```json
"recipient_selection": {
  "deliver_to": "mailing",
  "remove_duplicate_addresses": false,
  "piece_count": 498
}
```

Always read the emitted `recipient_selection` rather than assuming a default — it is the authoritative value for billing and recipient-upload sizing.

**If your `piece_counts` omits the `mailing` block**, the opening selection lands on an option that is not selectable. Consistent with the missing-key rule above, the iframe disables that option, shows a recipient count of 0, and blocks forward progress until the user chooses an available `Deliver To`: on the list step every campaign type is marked ineligible and **Next** stays disabled, and the final **Continue to Payment** on the Order Summary is fail-closed (see [Fail-closed submit](#fail-closed-submit) below). There is no automatic fallback to another option. Send a `mailing` block if you want the default to resolve to a count.

#### Fail-closed submit

The Order Summary's **Continue to Payment** is guarded: when a `piece_counts` table is active, the iframe will not create an order or emit `campaign_submitted` unless the resolved `piece_count` is a positive number. This protects the case where a same-`listId` refresh arrives while the user is on the Order Summary and its table no longer contains the active combination — the selection resets to a default that resolves to no count. Rather than emit a `null` `piece_count` or a placeholder order, the iframe stops, shows an actionable message, and leaves the flow interactive so the user can use **Previous** to go back and choose an available `Deliver To`. No order is created and no `campaign_submitted` fires in that state. Partners without `piece_counts` are unaffected — this guard applies only when a table is active.

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

If provided, the iframe reconciles the parent-owned Marketing Profile into its read-only sender views. The parent remains the source of truth: users request setup or edits through `sender_setup_requested`, and the parent replies with a new `set_sender` after a successful save.

| Field | Type | Description |
|-------|------|-------------|
| `fullName` | string | Canonical sender name or company. When present, this value wins over the name aliases below. |
| `firstName` | string | Optional person-name alias. If `fullName` is omitted, the iframe derives it from `businessName`, or from `firstName` + `lastName`. |
| `lastName` | string | Optional person-name alias used with `firstName` when `fullName` and `businessName` are omitted. |
| `businessName` | string | Optional company-name alias. If `fullName` is omitted, a non-empty `businessName` takes precedence over the derived person name. |
| `address` | string | Street address |
| `city` | string | City |
| `state` | string | Two-letter state code (e.g. `FL`) |
| `zip` | string or number | ZIP code: 5 digits, 9 digits, or ZIP+4 (`12345-6789`). Alphabetic/malformed values are rejected. |
| `phone` | string | 10 digits, or 11 digits beginning with `1`. Standard `+`, parentheses, space, period, and hyphen formatting is accepted; letters are rejected. |
| `email` | string | Optional email address |
| `website` | string | Website URL |
| `logo` | string | Optional. URL to sender logo image |
| `externalUserIsAccountOwner` | boolean | Optional Dashboard-first role bootstrap. Honored only until a singular `set_list` is accepted; `set_list` is authoritative afterward. Strict boolean `true` is required. |
| `tenantKey` | string | Optional. Tenant scope key |

#### Reconciliation semantics

- **First accepted payload is a snapshot.** The first `set_sender` in an iframe load/tenant scope clears any sender values cached for that scope before applying the supplied fields. This prevents stale Marketing Profile data from a prior session from surviving.
- **Later payloads are patches.** A later `set_sender` in the same iframe load/tenant scope updates only fields present in the message. Omitted fields preserve their current values; a field sent explicitly as `""` clears that value.
- **A late first tenant assignment preserves the accepted snapshot.** In a Dashboard-first bootstrap, `set_sender` may arrive before the first `tenantKey`. When `set_list`, `set_lists`, `set_api_config`, or `set_tenant` later establishes that first tenant scope, the iframe persists the already-accepted sender snapshot in the tenant-scoped namespace before continuing and removes the temporary unscoped copy after the scoped write succeeds. This applies only to the transition from no tenant to the first tenant; it never copies sender data between two established tenants.
- **Name derivation is deterministic.** Send `fullName` when possible. If it is omitted and any name alias is present, `businessName` wins; otherwise `firstName` and `lastName` are joined.
- **Invalid contact fields fail closed.** A non-empty `zip` or `phone` that does not match the formats above is discarded rather than stripped into a different value. The profile remains partial and cannot advance or submit until a valid replacement arrives.
- **Tenant scope is locked.** After sender state is established for a tenant, a later `set_sender` cannot switch to another `tenantKey`; the mismatched message is rejected without changing sender state.

#### Complete and partial profiles

A sender profile is complete only when `fullName`, `address`, `city`, and `state` are non-empty and both `zip` and `phone` are valid according to the formats above. `email`, `website`, and `logo` are optional.

| Profile received | Sender Information step | Direct Mail Dashboard |
|------------------|-------------------------|-----------------------|
| Complete | The iframe may advance to Direct Mail Type. If another parent modal is open, the parent still owns when that modal closes. | An account owner sees the sender summary and **Edit**. A non-owner sees no Sender Information card. |
| Partial | The step remains open. Supplied fields are prefilled read-only, missing fields remain empty, and an account owner sees **Complete in Marketing Profile**. | An account owner sees available values, `Not set` for missing values, and **Edit**. A non-owner sees no Sender Information card. |
| Empty + account owner | Shows **Set up now**. | Shows **Set up now**. |
| Empty + non-owner | Shows the account-owner blocked state and emits no setup request. | The Sender Information card is hidden entirely and no setup request is emitted. |

For the most predictable reconciliation after a Marketing Profile save, send a complete profile snapshot with all supported fields. Patch messages are supported when intentional; include an explicit empty string when a previously supplied value must be cleared.

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
  "buildStamp": "b88d6fd",
  "build": {
    "environment": "staging",
    "buildId": "b88d6fd",
    "releaseTag": "",
    "deployedAt": "2026-06-16T21:21:51Z"
  },
  "contractVersions": {
    "iframe": "1",
    "api": "3.1",
    "partner": "1.7.29"
  }
}
```

##### `build` and `contractVersions` (diagnostic, optional)

Both blocks are additive (v1.6.7+) and carry the same shape returned by `GET /v1/billing/partner/health` so parents and dashboards can correlate the iframe build with the API build using a single parser.

- `build.environment` — `"production"`, `"staging"`, or a local-dev label.
- `build.buildId` — git short SHA at deploy. `"dev"` / `"unknown"` for local serves.
- `build.releaseTag` — git tag on production deploys; `""` on staging and local.
- `build.deployedAt` — ISO-8601 UTC timestamp at deploy; `""` when not built by CI.
- `contractVersions.iframe` — matches the `version:1` envelope and `iframeVersion`.
- `contractVersions.api` — kept in lockstep with the API's `API_VERSION`.
- `contractVersions.partner` — kept in lockstep with this CHANGELOG's top entry.

These fields are diagnostic and non-sensitive. Partners may ignore them — they do not affect handshake, ordering, billing, or any contract behavior. Existing `iframeVersion`, `maxVersion`, and `buildStamp` are unchanged.

The example above shows the values from a **staging** deploy (`environment: "staging"`, `releaseTag: ""`), which is the currently deployed environment. On a production deploy, `environment` reads `"production"` and `releaseTag` carries the release git tag — the field shapes are identical.

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

#### `edit_leads_requested` — User clicked "Edit Leads"

**Historical note (iframe staging-only):** the original list-level header button (`{listId, listName, recipientCount, externalAccountId, externalUserId}` emitted from a single global header button) has been replaced by per-campaign-card buttons. The header button is removed; each campaign card in My Campaigns — single send, A/B split, and multi-month — now has its own Edit Leads button when at least one of its orders is still pre-production and unbilled.

**Current placements:**
- **Creation flow:** the Mailing List panel on the Customize step exposes **Edit Leads** for single send, A/B split, and multi-month before the campaign is submitted.
- **My Campaigns:** campaign cards / campaign details expose **Edit Leads** after creation when at least one order is still editable.

**When emitted (creation flow):** the user clicks **Edit Leads** while building a campaign, before any Ballpoint order exists. The iframe emits the same event type with `scope: "creation_flow"`, active list context, and empty `affectedOrders[]` / `lockedOrders[]`. There are no order ids or PATCH endpoints yet. This placement requires a concrete active list from an accepted `set_list` or selected `set_lists` item; demo/default context does not emit.

**Creation-flow payload:**

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "edit_leads_requested",
  "scope": "creation_flow",
  "creationStage": "customize",
  "campaignId": null,
  "ballpointCampaignId": null,
  "campaignType": "split",
  "campaignDeltaEndpoint": null,
  "campaignDeltaMethod": null,
  "listId": "ps_list_654",
  "listName": "Probate Leads",
  "recipientCount": 400,
  "externalAccountId": "ps_acc_42",
  "externalUserId": "user_789",
  "affectedOrders": [],
  "lockedOrders": []
}
```

For `scope: "creation_flow"`, PropStream should open its Edit Leads modal and, on save, send a same-list [`set_list` refresh](#set_list-refresh-post-modal-sync) with the updated `count`, `name`, and optional `piece_counts`. Do **not** PATCH recipients or send `recipients_updated` for this pre-submission path, because no Ballpoint orders exist yet. For A/B split creation, update the campaign-level list/count first; variant allocation happens later when the submitted orders are created.

**When emitted (post-creation):** the user clicks the Edit Leads button on any campaign card (single send, A/B split, or multi-month). Eligibility requires:
- All orders have `paymentConfirmed` not null (defense: campaigns with any null are skipped — typically non-gated accounts)
- At least one order is "affected" (see classification below)

**Eligibility (v1.6.0).** Edit Leads is available **only** for payment-gated campaigns/orders that are still `scheduled` or `pending_payment` and unbilled (`paymentConfirmed === false`) — i.e. pre-production and not yet paid. Once an order is paid, `accepted`, in production, mailed, delivered, or terminal, it is **locked** and its Edit Leads button is hidden (the underlying `PATCH .../recipients` returns `409 RECIPIENTS_LOCKED` / `PAID_LOCKED`). **Non-gated accounts do not expose Edit Leads** because the payment gate is not active. Full per-order classification is in "Affected allowlist" below; see also `API_KIT.md §6n/§6o`. Tightened in CHANGELOG v1.6.0.

**Post-creation payload:**

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "edit_leads_requested",
  "scope": "multi_month_campaign",
  "campaignId": "api_campaign_camp_propstream_4192",
  "ballpointCampaignId": "camp_mrx17n8ccqe52ve",
  "campaignType": "multi",
  "campaignDeltaEndpoint": "/v1/billing/campaigns/camp_propstream_4192/recipients",
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
| `scope` | One of `creation_flow` \| `multi_month_campaign` \| `single_send` \| `ab_split`. `creation_flow` is pre-submission and has no Ballpoint orders yet. Other values are post-creation and reflect the campaign type so the parent listener can route to the right modal. `multi_month_campaign` value unchanged from prior releases for backwards compatibility. |
| `creationStage` | Present for `scope: "creation_flow"`; currently `"customize"`. Omitted on post-creation campaign-card events. |
| `campaignId` | Iframe-local group key (e.g. `api_campaign_<id>` for API-loaded campaigns; `cmp_<local>` for in-builder). Use `ballpointCampaignId` for cross-system reference. |
| `ballpointCampaignId` | The persisted cross-system campaign id shared by the campaign's orders (`orders.external_campaign_id`, i.e. the original `campaign_created.campaignId`) — **not** the Ballpoint-internal API `campaign_id`. `null` when the orders do not share a single persisted `external_campaign_id`. |
| `campaignType` | `"single"` \| `"multi"` \| `"split"`. Mirrors `campaign.type` in the iframe. |
| `campaignDeltaEndpoint` | Campaign-level PATCH endpoint for delta add/remove (`/v1/billing/campaigns/{campaign_id}/recipients`, where `{campaign_id}` is the Ballpoint-internal API campaign id — **not** `ballpointCampaignId`). Preferred for multi-month campaigns. `null` if campaign not yet persisted server-side. See `API_KIT.md §6o`. |
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

**Emit rules:** for post-creation campaign cards, the iframe does NOT emit this event when `affectedOrders.length === 0`; the button is hidden in that case. For `scope: "creation_flow"`, `affectedOrders[]` is intentionally empty because the campaign has not been submitted yet; emission is gated by concrete active list context instead.

**Expected PropStream behavior**

1. Listen for `edit_leads_requested`.
2. Open the Edit Leads modal (PropStream-hosted, on top of the iframe).
3. **Creation flow (`scope: "creation_flow"`):** after modal save, send a same-list [`set_list` refresh](#set_list-refresh-post-modal-sync). Do not PATCH recipients and do not send `recipients_updated`.
4. **Post-creation Option A (campaign-level, preferred for multi-month):** PATCH `campaignDeltaEndpoint` with delta `{added, removed, remove_all}`. One call distributes to all editable drops. See `API_KIT.md §6o`.
5. **Post-creation Option B (per-order, required for A/B split variant allocation):** PATCH each `affectedOrders[].editRecipientsEndpoint` with the full replacement list. See `API_KIT.md §6n`.
    - **A/B split:** the variant-specific slice goes to each variant's endpoint, not the full list. Use the `variant` field on each `affectedOrders[]` item to identify A vs B. PropStream's split allocation logic determines what slice goes to each.
6. After all post-creation PATCHes succeed, emit [`recipients_updated`](#recipients_updated--partner-finished-editing-recipients) back to the iframe so it can refresh the campaign card.
7. On modal close without changes, no postMessage required.

**Testing this flow.** Use a payment-gated staging account (`requires_payment_confirmation = true`). Create a campaign but **do not confirm payment** — the order stays `pending_payment` (send-now) or `scheduled` with `paymentConfirmed = false` (future-dated), and the **Edit Leads button is available** on the campaign card. After payment is confirmed (or the order moves to `accepted` / production), the button disappears and the order shows in `lockedOrders`.

#### `recipients_updated` — Partner finished editing recipients (parent → iframe)

Emitted by the parent app (e.g. PropStream) after successfully PATCHing each `affectedOrder`. Triggers the iframe to re-fetch campaign history and re-render My Campaigns.

```json
{
  "source": "propstream",
  "version": 1,
  "type": "recipients_updated",
  "tenantKey": "ps_acc_42",
  "campaignId": "api_campaign_camp_propstream_4192",
  "ballpointCampaignId": "camp_mrx17n8ccqe52ve",
  "updatedBallpointOrderIds": ["ord_abc123", "ord_def456"]
}
```

| Field | Description |
|---|---|
| `tenantKey` | MUST match the iframe's active tenant scope. The iframe rejects mismatches without mutating tenant state — this event cannot be used to establish or change tenant scope. |
| `campaignId` | Iframe-local group key, echoed from the original `edit_leads_requested` event. |
| `ballpointCampaignId` | Echo of the persisted cross-system campaign id from the original `edit_leads_requested` event (`orders.external_campaign_id`) — **not** the internal Ballpoint API `campaign_id`. |
| `updatedBallpointOrderIds` | Array of `ballpointOrderId` strings that were PATCHed. Maximum 1000 IDs, each up to 256 chars. The iframe treats this as advisory (full refresh happens regardless). |

**Iframe behavior on receipt:**

1. Validate `tenantKey` against the active scope (read-only check; mismatch → rejected, no state mutation).
2. Validate `updatedBallpointOrderIds` array shape + per-element string + length caps.
3. Re-fetch campaign history (full refresh).
4. Re-render My Campaigns page so the user sees the new `piece_count` and price for the edited drops.

**Defense in depth:** the iframe does NOT trust `updatedBallpointOrderIds` for access control. The list is advisory; refresh is unconditional once tenant + shape validation pass. This prevents a malicious or buggy parent from selectively invalidating per-order state.

#### `sender_setup_requested` — User requested sender info setup

Sent when an account owner clicks **Set up now** or **Complete in Marketing Profile** on the Sender Information step, or **Set up now** / **Edit** on the Direct Mail Dashboard. PropStream's parent app should open its Marketing Profile modal and reply with a new [`set_sender`](#set_sender--pre-fill-sender-info-optional) after a successful save.

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
| `page` | string | V1 enum: `"setup"` \| `"campaigns"`. `"setup"` identifies the Sender Information step; `"campaigns"` identifies the Direct Mail Dashboard. |
| `externalAccountId` | string | Partner account identifier echoed verbatim from the most recent `set_list` / `set_tenant`. **MAY be empty string** if the user reaches "Set up now" before any `set_list` or `set_tenant` has arrived (e.g., very first session before list selection). |
| `externalUserId` | string | Partner user identifier echoed verbatim from the most recent `set_list` / `set_tenant`. **MAY be empty string** under the same condition as `externalAccountId`. |

No sender PII (`fullName`, `firstName`, `lastName`, `businessName`, `address`, `city`, `state`, `zip`, `phone`, `email`, `website`, `logo`) is ever included in this event. The parent already owns the sender data via the existing `set_sender` flow.

**Visibility / lifecycle**

- **Gated by the effective `externalUserIsAccountOwner === true`.** The value may be bootstrapped by `set_sender` before list context exists; an accepted singular `set_list` is authoritative afterward. When the effective value is `false`, missing, or non-`true`, setup/edit actions are hidden and `sender_setup_requested` is not emitted. See [Sender-info setup gate](#sender-info-setup-gate-externaluserisaccountowner).
- On the Sender Information step, an empty profile renders **Set up now** and a partial profile renders its available fields plus **Complete in Marketing Profile**. A complete profile may advance the active create flow.
- On the Direct Mail Dashboard, an account owner sees **Set up now** for an empty profile and the available sender summary plus **Edit** for a partial or complete profile. A non-owner sees no Sender Information card in any sender state. Dashboard clicks use `page: "campaigns"`.
- In standalone (non-embed) mode the iframe falls back to its built-in inline sender form. The CTA is suppressed.
- **Pre-lock behavior:** queued by the iframe until the parent origin lock completes, then delivered only to the locked parent origin. Not broadcast to all allowlisted origins. Identical treatment to `edit_leads_requested`.
- **Parent owns its modal lifecycle.** The iframe does not emit a modal-close or modal-cancel event. Receiving `set_sender` may update or advance the iframe underneath, but it does not instruct PropStream to close its Marketing Profile modal. Keep that modal open until the parent completes its own explicit save or close action.

**Expected PropStream behavior**

1. Listen for the `sender_setup_requested` event.
2. Open the Marketing Profile modal overlay (PropStream-hosted, on top of the iframe) and keep it open until the user explicitly saves or closes it.
3. After a successful save, send a fresh [`set_sender`](#set_sender--pre-fill-sender-info-optional) containing the updated sender data. A complete snapshot is recommended.
4. Close the parent modal according to PropStream's own save/close lifecycle. On close without changes, no postMessage is required.

#### `page_changed` — User navigated to a different view

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "page_changed",
  "page": "products"
}
```

`page_changed` is an informational state event, not a navigation or reload
command for the parent. While a create flow is active, the parent MUST preserve
the existing iframe element, `src`, key/mount identity and `contentWindow` when
this event arrives. Recreating or reloading the iframe starts a new document and
therefore discards the in-memory campaign selections and per-piece scheduling
progress.

In-flow controls such as **Previous** are owned by the iframe. For example,
**Previous** from a Multi Send blank **Create Your Own Design** piece returns to
the Multi campaign review and emits `page_changed` with `page:
"campaign-review"`; it does not request a parent route change, create an order,
or start a new campaign session. A parent should remount only for an intentional
fresh-session transition, such as the new/permanent `listId` case documented
under `create_direct_mail_requested` below.

#### `campaign_home_requested` — User requested the partner campaign home

Sent once when the user clicks **Back to Campaign Home** on the iframe's Direct Mail Dashboard / My Campaigns page. This is a fire-and-forget navigation request: the iframe stays on the Dashboard while the PropStream parent owns the campaign-home navigation or iframe unmount.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "campaign_home_requested"
}
```

The envelope above is the complete event. It contains no payload object, identifiers, tenant/list/user fields, page, reason, or PII, and the iframe does not wait for an acknowledgement.

**Lifecycle and delivery semantics**

- Exactly one event is emitted per user click.
- The click does not emit `cancelled`, does not emit `page_changed`, and does not end an active create-flow lifecycle.
- **Pre-lock behavior:** queued until the parent-origin lock completes and then delivered only to that locked parent origin. It is not broadcast to every allowlisted origin.
- In standalone mode no postMessage is emitted; the button falls back to the iframe's local Sender Information page.

**Adjacent Previous-button behavior:** clicking **Previous** on the Direct Mail Type step is local in-flow navigation back to Sender Information. It does not emit `cancelled` or end the create lifecycle, and the user can continue forward again in the same session.

#### `create_direct_mail_requested` — User clicked Create Direct Mail

Sent when the user clicks the iframe-owned **Create Direct Mail** CTA. The event has **two payload shapes** depending on whether the iframe currently has an active list context — partners should branch on the presence of `listId` to distinguish them.

##### Shape A — with list context (`set_list`-first flow)

Fired when the user clicks **+ Create Direct Mail** after the iframe has a concrete active list context from `set_list` or a selected `set_lists` item. The event is emitted before the iframe opens the create flow, so the parent can pre-create its own Direct Mail Campaign record if needed.

**Fire-and-forget semantics (not a blocking handshake).** This event is a one-way notification. The iframe emits `create_direct_mail_requested` and then IMMEDIATELY opens its create flow using the CURRENT active list context (the `listId` already accepted via `set_list` or selected from `set_lists`). The iframe does NOT pause, await an ack, or wait for any parent response before proceeding into the create flow.

The iframe also does NOT switch `listId` mid-session in response to this event. If PropStream wants the new campaign to use a new or permanent `listId` (for example, promoting a temporary working list to a saved list), it should start a FRESH iframe session — remount the iframe element or reload its `src` — and send a new `set_list` with that id at session start. This matches PropStream's own stated plan ("create a new list_id and pass it in a fresh iframe session"); the same `set_list` value will be honored only at the beginning of a session, not as a live swap on top of an already-open create flow.

If a future integration genuinely needs blocking behavior (iframe waits for a fresh `set_list` from the parent before continuing into the create flow), that is a separate contract change and must be agreed and versioned first — today's contract is notification-only.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "create_direct_mail_requested",
  "listId": "your_list_id",
  "listName": "Pre-Foreclosure Leads",
  "recipientCount": 847,
  "entryPoint": "campaign_home"
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `listId` | string | Active PropStream list id accepted by `set_list`, or selected from `set_lists`. |
| `listName` | string | Active list display name. |
| `recipientCount` | number | Original concrete count supplied by the parent for the active list. |
| `entryPoint` | string | Today the iframe emits ONLY `"campaign_home"`, fired from the Direct Mail dashboard / My Campaigns CTA (this includes the empty-state "create your first direct mail" button). `"products"` is a RESERVED value reflecting a possible future product-page entry point; there is no product-page "Create Direct Mail" CTA in the iframe today, so partner integrators should NOT expect to receive a `"products"` value from the current iframe build. |

This shape is not emitted for demo/default context without a real `set_list` / selected `set_lists` item.

##### Shape B — no list context (dashboard-first flow)

Fired when the user clicks **+ Create Direct Mail** on the Dashboard in **dashboard-first mode** (the iframe was opened with [`open_direct_mail_dashboard`](#open_direct_mail_dashboard--open-the-direct-mail-dashboard-parent--iframe) and no active list context exists yet). The iframe emits the event so the parent can create its own list/record on the backend, then **stays on the Dashboard**. The iframe does **not** open the create flow on its own in this mode — the parent drives the next step by sending `set_list` then [`open_create_direct_mail`](#open_create_direct_mail--open-the-create-direct-mail-flow-optional) (see the [dashboard-first handshake](#dashboard-first-handshake-worked-example) for the full sequence).

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "create_direct_mail_requested",
  "entryPoint": "campaign_home"
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `entryPoint` | string | Same enum as Shape A. Today only `"campaign_home"` is emitted. |

`listId`, `listName`, and `recipientCount` are **omitted from the payload** (not set to `null`) in this shape — there is no active list to echo back. Partners parsing the event should branch on the presence of `listId` to route Shape A vs Shape B.

##### Common to both shapes

This event is not emitted when the parent sends [`open_create_direct_mail`](#open_create_direct_mail--open-the-create-direct-mail-flow-optional); that command remains parent-initiated and either opens the flow or emits [`open_create_direct_mail_failed`](#open_create_direct_mail_failed--create-direct-mail-command-rejected).

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

This terminal event is reserved for explicit cancellation/abandonment actions. Ordinary in-flow **Previous** navigation and **Back to Campaign Home** do not emit it.

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

#### `add_to_marketing_list_requested` — User clicked "Add to Marketing List"

Sent when the user clicks the iframe's **Add to Marketing List** CTA on the RTS Suppression List (campaign-detail view). The event hands the partner-side `contact_id`s for every RTS suppression entry that carries one so PropStream can open its own native marketing-list modal seeded with those contacts.

**Fire-and-forget semantics (not a blocking handshake).** This event is a one-way notification. The iframe emits `add_to_marketing_list_requested` and does NOT pause, await an ack, or wait for any parent response. The iframe takes no further UI action on its own — opening the marketing-list modal is entirely PropStream-side.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "add_to_marketing_list_requested",
  "recipients": [
    { "contact_id": "ps_contact_8821", "contact_type": "PROPERTY" },
    { "contact_id": "ps_contact_4410", "contact_type": "MAILING" }
  ],
  "ballpointCampaignId": "camp_mrx17n8ccqe52ve"
}
```

| Field | Type | Notes |
|-------|------|-------------|
| `source` | string | Always `ballpoint-mailer`. |
| `version` | number | Always `1`. |
| `type` | string | Always `add_to_marketing_list_requested`. |
| `recipients` | array | Non-empty list of suppression entries the user is forwarding to the marketing list. Order mirrors the suppression list view. |
| `recipients[].contact_id` | string | Partner-supplied opaque contact identifier echoed verbatim from the original recipient upload (the same value PropStream uploaded and that the `GET /v1/campaigns/{campaign_id}/mail-tracking/rts` suppression endpoint surfaces, documented in v1.7.1). |
| `recipients[].contact_type` | string \| null | `"PROPERTY"` or `"MAILING"` when the partner supplied it; `null` when no address-type was supplied. Disambiguates two pieces sharing the same `contact_id`. |
| `ballpointCampaignId` | string \| null | The **persisted cross-system campaign id** — the value the iframe originally emitted as `campaign_created.campaignId` and that Ballpoint stores as `external_campaign_id` on each order (round-tripped on `GET /orders`). This is **not** the PropStream `listId`, and it is **not** the Ballpoint-internal API `campaign_id` (the list-derived grouping id used in Ballpoint campaign endpoints such as `GET /v1/campaigns/{campaign_id}/mail-tracking/rts` — that id is unknown to PropStream and must never appear here). Always present on this event; `null` when the campaign's orders do not share a single persisted `external_campaign_id` (e.g. legacy orders created without one). |

No recipient PII (no `recipient_name` / `recipient_address` / `recipient_city` / `recipient_state` / `recipient_zip`) is included in this event. The parent already owns those values via its own CRM keyed by `(contact_id, contact_type)`.

**Visibility / lifecycle**

- Emitted only in **embed (iframe) mode**. In standalone (non-embedded) mode the CTA is suppressed and this event is not emitted.
- `recipients[]` is **filtered to suppression entries that carry a `contact_id`** — RTS entries without a `contact_id` (e.g. legacy uploads or Ballpoint-direct manifests with no partner key column) are omitted. If no suppression entry carries a `contact_id`, the event is **suppressed entirely** (the iframe does not emit an empty `recipients[]`).
- **Pre-lock behavior:** queued by the iframe until the parent origin lock completes, then delivered only to the locked parent origin. Not broadcast to all allowlisted origins. Identical treatment to [`create_direct_mail_requested`](#create_direct_mail_requested--user-clicked-create-direct-mail).
- The iframe does not call any Ballpoint API in response to this click — the contact ids are already in the iframe's RTS suppression view and are simply forwarded to the parent.

**Expected PropStream behavior**

1. Listen for `add_to_marketing_list_requested`.
2. Open your native marketing-list modal seeded with the supplied `recipients[]`, resolving each entry to a CRM contact by `(contact_id, contact_type)`.
3. No reply postMessage is required. The iframe does not wait for one.

#### `auto_suppress_next_drop_changed` — User changed the next-drop auto-suppress preference

Sent when the user checks or unchecks **Auto-suppress on next drop** in the RTS Suppression List. This is a PropStream-only, fire-and-forget preference intent. It tells the parent what the user selected; it does not perform suppression inside the iframe.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "auto_suppress_next_drop_changed",
  "enabled": true,
  "ballpointCampaignId": "cmp_abc"
}
```

| Field | Type | Notes |
|-------|------|-------|
| `source` | string | Always `ballpoint-mailer`. |
| `version` | number | Always `1`. |
| `type` | string | Always `auto_suppress_next_drop_changed`. |
| `enabled` | boolean | `true` when checked; `false` when unchecked. |
| `ballpointCampaignId` | string | Non-empty server-side Ballpoint campaign id for the suppression-list view. Never a PropStream list id and never `null` on this event. |

The event contains no recipients, contact identifiers, recipient PII, counts, prices, order ids, request id, or acknowledgement fields. The iframe does not choose which future order is the "next drop," call a recipient-update endpoint, or update any displayed count/price in response to the click.

**Visibility and state**

- The checkbox is rendered only for an allowlisted **PropStream** parent origin. It is absent in standalone/demo mode and other partner embeds.
- The checkbox is rendered only when the iframe can resolve a non-empty `ballpointCampaignId` from the active campaign detail.
- The iframe remembers a successfully emitted choice only for the lifetime of the current iframe document so ordinary detail re-renders do not visually undo the click. Reloading the iframe resets that visual state in v1.7.11; there is no hydration message in this contract.
- The event is delivered only to the origin-locked parent. It is queued until that lock exists and is never added to the pre-lock broadcast allowlist.
- Fire-and-forget: no parent acknowledgement, retry, replay, or optimistic count/pricing update is defined.

**Expected PropStream behavior**

1. Listen for `auto_suppress_next_drop_changed` and persist the boolean preference against the supplied `ballpointCampaignId` (or the corresponding campaign record on the PropStream side).
2. When the next drop becomes applicable, determine the target order and suppression set using PropStream's own campaign/contact context.
3. Apply the recipient change through the existing Ballpoint recipient-update API flow; this event does not introduce a new Ballpoint endpoint.
4. After the authoritative recipient update succeeds, send the existing [`recipients_updated`](#recipients_updated--partner-finished-editing-recipients) message. The iframe then performs its existing campaign-history refresh.
5. No reply is required for the checkbox click itself. Before production rollout, Ballpoint and PropStream must confirm whether a future hydration contract is needed to restore the checkbox after iframe reload.

#### `recipient_opt_out_changed` — User toggled Opt Out on a recipient row

Sent when the user clicks the iframe's **Opt Out** control on a recipient row (either opting them out, `opted_out: true`, or undoing a previous opt-out, `opted_out: false`). The event hands the partner-side `contact_id`s for every piece at the affected address so PropStream can mirror the suppression state in its own CRM.

**Fire-and-forget semantics (not a blocking handshake).** This event is a one-way notification. The iframe emits `recipient_opt_out_changed` and does NOT pause, await an ack, or wait for any parent response. The server-side opt-out has already been applied (via `POST /v1/mail-tracking/recipients/opt-out` or `DELETE /v1/mail-tracking/recipients/opt-out`) before the event is emitted; the parent takes whatever CRM action it wants and the iframe takes no further UI action.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "recipient_opt_out_changed",
  "opted_out": true,
  "recipients": [
    { "contact_id": "ps_contact_8821", "contact_type": "PROPERTY" }
  ]
}
```

| Field | Type | Notes |
|-------|------|-------------|
| `source` | string | Always `ballpoint-mailer`. |
| `version` | number | Always `1`. |
| `type` | string | Always `recipient_opt_out_changed`. |
| `opted_out` | boolean | `true` when the user just opted the recipient out; `false` when the user undid a previous opt-out. |
| `recipients` | array | Non-empty list of distinct partner contacts at the affected address. |
| `recipients[].contact_id` | string | Partner-supplied opaque contact identifier echoed verbatim from the original recipient upload (the same value PropStream uploaded and that the suppression / RTS endpoints surface). |
| `recipients[].contact_type` | string \| null | `"PROPERTY"` or `"MAILING"` when the partner supplied it; `null` when no address-type was supplied. Disambiguates two pieces sharing the same `contact_id`. |

No recipient PII (no `recipient_name` / `recipient_address` / `recipient_city` / `recipient_state` / `recipient_zip`) is included in this event. The parent already owns those values via its own CRM keyed by `(contact_id, contact_type)`.

**Suppression is tenant-wide and address-level, not user- or campaign-scoped.** The server matches the target row by normalized address (case-insensitive `address`/`city`/`state` + first 5 digits of `zip`) across every campaign the tenant owns, and the opt-out flag is written to **every** piece_tracking row at that address for the tenant. Consequently, `recipients[]` lists **all distinct `contact_id`s** the tenant has ever mailed to that address across their campaigns — not just the piece the user clicked and not just the current campaign. The parent should mirror the suppression state at the same scope on its side (tenant-scoped, keyed by contact or by address, whichever the partner CRM uses).

**Visibility / lifecycle**

- Emitted only in **embed (iframe) mode**. In standalone (non-embedded) mode the CTA is present but this event is not emitted.
- Emitted on **both directions** — `opted_out: true` when the user opts a recipient out, `opted_out: false` when the user undoes a previous opt-out. The `recipients[]` set is computed identically in both directions (the full tenant-scoped address group).
- `recipients[]` is **filtered to affected pieces that carry a `contact_id`** — pieces without a `contact_id` (e.g. legacy uploads or Ballpoint-direct manifests with no partner key column) are omitted. **If no piece at the address carries a `contact_id`, the event is suppressed entirely** (the iframe does not emit an empty `recipients[]`). The server-side opt-out still applies in that case — it is only the parent-side notification that is skipped. This means `contact_id` on the original recipient upload is what makes the opt-out state round-trip to the partner CRM.
- Emitted on **every user toggle**, including idempotent repeats where the server-side `rows_affected` is `0` (e.g. re-opting-out an already opted-out recipient). The server always returns the full contact set for the address group regardless of `rows_affected`, so the iframe can safely re-emit.
- **Pre-lock behavior:** queued by the iframe until the parent origin lock completes, then delivered only to the locked parent origin. Not broadcast to all allowlisted origins. Identical treatment to [`create_direct_mail_requested`](#create_direct_mail_requested--user-clicked-create-direct-mail).

**Expected PropStream behavior**

1. Listen for `recipient_opt_out_changed`.
2. For each `recipients[]` entry, resolve to a CRM contact by `(contact_id, contact_type)` and mirror the suppression state on your side (`opted_out: true` → mark suppressed; `opted_out: false` → clear suppression).
3. No reply postMessage is required. The iframe does not wait for one.

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
>
> **Do not poll `GET /v1/billing/orders` for individual drops mid-flow (Multi Send / A/B Split).** During scheduling and before `campaign_submitted` fires, the per-drop orders do **not** exist server-side — `campaign_created.orderIds` (and any `order_added.orderId`, see below) are local pre-API ids. Polling `GET /v1/billing/orders` or `GET /v1/billing/orders/{order_id}` for these ids will return nothing / 404 because there is no Ballpoint order yet. Wait for `campaign_submitted` and consume `orders[].ballpointOrderId` as the authoritative server-assigned id. If `orders[].ballpointOrderId` is `null` for a given entry, that drop's submission is pending retry — see the field note in the [`campaign_submitted` table](#campaign_submitted--campaign-submitted-to-ballpoint) below; in that case poll `GET /v1/billing/orders` only **after** `campaign_submitted`, scoped to the campaign / `external_user_id`.

#### `campaign_submitted` — Campaign submitted to Ballpoint

This is the most important event. It confirms the order(s) were sent to Ballpoint for processing. It fires from two paths — the campaigns flow (single / split / multi-send) and the canvas builder (single ad-hoc order). Both emit the same field shape; the canvas builder sets `campaignId: null` because it does not own a multi-order campaign concept on the iframe side.

> **Terminal in a partner embed (v1.6.6).** After this event is emitted, the iframe shows a neutral hand-off ("Opening secure checkout…") and defers final completion to the partner's billing flow — there is no internal "Campaign Submitted!" confirmation page in a partner embed. The campaign is not "submitted/complete" until billing succeeds on the partner side. Event semantics are unchanged: `campaign_submitted` remains the authoritative billing trigger, and partners should continue to key off `orders[].ballpointOrderId` as the server-assigned order id.

> **May be emitted more than once per checkout session (v1.7.8).** In a partner embed, `campaign_submitted` MAY now be re-emitted on repeat **Continue to Payment** clicks from the same Order Summary — for example, if the user closes the partner's Payment Preview modal without completing payment and clicks **Continue to Payment** again. The first emit happens at order creation (unchanged); subsequent emits **replay the identical cached payload** from the first successful emit — same `campaignId`, same `orderIds`, same `ballpointOrderIds`, same `total_tcents` / `total_dollars`, same `orders[]` array. **No new orders are ever created by a re-emit** — the iframe caches the successful first-emit payload and replays it rather than re-submitting to `POST /orders`. The cache is cleared when the user navigates away (starts a new campaign / returns to the Dashboard), so a re-emit will never carry a stale cross-campaign payload.
>
> **Partner MUST treat re-emits as idempotent.** A repeat `campaign_submitted` for the same `campaignId` / `orderIds` should only **reopen the Payment Preview modal** — no re-processing, no duplicate database writes, no duplicate charges, no duplicate analytics events on the partner side. Key idempotency off `orders[].ballpointOrderId` (server-assigned) or `campaignId` (iframe-local, stable across re-emits).
>
> **Do not send [`payment_result: cancelled`](#payment_result--payment-popup-outcome-parent--iframe) on a plain Payment Preview modal close.** Sending `cancelled` routes the iframe to the **Payment Not Completed** result screen and ends the reopen flow — the user is dead-ended on a result screen instead of able to click **Continue to Payment** again. Reserve `cancelled` / `failed` for genuinely abandoned or failed payment outcomes (see the [`payment_result` status semantics table](#payment_result--payment-popup-outcome-parent--iframe)). `cancelled` remains a valid `payment_result.status` value in the existing schema (`status ∈ success | failed | failure | cancelled` is unchanged) — this is guidance narrowing **when** to send it, not a schema change.
>
> **Refetch authoritative amounts on every emit — including re-emits.** The `total_tcents` / `total_dollars` values on re-emitted payloads are **UX/display only** (same rule that has always applied to first-emit payloads). A re-emit could theoretically be stale relative to server-side state, so the partner backend must **always** refetch the authoritative billing amounts before charging via [`POST /v1/billing/campaigns/preview`](API_KIT.md#6a-ii-preview-campaign-cost-payment-gate) (campaign-level, one call — read `campaign_partner_debit_cents` for the exact whole-cent `/confirm-payment` result, plus the raw `campaign_partner_cost_total_tcents` / per-order `partner_cost_total_tcents` tcents for reconciliation). `GET /v1/billing/partner/orders` is a dashboard/read model and is not the authoritative current-price billing source. Never trust the emitted `total_tcents` / `total_dollars` as the billing source of truth, including on re-emits.

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
| `campaignId` | string or null | Iframe-local, **event-stream** id for this Direct Mail instance (stable across a multi-send's drops). Use it to **separate Direct Mail instances** in your UI / event stream. **Do not join it against the backend `campaign_id`** returned by Get/List Orders — they are different ids (see [API_KIT.md Get Orders → ID reconciliation](API_KIT.md#6c-get-order)). For per-order API reconciliation, use `orders[].ballpointOrderId`. `null` when the canvas builder emits a single ad-hoc order. |
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
| `orders[].total_tcents` | number | Marked-up total for this order in tenth-cents. UX/display only for payment-gated partner flows. |
| `orders[].recipientsEndpoint` | string or null | API path to POST recipients (null if pending). |
| `orders[].campaignInstanceId` | string or null | Opaque submit/split instance key. `null` for `single` and `multi` campaigns (no cross-order dedup expected). For `split` campaigns, all sibling orders in the same `campaign_submitted` payload share the same opaque string value — Ballpoint uses this server-side as a guard-rail to enforce disjoint slices across A/B variants (see [Campaign Dedup (automatic)](#campaign-dedup-automatic)). Treat as opaque on the partner side; do not parse, mutate, or echo back. |
| `total_tcents` | number | Marked-up total across all orders, in tenth-cents. UX/display only for payment-gated partner flows. |
| `total_dollars` | string | Same total as a fixed-2 dollar string. **UX/display only.** After `campaign_submitted`, refetch the authoritative Ballpoint debit amount server-side with [`POST /v1/billing/campaigns/preview`](https://github.com/Ballpoint-Marketing/ballpoint-api-docs/blob/main/API_KIT.md#6a-ii-preview-campaign-cost-payment-gate) (campaign-level, one call) and read `campaign_partner_debit_cents` (exact whole-cent ledger debit) plus the raw tcents fields for reconciliation. |
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
>
> **Do not poll `GET /v1/billing/orders` for these per-drop ids mid-flow.** As with `campaign_created.orderIds`, `order_added.orderId` is a **local pre-API id** — the drop does not exist server-side until `campaign_submitted` fires. Polling `GET /v1/billing/orders` (or `GET /v1/billing/orders/{order_id}`) against this id mid-flow will not find it. Wait for `campaign_submitted` and reconcile via the matching `orders[].ballpointOrderId`; if that field is `null` for a drop, see the pending-retry caveat in the [`campaign_submitted` field note](#campaign_submitted--campaign-submitted-to-ballpoint) and only poll `GET /v1/billing/orders` **after** submission.

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
- The Ballpoint webhook (`order.rescheduled`) carries `previous_mail_date` / `new_mail_date` (`YYYY-MM-DD` strings) — see `API_KIT.md §7`. It does **NOT** carry `previous_scheduled_production_date` / `new_scheduled_production_date`; those are returned only in the synchronous reschedule API response (`API_KIT.md §6m`). The iframe postMessage intentionally omits all of these mail/production-date fields (the parent app rarely needs them directly; if you do, consume the webhook or the API response).

**How to Test.** The order must be in `scheduled` status and **unbilled** (`payment_confirmed = false`). Open it on the Campaign Detail page, click **Reschedule**, pick a new mail date, and Save — you'll receive one `order_rescheduled` (suppressed if the date is unchanged). Paid (`payment_confirmed = true`), `accepted`, `prep`, in-production, and terminal orders do **not** offer Reschedule.

**Blocked attempts.** Paid rows (`payment_confirmed = true`) show a locked note in place of the Reschedule button; `accepted` / `prep` / in-production / terminal rows simply do not render a Reschedule button. If a reschedule is submitted on an order the backend no longer permits (e.g. it advanced or was paid after the row rendered → `409 PAID_LOCKED` / `SEND_NOW_PROCESSING` / `IN_PRODUCTION`, see `API_KIT.md §6m`), the iframe surfaces a **"Can't Modify Order"** modal and emits **no** `order_rescheduled`.

#### `payment_retry_requested` — User clicked "Try Again" on the failure screen

> **Current staging contract — pending PropStream wiring.** Companion to the parent → iframe [`payment_result`](#payment_result--payment-popup-outcome-parent--iframe) message. The iframe expects the parent (PropStream) to listen for this event and **reopen its payment popup** for the same campaign / order. PropStream's handler is not yet wired — this section documents what the iframe emits today on staging.

Emitted when the user clicks **Try Again** on the iframe's in-iframe **Payment Failed** screen in partner-embedded mode. The iframe is asking the parent to reopen the payment popup so the user can retry the charge.

```json
{
  "source": "ballpoint-mailer",
  "version": 1,
  "type": "payment_retry_requested",
  "campaignId": "camp_abc123",
  "ballpointCampaignId": "cmp_abc",
  "orderIds": ["ord_local_001"],
  "ballpointOrderIds": ["ord_abc123"],
  "reason": "card_declined"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Always `"ballpoint-mailer"`. |
| `version` | number | Always `1`. |
| `type` | string | Always `"payment_retry_requested"`. |
| `campaignId` | string or omitted | Iframe-local campaign handle, echoed back **only if it was provided on the original `payment_result`**. The iframe does **not** fall back to a prior `campaign_submitted` value. Omitted when `payment_result` did not carry it. |
| `ballpointCampaignId` | string or omitted | Server-side campaign id, echoed back **only if it was provided on the original `payment_result`**. Omitted otherwise. |
| `orderIds` | array of strings or omitted | Iframe-local order ids, echoed back **only if provided on the original `payment_result`**. Omitted otherwise. |
| `ballpointOrderIds` | array of strings or omitted | Server-side `ballpointOrderId` values, echoed back **only if provided on the original `payment_result`**. Omitted otherwise. |
| `reason` | string or omitted | The `reason` carried on the original `payment_result` (e.g. card-decline reason; trimmed and capped to 300 chars by the iframe), echoed back so the parent's payment popup can prefill / surface the previous failure context. Omitted otherwise. |

**No duplicate orders.** This event is a UI-level request to the parent to reopen its payment popup. The iframe does **not** call `POST /orders`, does **not** create or clone a Ballpoint order, and does **not** call `/confirm-payment` in response to the Try Again click. The retry of the underlying charge is entirely owned by the partner. The `ballpointOrderIds` / `campaignId` echoed in this payload reference the **existing** Ballpoint order/campaign from the original submission — the same ids the parent already debited (or attempted to debit) against.

**Expected PropStream behavior**

1. Listen for `payment_retry_requested`.
2. Reopen the payment popup for the campaign / order referenced by the echoed ids.
3. When the popup resolves again, send a fresh [`payment_result`](#payment_result--payment-popup-outcome-parent--iframe) back to the iframe with the new outcome.

**Standalone mode.** In standalone (non-embedded) mode, the failure screen's Try Again action stays internal — `payment_retry_requested` is not emitted because there is no parent to receive it.

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
5. iframe calls `POST /orders` on the API base URL with the selected `postage_type`. Ballpoint persists that exact class and records a creation-time price **estimate** for payment-gated accounts (the wholesale debit is resolved against the current pricing tier at `/confirm-payment`; refetch `POST /v1/billing/campaigns/preview` before charging); only legacy requests that omit the field default to `first_class`. The order is created in `pending_payment` (send-now) or `scheduled` with `payment_confirmed=false` (future-dated). No charge occurs yet.
6. iframe emits `campaign_submitted` to the parent (carries `orders[].ballpointOrderId` and `total_dollars` for UX). This triggers the backend handoff; it is not authorization to collect payment yet.
7. Parent backend waits until every `campaign_submitted.orders[].ballpointOrderId` is non-null, then uploads the matching recipients to every order with `POST /v1/billing/orders/{order_id}/recipients`. For A/B Split, upload a different address-disjoint slice to each variant. Verify every upload reports `ready === true` and `piece_count > 0`.
8. Parent backend calls [`POST /v1/billing/campaigns/preview`](https://github.com/Ballpoint-Marketing/ballpoint-api-docs/blob/main/API_KIT.md#6a-ii-preview-campaign-cost-payment-gate) **once** with the `ballpointOrderId`s it intends to charge in this payment event (the endpoint prices exactly the caller-selected set; it does not compute billing windows). Read `campaign_partner_debit_cents` as the exact whole-cent ledger amount recorded on successful confirmation, with the raw tcents fields available for reconciliation. Call `/confirm-payment` only for response rows where `excluded_from_totals=false`; do not confirm rows excluded from the quoted total. Re-preview after any order/recipient edit before collecting or confirming payment. The legacy per-order `POST /v1/billing/orders/preview` loop is no longer required for this step. `total_dollars` from the iframe is UX/display only and must not be used as the billing source of truth.
9. Parent shows the payment popup; end-user pays via the parent's payment provider.
10. Parent backend calls `POST /v1/billing/orders/{order_id}/confirm-payment` with `status: success` (or `failed`).
11. On success, Ballpoint applies the account billing policy (stripe debits balance; manual records usage; none records no charge/usage) and moves the order to `accepted`. Production proceeds.

**Postage label mapping:** Hybrid Letter and Greeting Letter display
**Standard Class** to the end user but submit `postage_type: "presort"` to the
API. This is a display label only. `standard` remains a separate API value for
supported postcards and Color Letter.

**Color Letter V1 print options:** the 8.5x11 insert is full color, one sheet,
one-sided, and tri-folded to fit the #10 envelope. The iframe does not expose a
black-and-white selector; the end user chooses only between Standard Class and
First Class postage.

**Important distinction.** After `campaign_submitted`, the iframe lifecycle and payment lifecycle are separate. The iframe may emit `campaign_complete` / `done` once the iframe submission flow finishes, independent of the payment popup. That does not mean production is complete and does not replace `/confirm-payment`. Production status continues separately through `order.status_changed` webhooks (`accepted` → `prep` → ... → `complete`).

For payment, reconciliation, or backend workflows, key off `campaign_submitted.orders[].ballpointOrderId` — not `campaign_created.orderIds` (those are pre-API local IDs). Equivalently: **don't poll `GET /v1/billing/orders` mid-flow** to discover per-drop ids for Multi Send or A/B Split; orders only exist server-side after Continue to Payment fires `campaign_submitted`. See the [`campaign_created`](#campaign_created--campaign-created-before-submission) and [`order_added`](#order_added--new-order-added-multi-month-campaigns) timing notes for details.

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

Cross-order dedup is a server-side safety net, not a substitute for constructing the A/B split. The partner must upload address-disjoint slices and inspect `accepted`, `rejected`, `rejected_details`, `ready`, and `piece_count` on every response. Do not proceed to preview or payment unless every variant reports `ready === true` and `piece_count > 0`. If every submitted address for a variant overlaps a sibling, the API rejects those rows as `duplicate_in_campaign`, the variant may end at `piece_count: 0`, and billing endpoints return `409 INVALID_PIECE_COUNT` until the recipient slice is corrected. For same-order (intra-payload) duplicates, see below.

Once the initial POST has reduced an order to zero, a positive retry on that same endpoint exceeds the order's current piece count. Recover an eligible gated, unconfirmed order with the Edit Leads `PATCH /v1/billing/orders/{order_id}/recipients` using a verified address-disjoint replacement slice, or cancel and recreate the order. The PATCH does not perform cross-order A/B dedup, so slice correctness remains the partner's responsibility. If you recover by cancelling, drop the cancelled order's id from every later `POST /v1/billing/campaigns/preview` call — a cancelled order that is still at `piece_count: 0` keeps returning `409 INVALID_PIECE_COUNT` for the whole preview; pass only the ids of the orders you intend to charge (the recreated submission's `campaign_submitted.orders[]`).

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
| `zip` | string | 10 | Sender ZIP: 5 digits, 9 digits, or ZIP+4. Invalid values leave the sender profile incomplete. |
| `phone` | string | 20 | Sender phone: 10 digits, or 11 beginning with `1`; standard formatting is accepted. Invalid values leave the sender profile incomplete. |
| `website` | string | 200 | Sender website |

> **Important:** The API token (`apiToken`) must **never** be passed as a URL parameter. It must always be sent via `postMessage` using `set_api_config`. URLs are visible in browser history, Referer headers, and server logs.

---

## 9. Security Notes

- **Origin validation:** The iframe only accepts `postMessage` from allowlisted parent origins. Contact Ballpoint to add your domain to the allowlist.
- **Token delivery:** `apiToken` is only accepted via `postMessage`, never via URL params.
- **State reconciliation:** `set_tenant` establishes the tenant scope and cannot switch it later in the iframe session. The first `set_sender` for a load/tenant is a fresh snapshot; later same-scope `set_sender` messages are patches where omitted fields are preserved and explicitly empty fields are cleared. `set_api_config` can be resent to refresh the token. `set_list` may be resent with the SAME `listId` to refresh `count` / `name` / `piece_counts` after PropStream's Edit Leads modal saves (see [`set_list` refresh](#set_list-refresh-post-modal-sync)); a different `listId` is still rejected as a list-switch attempt.
- **Rate limiting:** The iframe processes at most 20 PropStream protocol attempts per 5 seconds for each loaded iframe document. Unrelated parent messages outside the PropStream envelope do not consume this protocol allowance; malformed or unsupported PropStream attempts are still rate-limited. An intentional iframe reload or remount creates a new document and starts a fresh rate window. Continue to send each bootstrap message once per `ready` event rather than using the reset to create bursts.
- **CSP:** The iframe is served with a strict Content Security Policy. Your domain must be listed in the `frame-ancestors` directive. Contact Ballpoint if you receive CSP errors.

---

## 10. Troubleshooting

### "Classic templates unavailable (API not configured)"

**Cause:** `set_api_config` was not sent, or the `apiToken` value is empty/invalid.

**Fix:** Ensure the parent sends `set_api_config` with a valid `apiBaseUrl` and `apiToken` before the user reaches the product selection page. The iframe queues actions until config arrives, but the Classic tab requires a configured API client to fetch templates. Verify the token is a valid `pk_...` key and that `apiBaseUrl` points to the correct [environment](#3-environments).

### "Please contact your account owner to set up sender information"

**Cause:** The iframe is embedded, sender information is incomplete, and the effective `externalUserIsAccountOwner` value is missing or `false`. The message appears on the Sender Information step. The Direct Mail Dashboard hides the Sender Information card for that non-owner in every sender state.

**Fix:** Send a complete [`set_sender`](#set_sender--pre-fill-sender-info-optional) if the Marketing Profile is already complete. Otherwise provide strict boolean `externalUserIsAccountOwner: true` in `set_sender` during Dashboard-first bootstrap or in [`set_list`](#set_list--recipient-list-info-required) once list context exists, so the user can request setup/edit through [`sender_setup_requested`](#sender_setup_requested--user-requested-sender-info-setup). A partial `set_sender` intentionally keeps setup required; after singular `set_list` is accepted, its owner value is authoritative. See [Sender-info setup gate](#sender-info-setup-gate-externaluserisaccountowner) for full details.

---

## Support

For iframe access, environment keys, and technical support, reach out to your partner technical contact at Ballpoint.

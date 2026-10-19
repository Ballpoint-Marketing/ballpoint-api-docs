# Ballpoint API — Your First Complete Staging Order

Use this walkthrough for a **backend-to-backend integration** after Ballpoint has enabled your staging account. It submits a two-recipient 4×6 printed postcard with sample artwork, uploads the mailing list, reads the order and checks delivery of a signed status notification.

**Staging only.** The included names, addresses and artwork are fictional test data. Nothing is printed or mailed on staging. Keep the staging host below: a key prefix alone does not turn production into a test environment. This walkthrough does not approve a product, postal layout or account for live fulfillment.

For an embedded editor, use the [Iframe Kit](IFRAME_KIT.md). For print-ready PDF jobs, use [API Kit §6t](API_KIT.md#6t-print-jobs-print-ready-pdfs); those credentials do not necessarily authorize the order flow below.

## 1. Get the integration prerequisites

Ballpoint supplies the following during onboarding:

- A staging **server key**, kept only on your backend. For the assisted API-orders profile, Ballpoint provisions `read`, `orders:write`, `recipients:write` and `tracking:read` after confirming that this profile is deployed in staging.
- A separate staging account for your company, configured by Ballpoint with the agreed product, base prices and spending limits. Account and key creation are assisted; this guide does not provide self-service signup.
- Access to each operation in the table below, including `recipients:write`. Possessing a server key does not by itself guarantee access to every route.
- A registered HTTPS webhook endpoint for your account and its own signing secret, when you reach step 7.

| Operation | Route |
|---|---|
| Check credentials and quote | `POST /v1/billing/orders/preview` |
| Create order including artwork | `POST /orders` |
| Upload the mailing list | `POST /v1/billing/orders/{order_id}/recipients` |
| Read order and render status | `GET /v1/billing/orders/{order_id}` |
| Read USPS tracking, when available | `GET /v1/orders/{order_id}/mail-tracking` |

For this first walkthrough, ask Ballpoint to confirm a staging profile **without partner-side payment confirmation**. If your integration collects payment itself, use the [payment-gated flow](API_KIT.md#6k-confirm-payment-partner-payment-gate) after recipient upload. An order waiting for payment is not ready for fulfillment.

A `403 INSUFFICIENT_SCOPE` with `required_scope: null` means the route is unavailable to that key. Give Ballpoint the method, route and trace ID; access must be configured before continuing. Do not substitute an embed key or another customer's key.

## 2. Prepare one test run

Requirements: Bash (including WSL), curl 7.76+ (`--fail-with-body`), jq and Python 3. Download or clone this repository, then run the commands **from its root**.

```bash
set -euo pipefail
umask 077
export BALLPOINT_BASE='https://staging-api.ballpointmarketing.com'
read -r -s -p 'Staging server key: ' BALLPOINT_API_KEY
printf '\n'
export BALLPOINT_API_KEY

FIXTURE_DIR="$PWD/examples/api-onboarding"
RUN_DIR="$(mktemp -d)"
printf 'Keep this run directory for retries: %s\n' "$RUN_DIR"
cd "$RUN_DIR"

python3 -c 'import uuid; print(uuid.uuid4())' > create-key.txt
python3 -c 'import uuid; print(uuid.uuid4())' > recipients-key.txt
cp "$FIXTURE_DIR/order.json" order-template.json
cp "$FIXTURE_DIR/preview.json" preview-request.json
cp "$FIXTURE_DIR/recipients.json" recipients-request.json
```

Keep this shell open. To resume after closing it, re-enter your staging key and base URL, then `cd` to the printed run directory. Reuse its request and key files. **Create a new run directory only for an intentionally new order.**

## 3. Verify access and inspect the price

This authenticated, read-only preview validates the key's access to the quote operation. It does not create an order. `GET /health` checks service availability only; it does not verify a key.

```bash
curl --fail-with-body --silent --show-error \
  -D preview-headers.txt -o preview-response.json \
  -X POST "$BALLPOINT_BASE/v1/billing/orders/preview" \
  -H "X-Partner-Key: $BALLPOINT_API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @preview-request.json
jq . preview-response.json
jq -e '.product_type == "4x6_printed" and .postage_type == "first_class"
  and .piece_count == 2 and .limits.passed == true
  and has("unit_price_tcents") and has("total_tcents")' preview-response.json
```

Expected: HTTP **200**, a quote for two pieces, and `limits.passed: true`. Review the price against the terms supplied by Ballpoint. Prices expressed in `tcents` use 10,000 units per dollar. The primary fields are display prices; `partner_cost_*` fields are the Ballpoint base cost. Do not hardcode a price or infer weekly card charging from `billing_mode`.

For new accounts explicitly enabled on the standard API price profile, the base unit price is flat at every quantity; volume discounts are not enabled. Existing integrations retain their agreed pricing. This profile is pending deployment and account setup; Ballpoint must confirm availability before you use it. The preview for your own account is the source of truth, not another integration's price table.

Build the exact creation request **once**, preserving both the quote and a unique reference:

```bash
RUN_REF="onboarding-$(cat create-key.txt)"
jq --arg ref "$RUN_REF" --slurpfile quote preview-response.json \
  '.external_id = $ref | .list_id = $ref
   | .expected_retail_unit_price_tcents = $quote[0].unit_price_tcents
   | .expected_retail_total_price_tcents = $quote[0].total_tcents' \
  order-template.json > order-request.json
```

The [order fixture](examples/api-onboarding/order.json) includes sender details, two-sided Fabric canvas artwork, `postcard_size`, product, postage and `pieces: 2`. The [recipient fixture](examples/api-onboarding/recipients.json) supplies exactly two addresses. The sample does not draw a fake address or postage block; Ballpoint adds the postal layer.

For your own design, replace the sample artwork and agree the postal layout with Ballpoint before a live order. A plain `message` field does not replace missing canvas artwork for this printed-card workflow.

## 4. Create the order

```bash
curl --fail-with-body --silent --show-error \
  -D create-headers.txt -o create-response.json \
  -X POST "$BALLPOINT_BASE/orders" \
  -H "X-Partner-Key: $BALLPOINT_API_KEY" \
  -H "Idempotency-Key: $(cat create-key.txt)" \
  -H 'Content-Type: application/json' \
  --data-binary @order-request.json
jq . create-response.json
ORDER_ID="$(jq -er '.id | select(type == "string" and startswith("ord_"))' create-response.json)"
printf '%s\n' "$ORDER_ID" > order-id.txt
```

Expected: HTTP **200**, with the order identifier in **`id`**. For the agreed non-payment-gated profile, with no scheduled mail date, the initial `status` is `accepted`. If it is `pending_payment`, confirm the account's payment flow with Ballpoint; do not report it as ready to fulfill.

Ballpoint derives the campaign from your account and `list_id` and creates it when needed. A separate dashboard campaign-creation step is not required for this route. Use a stable list ID for orders you intentionally want grouped.

**Retry proof:** run only the creation `curl` again with the saved `create-key.txt` and identical `order-request.json`. Within the idempotency retention window, a completed replay returns the same order ID. Compare it with `order-id.txt`. A lost response is not a reason to generate a new key.

There is also a valid `POST /v1/billing/orders` route with a different request and a **202** response containing **`order_id`**. This walkthrough uses `POST /orders` so the request can carry artwork and sender details. Keep these request and response formats separate.

## 5. Upload all recipients

If resuming, load `ORDER_ID="$(cat order-id.txt)"` first.

```bash
curl --fail-with-body --silent --show-error \
  -D recipients-headers.txt -o recipients-response.json \
  -X POST "$BALLPOINT_BASE/v1/billing/orders/$ORDER_ID/recipients" \
  -H "X-Partner-Key: $BALLPOINT_API_KEY" \
  -H "Idempotency-Key: $(cat recipients-key.txt)" \
  -H 'Content-Type: application/json' \
  --data-binary @recipients-request.json
jq . recipients-response.json
jq -e --arg id "$ORDER_ID" '.order_id == $id and .accepted == 2
  and .rejected == 0 and .total_recipients == 2
  and .piece_count == 2 and .ready == true' recipients-response.json
```

Expected: HTTP **200** and every assertion above passes. An HTTP 200 alone is insufficient: individual rows can be rejected. Inspect `rejected_details` if the counts differ.

Here `append: false` replaces the list. Do not send a second replacement with a new key merely because a response was lost. Retry the saved upload with its original key and identical body; it returns the original receipt. Keep create and upload keys separate. For larger lists, use the [chunking and retry contract](API_KIT.md#6n-upload-recipients-initial-upload).

**`ready: true` means the recipient count matches the order.** For this canvas-backed order it also allows rendering to be queued; it does not mean the PDFs are finished, payment is confirmed or mail has been sent.

## 6. Read the order and check rendering

```bash
curl --fail-with-body --silent --show-error \
  -D order-headers.txt -o order-response.json \
  "$BALLPOINT_BASE/v1/billing/orders/$ORDER_ID" \
  -H "X-Partner-Key: $BALLPOINT_API_KEY"
jq '{id, piece_count, production_status, display_status, render_status,
     payment_confirmed}' order-response.json
jq -e --arg id "$ORDER_ID" '.id == $id and .piece_count == 2' order-response.json
```

Expected: HTTP **200** and the same order ID and piece count. Rendering is asynchronous: repeat this read later rather than submitting another order. `render_status: complete` means rendering finished. If it remains pending or fails, give Ballpoint the order and trace IDs so the render job can be checked.

Ballpoint operations must inspect the generated front/back PDFs for the two recipients: content and personalization, sender, addresses, postal areas and page count. That inspection is the proof of usable output; acceptance of the request alone is not.

`production_status` describes fulfillment, `render_status` describes file generation, and `display_status` is the combined customer-facing status. Staging has no physical fulfillment or real USPS scans. Do not wait for this order to arrive in the mail.

Optional tracking read, once the key has permission:

```bash
curl --fail-with-body --silent --show-error \
  "$BALLPOINT_BASE/v1/orders/$ORDER_ID/mail-tracking" \
  -H "X-Partner-Key: $BALLPOINT_API_KEY"
```

Treat staging tracking as an API response-shape check. Empty tracking or a display label is not evidence of mailing or delivery.

## 7. Receive and verify one signed notification

Give Ballpoint your HTTPS receiver URL. Ballpoint registers it for your account and supplies a per-endpoint signing secret. Webhook registration and test-event triggering are assisted onboarding steps today.

Start with the [receiver examples](README.md#examples) and the [signature and processing contract](API_KIT.md#7-status-updates-via-webhooks). Before accepting any event:

1. Require the configured secret, signature, timestamp and event ID.
2. Verify HMAC-SHA256 over **timestamp + exact raw body bytes**, before parsing or modifying the JSON.
3. Reject bad signatures, timestamps older than five minutes or more than two minutes in the future. Treat `X-Ballpoint-Insecure: true` as unauthenticated.
4. Store/deduplicate `X-Ballpoint-Event-Id` durably before business effects; handle delivery retries without applying the event twice. `X-Ballpoint-Delivery` changes per attempt.
5. Acknowledge accepted events quickly and process queued work asynchronously.

Ask Ballpoint to trigger a signed staging event for the order. Record the order ID, event ID and verification result. Demonstrate a successful event, a duplicate with no second business effect, and rejection of a tampered payload. Label simulated production/USPS statuses as test events; they do not prove physical mailing.

## 8. Decide whether the integration test is complete

- [ ] Authenticated preview matches the selected product, count and agreed price.
- [ ] Create returns an order ID; an identical retry returns that same ID.
- [ ] Recipient upload accepts two, rejects zero and reports a complete list.
- [ ] An upload retry preserves the result without adding recipients.
- [ ] The order read agrees with the request; rendering completes and Ballpoint checks both recipients' print output.
- [ ] A signed test event is verified; duplicates and tampered events are handled correctly.
- [ ] Ballpoint and the partner verify isolation using designated test accounts: a key for another account cannot read this order. Never use another customer's credentials.
- [ ] Any account access, payment, render or webhook blocker is recorded explicitly.

A local mock or sample response validates your client logic; it does **not** satisfy the staging or print-output checks. Keep the request/response evidence and IDs, excluding keys, webhook secrets and personal data.

Go-live is a separate approval with live credentials, product/pricing confirmation, artwork/production validation and the agreed billing setup. Do not point this fictional sample at production.

## Troubleshooting

| Result | Next step |
|---|---|
| `401` | Check the server key and staging host with Ballpoint. |
| `403 INSUFFICIENT_SCOPE` | Request the missing operation; `required_scope: null` means that route is unavailable to this key. |
| `400 NO_PRICING` or failed preview limits | Confirm product/postage, account pricing and limits. Do not proceed with a guessed price. |
| `409 PRICE_QUOTE_STALE` | The quote changed before creation. Review a fresh quote and follow the error contract before rebuilding the request; do not treat it as a network retry. |
| `409 IDEMPOTENCY_KEY_IN_PROGRESS` | Wait the indicated `Retry-After`, then retry the exact request with the same key. |
| `422 IDEMPOTENCY_KEY_REUSE` | The key was reused with a changed body. Recover the saved request; do not blindly create another order. |
| Recipient `rejected > 0` or `ready: false` | Inspect row errors and counts; coordinate correction before proceeding. |
| `404 ORDER_NOT_FOUND` | Confirm ID, environment and account. Cross-account and missing orders both return 404. |
| `429`, transient `5xx` or lost response | Follow [retry guidance](API_KIT.md#retry-strategy), respecting `Retry-After` where present and preserving key/body. After receipt retention expires, reconcile before resubmitting. |

For support, share method/path, HTTP status, error code, trace ID and order ID when available. Never send the API key or signing secret in an error report.

## Reference material

[API Kit](API_KIT.md) · [OpenAPI](docs/ballpoint-api-spec-v2.yaml) · [Postman collection](examples/ballpoint.postman_collection.json) · [Webhook schemas and fixtures](contracts/webhooks/README.md)

The general Postman collection is an endpoint reference. Several requests require pre-existing IDs and its tolerant example checks are not a substitute for the ordered acceptance checks above.

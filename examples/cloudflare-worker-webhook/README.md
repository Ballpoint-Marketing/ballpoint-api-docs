# Ballpoint Webhook Receiver — Cloudflare Worker

Minimal Cloudflare Worker that receives Ballpoint webhook events, verifies
the HMAC-SHA256 signature using the Web Crypto API, and rejects stale/replayed
requests.

## Webhook Contract

```
Required headers:
  X-Ballpoint-Signature: sha256=<hex>
  X-Ballpoint-Timestamp: 2026-03-01T01:23:45Z (ISO 8601)
  X-Ballpoint-Event-Id: evt_...

Signature base string:
  HMAC-SHA256(secret, timestamp + raw_body)  — no delimiter

Validation checklist:
  ✓ Verify signature (constant-time comparison)
  ✓ Reject timestamps older than 5 minutes
  ✓ Reject timestamps more than 2 minutes in the future
  ✓ Reject duplicate event IDs (store with TTL)
  ✓ Return 2xx quickly — do heavy processing async
```

## Setup

### 1. Create the worker

```bash
npx wrangler init ballpoint-webhook
# Choose "Hello World" worker → ES module syntax
```

Replace the generated `src/index.js` with `worker.js` from this directory.

### 2. Set the webhook secret

```bash
npx wrangler secret put WEBHOOK_SECRET
# Paste your webhook secret (whsec_...) when prompted
```

### 3. Deploy

```bash
npx wrangler deploy
```

Your webhook URL will look like:

```
https://ballpoint-webhook.YOUR_SUBDOMAIN.workers.dev
```

### 4. Give Ballpoint your endpoint URL

Share the URL with Ballpoint and we'll configure webhook delivery.

## Testing

```bash
# Generate a test signature
SECRET="whsec_test"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BODY='{"type":"order.status_changed","data":{"order_id":"ord_test","display_status":"printing"}}'
SIG=$(echo -n "${TIMESTAMP}${BODY}" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

# Call your worker
curl -X POST https://ballpoint-webhook.YOUR_SUBDOMAIN.workers.dev \
  -H "Content-Type: application/json" \
  -H "X-Ballpoint-Signature: sha256=$SIG" \
  -H "X-Ballpoint-Timestamp: $TIMESTAMP" \
  -H "X-Ballpoint-Event-Id: evt_test_001" \
  -d "$BODY"
```

## How Signature Verification Works

1. Concatenate the timestamp header + raw request body (no delimiter)
2. HMAC-SHA256 with your webhook secret (using Web Crypto API)
3. Compare to the `X-Ballpoint-Signature` header (after stripping `sha256=` prefix)
4. Constant-length comparison to prevent timing attacks

See **Webhook Contract** above for the full validation checklist (timestamp window, deduplication, etc.).

## Notes

- Uses the Web Crypto API (`crypto.subtle`) instead of Node.js `crypto` module
- Request body is read once with `request.text()` — Workers can only consume the body once
- The worker uses ES module syntax (`export default`) — ensure your `wrangler.toml` uses `type = "module"`

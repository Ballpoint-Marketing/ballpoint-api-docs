# Ballpoint Webhook Receiver — AWS Lambda

Minimal AWS Lambda function that receives Ballpoint webhook events, verifies
the HMAC-SHA256 signature, and rejects stale/replayed requests.

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

### API Gateway Raw Body

Verify signatures against the exact raw body bytes. If your API Gateway integration sets `isBase64Encoded: true`, decode the body before verifying. The handler does this automatically — see `handler.js` lines 29-34.

## Setup

### 1. Create the Lambda function

```bash
# Zip the handler
zip handler.zip handler.js

# Create the function
aws lambda create-function \
  --function-name ballpoint-webhook \
  --runtime nodejs20.x \
  --handler handler.handler \
  --zip-file fileb://handler.zip \
  --role arn:aws:iam::YOUR_ACCOUNT:role/YOUR_LAMBDA_ROLE
```

### 2. Set the webhook secret

```bash
aws lambda update-function-configuration \
  --function-name ballpoint-webhook \
  --environment "Variables={WEBHOOK_SECRET=whsec_your_secret_here}"
```

### 3. Add an API Gateway trigger

**Option A — HTTP API (recommended):**

```bash
aws apigatewayv2 create-api \
  --name ballpoint-webhook \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:YOUR_ACCOUNT:function:ballpoint-webhook
```

HTTP API passes the raw body as a string by default — no extra configuration needed.

**Option B — REST API:**

If using REST API, ensure the integration passes the raw body through. You may
need to configure binary media types or a body mapping template.

### 4. Verify API Gateway → Lambda permissions

The `create-api --target` shortcut automatically creates a Lambda permission and
a `$default` catch-all route. If you set up the integration manually (console,
CloudFormation, etc.), you may need to add the permission yourself:

```bash
aws lambda add-permission \
  --function-name ballpoint-webhook \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:YOUR_ACCOUNT:API_ID/*"
```

**Optional — explicit route:** The `$default` catch-all works fine for a
single-purpose Lambda. If you want a specific route instead:

```bash
aws apigatewayv2 create-route \
  --api-id API_ID \
  --route-key "POST /webhooks/ballpoint" \
  --target integrations/INTEGRATION_ID
```

**Optional — stage deployment:** HTTP API creates a `$default` stage with
auto-deploy enabled. If you disabled auto-deploy, deploy the stage manually for
changes to take effect.

### 5. Give Ballpoint your endpoint URL

Your webhook URL will look like:

```
https://abc123.execute-api.us-east-1.amazonaws.com/webhooks/ballpoint
```

Share this with Ballpoint and we'll configure webhook delivery.

## Testing

```bash
# Generate a test signature
SECRET="whsec_test"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BODY='{"type":"order.status_changed","data":{"order_id":"ord_test","display_status":"printing"}}'
SIG=$(echo -n "${TIMESTAMP}${BODY}" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

# Call your endpoint
curl -X POST https://YOUR_API_GATEWAY_URL/webhooks/ballpoint \
  -H "Content-Type: application/json" \
  -H "X-Ballpoint-Signature: sha256=$SIG" \
  -H "X-Ballpoint-Timestamp: $TIMESTAMP" \
  -H "X-Ballpoint-Event-Id: evt_test_001" \
  -d "$BODY"
```

## How Signature Verification Works

1. Concatenate the timestamp header + raw request body (no delimiter)
2. HMAC-SHA256 with your webhook secret
3. Compare to the `X-Ballpoint-Signature` header (after stripping `sha256=` prefix)
4. Use constant-time comparison to prevent timing attacks

See **Webhook Contract** above for the full validation checklist (timestamp window, deduplication, etc.).

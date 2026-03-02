# Ballpoint API — Start Here

> Get from zero to a working test order in under 5 minutes.

---

## 1. Verify Your Key (30 seconds)

```bash
curl -s https://api.ballpointmarketing.com/health
```

You should see `{"status": "ok", ...}`. The API is up.

---

## 2. Create Your First Order (2 minutes)

```bash
curl -s -X POST https://api.ballpointmarketing.com/v1/billing/orders \
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ" \
  -H "Idempotency-Key: quickstart-$(date +%s)" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "camp_propstream_test",
    "product_type": "4x6_printed",
    "postage_type": "first_class",
    "piece_count": 10
  }'
```

**Expected response (`202 Accepted`):**

```json
{
  "order_id": "ord_...",
  "status": "accepted",
  "billing": { "total_cents": 25270 }
}
```

No mail is printed with your test key — this is a safe sandbox order.

---

## 3. Check Order Status

```bash
curl -s https://api.ballpointmarketing.com/v1/billing/orders/ORDER_ID_HERE \
  -H "X-Partner-Key: pk_test_propstream_X9hvTPr0zpYmzfAJj7mDkiFZzPwuMpGJ"
```

---

## 4. Set Up Webhooks (5 minutes)

1. **Give us your HTTPS endpoint URL** (e.g., `https://yourserver.com/webhooks/ballpoint`)
2. **We give you a webhook secret** (`whsec_...`)
3. **Add a handler** — minimal Node.js example:

```javascript
const crypto = require("crypto");

function verifySignature(body, timestamp, signature, secret) {
  const expected = crypto
    .createHmac("sha256", secret)
    .update(timestamp + body.toString())
    .digest("hex");
  return crypto.timingSafeEqual(
    Buffer.from(expected, "hex"),
    Buffer.from(signature.replace("sha256=", ""), "hex")
  );
}
```

4. **Test it** — ask us to trigger a test event against your endpoint. We can simulate the full order lifecycle.

---

## 5. What's Next

| Resource | Where |
|----------|-------|
| Full Integration Guide | [`PROPSTREAM_API_KIT.md`](PROPSTREAM_API_KIT.md) |
| OpenAPI Spec (interactive) | Import [`docs/ballpoint-api-spec-v2.yaml`](docs/ballpoint-api-spec-v2.yaml) into [editor.swagger.io](https://editor.swagger.io) |
| Postman Collection | Import [`examples/ballpoint.postman_collection.json`](examples/ballpoint.postman_collection.json) |
| Express Example App | [`examples/express-integration/`](examples/express-integration/) |
| Lambda Webhook Template | [`examples/lambda-webhook/`](examples/lambda-webhook/) |
| CF Worker Webhook Template | [`examples/cloudflare-worker-webhook/`](examples/cloudflare-worker-webhook/) |

---

## 6. API Reference (interactive)

To browse endpoints interactively, pick any of these:

- **Swagger Editor** — paste the YAML into [editor.swagger.io](https://editor.swagger.io)
- **Redoc** — `npx @redocly/cli preview-docs docs/ballpoint-api-spec-v2.yaml`
- **Postman** — import the collection (pre-built requests ready to fire)

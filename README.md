# Ballpoint Marketing API — Integration Docs

Everything you need to integrate with the Ballpoint Marketing direct mail API: ordering, real-time tracking, billing, and webhook delivery.

## Getting Started

**[START_HERE.md](START_HERE.md)** — Zero to a working test order in under 5 minutes.

## Documentation

| Resource | Description |
|----------|-------------|
| [API Integration Kit](API_KIT.md) | Full integration guide: auth, endpoints, webhooks, error handling, partner payment gate |
| [Iframe Integration Kit](IFRAME_KIT.md) | Embedded iframe pattern: bootstrap, message contracts, recipient upload, partner payment gate flow |
| [OpenAPI Spec](docs/ballpoint-api-spec-v2.yaml) | Machine-readable API specification (import into Postman, Swagger UI, etc.) |
| [Webhook Contract Catalog](contracts/webhooks/catalog.json) | Canonical event inventory, JSON Schemas, exact raw-body fixtures, and signed header fixtures |
| [Quick Start Guide](START_HERE.md) | Step-by-step first-order walkthrough |
| [Changelog](CHANGELOG.md) | Revision history for the integration kits |

## Examples

| Example | Description |
|---------|-------------|
| [Postman Collection](examples/ballpoint.postman_collection.json) | Pre-built requests for every endpoint |
| [Express Integration](examples/express-integration/) | Node.js/Express webhook receiver with signature verification |
| [Lambda Webhook](examples/lambda-webhook/) | AWS Lambda handler for webhook processing |
| [Cloudflare Worker](examples/cloudflare-worker-webhook/) | Cloudflare Worker webhook receiver |

### Postman Environments

- [Staging](examples/ballpoint-staging.postman_environment.json) — PropStream integration testing (`staging-api.ballpointmarketing.com`; paste your staging `pk_test` key)
- [Sandbox](examples/ballpoint-sandbox.postman_environment.json) — internal test key on `api.ballpointmarketing.com` (no real mail)
- [Production](examples/ballpoint-production.postman_environment.json) — live host for a tenant provisioned with a `pk_live` key

## Webhook Security

Webhook endpoints with a provisioned secret are signed with HMAC-SHA256. Your integration **must** verify signatures before processing events. A migration-grace endpoint without a secret is explicitly marked `X-Ballpoint-Insecure: true` and must not be treated as authenticated.

| Header | Purpose |
|--------|---------|
| `X-Ballpoint-Signature` | `sha256=<hex>` — HMAC of UTF-8(`X-Ballpoint-Timestamp + exact raw body bytes`) using your webhook secret |
| `X-Ballpoint-Timestamp` | ISO 8601 timestamp — reject if older than 5 minutes (replay protection) |
| `X-Ballpoint-Event-Id` | Unique event ID — store and check for deduplication |
| `X-Ballpoint-Delivery` | Unique HTTP-attempt ID — changes on each retry; do not use it for event deduplication |
| `Idempotency-Key` | Required on `POST /v1/billing/orders` — prevents duplicate orders on retry |

See the [API Integration Kit](API_KIT.md#7-status-updates-via-webhooks) for full verification examples and the webhook receiver templates in [`examples/`](examples/) for working implementations.

## Support

For API access, environment keys, and technical support, reach out to your partner technical contact at Ballpoint.

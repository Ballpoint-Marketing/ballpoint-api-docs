# Ballpoint Marketing API — Integration Docs

Everything you need to integrate with the Ballpoint Marketing direct mail API: ordering, real-time tracking, billing, and webhook delivery.

## Getting Started

**[START_HERE.md](START_HERE.md)** — Zero to a working test order in under 5 minutes.

## Documentation

| Resource | Description |
|----------|-------------|
| [API Integration Kit](API_KIT.md) | Full integration guide: auth, endpoints, webhooks, error handling |
| [OpenAPI Spec](docs/ballpoint-api-spec-v2.yaml) | Machine-readable API specification (import into Postman, Swagger UI, etc.) |
| [Quick Start Guide](START_HERE.md) | Step-by-step first-order walkthrough |

## Examples

| Example | Description |
|---------|-------------|
| [Postman Collection](examples/ballpoint.postman_collection.json) | Pre-built requests for every endpoint |
| [Express Integration](examples/express-integration/) | Node.js/Express webhook receiver with signature verification |
| [Lambda Webhook](examples/lambda-webhook/) | AWS Lambda handler for webhook processing |
| [Cloudflare Worker](examples/cloudflare-worker-webhook/) | Cloudflare Worker webhook receiver |

### Postman Environments

- [Sandbox](examples/ballpoint-sandbox.postman_environment.json) — for testing
- [Production](examples/ballpoint-production.postman_environment.json) — for live traffic

## Support

Contact your Ballpoint integration manager for API keys, webhook provisioning, and technical support.

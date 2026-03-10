# Changelog

## v1.1.0 — 2026-03-10

- **Production pipeline updated to 8 stages**: added `prep` (data formatting) and `shipping` (manifest/labeling) stages
- Updated production sequences for all product types
- Updated order lifecycle diagram with new stages
- Updated webhook event descriptions and test lifecycle examples

## v1.0.1 — 2026-03-02

- Webhook docs: prominent at-least-once delivery statement
- Webhook docs: deduplication promoted to required, with examples
- Webhook docs: processing model recommendation
- Webhook docs: expanded event catalog with example payloads
- Lambda example: uncommented DynamoDB dedup, added base64 guidance
- Cloudflare Worker example: uncommented KV dedup

## v1.0.0 — 2026-03-02

- Initial public release of integration documentation
- API Kit: ordering, tracking, webhooks, billing
- OpenAPI v2 specification
- Postman collection + sandbox/production environments
- Webhook receiver templates: Express, Lambda, Cloudflare Worker

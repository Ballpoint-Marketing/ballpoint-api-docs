# Ballpoint API Docs

Public-facing API integration documentation for partners. No code, no hosting — static docs only.

## Purpose
This is the **public repo** that partners (PropStream, future integrations) reference to integrate with the Ballpoint API. Contains everything a dev team needs: quickstart, full API kit, OpenAPI spec, examples.

## Project Structure
- `START_HERE.md` — 5-minute quickstart (zero to first test order)
- `API_KIT.md` — Full integration guide: auth, endpoints, billing, webhooks, SSE, error handling
- `SECURITY.md` — Vulnerability reporting policy
- `CHANGELOG.md` — Version history
- `docs/ballpoint-api-spec-v2.yaml` — OpenAPI v2 specification
- `examples/ballpoint.postman_collection.json` — Postman collection (all endpoints)
- `examples/ballpoint-sandbox.postman_environment.json` — Postman sandbox env
- `examples/ballpoint-production.postman_environment.json` — Postman production env
- `examples/express-integration/` — Node.js/Express webhook receiver with signature verification
- `examples/lambda-webhook/` — AWS Lambda webhook handler with DynamoDB dedup
- `examples/cloudflare-worker-webhook/` — Cloudflare Worker webhook receiver with KV dedup

## Deployment
No CI/CD — this is a static docs repo on GitHub. Changes are pushed directly.

## Keeping In Sync
This repo documents the API in `ballpoint-api`. When the API changes:
- **Production pipeline stages** → update `API_KIT.md` sections 6e, 9, and production sequences
- **New endpoints** → update `API_KIT.md` section 12 (Endpoint Quick Reference) and OpenAPI spec
- **Pricing changes** → update `API_KIT.md` section 5 (Product Catalog & Pricing)
- **Webhook events** → update `API_KIT.md` section 7 (Status Updates via Webhooks)
- Always bump version in `API_KIT.md` header and add entry to `CHANGELOG.md`

## Sister Repositories
- **`ballpoint-api`** — Backend API (Python/FastAPI, ECS Fargate) — the actual API this documents
- **`ballpoint-dashboard`** — Internal operations dashboard (CloudFront+S3)
- **`ballpoint-iframe`** — PropStream partner iframe embed (CloudFront+S3)

## Git Conventions
- Stage specific files (never `git add -A` or `git add .`)
- Conventional commits: `docs()`, `fix()`, `chore()`, etc.

# Deferred / not-in-staging endpoints — classification & DECISION REQUIRED

On 2026-05-29 a contract audit compared every path in `docs/ballpoint-api-spec-v2.yaml`
against the real FastAPI routes in `ballpoint-api` (staging). 16 operations had **no real
route in staging** and were removed from the public spec (which now documents only what
works in staging/v1 today).

Per Head directive, removal ≠ deletion of intent. Each removed endpoint is preserved in
`deferred-endpoints.draft.yaml` (16 operations across 14 paths) (NOT a published contract) and classified below. Items
marked **DECISION REQUIRED** are not silently dropped — they need a product/engineering
call (roadmap vs necessary gap) before being forgotten or implemented.

Classification key (Head's 4 categories):
1. **Roadmap** — real future intent; keep in backlog, out of current spec.
2. **Wrong path** — real capability exists under a different route; fix, don't remove. *(none found here)*
3. **Necessary gap** — needed by system/partner but unimplemented; **DECISION REQUIRED** (do not silently drop).
4. **Partner-side / example** — not a Ballpoint route; ignore. *(none here; those were markdown false-positives, untouched)*

| Endpoint (removed) | Stated intent | Class | Real staging coverage | Impact if left undocumented |
|---|---|---|---|---|
| `POST /v1/webhooks` | Register webhook | **3 — DECISION REQUIRED** | none (only inbound Stripe `POST /v1/billing/stripe/webhook`) | Partner cannot self-register webhook endpoints via API; presumed manual/out-of-band today |
| `GET /v1/webhooks` | List webhooks | **3 — DECISION REQUIRED** | none | No programmatic view of configured webhooks |
| `POST /v1/webhooks/{id}/rotate-secret` | Rotate webhook secret | **3 — DECISION REQUIRED** | none | No self-service secret rotation (security-relevant) |
| `POST /v1/webhooks/{id}/pause` · `/resume` | Pause/resume webhook | 1 — Roadmap | none | Convenience; not blocking |
| `GET /v1/webhooks/{id}/health` | Webhook health | 1 — Roadmap | none | Observability nicety |
| `POST /v1/sandbox/webhooks/{id}/trigger` | Trigger test webhook | 1 — Roadmap | none | Integration-testing DX |
| `GET /v1/sandbox/webhooks/{id}/test-signature` | Test signature verify | 1 — Roadmap | none | Integration-testing DX |
| `GET /v1/reconciliation/campaigns/{id}` | Get campaign reconciliation | **3 — DECISION REQUIRED** | partial: `GET /v1/billing/partner/orders?search=` | Reconciliation is a known partner concern; no dedicated endpoint |
| `GET /v1/reconciliation/campaigns/lookup` | Lookup campaign by external ID | 2-ish / **DECISION REQUIRED** | partial: list `search` matches external_order_id OR campaign_id | Lookup partially served by list search; confirm if dedicated route needed |
| `POST /v1/reconciliation/webhooks/replay/{event_id}` | Replay webhook event | **3 — DECISION REQUIRED** | none | No event replay; depends on webhook subsystem |
| `POST /v1/campaigns` | Create campaign | 1 — Roadmap | implicit: campaigns form via orders sharing `list_id` | Current model creates campaigns implicitly via orders; explicit CRUD likely v2 |
| `GET /v1/campaigns` · `GET /v1/campaigns/{id}` | List / get campaign | **3 — DECISION REQUIRED** | partial: only orders are listable (`GET /v1/billing/partner/orders`) | No campaign-level read API for partners |
| `POST /v1/campaigns/{id}/submit` · `/cancel` | Submit / cancel campaign | 1 — Roadmap | submit/cancel happen via order flow today | Explicit campaign lifecycle = v2 model |

## Final decisions (Head, 2026-05-29) — RESOLVED, do not reopen this round

This round closes WITHOUT putting any deferred endpoint back into the public OpenAPI.
The public contract stays staging/v1-real only (commit `36da6d2`). Resolutions:

| Group | Decision | Rationale | Status |
|---|---|---|---|
| **Webhook management / rotate-secret** (`POST/GET /v1/webhooks`, `rotate-secret`, pause/resume/health, sandbox trigger/test-signature) | **Do NOT expose as public API now.** Stays manual / out-of-band via Ballpoint. | Sensitive security surface — needs its own design for permissions, audit, ownership, retries, and secret rotation before becoming a contract. | **Backlog P1 — security/product** |
| **Reconciliation** (`GET reconciliation/campaigns/{id}`, `lookup`, `webhooks/replay`) | **Do NOT expose lookup/replay as public API now.** For v1/staging, partners use the real documented endpoints: orders, events, mail-tracking. Reconciliation/replay stays an internal support runbook. | Needs a safe design with idempotency + audit before exposure. | **Backlog P1 — partner-ops** |
| **Campaign read / CRUD** (`GET /v1/campaigns`, `/{id}`, create/submit/cancel) | **Do NOT expose campaign read/CRUD now.** Public contract stays order-centric; campaign remains an internal/derived concept until an explicit product decision. | Current model is order-centric (campaigns form implicitly via `list_id`). | **Backlog P2 — product** |

### Standing rules (until a future explicit product decision)
- The public spec (`docs/ballpoint-api-spec-v2.yaml`) stays staging-truthful — deferred endpoints do NOT go back in until a real, tested staging route exists.
- Do not add production. Do not add v2. Do not implement these endpoints as a side effect.
- Published material (PDF / CHANGELOG) and any partner reply must use ONLY endpoints present in the current OpenAPI (`36da6d2`); never cite a deferred endpoint.
- The local gate `tools/contract-check/check-spec.sh` validates only the PUBLIC spec, not this draft.
- This draft + table are the durable record; do not delete until product reopens with a decision.

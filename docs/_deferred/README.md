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

## What to do with this
- **DECISION REQUIRED** rows: product/eng must decide implement-now (gap) vs defer (roadmap). Do not delete the draft until decided.
- The public spec (`docs/ballpoint-api-spec-v2.yaml`) stays staging-truthful regardless — these do not go back in until a real, tested route exists.
- The local gate `tools/contract-check/check-spec.sh` only validates the PUBLIC spec, not this draft.

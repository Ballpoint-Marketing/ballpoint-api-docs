# contract-check

Verifies every `(method, path)` in `docs/ballpoint-api-spec-v2.yaml` resolves
to a real FastAPI mount in the `ballpoint-api` source tree. Catches phantom
paths and method mismatches before they reach partner-facing docs.

## What it does

- `resolve-routes.py` — builds the real route table by parsing
  `APIRouter(prefix=)` + `@router.<method>("path")` + `include_router(prefix=)`.
  Read-only, never imports the app.
- `check-spec.sh` — extracts method+path pairs from the OpenAPI spec, runs the
  resolver in `--check` mode for each, prints a table, exits non-zero on any
  PHANTOM or METHOD-MISMATCH.

## Usage

```
BALLPOINT_API_DIR=~/ballpoint-api ./tools/contract-check/check-spec.sh
```

Default API dir is `~/ballpoint-api` if `BALLPOINT_API_DIR` is unset.

## When to run

This MUST pass before:
- Publishing/regenerating the partner PDF
- Cutting a CHANGELOG release
- Sending a partner reply that cites an API path

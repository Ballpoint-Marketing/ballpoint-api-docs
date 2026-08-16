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
- `check-webhook-contracts.py` — validates the public webhook inventory,
  Draft 2020-12 schemas, logical/wire fixtures, exact serialized body bytes,
  header contract, independent HMAC, event/delivery identifiers, and RTS
  percentage/batch invariants.
- `check-partner-contract.py` — treats this repository as the canonical partner
  version, checks API/iframe metadata lockstep, and enforces explicit public or
  no-public classification for contract-sensitive iframe diffs. Exact lockstep
  remains the default. Its maintenance-release capability is an explicit,
  fail-closed exception for an unchanged older iframe contract when canonical
  docs have already advanced.

## Usage

```
BALLPOINT_API_DIR=~/ballpoint-api ./tools/contract-check/check-spec.sh
python tools/contract-check/check-webhook-contracts.py
python tools/contract-check/check-partner-contract.py --docs-root .
python -m unittest discover -s tools/contract-check/tests -v
```

For a maintenance branch or release tag whose iframe contract is older than
the canonical docs, the iframe workflow may add `--allow-maintenance-release`
to the normal classified invocation. The capability activates only when the
docs and iframe versions differ, and then requires all of the following:

- exactly one `No public contract change` classification with a concrete
  `No-public justification`;
- every iframe version surface agrees internally;
- the candidate iframe version is unchanged from `--base-ref`;
- the iframe version is not ahead of the canonical docs version.

An equal-version release still follows the normal public/no-public path even
when the capability flag is present. In `ballpoint-iframe`, only PRs targeting
`release/*` and `v*` tag deploy gates enable this capability; ordinary PRs and
`main` staging deploys keep exact lockstep. A tag receives the maintenance
capability only when its SHA belongs to a merged PR targeting `release/<tag>`;
ordinary equal-version tags remain on the normal gate. Every tag must already
be the exact `merge_commit_sha` produced by its selected PR and be reachable
from `origin/main`. Merge this canonical checker before publishing an iframe
workflow that invokes the new flag.

Default API dir is `~/ballpoint-api` if `BALLPOINT_API_DIR` is unset.

## When to run

This MUST pass before:
- Publishing/regenerating the partner PDF
- Cutting a CHANGELOG release
- Sending a partner reply that cites an API path

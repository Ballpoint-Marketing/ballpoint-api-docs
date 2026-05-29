#!/usr/bin/env bash
# check-spec.sh — verify every method+path in ballpoint-api-spec-v2.yaml
# resolves to a real FastAPI mount in the ballpoint-api source tree.
#
# Exit code: 0 only if every path MATCHes; non-zero with offender list otherwise.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
SPEC="$REPO_ROOT/docs/ballpoint-api-spec-v2.yaml"
RESOLVER="$HERE/resolve-routes.py"
API_DIR="${BALLPOINT_API_DIR:-$HOME/ballpoint-api}"

if [[ ! -f "$SPEC" ]]; then
  echo "ERROR: spec not found: $SPEC" >&2
  exit 2
fi
if [[ ! -x "$RESOLVER" ]]; then
  echo "ERROR: resolver not executable: $RESOLVER" >&2
  exit 2
fi
if [[ ! -d "$API_DIR" ]]; then
  echo "ERROR: API dir not found: $API_DIR (set BALLPOINT_API_DIR)" >&2
  exit 2
fi

# Extract method + path pairs from the spec (one per line: "METHOD /path")
mapfile -t PAIRS < <(python3 - "$SPEC" <<'PY'
import sys, yaml
spec = yaml.safe_load(open(sys.argv[1]))
methods = {"get","post","put","patch","delete","head","options"}
for path, item in (spec.get("paths") or {}).items():
    if not isinstance(item, dict):
        continue
    for m in item:
        if m.lower() in methods:
            print(f"{m.upper()} {path}")
PY
)

if [[ ${#PAIRS[@]} -eq 0 ]]; then
  echo "ERROR: no paths extracted from spec" >&2
  exit 2
fi

printf '%-7s %-50s %s\n' "METHOD" "PATH" "VERDICT"
printf '%-7s %-50s %s\n' "------" "----" "-------"

offenders=()
for entry in "${PAIRS[@]}"; do
  method="${entry%% *}"
  path="${entry#* }"
  if out=$("$RESOLVER" "$API_DIR" --check "$method $path" 2>&1); then
    verdict="MATCH"
  else
    rc=$?
    # First line of resolver output carries the verdict tag
    verdict=$(printf '%s\n' "$out" | head -n1)
    offenders+=("$method $path -> $verdict (rc=$rc)")
  fi
  printf '%-7s %-50s %s\n' "$method" "$path" "$verdict"
done

echo
if [[ ${#offenders[@]} -eq 0 ]]; then
  echo "OK: all ${#PAIRS[@]} spec paths match real API mounts."
  exit 0
fi

echo "FAIL: ${#offenders[@]} offender(s):"
for o in "${offenders[@]}"; do
  echo "  - $o"
done
exit 1

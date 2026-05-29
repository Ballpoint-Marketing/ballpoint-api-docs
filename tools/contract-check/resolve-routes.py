#!/usr/bin/env python3
"""Resolve the REAL mounted route table for ballpoint-api and verify a cited path.

Why this exists
---------------
Partner-facing docs/drafts have twice cited a phantom path that did not match
the real FastAPI mount (POST /v1/billing/partner/orders vs real POST /orders;
GET 405 because handler unregistered). The real mount is composed as:

    full_path = include_router(prefix=)   # mount-time prefix (main.py)
              + APIRouter(prefix=)        # constructor prefix (router file)
              + @router.<method>("path")  # decorator path

This script builds that table from source and answers "does this path exist?".

Usage
-----
  resolve-routes.py [API_DIR]                  # dump full route table
  resolve-routes.py [API_DIR] --check "POST /v1/billing/orders/{id}"

Verdicts: MATCH | PHANTOM (no such path) | METHOD-MISMATCH (path exists, other verbs)
Exit codes: 0 MATCH/dump-ok · 3 PHANTOM · 4 METHOD-MISMATCH · 2 usage/IO error
Read-only. Never imports the app, never executes API code.
"""
import re
import sys
import os
import glob

METHODS = ("get", "post", "put", "patch", "delete", "head", "options")

ctor_re = re.compile(r'([A-Za-z_]\w*)\s*=\s*APIRouter\(([^)]*)\)')
prefix_re = re.compile(r'prefix\s*=\s*["\']([^"\']*)["\']')
deco_re = re.compile(
    r'@([A-Za-z_]\w*)\.(' + "|".join(METHODS) + r')\(\s*["\']([^"\']*)["\']')
incl_re = re.compile(
    r'include_router\(\s*([A-Za-z_]\w*)\s*(?:,\s*prefix\s*=\s*["\']([^"\']*)["\'])?')


def norm(path):
    """Normalize for comparison: strip trailing slash, collapse {param} -> {}."""
    p = re.sub(r'\{[^}]*\}', '{}', path)
    p = re.sub(r'//+', '/', p)
    if len(p) > 1 and p.endswith('/'):
        p = p[:-1]
    return p or '/'


def _lineno(text, pos):
    return text.count("\n", 0, pos) + 1


def build_table(api_dir):
    py_files = [
        f for f in glob.glob(os.path.join(api_dir, "**", "*.py"), recursive=True)
        if "/test" not in f and not os.path.basename(f).startswith("test_")
    ]
    ctor_prefix = {}        # var -> constructor prefix
    ctor_def_files = {}     # var -> [files] (ambiguity detection)
    decorators = []         # (var, METHOD, path, file, line)
    includes = {}           # var -> mount prefix
    incl_files = {}         # var -> file where included

    # Scan each file as ONE text blob so multi-line decorators/calls are caught
    # (\s in the patterns already crosses newlines). Line numbers via match offset.
    for f in py_files:
        try:
            text = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        rel = os.path.relpath(f, api_dir)
        for m in ctor_re.finditer(text):
            var = m.group(1)
            pm = prefix_re.search(m.group(2))
            ctor_prefix[var] = pm.group(1) if pm else ""
            ctor_def_files.setdefault(var, []).append(rel)
        for m in deco_re.finditer(text):
            decorators.append((m.group(1), m.group(2).upper(), m.group(3),
                               rel, _lineno(text, m.start())))
        for m in incl_re.finditer(text):
            includes[m.group(1)] = m.group(2) or ""
            incl_files[m.group(1)] = rel

    rows = []
    warnings = []
    for var, method, path, f, line in decorators:
        ctor = ctor_prefix.get(var, "")
        if var in includes:
            mount = includes[var]
        else:
            mount = ""
            # `app` / `application` = the FastAPI() instance itself: routes mount
            # at root, so empty prefix is correct, not a warning.
            if var not in ("app", "application"):
                warnings.append(f"{var} has decorators but no include_router() found "
                                f"({f}:{line}) — mount prefix assumed empty")
        full = norm(mount + "/" + ctor + "/" + path)
        rows.append((method, full, var, f, line))
        if len(set(ctor_def_files.get(var, []))) > 1:
            warnings.append(f"{var} defined as APIRouter in multiple files "
                            f"{sorted(set(ctor_def_files[var]))} — path may be ambiguous")
    return rows, sorted(set(warnings))


def main():
    args = [a for a in sys.argv[1:]]
    check = None
    if "--check" in args:
        idx = args.index("--check")
        check = args[idx + 1] if idx + 1 < len(args) else None
        del args[idx:idx + 2]
    api_dir = args[0] if args else os.path.expanduser("~/ballpoint-api")
    if not os.path.isdir(api_dir):
        print(f"ERROR: API dir not found: {api_dir}", file=sys.stderr)
        return 2

    rows, warnings = build_table(api_dir)

    if check is None:
        for method, full, var, f, line in sorted(rows, key=lambda r: (r[1], r[0])):
            print(f"{method:7} {full:45} <- {var}  ({f}:{line})")
        if warnings:
            print("\n# warnings:", file=sys.stderr)
            for w in warnings:
                print(f"#   {w}", file=sys.stderr)
        print(f"\n# {len(rows)} routes", file=sys.stderr)
        return 0

    # --check mode
    parts = check.strip().split()
    if len(parts) == 2:
        q_method, q_path = parts[0].upper(), parts[1]
    else:
        q_method, q_path = None, parts[0]
    q_norm = norm(q_path)

    same_path = [(m, full, var, f, line) for (m, full, var, f, line) in rows
                 if full == q_norm]
    if not same_path:
        print(f"PHANTOM: no route matches path {q_norm!r}")
        # suggest near-misses
        near = sorted({full for (_, full, *_ ) in rows
                       if q_norm.rstrip('/').split('/')[-1] in full})
        if near:
            print("  did you mean:")
            for n in near[:5]:
                print(f"    {n}")
        return 3

    methods_here = sorted({m for (m, *_ ) in same_path})
    if q_method and q_method not in methods_here:
        print(f"METHOD-MISMATCH: {q_norm!r} exists but only for {methods_here}, "
              f"not {q_method}")
        for (m, full, var, f, line) in same_path:
            print(f"    {m:7} {full}  <- {var} ({f}:{line})")
        return 4

    print(f"MATCH: {q_method or '(any)'} {q_norm}")
    for (m, full, var, f, line) in same_path:
        print(f"    {m:7} {full}  <- {var} ({f}:{line})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

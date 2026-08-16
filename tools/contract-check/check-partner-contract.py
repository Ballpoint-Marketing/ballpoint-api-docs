#!/usr/bin/env python3
"""Fail closed when Ballpoint partner-contract surfaces drift.

The public docs repository is canonical. API and iframe consumers pass their
local root and a checkout of ballpoint-api-docs. The iframe can additionally
validate an explicit PR impact classification against a git base ref.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


VERSION = r"[0-9]+\.[0-9]+\.[0-9]+"
PUBLIC_BOX = re.compile(r"(?im)^\s*-\s*\[[xX]\]\s*Public contract change\s*$")
NO_PUBLIC_BOX = re.compile(r"(?im)^\s*-\s*\[[xX]\]\s*No public contract change\s*$")
class GateError(RuntimeError):
    pass


def text(path: Path) -> str:
    if not path.is_file():
        raise GateError(f"required file is missing: {path}")
    return path.read_text(encoding="utf-8")


def one(pattern: str, value: str, label: str, flags: int = 0) -> str:
    match = re.search(pattern, value, flags)
    if not match:
        raise GateError(f"cannot read {label}")
    return match.group(1)


def public_version(docs: Path) -> str:
    changelog = one(rf"^## v({VERSION})\s", text(docs / "CHANGELOG.md"), "CHANGELOG head", re.M)
    kit = one(
        rf"\*{{0,2}}Partner contract version:\*{{0,2}}\s*\*\*v?({VERSION})\*\*",
        text(docs / "IFRAME_KIT.md"),
        "IFRAME_KIT partner version",
        re.I,
    )
    collection = json.loads(text(docs / "examples" / "ballpoint.postman_collection.json"))
    postman = one(
        rf"Aligned to API_KIT v({VERSION})",
        collection.get("info", {}).get("description", ""),
        "Postman contract version",
    )
    api_kit = one(rf"^> \*\*v({VERSION})\s", text(docs / "API_KIT.md"), "API_KIT version", re.M)
    require_equal({
        "CHANGELOG": changelog,
        "IFRAME_KIT": kit,
        "API_KIT": api_kit,
        "Postman": postman,
    })
    return changelog


def api_version(api: Path) -> str:
    return one(
        rf'^PARTNER_CONTRACT_VERSION\s*=\s*"({VERSION})"',
        text(api / "constants.py"),
        "API PARTNER_CONTRACT_VERSION",
        re.M,
    )


def iframe_versions(iframe: Path) -> dict[str, str]:
    build = one(
        rf"partner:\s*'({VERSION})'",
        text(iframe / "js" / "build-info.js"),
        "iframe build-info partner version",
    )
    deploy = re.findall(
        rf"^\s*partner:\s*'({VERSION})'",
        text(iframe / ".github" / "workflows" / "deploy.yml"),
        re.M,
    )
    if len(deploy) != 2:
        raise GateError(f"expected exactly two iframe deploy partner literals; found {len(deploy)}")
    pager = one(
        rf"\*{{0,2}}Partner contract version:\*{{0,2}}\s*\*\*v?({VERSION})\*\*",
        text(iframe / "PROPSTREAM_ONE_PAGER.md"),
        "one-pager partner version",
        re.I,
    )
    result = {
        "iframe build-info": build,
        "iframe deploy staging": deploy[0],
        "iframe deploy production": deploy[1],
        "iframe one-pager": pager,
    }
    require_equal(result)
    return result


def require_equal(values: dict[str, str]) -> None:
    if len(set(values.values())) != 1:
        details = ", ".join(f"{key}={value}" for key, value in values.items())
        raise GateError(f"partner contract version drift: {details}")


def git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode:
        raise GateError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def changed_files(root: Path, base: str) -> set[str]:
    git(root, "rev-parse", "--verify", base)
    committed = git(root, "diff", "--name-only", f"{base}...HEAD")
    working = git(root, "diff", "--name-only", base)
    return {line.strip() for line in (committed + "\n" + working).splitlines() if line.strip()}


def version_at(root: Path, ref: str, path: str, pattern: str, label: str) -> str:
    value = git(root, "show", f"{ref}:{path}")
    return one(pattern, value, label, re.M)


def field(body: str, name: str) -> str:
    match = re.search(rf"(?im)^\s*{re.escape(name)}\s*:\s*(.+?)\s*$", body)
    return match.group(1).strip() if match else ""


def filled(value: str, minimum: int) -> bool:
    lowered = value.strip().lower()
    return len(value.strip()) >= minimum and "required" not in lowered and not lowered.startswith(("_", "<"))


def classification(body: str) -> str:
    public_checked = bool(PUBLIC_BOX.search(body))
    no_public_checked = bool(NO_PUBLIC_BOX.search(body))

    if public_checked == no_public_checked:
        raise GateError("select exactly one partner-contract impact classification in the PR body")

    if no_public_checked:
        justification = field(body, "No-public justification")
        if not filled(justification, 20):
            raise GateError("a contract-sensitive diff classified no-public needs a concrete justification")
        return "no-public"

    return "public"


def version_key(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(VERSION, value):
        raise GateError(f"invalid partner contract version: {value}")
    return tuple(int(part) for part in value.split("."))


def validate_classification(iframe: Path, docs_version: str, base: str, body: str) -> None:
    impact = classification(body)
    if impact == "no-public":
        return

    changed = changed_files(iframe, base)

    iframe_values = iframe_versions(iframe)
    current = next(iter(iframe_values.values()))
    old = version_at(
        iframe,
        base,
        "js/build-info.js",
        rf"partner:\s*'({VERSION})'",
        "base iframe partner version",
    )
    if current == old:
        raise GateError("public contract change did not bump the iframe partner version")
    if current != docs_version:
        raise GateError(f"public docs={docs_version} but iframe={current}")

    required_paths = {
        "PROPSTREAM_ONE_PAGER.md",
        "js/build-info.js",
        ".github/workflows/deploy.yml",
    }
    missing = sorted(required_paths - changed)
    if missing:
        raise GateError("public contract change is missing required iframe updates: " + ", ".join(missing))
    if not any(path.startswith("tests/") and path.endswith(('.js', '.mjs')) for path in changed):
        raise GateError("public contract change needs an affected contract test")

    declared = field(body, "Partner contract version").lstrip("v")
    if declared != current:
        raise GateError(f"PR body partner version={declared or 'missing'} but iframe={current}")
    for required in ("Public docs", "Consumers", "Communication"):
        if not filled(field(body, required), 8):
            raise GateError(f"PR body is missing required public-impact field: {required}")


def validate_maintenance_release(iframe: Path, docs_version: str, base: str, body: str) -> str:
    """Allow an unchanged older contract only for an explicitly no-public release.

    Public docs remain canonical and may be ahead of a maintenance branch. The
    candidate must keep every iframe version surface equal to its own base; a
    contract bump or public-impact classification still fails closed.
    """
    if classification(body) != "no-public":
        raise GateError("maintenance release mode requires No public contract change")

    iframe_values = iframe_versions(iframe)
    current = next(iter(iframe_values.values()))
    old = version_at(
        iframe,
        base,
        "js/build-info.js",
        rf"partner:\s*'({VERSION})'",
        "base iframe partner version",
    )
    if current != old:
        raise GateError(
            f"maintenance release changed the iframe partner version: base={old}, candidate={current}"
        )
    if version_key(current) > version_key(docs_version):
        raise GateError(
            f"maintenance iframe contract={current} is ahead of public docs={docs_version}"
        )
    return current


def maintenance_release_required(docs_version: str, iframe_values: dict[str, str]) -> bool:
    return bool(
        iframe_values
        and any(value != docs_version for value in iframe_values.values())
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-root", type=Path, required=True)
    parser.add_argument("--api-root", type=Path)
    parser.add_argument("--iframe-root", type=Path)
    parser.add_argument("--base-ref")
    parser.add_argument("--pr-body-file", type=Path)
    parser.add_argument("--pr-body-env", default="PR_BODY")
    parser.add_argument("--require-classification", action="store_true")
    parser.add_argument("--allow-maintenance-release", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        canonical = public_version(args.docs_root.resolve())
        platform_surfaces = {"public docs": canonical}
        if args.api_root:
            platform_surfaces["API"] = api_version(args.api_root.resolve())
        require_equal(platform_surfaces)

        iframe_surfaces = {}
        if args.iframe_root:
            iframe_surfaces = iframe_versions(args.iframe_root.resolve())

        if args.allow_maintenance_release and not args.require_classification:
            raise GateError("maintenance release mode requires --require-classification")

        surfaces = {**platform_surfaces, **iframe_surfaces}
        maintenance_active = bool(
            args.allow_maintenance_release
            and maintenance_release_required(canonical, iframe_surfaces)
        )

        if args.require_classification:
            if not args.iframe_root or not args.base_ref:
                raise GateError("classification requires --iframe-root and --base-ref")
            body = (
                text(args.pr_body_file)
                if args.pr_body_file
                else os.environ.get(args.pr_body_env, "")
            )
            if maintenance_active:
                validate_maintenance_release(
                    args.iframe_root.resolve(), canonical, args.base_ref, body
                )
            else:
                validate_classification(args.iframe_root.resolve(), canonical, args.base_ref, body)

        if not maintenance_active:
            require_equal(surfaces)

        mode = " maintenance" if maintenance_active else ""
        print(
            f"PASS partner contract{mode} gate: "
            + ", ".join(f"{key}={value}" for key, value in surfaces.items())
        )
        return 0
    except (GateError, json.JSONDecodeError) as exc:
        print(f"FAIL partner contract gate: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

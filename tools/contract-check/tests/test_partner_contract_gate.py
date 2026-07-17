from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "check-partner-contract.py"
SPEC = importlib.util.spec_from_file_location("partner_contract_gate", MODULE_PATH)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(gate)


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


class PartnerContractGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.docs = root / "docs"
        self.iframe = root / "iframe"
        self.api = root / "api"
        self.seed("1.7.15")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def seed(self, version: str) -> None:
        write(self.docs / "CHANGELOG.md", f"## v{version} — test\n")
        write(self.docs / "IFRAME_KIT.md", f"Partner contract version: **v{version}**\n")
        write(self.docs / "API_KIT.md", f"> **v{version} · test**\n")
        write(
            self.docs / "examples" / "ballpoint.postman_collection.json",
            json.dumps({"info": {"description": f"Aligned to API_KIT v{version}"}}),
        )
        write(self.api / "constants.py", f'PARTNER_CONTRACT_VERSION = "{version}"\n')
        write(self.iframe / "js" / "build-info.js", f"partner: '{version}',\n")
        write(
            self.iframe / ".github" / "workflows" / "deploy.yml",
            f"partner: '{version}',\npartner: '{version}',\n",
        )
        write(self.iframe / "PROPSTREAM_ONE_PAGER.md", f"Partner contract version: **v{version}**\n")
        write(self.iframe / "js" / "iframe-integration.js", "// baseline\n")
        write(self.iframe / "tests" / "sender-contract.spec.js", "// baseline\n")
        run("git", "init", "-b", "main", cwd=self.iframe)
        run("git", "config", "user.email", "gate@example.invalid", cwd=self.iframe)
        run("git", "config", "user.name", "Gate Test", cwd=self.iframe)
        run("git", "add", ".", cwd=self.iframe)
        run("git", "commit", "-m", "baseline", cwd=self.iframe)

    def bump_docs(self, version: str) -> None:
        write(self.docs / "CHANGELOG.md", f"## v{version} — test\n")
        write(self.docs / "IFRAME_KIT.md", f"Partner contract version: **v{version}**\n")
        write(self.docs / "API_KIT.md", f"> **v{version} · test**\n")
        write(
            self.docs / "examples" / "ballpoint.postman_collection.json",
            json.dumps({"info": {"description": f"Aligned to API_KIT v{version}"}}),
        )

    def bump_iframe(self, version: str, docs: bool = True) -> None:
        write(self.iframe / "js" / "build-info.js", f"partner: '{version}',\n")
        write(
            self.iframe / ".github" / "workflows" / "deploy.yml",
            f"partner: '{version}',\npartner: '{version}',\n",
        )
        write(self.iframe / "PROPSTREAM_ONE_PAGER.md", f"Partner contract version: **v{version}**\n")
        write(self.iframe / "js" / "iframe-integration.js", "// changed handler\n")
        write(self.iframe / "tests" / "sender-contract.spec.js", "// changed test\n")
        if docs:
            self.bump_docs(version)

    def public_body(self, version: str) -> str:
        return f"""- [x] Public contract change
- [ ] No public contract change
Partner contract version: {version}
Public docs: https://github.com/Ballpoint-Marketing/ballpoint-api-docs/blob/main/IFRAME_KIT.md
Consumers: PropStream iframe parent
Communication: staging validation draft prepared
"""

    def test_complete_release_passes(self) -> None:
        self.bump_iframe("1.7.16")
        gate.require_equal({"docs": gate.public_version(self.docs), **gate.iframe_versions(self.iframe)})
        gate.validate_classification(self.iframe, "1.7.16", "HEAD", self.public_body("1.7.16"))

    def test_handler_change_without_docs_fails(self) -> None:
        write(self.iframe / "js" / "iframe-integration.js", "// changed handler\n")
        with self.assertRaises(gate.GateError):
            gate.validate_classification(
                self.iframe,
                "1.7.15",
                "HEAD",
                "- [x] Public contract change\n- [ ] No public contract change\n",
            )

    def test_only_one_version_surface_fails(self) -> None:
        write(self.iframe / "js" / "build-info.js", "partner: '1.7.16',\n")
        with self.assertRaises(gate.GateError):
            gate.require_equal({"docs": gate.public_version(self.docs), **gate.iframe_versions(self.iframe)})

    def test_one_pager_without_public_kit_fails(self) -> None:
        self.bump_iframe("1.7.16", docs=False)
        with self.assertRaises(gate.GateError):
            gate.require_equal({"docs": gate.public_version(self.docs), **gate.iframe_versions(self.iframe)})

    def test_deploy_with_divergent_version_fails(self) -> None:
        self.bump_docs("1.7.16")
        with self.assertRaises(gate.GateError):
            gate.require_equal({"docs": gate.public_version(self.docs), **gate.iframe_versions(self.iframe)})

    def test_no_public_placeholder_is_not_a_justification(self) -> None:
        with self.assertRaises(gate.GateError):
            gate.validate_classification(
                self.iframe,
                "1.7.15",
                "HEAD",
                "- [ ] Public contract change\n- [x] No public contract change\n"
                "No-public justification: _Required when selecting no public change_\n",
            )


if __name__ == "__main__":
    unittest.main()

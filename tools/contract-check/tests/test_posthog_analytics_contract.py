from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
IFRAME_KIT = (ROOT / "IFRAME_KIT.md").read_text(encoding="utf-8")
API_KIT = (ROOT / "API_KIT.md").read_text(encoding="utf-8")
SPEC = (ROOT / "docs" / "ballpoint-api-spec-v2.yaml").read_text(encoding="utf-8")
POSTMAN = json.loads(
    (ROOT / "examples" / "ballpoint.postman_collection.json").read_text(
        encoding="utf-8"
    )
)


def yaml_block(source: str, heading: str) -> str:
    lines = source.splitlines()
    start = lines.index(heading)
    indentation = len(heading) - len(heading.lstrip())
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.strip() and len(line) - len(line.lstrip()) <= indentation:
            end = index
            break
    return "\n".join(lines[start:end])


def postman_item(name: str) -> dict[str, Any]:
    pending = list(POSTMAN["item"])
    while pending:
        item = pending.pop(0)
        if item.get("name") == name:
            return item
        pending.extend(item.get("item", []))
    raise AssertionError(f"Postman item not found: {name}")


def postman_tests(item: dict[str, Any]) -> str:
    return "\n".join(
        line
        for event in item.get("event", [])
        for line in event.get("script", {}).get("exec", [])
    )


class PostHogAnalyticsContractTests(unittest.TestCase):
    def test_version_and_public_examples_are_in_lockstep(self) -> None:
        expected = "1.7.38"
        self.assertTrue(CHANGELOG.startswith(f"# Changelog\n\n## v{expected}"))
        self.assertIn(f"Partner contract version: **v{expected}**", IFRAME_KIT)
        self.assertIn(f"> **v{expected} · August 2026**", API_KIT)
        self.assertRegex(SPEC, rf"(?m)^  x-partner-contract-version: {re.escape(expected)}$")
        self.assertIn(f"Aligned to API_KIT v{expected}", POSTMAN["info"]["description"])

    def test_config_analytics_is_a_closed_union(self) -> None:
        response = yaml_block(SPEC, "    PartnerConfigResponse:")
        disabled = yaml_block(SPEC, "    AnalyticsConfigDisabled:")
        enabled = yaml_block(SPEC, "    AnalyticsConfigEnabled:")
        union = yaml_block(SPEC, "    AnalyticsConfig:")

        self.assertIn("      - analytics", response)
        self.assertIn("analytics:\n          $ref: '#/components/schemas/AnalyticsConfig'", response)
        self.assertNotIn("posthog_analytics_enabled", response)

        self.assertIn("additionalProperties: false", disabled)
        self.assertIn("required: [enabled]", disabled)
        self.assertIn("enabled: { const: false }", disabled)
        self.assertNotIn("posthog_key", disabled)
        self.assertNotIn("posthog_host", disabled)
        self.assertNotIn("account_id", disabled)
        self.assertNotIn("partner_source", disabled)

        self.assertIn("additionalProperties: false", enabled)
        self.assertIn(
            "required: [enabled, posthog_key, posthog_host, account_id, partner_source]",
            enabled,
        )
        self.assertIn("enabled: { const: true }", enabled)
        self.assertIn("minLength: 8", enabled)
        self.assertIn("maxLength: 256", enabled)
        self.assertIn("pattern: '^phc_[A-Za-z0-9_-]+$'", enabled)
        self.assertIn("const: https://us.i.posthog.com", enabled)
        self.assertIn("account_id: { type: string, minLength: 1 }", enabled)
        self.assertIn("partner_source: { type: string, minLength: 1 }", enabled)

        self.assertIn("oneOf:", union)
        self.assertIn("#/components/schemas/AnalyticsConfigDisabled", union)
        self.assertIn("#/components/schemas/AnalyticsConfigEnabled", union)

    def test_order_response_identifiers_are_documented(self) -> None:
        response = yaml_block(SPEC, "    PartnerOrderCreateResponse:")
        route = yaml_block(SPEC, "  /orders:")

        self.assertIn("required: [id, campaign_id, external_campaign_id]", response)
        self.assertIn("campaign_id:", response)
        self.assertIn("external_campaign_id:", response)
        self.assertRegex(
            response,
            r"external_campaign_id:\n\s+type:\n\s+- string\n\s+- ['\"]?null['\"]?",
        )
        self.assertIn("#/components/schemas/PartnerOrderCreateResponse", route)
        self.assertIn("cached idempotent replay", API_KIT.lower())
        self.assertIn("Ballpoint's internal grouping key", API_KIT)
        self.assertIn("cross-system identifier", API_KIT)

    def test_recipients_updated_count_is_optional_and_non_blocking(self) -> None:
        section_start = IFRAME_KIT.index(
            "#### `recipients_updated` — Partner finished editing recipients"
        )
        section_end = IFRAME_KIT.index("\n#### ", section_start + 5)
        section = IFRAME_KIT[section_start:section_end]

        self.assertIn('"recipientCount": 24', section)
        self.assertRegex(
            section,
            r"\| `recipientCount` \| Optional integer.*1.*1,000,000",
        )
        self.assertIn("edit_leads_saved", section)
        self.assertIn("still refresh", section.lower())

    def test_postman_exercises_both_contract_branches(self) -> None:
        config = postman_item("Resolve partner feature flags")
        config_tests = postman_tests(config)
        self.assertIn("b.analytics.enabled", config_tests)
        self.assertIn("posthog_key", config_tests)
        self.assertIn("posthog_host", config_tests)
        self.assertIn("account_id", config_tests)
        self.assertIn("partner_source", config_tests)
        self.assertIn("https://us.i.posthog.com", config_tests)

        order = postman_item("Create order - partner iframe format")
        order_body = json.loads(order["request"]["body"]["raw"])
        self.assertRegex(order_body["external_campaign_id"], r"^[A-Za-z0-9_-]{1,128}$")
        self.assertEqual(order_body["drop_index"], 1)
        self.assertEqual(order_body["total_drops"], 1)
        order_tests = postman_tests(order)
        self.assertIn("campaign_id", order_tests)
        self.assertIn("external_campaign_id", order_tests)

        current_release = CHANGELOG.split("\n## ", 2)[1]
        self.assertIn("memory-only", current_release)
        self.assertIn("campaign_id", current_release)
        self.assertIn("external_campaign_id", current_release)
        self.assertIn("recipientCount", current_release)


if __name__ == "__main__":
    unittest.main()

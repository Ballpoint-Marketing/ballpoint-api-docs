#!/usr/bin/env python3
"""Validate the public webhook catalog, schemas, fixtures, headers, and HMAC."""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts" / "webhooks"
FIXTURE_SECRET = "fixture-secret-not-production"
EXPECTED_EMITTED = {
    "order.drop_completed",
    "order.drop_cancelled",
    "order.presort_suppressed",
    "order.status_changed",
    "order.rescheduled",
    "order.usps_update",
    "campaign.mail_tracking.rts_update",
}
EXPECTED_NOT_EMITTED = {
    "campaign.mail_tracking.in_transit",
    "campaign.mail_tracking.out_for_delivery",
    "campaign.mail_tracking.delivered",
    "campaign.mail_tracking.stalled",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    catalog = load_json(CONTRACTS / "catalog.json")
    resources = []
    for path in CONTRACTS.rglob("*.schema.json"):
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        if schema.get("$id"):
            resources.append((schema["$id"], Resource.from_contents(schema)))
    registry = Registry().with_resources(resources)
    checker = FormatChecker()

    def validate(instance, schema_path: Path) -> None:
        Draft202012Validator(
            load_json(schema_path), registry=registry, format_checker=checker
        ).validate(instance)

    entries = {entry["type"]: entry for entry in catalog["events"]}
    emitted = {name for name, entry in entries.items() if entry["status"] == "emitted"}
    not_emitted = {
        name for name, entry in entries.items() if entry["status"] == "not_emitted"
    }
    assert emitted == EXPECTED_EMITTED
    assert not_emitted == EXPECTED_NOT_EMITTED
    for name in EXPECTED_NOT_EMITTED:
        entry = entries[name]
        assert not ({"logical_schema", "wire_schema", "fixtures"} & entry.keys())

    header_schema = CONTRACTS / catalog["headers_contract"]
    fixture_count = 0
    event_ids = set()
    delivery_ids = set()
    for event_type in sorted(EXPECTED_EMITTED):
        entry = entries[event_type]
        logical_schema = CONTRACTS / entry["logical_schema"]
        wire_schema = CONTRACTS / entry["wire_schema"]
        for fixture in entry["fixtures"]:
            fixture_count += 1
            logical = load_json(CONTRACTS / fixture["logical"])
            wire = load_json(CONTRACTS / fixture["wire"])
            headers = load_json(CONTRACTS / fixture["headers"])
            raw_body = (CONTRACTS / fixture["raw_body"]).read_bytes()

            validate(logical, logical_schema)
            validate(wire, wire_schema)
            validate(headers, header_schema)
            assert json.loads(raw_body) == wire
            assert json.dumps(wire, ensure_ascii=False).encode("utf-8") == raw_body
            assert headers["X-Ballpoint-Event"] == event_type
            assert headers["X-Ballpoint-Event-Id"] == wire["event_id"]
            assert headers["X-Ballpoint-Timestamp"] == wire["timestamp"]

            event_id = wire["event_id"]
            delivery_id = headers["X-Ballpoint-Delivery"]
            assert event_id not in event_ids
            assert delivery_id not in delivery_ids
            event_ids.add(event_id)
            delivery_ids.add(delivery_id)

            digest = hmac.new(
                FIXTURE_SECRET.encode("utf-8"),
                headers["X-Ballpoint-Timestamp"].encode("utf-8") + raw_body,
                hashlib.sha256,
            ).hexdigest()
            assert hmac.compare_digest(
                headers["X-Ballpoint-Signature"], f"sha256={digest}"
            )

    assert fixture_count == 10
    unsigned = load_json(CONTRACTS / "headers" / "unsigned.fixture.json")
    validate(unsigned, header_schema)
    assert unsigned["X-Ballpoint-Insecure"] == "true"
    assert "X-Ballpoint-Signature" not in unsigned

    rts = load_json(
        CONTRACTS / "campaign.mail_tracking.rts_update" / "fixtures" / "wire.json"
    )
    assert rts["id"] != rts["event_id"]
    assert len(rts["data"]["new_rts_pieces"]) == 100
    for field in ("scan_coverage", "delivered_rate", "rts_rate"):
        assert 0 <= rts["data"][field] <= 100

    suppressed = load_json(
        CONTRACTS / "order.presort_suppressed" / "fixtures" / "wire.json"
    )
    assert suppressed["id"] != suppressed["event_id"]
    assert suppressed["data"]["suppressedCount"] == len(
        suppressed["data"]["recipients"]
    )
    assert "creditTotalTCents" not in suppressed["data"]

    print(f"OK: {len(entries)} catalog entries, {fixture_count} emitted fixtures")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, OSError, ValueError) as exc:
        print(f"FAIL: webhook contract validation: {exc}", file=sys.stderr)
        raise

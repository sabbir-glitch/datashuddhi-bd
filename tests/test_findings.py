"""Tests for the Finding data model."""

from __future__ import annotations

import dataclasses
import json
import re
from typing import Any

import pytest

from datashuddhi.findings import Confidence, Finding, Severity, format_finding_id
from datashuddhi.redaction import mask_email, mask_phone
from tests.synthetic import CANARY_EMAIL, CANARY_PHONE


def make_finding(**overrides: Any) -> Finding:
    values: dict[str, Any] = {
        "finding_id": "F-0001",
        "rule_id": "DS-BDPHONE-001",
        "category": "bangladeshi_mobile_number",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "path": "logs/app.log",
        "line": 143,
        "column": 9,
        "masked_value": mask_phone(CANARY_PHONE),
        "explanation": "Potential Bangladeshi mobile number.",
        "remediation": "Replace with synthetic data before sharing.",
    }
    values.update(overrides)
    return Finding(**values)


def test_severity_is_ordered_and_has_labels() -> None:
    assert Severity.LOW < Severity.MEDIUM < Severity.HIGH
    assert [s.label for s in Severity] == ["low", "medium", "high"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [("low", Severity.LOW), (" MEDIUM ", Severity.MEDIUM), ("High", Severity.HIGH)],
)
def test_severity_parse(text: str, expected: Severity) -> None:
    assert Severity.parse(text) is expected


def test_severity_parse_rejects_unknown_values_without_echoing_them() -> None:
    with pytest.raises(ValueError, match="unknown severity") as info:
        Severity.parse("CANARY-SEVERITY")
    assert "CANARY" not in str(info.value)


def test_finding_ids_are_sequential_and_value_independent() -> None:
    assert format_finding_id(1) == "F-0001"
    assert format_finding_id(42) == "F-0042"
    assert format_finding_id(12345) == "F-12345"
    with pytest.raises(ValueError, match="start at 1"):
        format_finding_id(0)


def test_valid_finding_round_trips_to_json_safe_dict() -> None:
    finding = make_finding()
    data = finding.to_dict()
    assert data["id"] == "F-0001"
    assert data["severity"] == "medium"
    assert data["confidence"] == "medium"
    assert data["masked_value"] == "*********00"
    assert json.loads(json.dumps(data)) == data
    assert list(data) == [
        "id", "rule_id", "category", "severity", "confidence", "path",
        "line", "column", "masked_value", "explanation", "remediation",
    ]  # fmt: skip


def test_finding_is_immutable() -> None:
    finding = make_finding()
    with pytest.raises(dataclasses.FrozenInstanceError):
        finding.line = 2  # type: ignore[misc]


def test_finding_has_no_field_that_could_hold_the_raw_value() -> None:
    names = {field.name for field in dataclasses.fields(Finding)}
    assert not {"raw", "raw_value", "value", "match", "text", "matched_text"} & names


def test_no_representation_of_a_finding_contains_the_raw_value() -> None:
    phone = make_finding()
    email = make_finding(
        rule_id="DS-EMAIL-001",
        category="email_address",
        severity=Severity.LOW,
        confidence=Confidence.HIGH,
        masked_value=mask_email(CANARY_EMAIL),
    )
    for finding in (phone, email):
        blobs = [
            repr(finding),
            str(finding),
            json.dumps(finding.to_dict()),
            json.dumps(dataclasses.asdict(finding), default=str),
        ]
        for blob in blobs:
            assert CANARY_PHONE not in blob
            assert CANARY_EMAIL not in blob
            assert "canary.zq7x" not in blob


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("finding_id", "1"),
        ("finding_id", "F-1"),
        ("rule_id", "bad id"),
        ("rule_id", "ds-email-001"),
        ("category", ""),
        ("category", "not an identifier"),
        ("path", ""),
        ("path", "/etc/passwd"),
        ("path", "\\server\\share"),
        ("path", "a/../b.txt"),
        ("path", "a\x00b.txt"),
        ("line", 0),
        ("column", 0),
        ("masked_value", ""),
        ("masked_value", "no-asterisk-here"),
        ("masked_value", "*" * 65),
        ("masked_value", "ab\n***"),
        ("explanation", ""),
        ("remediation", ""),
    ],
)
def test_invalid_fields_are_rejected(field: str, value: Any) -> None:
    with pytest.raises(ValueError, match=r"."):
        make_finding(**{field: value})


def test_validation_messages_do_not_echo_field_values() -> None:
    canary_path = "CANARY-PATH/../x"
    with pytest.raises(ValueError, match=re.escape("'..' segments")) as info:
        make_finding(path=canary_path)
    assert "CANARY" not in str(info.value)


def test_wrong_enum_types_are_rejected() -> None:
    with pytest.raises(TypeError):
        make_finding(severity="medium")
    with pytest.raises(TypeError):
        make_finding(confidence="high")


def test_unusual_but_legitimate_relative_paths_are_accepted() -> None:
    for path in ["a.txt", "dir/sub dir/file name.csv", "বাংলা/ফাইল.txt", "x/y\\z.log"]:
        assert make_finding(path=path).path == path

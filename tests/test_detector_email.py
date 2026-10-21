"""Tests for the email detector."""

from __future__ import annotations

import pytest

from datashuddhi.detectors import Detector, EmailDetector, default_detectors
from datashuddhi.findings import Confidence, Severity
from tests.synthetic import CANARY_EMAIL, to_bengali_digits

detector = EmailDetector()


def found(line: str) -> list[str]:
    return [m.raw for m in detector.find(line)]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("alice@example.com", ["alice@example.com"]),
        ("Contact: bob.smith+tag@example.org.", ["bob.smith+tag@example.org"]),
        ("<carol_99@mail.example.org>", ["carol_99@mail.example.org"]),
        ('"dave@example.net"', ["dave@example.net"]),
        ("a@b.test", ["a@b.test"]),
        ("x%y-z@example.test", ["x%y-z@example.test"]),
        ("one@example.com two@example.org", ["one@example.com", "two@example.org"]),
        ("one@example.com,two@example.org;", ["one@example.com", "two@example.org"]),
        ("mailto:eve@example.com?subject=hi", ["eve@example.com"]),
        ("EMAIL=Frank@EXAMPLE.COM", ["Frank@EXAMPLE.COM"]),
        ("a@b-c.example.com", ["a@b-c.example.com"]),
        ("নাম alice@example.com নাম", ["alice@example.com"]),
        (".leading@example.com", ["leading@example.com"]),
        ("trailing.@example.com", ["trailing.@example.com"]),
        ("a..b@example.com", ["a..b@example.com"]),
    ],
)
def test_detects_potential_addresses(line: str, expected: list[str]) -> None:
    assert found(line) == expected


@pytest.mark.parametrize(
    "line",
    [
        "",
        "no address here",
        "@example.com",
        "alice@",
        "alice@example",
        "alice@example.",
        "alice@.example.com",
        "alice@-example.test",
        "alice@example-.test",
        "alice@exa mple.com",
        "alice@example.c",
        "alice@example.c0m",
        "alice@example.com1",
        "alice@@",
        "alice at example dot com",
        "logo@2x.png",
        "icon@3x.JPG",
        "sprite@2x.svg",
        "x" * 70 + "@example.com",  # local part over 64 characters
        "user@" + "a" * 64 + ".com",  # label over 63 characters
        "ব্যবহারকারী@example.com",  # non-ASCII local part: documented limitation
        "alice@exämple.com",
    ],
)
def test_does_not_match_non_addresses(line: str) -> None:
    assert found(line) == []


def test_image_asset_filter_is_narrow() -> None:
    # Only "<pixel ratio>x.<image extension>" is suppressed; real-looking domains are kept.
    assert found("a@2x.test") == ["a@2x.test"]
    # "2xl.png" is not a pixel-ratio name, so it is still reported (documented limitation).
    assert found("a@2xl.png") == ["a@2xl.png"]
    assert found("a@x2.example.com") == ["a@x2.example.com"]


def test_offsets_are_code_point_columns_of_the_original_line() -> None:
    line = "নাম: alice@example.com!"
    (match,) = detector.find(line)
    assert line[match.start : match.end] == "alice@example.com"
    assert match.start == line.index("alice")


def test_leading_dot_is_excluded_from_offsets() -> None:
    line = "x .leading@example.com"
    (match,) = detector.find(line)
    assert line[match.start : match.end] == "leading@example.com"


def test_confidence_and_rule_metadata() -> None:
    (match,) = detector.find("alice@example.com")
    assert match.confidence is Confidence.HIGH
    rule = detector.rule
    assert rule.rule_id == "DS-EMAIL-001"
    assert rule.category == "email_address"
    assert rule.severity is Severity.LOW
    assert "not verified" in rule.explanation


def test_bengali_digits_do_not_create_email_matches() -> None:
    assert found(to_bengali_digits("a1@b2.test")) == []


def test_repr_of_a_match_does_not_contain_the_raw_value() -> None:
    (match,) = detector.find(CANARY_EMAIL)
    assert match.raw == CANARY_EMAIL
    assert CANARY_EMAIL not in repr(match)
    assert "canary" not in repr(match)


def test_build_finding_masks_and_drops_the_raw_value() -> None:
    (match,) = detector.find(f"contact {CANARY_EMAIL} today")
    finding = detector.rule.build_finding(
        match, finding_id="F-0001", path="a.txt", line=1, column=match.start + 1
    )
    assert finding.masked_value == "c***@***.com"
    assert CANARY_EMAIL not in repr(finding)
    assert finding.column == 9


def test_default_detectors_are_the_two_v010_rules() -> None:
    detectors = default_detectors()
    assert all(isinstance(d, Detector) for d in detectors)
    assert [d.rule.rule_id for d in detectors] == ["DS-EMAIL-001", "DS-BDPHONE-001"]

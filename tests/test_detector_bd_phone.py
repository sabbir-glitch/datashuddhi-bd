"""Tests for the Bangladeshi mobile number detector."""

from __future__ import annotations

import pytest

from datashuddhi.detectors import BangladeshiPhoneDetector
from datashuddhi.findings import Confidence, Severity
from tests.synthetic import (
    APPROVED_NATIONAL_NUMBERS,
    CANARY_PHONE,
    all_phone_variants,
    to_bengali_digits,
)

detector = BangladeshiPhoneDetector()
VARIANTS = all_phone_variants()


@pytest.mark.parametrize(
    ("national", "text", "confidence"),
    [(r[1], r[2], r[3]) for r in VARIANTS],
    ids=[r[0] for r in VARIANTS],
)
def test_detects_every_documented_format(national: str, text: str, confidence: str) -> None:
    # The number is embedded between words and punctuation to exercise the boundaries.
    for template in ("{}", "tel: {}.", "({}), next", "x {} y", "\t{}\t"):
        line = template.format(text)
        matches = list(detector.find(line))
        assert len(matches) == 1, line
        match = matches[0]
        assert match.raw == text
        assert line[match.start : match.end] == text  # offsets refer to the original line
        assert match.confidence.value == confidence
        assert national  # parametrised for readable ids


@pytest.mark.parametrize("national", APPROVED_NATIONAL_NUMBERS)
def test_all_approved_prefixes_are_recognised(national: str) -> None:
    assert [m.raw for m in detector.find(national)] == [national]


@pytest.mark.parametrize(
    "line",
    [
        "",
        "no number",
        "0171234567",  # 10 digits
        "017123456789",  # 12 digits
        "0171234567890123",  # long digit run
        "1701712345678",  # preceded by a digit
        "9701712345678",
        "01012345678",  # prefix 010 is not matched (unallocated when sources were checked)
        "01112345678",
        "01212345678",
        "02912345678",  # landline-like
        "+88 02 9123 4567",
        "+880 1212 345678",
        "+880 17123456",  # too short
        "+880 171234567890",  # too long
        "+8801712345678901",
        "880171234567",  # 11 digits after 880... too short
        "+1 7123456789",
        "017.1234.5678",  # dot separators are not supported
        "017/12345678",
        "01 7 1234 5678",  # irregular grouping
        "017  12345678",  # two spaces
        "+880(17)12345678",
        "০১৭১২৩৪৫৬৭",  # Bengali digits, 9 digits
        "٠١٧١٢٣٤٥٦٧٨",  # Arabic-Indic
        "۰۱۷۱۲۳۴۵۶۷۸",  # Extended A-I
    ],
)
def test_does_not_match(line: str) -> None:
    assert [m.raw for m in detector.find(line)] == []


def test_digits_adjacent_to_a_match_block_it() -> None:
    n = "01712345678"
    assert list(detector.find("7" + n)) == []
    assert list(detector.find(n + "7")) == []
    assert list(detector.find(to_bengali_digits("7" + n))) == []
    assert [m.raw for m in detector.find(f"ID{n}")] == [n]  # letters do not block (documented)
    assert [m.raw for m in detector.find(f"{n}-x")] == [n]


def test_two_numbers_in_one_line() -> None:
    a, b = APPROVED_NATIONAL_NUMBERS[0], APPROVED_NATIONAL_NUMBERS[1]
    line = f"{a}, +880{b[1:]}"
    matches = list(detector.find(line))
    assert [m.raw for m in matches] == [a, f"+880{b[1:]}"]
    assert [m.confidence for m in matches] == [Confidence.MEDIUM, Confidence.HIGH]


def test_mixed_digit_scripts_in_one_number() -> None:
    # ASCII and Bengali digits mixed in a single number are normalised per character.
    text = "\u09e61\u09ed\u09e72\u09e9\u09ea5\u09ec\u09ed8"  # 01712345678, mixed scripts
    assert [m.raw for m in detector.find(text)] == [text]


def test_offsets_count_code_points_not_bytes_or_graphemes() -> None:
    line = "ফোন: " + to_bengali_digits("+8801712345678") + " ✓"
    (match,) = detector.find(line)
    assert match.start == 5
    assert line[match.start : match.end] == to_bengali_digits("+8801712345678")


def test_source_line_is_not_modified() -> None:
    line = "ফোন: " + to_bengali_digits("01712345678")
    before = str(line)
    list(detector.find(line))
    assert line == before


def test_rule_metadata() -> None:
    rule = detector.rule
    assert rule.rule_id == "DS-BDPHONE-001"
    assert rule.category == "bangladeshi_mobile_number"
    assert rule.severity is Severity.MEDIUM
    assert "not verified" in rule.explanation


def test_build_finding_masks_and_drops_the_raw_value() -> None:
    line = f"call {to_bengali_digits('+880' + CANARY_PHONE[1:])} now"
    (match,) = detector.find(line)
    finding = detector.rule.build_finding(
        match, finding_id="F-0001", path="a.txt", line=1, column=match.start + 1
    )
    assert finding.masked_value == "*********00"
    assert finding.confidence is Confidence.HIGH
    text = repr(finding) + repr(match)
    assert CANARY_PHONE not in text
    assert CANARY_PHONE[1:] not in text
    assert to_bengali_digits(CANARY_PHONE[1:]) not in text

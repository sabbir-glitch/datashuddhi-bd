"""Tests for the masking policy."""

from __future__ import annotations

import re

import pytest

from datashuddhi.redaction import mask_email, mask_phone
from tests.synthetic import (
    APPROVED_NATIONAL_NUMBERS,
    CANARY_EMAIL,
    CANARY_PHONE,
    all_phone_variants,
)

PHONE_VARIANTS = all_phone_variants()


@pytest.mark.parametrize(
    ("national", "text"),
    [(row[1], row[2]) for row in PHONE_VARIANTS],
    ids=[row[0] for row in PHONE_VARIANTS],
)
def test_every_phone_format_masks_to_the_same_shape(national: str, text: str) -> None:
    # Policy: nine asterisks plus the last two digits of the national number, whatever the
    # input format (international prefix, separators, Bengali digits).
    assert mask_phone(text) == "*********" + national[-2:]


def test_phone_mask_matches_documented_example() -> None:
    assert mask_phone("01712345678") == "*********78"


@pytest.mark.parametrize("national", APPROVED_NATIONAL_NUMBERS)
def test_phone_mask_reveals_at_most_two_digits(national: str) -> None:
    masked = mask_phone(national)
    assert len(masked) == 11
    assert len(re.findall(r"[0-9]", masked)) == 2
    assert national[:9] not in masked


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("alice@example.com", "a***@***.com"),
        ("bob.smith+tag@example.org", "b***@***.org"),
        ("first.last@a.b.example.com", "f***@***.com"),
        ("X@EXAMPLE.NET", "X***@***.net"),  # final label lower-cased, first char kept as is
        ("1234@example.test", "1***@***.test"),
    ],
)
def test_email_mask_policy(raw: str, expected: str) -> None:
    assert mask_email(raw) == expected


def test_email_mask_hides_domain_and_rest_of_local_part() -> None:
    masked = mask_email("alice.synthetic@sub.example.com")
    assert "alice" not in masked
    assert "synthetic" not in masked
    assert "sub" not in masked
    assert "example" not in masked


@pytest.mark.parametrize(
    "bad",
    ["", "no-at-sign", "@example.com", "a@nodot", "a@b.c0m", "a@b.", "01700000000", "+8801700"],
)
def test_mask_email_rejects_non_email_shapes(bad: str) -> None:
    with pytest.raises(ValueError, match="supported email address shape"):
        mask_email(bad)


@pytest.mark.parametrize(
    "bad",
    ["", "0170000000", "017000000000", "02700000000", "abc", "+8801700", "99912345678"],
)
def test_mask_phone_rejects_non_phone_shapes(bad: str) -> None:
    with pytest.raises(ValueError, match="supported Bangladeshi mobile number shape"):
        mask_phone(bad)


def test_error_messages_never_contain_the_rejected_value() -> None:
    canary = "CANARY-9f3a-NOT-A-VALID-VALUE"
    for function in (mask_email, mask_phone):
        with pytest.raises(ValueError, match="supported") as info:
            function(canary)
        assert canary not in str(info.value)
        assert canary not in repr(info.value)


def test_masking_never_returns_the_original_value() -> None:
    assert CANARY_PHONE not in mask_phone(CANARY_PHONE)
    assert CANARY_EMAIL not in mask_email(CANARY_EMAIL)
    assert "canary" not in mask_email(CANARY_EMAIL).lower()


def _generated_phone_numbers() -> list[str]:
    """Deterministic (no RNG) synthetic national numbers across all operator prefixes."""
    numbers = []
    for prefix in range(13, 20):
        for step in range(40):
            tail = (step * 2_654_435) % 100_000_000  # arbitrary fixed stride, 8 digits
            numbers.append(f"0{prefix}{tail:08d}")
    return numbers


def _generated_emails() -> list[tuple[str, str]]:
    """Deterministic synthetic addresses on reserved domains: (address, local_part)."""
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789._"
    emails = []
    for tld in ("com", "org", "net"):
        for step in range(40):
            local = "".join(alphabet[(step * 7 + pos * 11) % len(alphabet)] for pos in range(12))
            emails.append((f"{local}@example.{tld}", local))
    return emails


@pytest.mark.parametrize("national", _generated_phone_numbers())
def test_generated_phone_masks_never_leak_more_than_policy_allows(national: str) -> None:
    masked = mask_phone(national)
    assert re.fullmatch(r"\*{9}[0-9]{2}", masked)
    assert masked[-2:] == national[-2:]


@pytest.mark.parametrize(("email", "local"), _generated_emails())
def test_generated_email_masks_never_leak_more_than_policy_allows(email: str, local: str) -> None:
    masked = mask_email(email)
    assert re.fullmatch(r"[^@*]\*\*\*@\*\*\*\.(com|org|net)", masked)
    assert masked[0] == local[0]
    assert local[1:] not in masked

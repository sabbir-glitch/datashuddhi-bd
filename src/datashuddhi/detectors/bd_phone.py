"""Detector for potential Bangladeshi mobile numbers.

What is matched
---------------
A number made of an optional prefix and a 10-digit subscriber part ``1X########`` where
``X`` is 3-9, i.e. the national form ``01X########`` (operator prefixes 013-019). Accepted
spellings (examples use a synthetic number)::

    01700000000            017-00000000        017 00000000
    01700-000000           017 0000 0000
    +8801700000000         +880 1700 000000    +880 17 0000 0000
    008801700000000        +88 01700000000
    8801700000000          (bare 880 prefix, lower confidence)

Bengali digits (U+09E6-U+09EF) are accepted by normalising a length-preserving copy of the
line, so reported columns refer to the unmodified source text. Arabic-Indic digits are
intentionally not normalised.

What a match means
------------------
A match is a *syntactic* match on number shape and operator prefix. It does not mean the
number is assigned, active, or belongs to a person. No official BTRC numbering plan was
located when this rule was written; see docs/data-detection-limitations.md for the
sources consulted and their limits. Order numbers, timestamps, IDs and other digit strings
of the same shape will produce false positives.

Confidence: HIGH when an explicit international prefix (``+`` or ``00``) is present,
MEDIUM otherwise.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from datashuddhi.detectors.base import Detector, RawMatch, Rule
from datashuddhi.findings import Confidence, Severity
from datashuddhi.normalize import normalize_digits
from datashuddhi.redaction import mask_phone

# Subscriber part after the national trunk "0": operator code 1[3-9], then 8 digits, in one of
# the supported groupings (2+8, 4+6, 2+4+4 or ungrouped) using a single space or hyphen.
_SUBSCRIBER = r"1[3-9](?:[0-9]{8}|[ \-][0-9]{8}|[0-9]{2}[ \-][0-9]{6}|[ \-][0-9]{4}[ \-][0-9]{4})"

_PHONE = re.compile(
    r"(?<![0-9])"
    r"(?:"
    r"(?P<intl>(?:\+|00)(?:880[ \-]?|88[ \-]?0))"  # +880.., 00880.., +88 0.., 0088 0..
    r"|(?P<bare>880[ \-]?)"  # 880.. without + or 00
    r"|0"  # national form
    r")"
    rf"{_SUBSCRIBER}"
    r"(?![0-9])",
    re.ASCII,
)

_RULE = Rule(
    rule_id="DS-BDPHONE-001",
    category="bangladeshi_mobile_number",
    severity=Severity.MEDIUM,
    explanation=(
        "Potential Bangladeshi mobile number (syntactic match on number shape and operator "
        "prefix 013-019; not verified as assigned, active or personal)."
    ),
    remediation=(
        "Remove or replace the number with synthetic data before sharing this file, or "
        "confirm that sharing it is authorised and necessary."
    ),
    mask=mask_phone,
)


class BangladeshiPhoneDetector(Detector):
    rule = _RULE

    def find(self, line: str) -> Iterator[RawMatch]:
        normalized = normalize_digits(line)  # same length as ``line``
        for match in _PHONE.finditer(normalized):
            start, end = match.span()
            confidence = Confidence.HIGH if match.group("intl") else Confidence.MEDIUM
            yield RawMatch(start=start, end=end, raw=line[start:end], confidence=confidence)

"""Detector for potential email addresses.

This is a deliberately conservative, ASCII-only pattern, not a full RFC 5322 parser. It
reports *potential* addresses; it never checks that a mailbox or domain exists.

Known limits (also listed in docs/data-detection-limitations.md):

* Internationalised addresses (non-ASCII local parts or domains) are not detected.
* Local-part characters outside ``A-Za-z0-9._%+-`` (for example ``'`` or ``!``) are not
  supported; a local part longer than 64 characters is not matched.
* A domain longer than 253 characters (or with a label over 63 characters) is not a valid DNS
  name and is not reported, not even partly.
* Quoted local parts, comments and IP-literal domains are not detected.
* Retina-style asset names such as ``logo@2x.png`` are suppressed; other look-alikes
  (for example some package specifiers) may still match.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from datashuddhi.detectors.base import Detector, RawMatch, Rule
from datashuddhi.findings import Confidence, Severity
from datashuddhi.redaction import mask_email

_LOCAL_CHARS = r"A-Za-z0-9._%+\-"
# RFC 1035 / RFC 5321: a domain name is at most 253 characters (255 octets on the wire, in
# presentation form without the root dot) and each label at most 63. The regex bounds the label
# count so that backtracking state stays small; the total length is checked after matching.
_MAX_DOMAIN_LENGTH = 253
_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?"

_EMAIL = re.compile(
    rf"(?<![{_LOCAL_CHARS}])"  # start of the local part: never inside a longer token
    rf"[{_LOCAL_CHARS}]{{1,64}}"
    r"@"
    rf"(?:{_LABEL}\.){{1,126}}"  # a DNS name has at most 127 labels: bounded, see tests
    r"[A-Za-z]{2,24}"
    r"(?![A-Za-z0-9])",
    re.ASCII,
)

# "icon@2x.png"-style image names: the "domain" is a pixel-ratio plus an image extension.
_IMAGE_ASSET_DOMAIN = re.compile(
    r"[0-9]{1,2}x\.(?:png|jpe?g|gif|webp|svg|bmp|ico|avif)", re.ASCII | re.IGNORECASE
)

_RULE = Rule(
    rule_id="DS-EMAIL-001",
    category="email_address",
    severity=Severity.LOW,
    explanation=(
        "Potential email address (syntactic match only; not verified to be a real, active "
        "or personal mailbox)."
    ),
    remediation=(
        "Remove or replace the address with synthetic data before sharing this file, or "
        "confirm that sharing it is authorised and necessary."
    ),
    mask=mask_email,
)


class EmailDetector(Detector):
    rule = _RULE

    def find(self, line: str) -> Iterator[RawMatch]:
        for match in _EMAIL.finditer(line):
            start, end = match.span()
            raw = match.group()
            stripped = raw.lstrip(".")  # a leading dot is not part of a plausible local part
            start += len(raw) - len(stripped)
            raw = stripped
            local, _, domain = raw.rpartition("@")
            if not local or len(domain) > _MAX_DOMAIN_LENGTH:
                continue  # not a valid DNS name: dropped whole, never reported as a partial match
            if _IMAGE_ASSET_DOMAIN.fullmatch(domain):
                continue
            yield RawMatch(start=start, end=end, raw=raw, confidence=Confidence.HIGH)

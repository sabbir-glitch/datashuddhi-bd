"""Detectors: small, independent rules that find *potential* personal data in one line."""

from __future__ import annotations

from datashuddhi.detectors.base import Detector, RawMatch, Rule
from datashuddhi.detectors.bd_phone import BangladeshiPhoneDetector
from datashuddhi.detectors.email import EmailDetector


def default_detectors() -> tuple[Detector, ...]:
    """The detectors enabled in v0.1.0 (email addresses and Bangladeshi mobile numbers)."""
    return (EmailDetector(), BangladeshiPhoneDetector())


__all__ = [
    "BangladeshiPhoneDetector",
    "Detector",
    "EmailDetector",
    "RawMatch",
    "Rule",
    "default_detectors",
]

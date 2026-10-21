"""Report rendering. Reports contain masked values only."""

from __future__ import annotations

DISCLAIMER = (
    "Findings are potential matches produced by pattern rules; they are not verified facts. "
    "A result with no findings does not prove that a file contains no personal data. "
    "Version 0.1.0 detects only email addresses and Bangladeshi mobile numbers and does not "
    "implement credential or secret detection."
)

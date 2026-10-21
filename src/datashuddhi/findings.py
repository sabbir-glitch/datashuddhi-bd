"""The ``Finding`` data model.

A ``Finding`` describes a *potential* match. It has no field for the original matched
value, so the value cannot reach reports or logs through this object. Only a masked
value (see :mod:`datashuddhi.redaction`) is stored.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Any

_FINDING_ID_RE = re.compile(r"F-\d{4,}")
_RULE_ID_RE = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+")
_MAX_MASKED_LENGTH = 64


class Severity(enum.IntEnum):
    """Provisional impact if the match were real personal data. Not proof of exposure."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @property
    def label(self) -> str:
        return self.name.lower()

    @classmethod
    def parse(cls, text: str) -> Severity:
        try:
            return cls[text.strip().upper()]
        except KeyError:
            raise ValueError("unknown severity") from None


class Confidence(enum.Enum):
    """How well the text fits the rule's documented format (not who the data belongs to)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def format_finding_id(number: int) -> str:
    """Return a per-scan identifier such as ``F-0001`` (not derived from the value)."""
    if number < 1:
        raise ValueError("finding numbers start at 1")
    return f"F-{number:04d}"


@dataclass(frozen=True, slots=True)
class Finding:
    """One potential match, with the matched value already masked."""

    finding_id: str
    rule_id: str
    category: str
    severity: Severity
    confidence: Confidence
    path: str
    line: int
    column: int
    masked_value: str
    explanation: str
    remediation: str

    def __post_init__(self) -> None:
        # Messages below never include the field values, only the field names.
        if not _FINDING_ID_RE.fullmatch(self.finding_id):
            raise ValueError("finding_id has an invalid format")
        if not _RULE_ID_RE.fullmatch(self.rule_id):
            raise ValueError("rule_id has an invalid format")
        if not self.category or not self.category.isidentifier():
            raise ValueError("category must be a simple identifier")
        if not isinstance(self.severity, Severity):
            raise TypeError("severity must be a Severity")
        if not isinstance(self.confidence, Confidence):
            raise TypeError("confidence must be a Confidence")
        if not self.path or "\x00" in self.path or self.path.startswith(("/", "\\")):
            raise ValueError("path must be a non-empty relative path")
        if ".." in self.path.split("/"):
            raise ValueError("path must not contain '..' segments")
        if self.line < 1 or self.column < 1:
            raise ValueError("line and column are 1-based")
        if not self.masked_value or len(self.masked_value) > _MAX_MASKED_LENGTH:
            raise ValueError("masked_value is empty or too long")
        if "*" not in self.masked_value or not self.masked_value.isprintable():
            raise ValueError("masked_value does not look masked")
        if not self.explanation or not self.remediation:
            raise ValueError("explanation and remediation are required")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary (still contains only the masked value)."""
        return {
            "id": self.finding_id,
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity.label,
            "confidence": self.confidence.value,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "masked_value": self.masked_value,
            "explanation": self.explanation,
            "remediation": self.remediation,
        }

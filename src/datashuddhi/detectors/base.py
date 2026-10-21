"""Detector interface and the transient match type.

A :class:`RawMatch` holds the matched text so that the rule's mask function can be applied.
It exists only between a detector and the scanner. It is *never* stored in a
:class:`~datashuddhi.findings.Finding`, and its ``raw`` field is excluded from ``repr``.
"""

from __future__ import annotations

import abc
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from datashuddhi.findings import Confidence, Finding, Severity

_RULE_ID = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+")


@dataclass(frozen=True, slots=True)
class RawMatch:
    """A potential match inside one line. Offsets are 0-based code-point indexes."""

    start: int
    end: int
    raw: str = field(repr=False)
    confidence: Confidence

    def __post_init__(self) -> None:
        if not 0 <= self.start < self.end:
            raise ValueError("match offsets are invalid")


@dataclass(frozen=True, slots=True)
class Rule:
    """Static description of a detection rule."""

    rule_id: str
    category: str
    severity: Severity
    explanation: str
    remediation: str
    mask: Callable[[str], str] = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if not _RULE_ID.fullmatch(self.rule_id):
            raise ValueError("rule_id has an invalid format")
        if not self.category.isidentifier():
            raise ValueError("category must be a simple identifier")

    def build_finding(
        self,
        match: RawMatch,
        *,
        finding_id: str,
        path: str,
        line: int,
        column: int,
    ) -> Finding:
        """Create a masked :class:`Finding`. The raw text is not retained."""
        return Finding(
            finding_id=finding_id,
            rule_id=self.rule_id,
            category=self.category,
            severity=self.severity,
            confidence=match.confidence,
            path=path,
            line=line,
            column=column,
            masked_value=self.mask(match.raw),
            explanation=self.explanation,
            remediation=self.remediation,
        )


class Detector(abc.ABC):
    """Finds potential matches in a single line of text (no newline characters)."""

    rule: Rule

    @abc.abstractmethod
    def find(self, line: str) -> Iterator[RawMatch]:
        """Yield matches in order of position. Must not raise on arbitrary text."""

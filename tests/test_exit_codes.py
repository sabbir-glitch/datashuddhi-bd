"""Tests for the exit-code decision rule."""

from __future__ import annotations

import pytest

from datashuddhi.config import FailOn
from datashuddhi.exit_codes import (
    EXIT_FATAL,
    EXIT_FINDINGS,
    EXIT_OK,
    EXIT_USAGE,
    decide_exit,
    threshold_reached,
)
from datashuddhi.findings import Confidence, Finding, Severity


def finding(severity: Severity) -> Finding:
    return Finding(
        finding_id="F-0001",
        rule_id="DS-TEST-001",
        category="test_category",
        severity=severity,
        confidence=Confidence.HIGH,
        path="a.txt",
        line=1,
        column=1,
        masked_value="a***",
        explanation="e",
        remediation="r",
    )


def test_documented_code_values() -> None:
    assert (EXIT_OK, EXIT_FINDINGS, EXIT_USAGE, EXIT_FATAL) == (0, 1, 2, 3)


@pytest.mark.parametrize(
    ("severities", "fail_on", "reached"),
    [
        ((), FailOn.LOW, False),
        ((Severity.LOW,), FailOn.LOW, True),
        ((Severity.LOW,), FailOn.MEDIUM, False),
        ((Severity.LOW,), FailOn.HIGH, False),
        ((Severity.MEDIUM,), FailOn.LOW, True),
        ((Severity.MEDIUM,), FailOn.MEDIUM, True),
        ((Severity.MEDIUM,), FailOn.HIGH, False),
        ((Severity.HIGH,), FailOn.HIGH, True),
        ((Severity.LOW, Severity.HIGH), FailOn.HIGH, True),
        ((Severity.HIGH,), FailOn.NEVER, False),
        ((Severity.LOW, Severity.MEDIUM, Severity.HIGH), FailOn.NEVER, False),
    ],
)
def test_threshold(severities: tuple[Severity, ...], fail_on: FailOn, reached: bool) -> None:
    assert threshold_reached(tuple(finding(s) for s in severities), fail_on) is reached


@pytest.mark.parametrize(
    ("severities", "complete", "fail_on", "expected"),
    [
        ((), True, FailOn.LOW, 0),
        ((), True, FailOn.NEVER, 0),
        ((Severity.LOW,), True, FailOn.LOW, 1),
        ((Severity.LOW,), True, FailOn.MEDIUM, 0),
        ((Severity.LOW,), True, FailOn.NEVER, 0),
        ((Severity.MEDIUM,), False, FailOn.LOW, 1),  # findings take priority
        ((), False, FailOn.LOW, 3),  # incomplete and clean is NOT a pass
        ((), False, FailOn.NEVER, 3),  # "never" does not hide an incomplete scan
        ((Severity.LOW,), False, FailOn.HIGH, 3),  # below threshold and incomplete
        ((Severity.LOW,), False, FailOn.NEVER, 3),
    ],
)
def test_decide_exit(
    severities: tuple[Severity, ...], complete: bool, fail_on: FailOn, expected: int
) -> None:
    findings = tuple(finding(s) for s in severities)
    assert decide_exit(findings=findings, complete=complete, fail_on=fail_on) == expected

"""Process exit codes and the decision rule that maps a scan result to one.

====  ==========================================================================
Code  Meaning
====  ==========================================================================
0     The scan was complete and no finding reached the ``--fail-on`` threshold.
1     At least one finding reached the threshold (the report says whether the scan
      was also incomplete).
2     Usage or configuration error (bad arguments, missing or unsupported path,
      unsafe output path). No scan result exists.
3     Fatal scan failure, interrupt, or an *unreliable* result: the scan was incomplete
      (something was skipped or a limit was hit) and no finding reached the threshold.
====  ==========================================================================

``--fail-on never`` removes only the finding-based failure. An incomplete scan still
returns 3, so that a partial scan can never be mistaken for a clean one.
"""

from __future__ import annotations

from datashuddhi.config import FailOn
from datashuddhi.findings import Finding, Severity

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_FATAL = 3


def threshold_reached(findings: tuple[Finding, ...], fail_on: FailOn) -> bool:
    if fail_on is FailOn.NEVER:
        return False
    threshold = Severity.parse(fail_on.value)
    return any(finding.severity >= threshold for finding in findings)


def decide_exit(*, findings: tuple[Finding, ...], complete: bool, fail_on: FailOn) -> int:
    if threshold_reached(findings, fail_on):
        return EXIT_FINDINGS
    if not complete:
        return EXIT_FATAL
    return EXIT_OK

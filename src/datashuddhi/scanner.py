"""Scan orchestration: discovery -> bounded read -> detectors -> masked findings.

Privacy rules enforced here
---------------------------
* Matched text lives only in a local variable between the detector and the rule's mask
  function. Only masked values reach a :class:`~datashuddhi.findings.Finding`.
* Failures are recorded as fixed-string issues (kind, relative path, errno name). Exception
  *text* is never stored, because it could contain file content or paths.
* If masking or a detector fails, the scanner fails closed: it records an
  ``internal_error`` issue (so the scan is "incomplete") and keeps no value.
* Scanned files are only read, never written or executed.

Completeness
------------
A scan is *complete* only if no issue was recorded. Reaching the findings limit, the file
limit, or skipping a file for any unexpected reason makes the scan incomplete.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from datashuddhi.config import ScanLimits, ScanOptions
from datashuddhi.detectors import Detector, RawMatch, default_detectors
from datashuddhi.discovery import discover
from datashuddhi.findings import Finding, Severity, format_finding_id
from datashuddhi.issues import IssueKind, IssueLog
from datashuddhi.reader import NotRead, read_text, split_lines


@dataclass(frozen=True, slots=True)
class ScanResult:
    root_name: str
    findings: tuple[Finding, ...]
    log: IssueLog
    limits: ScanLimits
    exclude: tuple[str, ...]
    files_discovered: int
    files_scanned: int
    files_not_scanned: int
    excluded_dirs: int
    excluded_files: int
    unsupported_files: int
    findings_truncated: bool
    rule_ids: tuple[str, ...] = field(default=())

    @property
    def complete(self) -> bool:
        return not self.log.incomplete

    @property
    def status(self) -> str:
        return "complete" if self.complete else "incomplete"

    def count_by_severity(self) -> dict[str, int]:
        counts = {severity.label: 0 for severity in Severity}
        for finding in self.findings:
            counts[finding.severity.label] += 1
        return counts

    def count_by_rule(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in self.findings:
            counts[finding.rule_id] = counts.get(finding.rule_id, 0) + 1
        return counts


def scan_path(
    path: str,
    options: ScanOptions | None = None,
    detectors: Sequence[Detector] | None = None,
) -> ScanResult:
    """Scan ``path`` (a directory or one supported file) and return masked findings.

    Raises :class:`~datashuddhi.errors.InvalidScanRootError` if the root is unusable.
    """
    options = options or ScanOptions()
    active = tuple(detectors) if detectors is not None else default_detectors()
    log = IssueLog()
    discovery = discover(path, options, log)

    findings: list[Finding] = []
    scanned = 0
    not_scanned = 0
    truncated = False
    max_findings = options.limits.max_findings

    for found in discovery.files:
        content = read_text(found.path, options.limits.max_file_bytes)
        if isinstance(content, NotRead):
            log.add(content.kind, found.rel, content.detail)
            not_scanned += 1
            continue
        if content.replaced:
            log.add(IssueKind.DECODE_REPLACED, found.rel)

        failed = False
        for line_number, line in enumerate(split_lines(content.text), start=1):
            if not line:
                continue
            pairs: list[tuple[Detector, RawMatch]] = []
            for detector in active:
                try:
                    pairs.extend((detector, match) for match in detector.find(line))
                except Exception:  # fail closed; the exception text is deliberately dropped
                    log.add(IssueKind.INTERNAL_ERROR, found.rel, "detector_failed")
                    failed = True
            pairs.sort(key=lambda pair: (pair[1].start, pair[0].rule.rule_id))
            for detector, match in pairs:
                if len(findings) >= max_findings:
                    truncated = True
                    break
                try:
                    finding = detector.rule.build_finding(
                        match,
                        finding_id=format_finding_id(len(findings) + 1),
                        path=found.rel,
                        line=line_number,
                        column=match.start + 1,
                    )
                except Exception:  # fail closed; never keep or format the value
                    log.add(IssueKind.INTERNAL_ERROR, found.rel, "finding_rejected")
                    failed = True
                    continue
                findings.append(finding)
            if truncated:
                break
        if truncated:
            log.add(IssueKind.FINDING_LIMIT_REACHED)
            not_scanned += 1
            break
        if failed:
            not_scanned += 1
        else:
            scanned += 1

    if truncated:
        # Files after the one that hit the limit were never examined.
        not_scanned = len(discovery.files) - scanned

    return ScanResult(
        root_name=discovery.root_name,
        findings=tuple(findings),
        log=log,
        limits=options.limits,
        exclude=options.exclude,
        files_discovered=len(discovery.files),
        files_scanned=scanned,
        files_not_scanned=not_scanned,
        excluded_dirs=discovery.excluded_dirs,
        excluded_files=discovery.excluded_files,
        unsupported_files=discovery.unsupported_files,
        findings_truncated=truncated,
        rule_ids=tuple(d.rule.rule_id for d in active),
    )

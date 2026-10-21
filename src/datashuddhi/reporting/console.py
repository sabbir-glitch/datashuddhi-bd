"""Human-readable report.

Everything derived from the file system (paths, the root name) is passed through
:func:`sanitize` so that control characters and bidirectional-text overrides in file names
cannot corrupt or spoof the terminal.
"""

from __future__ import annotations

import unicodedata
from typing import TextIO

from datashuddhi import __version__
from datashuddhi.config import FailOn
from datashuddhi.exit_codes import EXIT_FATAL, EXIT_FINDINGS, EXIT_OK, EXIT_USAGE
from datashuddhi.exit_codes import threshold_reached as _threshold_reached
from datashuddhi.reporting import DISCLAIMER
from datashuddhi.scanner import ScanResult

_UNSAFE_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})

EXIT_MEANING = {
    EXIT_OK: "scan complete, no finding reached the --fail-on threshold",
    EXIT_FINDINGS: "at least one finding reached the --fail-on threshold",
    EXIT_USAGE: "usage or configuration error",
    EXIT_FATAL: "scan incomplete or failed; the result is not a complete clean scan",
}


def sanitize(text: str) -> str:
    """Escape control, format (including bidi), surrogate, private-use and unassigned chars."""
    pieces: list[str] = []
    for char in text:
        if char != " " and unicodedata.category(char) in _UNSAFE_CATEGORIES:
            code = ord(char)
            if code <= 0xFF:
                pieces.append(f"\\x{code:02x}")
            elif code <= 0xFFFF:
                pieces.append(f"\\u{code:04x}")
            else:
                pieces.append(f"\\U{code:08x}")
        else:
            pieces.append(char)
    return "".join(pieces)


def encodable_for(text: str, stream: TextIO) -> str:
    """Return ``text`` with anything the stream's encoding cannot represent backslash-escaped."""
    encoding = getattr(stream, "encoding", None) or "utf-8"
    try:
        return text.encode(encoding, errors="backslashreplace").decode(encoding, errors="strict")
    except (LookupError, UnicodeError):
        return text.encode("ascii", errors="backslashreplace").decode("ascii")


def render_text(result: ScanResult, fail_on: FailOn, exit_code: int) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"DataShuddhi BD {__version__} - potential personal data scan")
    add(f"Scan root: {sanitize(result.root_name)}")
    status = "COMPLETE" if result.complete else "INCOMPLETE - NOT a complete clean scan"
    add(f"Status: {status}")
    add(
        f"Files: {result.files_discovered} found, {result.files_scanned} scanned, "
        f"{result.files_not_scanned} not scanned"
    )
    add(
        f"Skipped on purpose (not issues): {result.excluded_dirs} excluded directories, "
        f"{result.excluded_files} excluded files, {result.unsupported_files} unsupported file types"
    )
    severity = result.count_by_severity()
    add(
        f"Potential findings: {len(result.findings)} "
        f"(high {severity['high']}, medium {severity['medium']}, low {severity['low']})"
    )
    add("")

    if result.findings:
        for finding in result.findings:
            add(
                f"{finding.finding_id} [{finding.severity.label.upper()}, "
                f"confidence {finding.confidence.value}] {finding.rule_id} {finding.category}"
            )
            location = f"{sanitize(finding.path)}:{finding.line}:{finding.column}"
            add(f"  {location}  {finding.masked_value}")
            add(f"  {finding.explanation}")
            add(f"  Next step: {finding.remediation}")
            add("")
    else:
        add("No potential findings were reported for the files that were scanned.")
        add("")

    log = result.log
    if log.issue_total:
        add(f"Issues ({log.issue_total}) - these make the scan incomplete:")
        for issue in log.issues:
            where = sanitize(issue.path) if issue.path else "(scan-wide)"
            detail = f" ({sanitize(issue.detail)})" if issue.detail else ""
            add(f"  - {issue.kind.value}: {where}{detail}")
        if log.issues_omitted:
            add(f"  ... {log.issues_omitted} more issues not listed")
        add("")
    if log.warning_total:
        add(f"Warnings ({log.warning_total}) - these do not make the scan incomplete:")
        for warning in log.warnings:
            where = sanitize(warning.path) if warning.path else "(scan-wide)"
            add(f"  - {warning.kind.value}: {where}")
        if log.warnings_omitted:
            add(f"  ... {log.warnings_omitted} more warnings not listed")
        add("")
    if result.findings_truncated:
        add(
            "The findings limit was reached: later matches were not collected. "
            "Raise --max-findings to see more."
        )
        add("")

    reached = _threshold_reached(result.findings, fail_on)
    add(f"Fail threshold (--fail-on): {fail_on.value}; reached: {'yes' if reached else 'no'}")
    add(f"Exit code: {exit_code} ({EXIT_MEANING[exit_code]})")
    add("")
    add(f"Note: {DISCLAIMER}")
    return "\n".join(lines) + "\n"


def render_summary(result: ScanResult, exit_code: int) -> str:
    """Short summary printed when the full report goes to ``--output``."""
    severity = result.count_by_severity()
    status = "complete" if result.complete else "INCOMPLETE (not a complete clean scan)"
    return (
        f"Scan {status}: {len(result.findings)} potential findings "
        f"(high {severity['high']}, medium {severity['medium']}, low {severity['low']}); "
        f"{result.files_scanned} of {result.files_discovered} files scanned.\n"
        f"Exit code: {exit_code} ({EXIT_MEANING[exit_code]})\n"
    )

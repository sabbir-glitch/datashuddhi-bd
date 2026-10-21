"""Scan issues and warnings.

Completeness model
------------------
* An **issue** means something that should have been scanned was not (or not fully):
  the scan result is *incomplete* and must never be presented as a complete clean scan.
* A **warning** does not make the result incomplete (for example, bytes that could not be
  decoded were replaced, but the rest of the file was scanned).
* Files and directories that are skipped on purpose (default exclusions, ``--exclude``,
  unsupported file types) are only *counted*; they are not issues.

Issue details are short fixed strings (for example an errno name). They never contain
file content, matched values, or operating-system error messages.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class IssueKind(enum.StrEnum):
    TOO_LARGE = "too_large"
    BINARY_CONTENT = "binary_content"
    UNSUPPORTED_ENCODING = "unsupported_encoding"
    UNREADABLE = "unreadable"
    UNREADABLE_DIRECTORY = "unreadable_directory"
    LINK_NOT_FOLLOWED = "link_not_followed"
    OUTSIDE_SCOPE = "outside_scope"
    NOT_REGULAR_FILE = "not_regular_file"
    FILE_LIMIT_REACHED = "file_limit_reached"
    FINDING_LIMIT_REACHED = "finding_limit_reached"
    INTERNAL_ERROR = "internal_error"
    DECODE_REPLACED = "decode_replaced"  # warning only


WARNING_KINDS = frozenset({IssueKind.DECODE_REPLACED})

MAX_LOGGED_ENTRIES = 1000


@dataclass(frozen=True, slots=True)
class ScanIssue:
    kind: IssueKind
    path: str | None = None  # relative path with '/' separators, or None for scan-wide issues
    detail: str = ""

    def to_dict(self) -> dict[str, str | None]:
        return {"kind": self.kind.value, "path": self.path, "detail": self.detail}


@dataclass(slots=True)
class IssueLog:
    """Collects issues and warnings; stores at most ``max_entries`` of each but counts all."""

    max_entries: int = MAX_LOGGED_ENTRIES
    issues: list[ScanIssue] = field(default_factory=list)
    warnings: list[ScanIssue] = field(default_factory=list)
    counts: dict[IssueKind, int] = field(default_factory=dict)

    def add(self, kind: IssueKind, path: str | None = None, detail: str = "") -> None:
        self.counts[kind] = self.counts.get(kind, 0) + 1
        target = self.warnings if kind in WARNING_KINDS else self.issues
        if len(target) < self.max_entries:
            target.append(ScanIssue(kind, path, detail))

    @property
    def issue_total(self) -> int:
        return sum(n for kind, n in self.counts.items() if kind not in WARNING_KINDS)

    @property
    def warning_total(self) -> int:
        return sum(n for kind, n in self.counts.items() if kind in WARNING_KINDS)

    @property
    def issues_omitted(self) -> int:
        return self.issue_total - len(self.issues)

    @property
    def warnings_omitted(self) -> int:
        return self.warning_total - len(self.warnings)

    @property
    def incomplete(self) -> bool:
        """True if anything that should have been scanned was not scanned in full."""
        return self.issue_total > 0

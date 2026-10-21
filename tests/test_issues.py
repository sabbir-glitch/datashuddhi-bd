"""Tests for the issue/warning log and the completeness model."""

from __future__ import annotations

from datashuddhi.issues import MAX_LOGGED_ENTRIES, IssueKind, IssueLog, ScanIssue


def test_empty_log_is_complete() -> None:
    log = IssueLog()
    assert not log.incomplete
    assert log.issue_total == 0
    assert log.warning_total == 0


def test_warnings_do_not_make_a_scan_incomplete() -> None:
    log = IssueLog()
    log.add(IssueKind.DECODE_REPLACED, "a.txt")
    assert not log.incomplete
    assert log.warning_total == 1
    assert log.issue_total == 0
    assert log.warnings == [ScanIssue(IssueKind.DECODE_REPLACED, "a.txt")]
    assert log.issues == []


def test_every_non_warning_kind_makes_a_scan_incomplete() -> None:
    for kind in IssueKind:
        if kind is IssueKind.DECODE_REPLACED:
            continue
        log = IssueLog()
        log.add(kind, "x.txt")
        assert log.incomplete, kind


def test_entries_are_capped_but_counted() -> None:
    log = IssueLog(max_entries=3)
    for i in range(10):
        log.add(IssueKind.UNREADABLE, f"f{i}.txt", "EACCES")
    for i in range(5):
        log.add(IssueKind.DECODE_REPLACED, f"w{i}.txt")
    assert len(log.issues) == 3
    assert log.issue_total == 10
    assert log.issues_omitted == 7
    assert len(log.warnings) == 3
    assert log.warning_total == 5
    assert log.warnings_omitted == 2
    assert log.counts[IssueKind.UNREADABLE] == 10


def test_default_cap_is_documented_value() -> None:
    assert MAX_LOGGED_ENTRIES == 1000
    log = IssueLog()
    for i in range(MAX_LOGGED_ENTRIES + 5):
        log.add(IssueKind.TOO_LARGE, f"f{i}.log")
    assert len(log.issues) == MAX_LOGGED_ENTRIES
    assert log.issues_omitted == 5


def test_issue_serialisation_has_only_safe_fields() -> None:
    issue = ScanIssue(IssueKind.TOO_LARGE, "logs/big.log")
    assert issue.to_dict() == {"kind": "too_large", "path": "logs/big.log", "detail": ""}

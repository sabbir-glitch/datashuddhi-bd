"""End-to-end tests of scan_path (no CLI)."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from datashuddhi import reader
from datashuddhi.config import ScanLimits, ScanOptions
from datashuddhi.detectors import Detector, EmailDetector, RawMatch, Rule, default_detectors
from datashuddhi.errors import InvalidScanRootError
from datashuddhi.findings import Confidence, Severity
from datashuddhi.issues import IssueKind
from datashuddhi.scanner import ScanResult, scan_path
from tests.synthetic import to_bengali_digits

EMAIL = "alice@example.com"
PHONE = "01712345678"


def put(root: Path, rel: str, data: str | bytes, encoding: str = "utf-8") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode(encoding))
    return path


def scan(root: Path, **kwargs: object) -> ScanResult:
    limits = kwargs.pop("limits", None)
    exclude = kwargs.pop("exclude", ())
    options = ScanOptions(limits=limits or ScanLimits(), exclude=exclude)  # type: ignore[arg-type]
    return scan_path(str(root), options, **kwargs)  # type: ignore[arg-type]


def positions(result: ScanResult) -> list[tuple[str, int, int, str]]:
    return [(f.path, f.line, f.column, f.rule_id) for f in result.findings]


def test_clean_directory_is_a_complete_scan_with_no_findings(tmp_path: Path) -> None:
    put(tmp_path, "a.txt", "nothing to see here\n")
    result = scan(tmp_path)
    assert result.findings == ()
    assert result.complete
    assert result.status == "complete"
    assert (result.files_discovered, result.files_scanned, result.files_not_scanned) == (1, 1, 0)


def test_every_supported_type_is_scanned(tmp_path: Path) -> None:
    for name in ["a.txt", "b.csv", "c.json", "d.log", "e.ini", "f.toml", "g.yaml", "h.yml", ".env"]:
        put(tmp_path, name, f"contact={EMAIL}\n")
    result = scan(tmp_path)
    assert len(result.findings) == 9
    assert result.files_scanned == 9
    assert result.complete


def test_findings_are_masked_ordered_and_numbered(tmp_path: Path) -> None:
    put(tmp_path, "b.txt", f"{PHONE}\n")
    put(tmp_path, "a.txt", f"x\nuser {EMAIL} and +880{PHONE[1:]}\n")
    result = scan(tmp_path)
    assert [f.finding_id for f in result.findings] == ["F-0001", "F-0002", "F-0003"]
    assert positions(result) == [
        ("a.txt", 2, 6, "DS-EMAIL-001"),
        ("a.txt", 2, 28, "DS-BDPHONE-001"),
        ("b.txt", 1, 1, "DS-BDPHONE-001"),
    ]
    assert [f.masked_value for f in result.findings] == [
        "a***@***.com",
        "*********78",
        "*********78",
    ]
    assert [f.severity for f in result.findings] == [Severity.LOW, Severity.MEDIUM, Severity.MEDIUM]
    assert result.findings[1].confidence is Confidence.HIGH
    assert result.findings[2].confidence is Confidence.MEDIUM
    assert result.count_by_severity() == {"low": 1, "medium": 2, "high": 0}
    assert result.count_by_rule() == {"DS-EMAIL-001": 1, "DS-BDPHONE-001": 2}


def test_scan_is_deterministic(tmp_path: Path) -> None:
    for i in range(5):
        put(tmp_path, f"d{i}/f.txt", f"{EMAIL} {PHONE}\n")
    first, second = scan(tmp_path), scan(tmp_path)
    assert first.findings == second.findings


def test_overlapping_matches_from_different_rules_are_both_reported(tmp_path: Path) -> None:
    put(tmp_path, "a.txt", f"{PHONE}@example.com\n")
    rules = [f.rule_id for f in scan(tmp_path).findings]
    assert rules == [
        "DS-BDPHONE-001",
        "DS-EMAIL-001",
    ]  # same start offset: ordered by rule id


def test_line_endings_crlf_cr_and_lf(tmp_path: Path) -> None:
    put(tmp_path, "crlf.txt", f"one\r\n{EMAIL}\r\n")
    put(tmp_path, "cr.txt", f"one\r{EMAIL}\r")
    put(tmp_path, "lf.txt", f"one\n{EMAIL}\n")
    result = scan(tmp_path)
    assert [(f.path, f.line, f.column) for f in result.findings] == [
        ("cr.txt", 2, 1),
        ("crlf.txt", 2, 1),
        ("lf.txt", 2, 1),
    ]


def test_bengali_digits_report_source_columns(tmp_path: Path) -> None:
    line = "ফোন: " + to_bengali_digits(PHONE) + "\n"
    put(tmp_path, "bn.txt", line)
    (finding,) = scan(tmp_path).findings
    assert (finding.line, finding.column) == (1, 6)
    assert finding.masked_value == "*********78"


def test_utf8_bom_does_not_shift_columns(tmp_path: Path) -> None:
    put(tmp_path, "bom.txt", b"\xef\xbb\xbf" + EMAIL.encode())
    (finding,) = scan(tmp_path).findings
    assert (finding.line, finding.column) == (1, 1)


@pytest.mark.parametrize("codec", ["utf-16-le", "utf-16-be"])
def test_utf16_with_bom_is_scanned(tmp_path: Path, codec: str) -> None:
    bom = b"\xff\xfe" if codec == "utf-16-le" else b"\xfe\xff"
    put(tmp_path, "ps.log", bom + f"INFO\r\nuser {EMAIL}\r\ncall {PHONE}\r\n".encode(codec))
    result = scan(tmp_path)
    assert positions(result) == [
        ("ps.log", 2, 6, "DS-EMAIL-001"),
        ("ps.log", 3, 6, "DS-BDPHONE-001"),
    ]
    assert result.complete


def test_non_bmp_characters_count_as_one_column(tmp_path: Path) -> None:
    put(tmp_path, "emoji.txt", f"\U0001f600\U0001f600 {EMAIL}")
    (finding,) = scan(tmp_path).findings
    assert finding.column == 4


def test_single_file_root(tmp_path: Path) -> None:
    path = put(tmp_path, "one.csv", f"{EMAIL}\n")
    result = scan_path(str(path))
    assert [f.path for f in result.findings] == ["one.csv"]
    assert result.root_name == "one.csv"


def test_invalid_root_raises_usage_error(tmp_path: Path) -> None:
    with pytest.raises(InvalidScanRootError):
        scan_path(str(tmp_path / "missing"))


def test_oversize_file_makes_the_scan_incomplete(tmp_path: Path) -> None:
    put(tmp_path, "big.log", "x" * 200)
    put(tmp_path, "ok.txt", f"{EMAIL}\n")
    result = scan(tmp_path, limits=ScanLimits(max_file_bytes=100))
    assert len(result.findings) == 1
    assert not result.complete
    assert [(i.kind, i.path) for i in result.log.issues] == [(IssueKind.TOO_LARGE, "big.log")]
    assert (result.files_scanned, result.files_not_scanned) == (1, 1)


def test_binary_and_utf32_files_are_reported(tmp_path: Path) -> None:
    put(tmp_path, "bin.txt", b"abc\x00" + EMAIL.encode())
    put(tmp_path, "u32.txt", b"\xff\xfe\x00\x00a\x00\x00\x00")
    result = scan(tmp_path)
    assert result.findings == ()
    assert not result.complete
    kinds = sorted(i.kind for i in result.log.issues)
    assert kinds == [IssueKind.BINARY_CONTENT, IssueKind.UNSUPPORTED_ENCODING]


def test_invalid_utf8_is_a_warning_and_the_file_is_still_scanned(tmp_path: Path) -> None:
    put(tmp_path, "a.txt", b"junk \xff\xfe \xc3( " + EMAIL.encode() + b"\n")
    result = scan(tmp_path)
    assert len(result.findings) == 1
    assert result.complete  # a warning does not make the scan incomplete
    assert [(w.kind, w.path) for w in result.log.warnings] == [(IssueKind.DECODE_REPLACED, "a.txt")]


def test_unreadable_file_is_reported_with_errno_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    put(tmp_path, "a.txt", f"{EMAIL}\n")

    def deny(*args: object, **kwargs: object) -> int:
        raise PermissionError(13, f"denied reading {EMAIL}")

    monkeypatch.setattr(reader.os, "open", deny)
    result = scan(tmp_path)
    assert not result.complete
    (issue,) = result.log.issues
    assert (issue.kind, issue.path, issue.detail) == (IssueKind.UNREADABLE, "a.txt", "EACCES")
    assert EMAIL not in repr(result)


def test_file_limit_is_reported_as_incomplete(tmp_path: Path) -> None:
    for i in range(4):
        put(tmp_path, f"f{i}.txt", f"{EMAIL}\n")
    result = scan(tmp_path, limits=ScanLimits(max_files=2))
    assert len(result.findings) == 2
    assert not result.complete
    assert result.log.counts[IssueKind.FILE_LIMIT_REACHED] == 1


def test_findings_limit_truncates_and_is_reported(tmp_path: Path) -> None:
    put(tmp_path, "a.txt", "\n".join([EMAIL] * 5))
    put(tmp_path, "b.txt", f"{EMAIL}\n")
    result = scan(tmp_path, limits=ScanLimits(max_findings=3))
    assert len(result.findings) == 3
    assert result.findings_truncated
    assert not result.complete
    assert result.log.counts[IssueKind.FINDING_LIMIT_REACHED] == 1
    assert result.files_scanned + result.files_not_scanned == result.files_discovered
    assert result.files_not_scanned == 2


def test_exactly_the_findings_limit_is_complete(tmp_path: Path) -> None:
    put(tmp_path, "a.txt", "\n".join([EMAIL] * 3))
    result = scan(tmp_path, limits=ScanLimits(max_findings=3))
    assert len(result.findings) == 3
    assert not result.findings_truncated
    assert result.complete


def test_limit_one_with_two_matches_on_one_line(tmp_path: Path) -> None:
    put(tmp_path, "a.txt", f"{EMAIL} {PHONE}\n")
    result = scan(tmp_path, limits=ScanLimits(max_findings=1))
    assert len(result.findings) == 1
    assert result.findings_truncated
    assert not result.complete


def test_exclusions_are_counted_but_do_not_make_the_scan_incomplete(tmp_path: Path) -> None:
    put(tmp_path, "keep.txt", "clean\n")
    put(tmp_path, "node_modules/x.txt", f"{EMAIL}\n")
    put(tmp_path, "skip.log", f"{EMAIL}\n")
    put(tmp_path, "tool.py", f"{EMAIL}\n")
    result = scan(tmp_path, exclude=("*.log",))
    assert result.findings == ()
    assert result.complete
    assert (result.excluded_dirs, result.excluded_files, result.unsupported_files) == (1, 1, 1)


def test_symlinks_are_not_followed_and_make_the_scan_incomplete(tmp_path: Path) -> None:
    outside = put(tmp_path / "outside", "secret.txt", f"{EMAIL}\n")
    scan_root = tmp_path / "scan"
    put(scan_root, "ok.txt", "clean\n")
    try:
        (scan_root / "link.txt").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    result = scan(scan_root)
    assert result.findings == ()
    assert not result.complete
    assert result.log.counts[IssueKind.LINK_NOT_FOLLOWED] == 1


class _Boom(Detector):
    rule = EmailDetector.rule

    def find(self, line: str) -> Iterator[RawMatch]:
        raise RuntimeError(f"CANARY-DETECTOR-FAILURE {line}")
        yield  # pragma: no cover


def test_detector_failure_fails_closed_without_keeping_the_exception_text(tmp_path: Path) -> None:
    put(tmp_path, "a.txt", f"{EMAIL}\n")
    result = scan(tmp_path, detectors=[_Boom()])
    assert not result.complete
    assert result.findings == ()
    (issue,) = result.log.issues
    assert (issue.kind, issue.detail) == (IssueKind.INTERNAL_ERROR, "detector_failed")
    assert "CANARY" not in repr(result)
    assert EMAIL not in repr(result)


def test_mask_failure_fails_closed_and_keeps_no_value(tmp_path: Path) -> None:
    def bad_mask(raw: str) -> str:
        raise ValueError(f"CANARY-MASK-FAILURE {raw}")

    rule = Rule(
        rule_id="DS-TEST-001",
        category="test_category",
        severity=Severity.LOW,
        explanation="e",
        remediation="r",
        mask=bad_mask,
    )

    class Custom(EmailDetector):
        pass

    Custom.rule = rule
    put(tmp_path, "a.txt", f"{EMAIL}\n")
    result = scan(tmp_path, detectors=[Custom()])
    assert result.findings == ()
    assert not result.complete
    assert result.log.issues[0].detail == "finding_rejected"
    assert "CANARY" not in repr(result)
    assert EMAIL not in repr(result)


def test_mask_returning_something_invalid_is_rejected(tmp_path: Path) -> None:
    rule = Rule(
        rule_id="DS-TEST-001",
        category="test_category",
        severity=Severity.LOW,
        explanation="e",
        remediation="r",
        mask=lambda raw: raw,  # a broken mask that returns the raw value (no asterisk)
    )

    class Custom(EmailDetector):
        pass

    Custom.rule = rule
    put(tmp_path, "a.txt", f"{EMAIL}\n")
    result = scan(tmp_path, detectors=[Custom()])
    assert result.findings == ()  # Finding validation refuses an unmasked value
    assert not result.complete


def test_empty_detector_list_is_a_complete_scan_with_no_findings(tmp_path: Path) -> None:
    put(tmp_path, "a.txt", f"{EMAIL}\n")
    result = scan(tmp_path, detectors=[])
    assert result.findings == ()
    assert result.complete
    assert result.rule_ids == ()


def test_rule_ids_are_recorded(tmp_path: Path) -> None:
    put(tmp_path, "a.txt", "x\n")
    assert scan(tmp_path).rule_ids == tuple(d.rule.rule_id for d in default_detectors())


def _snapshot(root: Path) -> dict[str, tuple[int, int, str]]:
    snapshot = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            stat = path.stat()
            snapshot[path.relative_to(root).as_posix()] = (
                stat.st_size,
                stat.st_mtime_ns,
                hashlib.sha256(data).hexdigest(),
            )
        else:
            snapshot[path.relative_to(root).as_posix() + "/"] = (0, 0, "")
    return snapshot


def test_scanning_never_modifies_or_creates_files(tmp_path: Path) -> None:
    put(tmp_path, "a.txt", f"{EMAIL}\r\n{PHONE}\n")
    put(tmp_path, "sub/b.csv", b"\xef\xbb\xbf" + EMAIL.encode())
    put(tmp_path, "sub/c.log", b"\xff\xfe" + f"{EMAIL}".encode("utf-16-le"))
    put(tmp_path, "bad.txt", b"\xff\xfe\x00 broken")
    before = _snapshot(tmp_path)
    scan(tmp_path)
    scan(tmp_path, limits=ScanLimits(max_findings=1))
    assert _snapshot(tmp_path) == before


def test_scan_opens_files_read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    put(tmp_path, "a.txt", f"{EMAIL}\n")
    real_open = os.open
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND

    def checked(path: object, flags: int, *args: object, **kwargs: object) -> int:
        assert flags & write_flags == 0, "scanner opened a file for writing"
        return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(reader.os, "open", checked)
    assert len(scan(tmp_path).findings) == 1

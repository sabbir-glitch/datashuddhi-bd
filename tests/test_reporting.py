"""Tests for the text and JSON reports."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from datashuddhi import __version__
from datashuddhi.config import FailOn, ScanLimits, ScanOptions
from datashuddhi.exit_codes import decide_exit
from datashuddhi.reporting import DISCLAIMER
from datashuddhi.reporting.console import (
    encodable_for,
    render_summary,
    render_text,
    sanitize,
)
from datashuddhi.reporting.json_report import SCHEMA_VERSION, build_report, render_json
from datashuddhi.scanner import ScanResult, scan_path
from tests.synthetic import CANARY_EMAIL, CANARY_PHONE

EMAIL = "alice@example.com"
PHONE = "01712345678"


def scan(root: Path, **limits: int) -> ScanResult:
    return scan_path(str(root), ScanOptions(limits=ScanLimits(**limits)))


def code_for(result: ScanResult, fail_on: FailOn = FailOn.LOW) -> int:
    return decide_exit(findings=result.findings, complete=result.complete, fail_on=fail_on)


@pytest.fixture
def findings_tree(tmp_path: Path) -> Path:
    (tmp_path / "a.txt").write_text(f"{EMAIL} {PHONE}\n", encoding="utf-8")
    return tmp_path


def _c(code: int) -> str:
    return chr(code)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("plain text", "plain text"),
        ("tab" + _c(9) + "here", "tab\\x09here"),
        ("new" + _c(10) + "line", "new\\x0aline"),
        ("esc" + _c(0x1B) + "[31m", "esc\\x1b[31m"),
        ("nul" + _c(0), "nul\\x00"),
        ("bidi" + _c(0x202E) + "txt", "bidi\\u202etxt"),
        ("iso" + _c(0x2066) + "x" + _c(0x2069), "iso\\u2066x\\u2069"),
        ("zero" + _c(0x200B) + "width", "zero\\u200bwidth"),
        ("bom" + _c(0xFEFF), "bom\\ufeff"),
        ("sep" + _c(0x2028) + "para" + _c(0x2029), "sep\\u2028para\\u2029"),
        ("lone" + _c(0xDCFF), "lone\\udcff"),
        ("private" + _c(0xE000), "private\\ue000"),
        ("astral" + _c(0xE0001), "astral\\U000e0001"),
        ("বাংলা ✓ café", "বাংলা ✓ café"),
        ("nbsp" + _c(0xA0) + "ok", "nbsp" + _c(0xA0) + "ok"),
    ],
)
def test_sanitize(raw: str, expected: str) -> None:
    assert sanitize(raw) == expected


def test_sanitized_text_has_no_control_or_bidi_characters() -> None:
    nasty = "".join(chr(c) for c in [*range(0, 32), 127, 0x85, 0x202A, 0x202E, 0x2066, 0x2069])
    cleaned = sanitize(nasty)
    assert all(ch.isprintable() for ch in cleaned)


def stream_with(encoding: str) -> io.TextIOWrapper:
    return io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors="strict")


@pytest.mark.parametrize("encoding", ["ascii", "cp1252", "cp437", "utf-8", "utf-16"])
def test_encodable_text_can_always_be_written(encoding: str) -> None:
    stream = stream_with(encoding)
    text = "ফোন ✓ café 😀 plain"
    stream.write(encodable_for(text, stream))  # would raise UnicodeEncodeError otherwise
    stream.flush()


def test_encodable_escapes_only_what_the_encoding_cannot_represent() -> None:
    assert encodable_for("café বা", stream_with("cp1252")) == "café \\u09ac\\u09be"
    assert encodable_for("café", stream_with("utf-8")) == "café"
    assert encodable_for("abc", stream_with("ascii")) == "abc"


def test_encodable_survives_streams_without_an_encoding() -> None:
    class Bare:
        encoding = None

    assert encodable_for("বা", Bare()) == "বা"  # type: ignore[arg-type]

    class Odd:
        encoding = "no-such-codec"

    assert encodable_for("বা", Odd()) == "\\u09ac\\u09be"  # type: ignore[arg-type]


def test_text_report_for_findings(findings_tree: Path) -> None:
    result = scan(findings_tree)
    text = render_text(result, FailOn.LOW, 1)
    assert f"DataShuddhi BD {__version__}" in text
    assert "Status: COMPLETE" in text
    assert "Potential findings: 2 (high 0, medium 1, low 1)" in text
    assert "F-0001 [LOW, confidence high] DS-EMAIL-001 email_address" in text
    assert "a.txt:1:1  a***@***.com" in text
    assert "*********78" in text
    assert "Fail threshold (--fail-on): low; reached: yes" in text
    assert "Exit code: 1" in text
    assert DISCLAIMER in text
    assert "does not implement credential or secret detection" in text
    assert EMAIL not in text
    assert PHONE not in text


def test_text_report_for_a_clean_complete_scan(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("nothing here\n", encoding="utf-8")
    result = scan(tmp_path)
    text = render_text(result, FailOn.LOW, 0)
    assert "Status: COMPLETE" in text
    assert "No potential findings were reported for the files that were scanned." in text
    assert "INCOMPLETE" not in text
    assert "Exit code: 0" in text


def test_text_report_for_an_empty_directory(tmp_path: Path) -> None:
    text = render_text(scan(tmp_path), FailOn.LOW, 0)
    assert "Files: 0 found, 0 scanned, 0 not scanned" in text
    assert "Status: COMPLETE" in text


def test_text_report_states_clearly_when_incomplete(tmp_path: Path) -> None:
    (tmp_path / "big.txt").write_text("x" * 500, encoding="utf-8")
    result = scan(tmp_path, max_file_bytes=100)
    text = render_text(result, FailOn.LOW, code_for(result))
    assert "Status: INCOMPLETE - NOT a complete clean scan" in text
    assert "Issues (1) - these make the scan incomplete:" in text
    assert "too_large: big.txt" in text
    assert "Exit code: 3" in text


def test_text_report_lists_warnings_separately(tmp_path: Path) -> None:
    (tmp_path / "bad.txt").write_bytes(b"\xc3( " + EMAIL.encode())
    result = scan(tmp_path)
    text = render_text(result, FailOn.NEVER, code_for(result, FailOn.NEVER))
    assert "Warnings (1) - these do not make the scan incomplete:" in text
    assert "decode_replaced: bad.txt" in text
    assert "Status: COMPLETE" in text


def test_text_report_mentions_truncation_and_omitted_entries(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("\n".join([EMAIL] * 3), encoding="utf-8")
    result = scan(tmp_path, max_findings=1)
    text = render_text(result, FailOn.LOW, code_for(result))
    assert "The findings limit was reached" in text
    result.log.max_entries = 0
    result.log.add(
        __import__("datashuddhi.issues", fromlist=["IssueKind"]).IssueKind.UNREADABLE, "x"
    )
    assert "more issues not listed" in render_text(result, FailOn.LOW, 1)


def test_hostile_file_names_cannot_inject_terminal_sequences(tmp_path: Path) -> None:
    name = "evil‮⁦name.txt"
    (tmp_path / name).write_text(f"{EMAIL}\n", encoding="utf-8")
    result = scan(tmp_path)
    text = render_text(result, FailOn.LOW, 1)
    assert "‮" not in text
    assert "⁦" not in text
    assert "evil\\u202e\\u2066name.txt" in text


def test_summary_is_short_and_masked(findings_tree: Path) -> None:
    result = scan(findings_tree)
    summary = render_summary(result, 1)
    assert "2 potential findings" in summary
    assert "Exit code: 1" in summary
    assert EMAIL not in summary
    assert len(summary.splitlines()) == 2


def test_json_report_structure_and_values(findings_tree: Path) -> None:
    result = scan(findings_tree)
    report = build_report(result, FailOn.MEDIUM, 1)
    assert report["schema_version"] == SCHEMA_VERSION == "1"
    assert report["tool"] == {"name": "datashuddhi-bd", "version": __version__}
    assert list(report) == [
        "schema_version", "tool", "scan", "summary", "findings", "issues", "warnings",
        "outcome", "disclaimer",
    ]  # fmt: skip
    assert report["scan"]["status"] == "complete"
    assert report["scan"]["root_name"] == findings_tree.name
    assert report["scan"]["limits"] == {
        "max_file_size_bytes": 5 * 1024 * 1024,
        "max_files": 10_000,
        "max_findings": 10_000,
    }
    assert report["scan"]["rules"] == ["DS-EMAIL-001", "DS-BDPHONE-001"]
    assert report["scan"]["files"] == {
        "discovered": 1,
        "scanned": 1,
        "not_scanned": 0,
        "excluded_directories": 0,
        "excluded_files": 0,
        "unsupported_type": 0,
    }
    assert report["summary"] == {
        "total_findings": 2,
        "by_severity": {"low": 1, "medium": 1, "high": 0},
        "by_rule": {"DS-EMAIL-001": 1, "DS-BDPHONE-001": 1},
    }
    first = report["findings"][0]
    assert first["id"] == "F-0001"
    assert first["masked_value"] == "a***@***.com"
    assert first["severity"] == "low"
    assert report["outcome"] == {"fail_on": "medium", "threshold_reached": True, "exit_code": 1}
    assert report["issues"] == {"total": 0, "omitted": 0, "by_kind": {}, "items": []}
    assert report["disclaimer"] == DISCLAIMER


def test_json_text_is_valid_ascii_only_and_round_trips(findings_tree: Path) -> None:
    result = scan(findings_tree)
    report = build_report(result, FailOn.LOW, 1)
    text = render_json(report)
    text.encode("ascii")
    assert json.loads(text) == report
    assert text.endswith("\n")


def test_json_is_deterministic(findings_tree: Path) -> None:
    first = render_json(build_report(scan(findings_tree), FailOn.LOW, 1))
    second = render_json(build_report(scan(findings_tree), FailOn.LOW, 1))
    assert first == second


def test_json_never_contains_absolute_paths_or_timestamps(findings_tree: Path) -> None:
    text = render_json(build_report(scan(findings_tree), FailOn.LOW, 1))
    assert str(findings_tree) not in text
    assert str(findings_tree.parent) not in text
    for forbidden in ("timestamp", "generated_at", "date", "hostname", "username"):
        assert forbidden not in text.lower().replace("by_kind", "")


def test_json_reports_incomplete_scans_and_warnings(tmp_path: Path) -> None:
    (tmp_path / "big.txt").write_text("x" * 500, encoding="utf-8")
    (tmp_path / "bad.txt").write_bytes(b"\xc3( ok")
    result = scan(tmp_path, max_file_bytes=100)
    report = build_report(result, FailOn.NEVER, code_for(result, FailOn.NEVER))
    assert report["scan"]["status"] == "incomplete"
    assert report["issues"]["total"] == 1
    assert report["issues"]["by_kind"] == {"too_large": 1}
    assert report["issues"]["items"] == [{"kind": "too_large", "path": "big.txt", "detail": ""}]
    assert report["outcome"]["exit_code"] == 3
    assert report["outcome"]["threshold_reached"] is False


def test_json_records_user_exclusions_and_truncation(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("\n".join([EMAIL] * 3), encoding="utf-8")
    result = scan_path(
        str(tmp_path), ScanOptions(limits=ScanLimits(max_findings=2), exclude=("*.log",))
    )
    report = build_report(result, FailOn.LOW, 1)
    assert report["scan"]["exclusions"]["user_patterns"] == ["*.log"]
    assert report["scan"]["findings_truncated"] is True
    assert ".git" in report["scan"]["exclusions"]["default_directories"]
    assert report["scan"]["exclusions"]["default_directory_patterns"] == ["*.egg-info"]


def test_reports_never_contain_raw_values(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text(f"{CANARY_EMAIL} {CANARY_PHONE} +880{CANARY_PHONE[1:]}\n")
    result = scan(tmp_path)
    for blob in (
        render_text(result, FailOn.LOW, 1),
        render_json(build_report(result, FailOn.LOW, 1)),
        render_summary(result, 1),
    ):
        assert CANARY_EMAIL not in blob
        assert "canary" not in blob.lower()
        assert CANARY_PHONE not in blob
        assert CANARY_PHONE[1:] not in blob

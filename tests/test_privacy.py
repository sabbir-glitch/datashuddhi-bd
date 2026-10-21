"""Privacy canary tests for the scan pipeline.

A *canary* is a unique synthetic value planted in scanned files. After a scan, the canary
(in every spelling used) must not appear in any object, log record, console output or
exception message the pipeline produces. The CLI-level canary tests live in test_cli_scan.py.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import socket
import subprocess
from pathlib import Path

import pytest

from datashuddhi.config import ScanLimits, ScanOptions
from datashuddhi.errors import ConfigError, InvalidScanRootError
from datashuddhi.scanner import ScanResult, scan_path
from tests.synthetic import CANARY_EMAIL, CANARY_PHONE, to_bengali_digits

LOCAL_PART = CANARY_EMAIL.split("@")[0]
PHONE_TAIL = CANARY_PHONE[1:]


def forbidden_strings() -> list[str]:
    """Every spelling of the canaries that must never be emitted."""
    spellings = [
        CANARY_EMAIL,
        CANARY_EMAIL.upper(),
        LOCAL_PART,
        CANARY_EMAIL.split("@")[1].split(".")[0] + "." + CANARY_EMAIL.rsplit(".", 1)[1],
        CANARY_PHONE,
        PHONE_TAIL,
        f"+880{PHONE_TAIL}",
        f"880{PHONE_TAIL}",
        f"{CANARY_PHONE[:3]}-{CANARY_PHONE[3:]}",
        to_bengali_digits(CANARY_PHONE),
        to_bengali_digits(PHONE_TAIL),
    ]
    return [s for s in spellings if len(s) >= 8 and s != "example.com"]


def build_canary_tree(root: Path) -> None:
    lines = [
        f"email: {CANARY_EMAIL}",
        f"EMAIL: {CANARY_EMAIL.upper()}",
        f"phone: {CANARY_PHONE}",
        f"intl: +880{PHONE_TAIL}",
        f"hyphen: {CANARY_PHONE[:3]}-{CANARY_PHONE[3:]}",
        f"bengali: {to_bengali_digits(CANARY_PHONE)}",
        f"bengali-intl: {to_bengali_digits('+880' + PHONE_TAIL)}",
    ]
    text = "\n".join(lines) + "\n"
    (root / "sub").mkdir()
    (root / "a.txt").write_text(text, encoding="utf-8")
    (root / "sub" / "b.csv").write_text(text.replace("\n", ","), encoding="utf-8")
    (root / "c.json").write_text(json.dumps({"x": lines}), encoding="utf-8")
    (root / "d.log").write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    (root / "bad-utf8.txt").write_bytes(b"\xc3( " + text.encode())
    (root / "binary.txt").write_bytes(b"\x00\x01" + text.encode())
    (root / "too-large.txt").write_text(text * 50, encoding="utf-8")


def assert_clean(blob: str, where: str) -> None:
    for secret in forbidden_strings():
        assert secret not in blob, f"canary {secret!r} leaked into {where}"


@pytest.fixture
def canary_scan(tmp_path: Path) -> ScanResult:
    build_canary_tree(tmp_path)
    options = ScanOptions(limits=ScanLimits(max_file_bytes=2048))
    return scan_path(str(tmp_path), options)


def test_canary_tree_actually_produces_findings_and_issues(canary_scan: ScanResult) -> None:
    # Guard against a vacuous test: the scan must find the canaries and also hit failure paths.
    assert len(canary_scan.findings) >= 20
    assert {i.kind.value for i in canary_scan.log.issues} >= {"binary_content", "too_large"}
    assert {w.kind.value for w in canary_scan.log.warnings} == {"decode_replaced"}


def test_canary_absent_from_all_result_representations(canary_scan: ScanResult) -> None:
    assert_clean(repr(canary_scan), "repr(result)")
    assert_clean(str(canary_scan), "str(result)")
    for finding in canary_scan.findings:
        assert_clean(repr(finding), "repr(finding)")
        assert_clean(json.dumps(finding.to_dict(), ensure_ascii=False), "finding json")
        assert_clean(json.dumps(finding.to_dict(), ensure_ascii=True), "finding json (ascii)")
    assert_clean(json.dumps(dataclasses.asdict(canary_scan), default=str), "asdict(result)")
    for issue in [*canary_scan.log.issues, *canary_scan.log.warnings]:
        assert_clean(json.dumps(issue.to_dict()), "issue json")


def test_findings_hold_only_masked_values(canary_scan: ScanResult) -> None:
    for finding in canary_scan.findings:
        assert "*" in finding.masked_value
        if finding.category == "bangladeshi_mobile_number":
            assert finding.masked_value == "*********00"
        else:
            assert finding.masked_value in {"c***@***.com", "C***@***.com"}


def test_no_log_records_or_console_output(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    build_canary_tree(tmp_path)
    with caplog.at_level(logging.DEBUG):
        scan_path(str(tmp_path), ScanOptions(limits=ScanLimits(max_file_bytes=2048)))
    assert caplog.records == []  # the library does not log at all
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""  # noqa: PT018 - both streams must be silent


def test_no_warnings_are_emitted(tmp_path: Path) -> None:
    import warnings

    build_canary_tree(tmp_path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        scan_path(str(tmp_path), ScanOptions(limits=ScanLimits(max_file_bytes=2048)))
    assert [str(w.message) for w in caught] == []


def test_exception_messages_do_not_contain_scanned_content(tmp_path: Path) -> None:
    build_canary_tree(tmp_path)
    errors: list[BaseException] = []
    for action in (
        lambda: scan_path(str(tmp_path / "missing")),
        lambda: scan_path(str(tmp_path / "binary.txt" / "x")),
        lambda: ScanLimits(max_files=CANARY_EMAIL),  # type: ignore[arg-type]
        lambda: ScanOptions(exclude=(CANARY_EMAIL + "\x00",)),
    ):
        with pytest.raises((InvalidScanRootError, ConfigError)) as info:
            action()
        errors.append(info.value)
    for error in errors:
        assert_clean(str(error), "exception message")
        assert_clean(repr(error), "exception repr")


def test_scan_makes_no_network_connections_and_starts_no_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_canary_tree(tmp_path)
    calls: list[str] = []

    def refuse(name: str):
        def blocked(*args: object, **kwargs: object) -> None:
            calls.append(name)
            raise AssertionError(f"unexpected {name} during a scan")

        return blocked

    monkeypatch.setattr(socket.socket, "connect", refuse("socket.connect"))
    monkeypatch.setattr(socket.socket, "connect_ex", refuse("socket.connect_ex"))
    monkeypatch.setattr(socket.socket, "sendto", refuse("socket.sendto"))
    monkeypatch.setattr(socket, "getaddrinfo", refuse("getaddrinfo"))
    monkeypatch.setattr(socket, "gethostbyname", refuse("gethostbyname"))
    monkeypatch.setattr(socket, "create_connection", refuse("create_connection"))
    monkeypatch.setattr(subprocess.Popen, "__init__", refuse("subprocess.Popen"))
    monkeypatch.setattr(os, "system", refuse("os.system"))

    result = scan_path(str(tmp_path), ScanOptions(limits=ScanLimits(max_file_bytes=2048)))
    assert result.findings
    assert calls == []

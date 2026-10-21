"""End-to-end tests of ``datashuddhi scan`` through ``main()`` and as a subprocess."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest

from datashuddhi import cli
from datashuddhi.cli import main
from datashuddhi.errors import ScanFatalError
from tests.synthetic import CANARY_EMAIL, CANARY_PHONE, to_bengali_digits
from tests.test_privacy import assert_clean, build_canary_tree

EMAIL = "alice@example.com"  # LOW severity
PHONE = "01712345678"  # MEDIUM severity


def run(capsys: pytest.CaptureFixture[str], *argv: str | Path) -> tuple[int, str, str]:
    code = main([str(a) for a in argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def write(root: Path, rel: str, data: str | bytes) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    return path


def digest_tree(root: Path) -> dict[str, tuple[int, int, str]]:
    result = {}
    for path in sorted(root.rglob("*")):
        key = path.relative_to(root).as_posix()
        if path.is_file():
            stat = path.stat()
            result[key] = (
                stat.st_size,
                stat.st_mtime_ns,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        else:
            result[key + "/"] = (0, 0, "")
    return result


# ----------------------------------------------------------------------------- basics


def test_help_lists_the_scan_command(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(capsys, "--help")
    assert code == 0
    assert "scan" in out
    assert "Find potential personal data before you share it" in out
    assert err == ""


def test_scan_help_documents_options_and_exit_codes(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "scan", "--help")
    assert code == 0
    for option in (
        "--format", "--output", "--exclude", "--max-file-size", "--max-files",
        "--max-findings", "--fail-on", "--force", "--allow-output-in-scan-root",
    ):  # fmt: skip
        assert option in out
    assert "exit codes" in out
    assert "--reveal" not in out  # there is deliberately no reveal mode


def test_scan_without_a_path_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(capsys, "scan")
    assert (code, out) == (2, "")
    assert "PATH" in err


# ------------------------------------------------------------------- exit code matrix


@pytest.mark.parametrize(
    ("fail_on", "email_code", "phone_code"),
    [("low", 1, 1), ("medium", 0, 1), ("high", 0, 0), ("never", 0, 0)],
)
def test_fail_on_thresholds_for_complete_scans(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    fail_on: str,
    email_code: int,
    phone_code: int,
) -> None:
    email_dir = tmp_path / "email"
    phone_dir = tmp_path / "phone"
    write(email_dir, "a.txt", f"{EMAIL}\n")
    write(phone_dir, "a.txt", f"{PHONE}\n")
    assert run(capsys, "scan", email_dir, "--fail-on", fail_on)[0] == email_code
    assert run(capsys, "scan", phone_dir, "--fail-on", fail_on)[0] == phone_code


def test_default_threshold_is_low(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "a.txt", f"{EMAIL}\n")
    code, out, _ = run(capsys, "scan", tmp_path)
    assert code == 1
    assert "--fail-on): low; reached: yes" in out


def test_clean_scan_exits_zero_for_every_threshold(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "a.txt", "nothing\n")
    for fail_on in ("low", "medium", "high", "never"):
        code, out, err = run(capsys, "scan", tmp_path, "--fail-on", fail_on)
        assert code == 0
        assert "Status: COMPLETE" in out
        assert err == ""


def test_empty_directory_is_a_complete_clean_scan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = run(capsys, "scan", tmp_path)
    assert code == 0
    assert "Files: 0 found, 0 scanned" in out


@pytest.mark.parametrize("fail_on", ["low", "medium", "high", "never"])
def test_incomplete_scan_without_findings_is_exit_3_for_every_threshold(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], fail_on: str
) -> None:
    write(tmp_path, "big.txt", "x" * 500)
    code, out, _ = run(capsys, "scan", tmp_path, "--max-file-size", "100", "--fail-on", fail_on)
    assert code == 3
    assert "INCOMPLETE" in out
    assert "Exit code: 3" in out


def test_incomplete_scan_with_findings_below_threshold_is_exit_3(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "big.txt", "x" * 500)
    write(tmp_path, "a.txt", f"{EMAIL}\n")  # LOW finding
    assert run(capsys, "scan", tmp_path, "--max-file-size", "100", "--fail-on", "high")[0] == 3
    assert run(capsys, "scan", tmp_path, "--max-file-size", "100", "--fail-on", "never")[0] == 3


def test_incomplete_scan_with_findings_at_threshold_is_exit_1_and_still_flagged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "big.txt", "x" * 500)
    write(tmp_path, "a.txt", f"{EMAIL}\n")
    code, out, _ = run(capsys, "scan", tmp_path, "--max-file-size", "100")
    assert code == 1
    assert "Status: INCOMPLETE" in out


# --------------------------------------------------------------- usage errors (exit 2)


@pytest.mark.parametrize(
    "extra",
    [
        ["--max-file-size", "abc"],
        ["--max-file-size", "5MB"],
        ["--max-file-size", "0"],
        ["--max-file-size", "257MiB"],
        ["--max-files", "0"],
        ["--max-files", "abc"],
        ["--max-files", "-1"],
        ["--max-files", "1000001"],
        ["--max-findings", "0"],
        ["--max-findings", "1.5"],
        ["--fail-on", "critical"],
        ["--format", "xml"],
        ["--exclude", ""],
        ["--exclude", "   "],
        ["--no-such-option"],
        ["--reveal"],
    ],
)
def test_invalid_options_are_usage_errors_and_scan_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], extra: list[str]
) -> None:
    write(tmp_path, "a.txt", f"{EMAIL}\n")
    code, out, err = run(capsys, "scan", tmp_path, *extra)
    assert code == 2
    assert out == ""
    assert err != ""


def test_missing_scan_root_is_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(capsys, "scan", tmp_path / "CANARY-missing")
    assert code == 2
    assert out == ""
    assert "does not exist" in err
    assert "CANARY" not in err


def test_unsupported_file_as_root_is_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, "tool.py", "x")
    code, out, err = run(capsys, "scan", path)
    assert (code, out) == (2, "")
    assert "unsupported type" in err


def test_usage_errors_never_exit_zero_or_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for args in (["scan"], ["scan", str(tmp_path / "nope")], ["scan", str(tmp_path), "--bad"]):
        assert run(capsys, *args)[0] == 2


# --------------------------------------------------------------------- limits / skips


def test_resource_limits_are_enforced_and_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for i in range(4):
        write(tmp_path, f"f{i}.txt", f"{EMAIL}\n")
    code, out, _ = run(capsys, "scan", tmp_path, "--max-files", "2", "--format", "json")
    report = json.loads(out)
    assert code == 1
    assert report["summary"]["total_findings"] == 2
    assert report["scan"]["status"] == "incomplete"
    assert report["issues"]["by_kind"] == {"file_limit_reached": 1}

    code, out, _ = run(capsys, "scan", tmp_path, "--max-findings", "3", "--format", "json")
    report = json.loads(out)
    assert report["summary"]["total_findings"] == 3
    assert report["scan"]["findings_truncated"] is True
    assert report["issues"]["by_kind"] == {"finding_limit_reached": 1}

    code, out, _ = run(capsys, "scan", tmp_path, "--max-findings", "4", "--format", "json")
    assert json.loads(out)["scan"]["status"] == "complete"


def test_size_limit_accepts_units(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "a.txt", "x" * 2000)
    assert run(capsys, "scan", tmp_path, "--max-file-size", "1KiB")[0] == 3
    assert run(capsys, "scan", tmp_path, "--max-file-size", "2KiB")[0] == 0
    assert run(capsys, "scan", tmp_path, "--max-file-size", "2000")[0] == 0
    assert run(capsys, "scan", tmp_path, "--max-file-size", "1999")[0] == 3


def test_skipped_binary_and_unsupported_files_are_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "bin.txt", b"\x00\x01\x02")
    write(tmp_path, "tool.py", f"{EMAIL}\n")
    write(tmp_path, "ok.txt", "clean\n")
    code, out, _ = run(capsys, "scan", tmp_path, "--format", "json")
    report = json.loads(out)
    assert code == 3
    assert report["issues"]["by_kind"] == {"binary_content": 1}
    assert report["scan"]["files"]["unsupported_type"] == 1
    assert report["scan"]["files"]["scanned"] == 1
    assert report["scan"]["files"]["not_scanned"] == 1


def test_exclude_patterns_are_applied_and_not_issues(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "keep.txt", "clean\n")
    write(tmp_path, "secret.log", f"{EMAIL}\n")
    write(tmp_path, "private/x.txt", f"{EMAIL}\n")
    code, out, _ = run(
        capsys, "scan", tmp_path, "--exclude", "*.LOG", "--exclude", "private", "--format", "json"
    )
    report = json.loads(out)
    assert code == 0
    assert report["scan"]["status"] == "complete"
    assert report["scan"]["files"]["excluded_files"] == 1
    assert report["scan"]["files"]["excluded_directories"] == 1
    assert report["scan"]["exclusions"]["user_patterns"] == ["*.LOG", "private"]


def test_single_file_scan(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = write(tmp_path, "one.csv", f"id,mail\n1,{EMAIL}\n")
    code, out, _ = run(capsys, "scan", path, "--format", "json")
    report = json.loads(out)
    assert code == 1
    assert report["findings"][0]["path"] == "one.csv"
    assert report["findings"][0]["line"] == 2
    assert report["findings"][0]["column"] == 3


def test_bengali_digits_and_utf16_through_the_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "bn.txt", "ফোন: " + to_bengali_digits(PHONE) + "\n")
    write(tmp_path, "ps.log", b"\xff\xfe" + f"user {EMAIL}\r\n".encode("utf-16-le"))
    code, out, _ = run(capsys, "scan", tmp_path, "--format", "json")
    findings = json.loads(out)["findings"]
    assert code == 1
    assert [(f["path"], f["line"], f["column"], f["masked_value"]) for f in findings] == [
        ("bn.txt", 1, 6, "*********78"),
        ("ps.log", 1, 6, "a***@***.com"),
    ]


# ------------------------------------------------------------------------ stdout / json


def test_json_stdout_contains_only_valid_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "a.txt", f"{EMAIL} {PHONE}\n")
    code, out, err = run(capsys, "scan", tmp_path, "--format", "json")
    report = json.loads(out)  # raises if anything else is on stdout
    assert code == 1
    assert err == ""
    assert report["outcome"] == {"fail_on": "low", "threshold_reached": True, "exit_code": 1}
    assert report["summary"]["total_findings"] == 2


def test_incomplete_json_scan_also_warns_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "bin.txt", b"\x00")
    code, out, err = run(capsys, "scan", tmp_path, "--format", "json")
    assert code == 3
    assert json.loads(out)["scan"]["status"] == "incomplete"
    assert "INCOMPLETE" in err


def test_stdout_report_is_stable_across_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for i in range(3):
        write(tmp_path, f"d{i}/a.txt", f"{EMAIL}\n{PHONE}\n")
    first = run(capsys, "scan", tmp_path, "--format", "json")
    second = run(capsys, "scan", tmp_path, "--format", "json")
    assert first == second


def test_scanning_does_not_modify_the_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scan = tmp_path / "scan"
    write(scan, "a.txt", f"{EMAIL}\r\n")
    write(scan, "sub/b.csv", f"{PHONE}\n")
    write(scan, "bad.txt", b"\x00")
    before = digest_tree(scan)
    run(capsys, "scan", scan)
    run(capsys, "scan", scan, "--format", "json")
    assert digest_tree(scan) == before


# ------------------------------------------------------------------------------ output


def test_output_file_receives_the_report_and_stdout_only_a_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scan, out_dir = tmp_path / "scan", tmp_path / "out"
    out_dir.mkdir()
    write(scan, "a.txt", f"{EMAIL}\n")
    code, out, err = run(capsys, "scan", scan, "--format", "json", "--output", out_dir / "r.json")
    assert code == 1
    assert "Report written to the requested output file." in out
    assert "F-0001" not in out
    assert err == ""
    report = json.loads((out_dir / "r.json").read_text(encoding="utf-8"))
    assert report["findings"][0]["masked_value"] == "a***@***.com"


def test_output_text_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    scan, out_dir = tmp_path / "scan", tmp_path / "out"
    out_dir.mkdir()
    write(scan, "a.txt", f"{EMAIL}\n")
    run(capsys, "scan", scan, "--output", out_dir / "r.txt")
    assert "F-0001 [LOW" in (out_dir / "r.txt").read_text(encoding="utf-8")


def test_output_refuses_an_existing_file_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scan, out_dir = tmp_path / "scan", tmp_path / "out"
    out_dir.mkdir()
    write(scan, "a.txt", f"{EMAIL}\n")
    existing = write(out_dir, "r.json", "precious")
    code, out, err = run(capsys, "scan", scan, "--output", existing)
    assert (code, out) == (2, "")
    assert "--force" in err
    assert existing.read_text(encoding="utf-8") == "precious"


def test_output_force_replaces_an_existing_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scan, out_dir = tmp_path / "scan", tmp_path / "out"
    out_dir.mkdir()
    write(scan, "a.txt", "clean\n")
    existing = write(out_dir, "r.json", "old")
    code, _, _ = run(capsys, "scan", scan, "--format", "json", "--output", existing, "--force")
    assert code == 0
    assert json.loads(existing.read_text(encoding="utf-8"))["scan"]["status"] == "complete"


def test_output_inside_the_scan_root_is_refused_and_nothing_is_created(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "a.txt", f"{EMAIL}\n")
    before = digest_tree(tmp_path)
    code, out, err = run(capsys, "scan", tmp_path, "--output", tmp_path / "report.json")
    assert (code, out) == (2, "")
    assert "--allow-output-in-scan-root" in err
    assert digest_tree(tmp_path) == before


def test_output_inside_the_scan_root_with_explicit_permission(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "a.txt", "clean\n")
    code, _, _ = run(
        capsys, "scan", tmp_path, "--output", tmp_path / "report.json",
        "--allow-output-in-scan-root", "--format", "json",
    )  # fmt: skip
    assert code == 0
    # The report is created AFTER the scan, so it is not part of that scan's findings.
    assert (
        json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["scan"]["files"][
            "discovered"
        ]
        == 1
    )


@pytest.mark.parametrize("flags", [[], ["--force"], ["--allow-output-in-scan-root"],
                                   ["--force", "--allow-output-in-scan-root"]])  # fmt: skip
def test_output_can_never_overwrite_a_scanned_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], flags: list[str]
) -> None:
    victim = write(tmp_path, "a.txt", f"{EMAIL}\n")
    other = write(tmp_path, "sub/b.json", "{}")
    for target in (victim, other):
        before = target.read_bytes()
        code, out, _ = run(capsys, "scan", tmp_path, "--output", target, *flags)
        assert code == 2, (target, flags)
        assert out == ""
        assert target.read_bytes() == before


@pytest.mark.parametrize("flags", [[], ["--force"], ["--allow-output-in-scan-root", "--force"]])
def test_output_can_never_overwrite_the_single_file_being_scanned(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], flags: list[str]
) -> None:
    victim = write(tmp_path, "a.txt", f"{EMAIL}\n")
    before = victim.read_bytes()
    code, _, err = run(capsys, "scan", victim, "--output", victim, *flags)
    assert code == 2
    assert "scanned location" in err
    assert victim.read_bytes() == before


def test_output_to_a_missing_directory_is_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path / "scan", "a.txt", "x")
    code, _, err = run(capsys, "scan", tmp_path / "scan", "--output", tmp_path / "nope" / "r.txt")
    assert code == 2
    assert "does not exist" in err
    assert not (tmp_path / "nope").exists()


def test_unwritable_output_after_a_successful_scan_is_exit_3(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from datashuddhi.output import OutputWriteError

    def fail(*args: object, **kwargs: object) -> None:
        raise OutputWriteError("the report could not be written")

    monkeypatch.setattr(cli, "write_report", fail)
    scan, out_dir = tmp_path / "scan", tmp_path / "out"
    out_dir.mkdir()
    write(scan, "a.txt", "clean\n")
    code, out, err = run(capsys, "scan", scan, "--output", out_dir / "r.txt")
    assert (code, out) == (3, "")
    assert "could not be written" in err


# ------------------------------------------------------------- failure-path behaviours


def test_internal_errors_are_exit_3_and_never_echo_exception_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError(f"CANARY {CANARY_EMAIL}")

    monkeypatch.setattr(cli, "scan_path", boom)
    write(tmp_path, "a.txt", "x")
    code, out, err = run(capsys, "scan", tmp_path)
    assert (code, out) == (3, "")
    assert "RuntimeError" in err
    assert "CANARY" not in err
    assert CANARY_EMAIL not in err


def test_fatal_scan_errors_are_exit_3(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fatal(*args: object, **kwargs: object) -> None:
        raise ScanFatalError("scan could not produce a reliable result")

    monkeypatch.setattr(cli, "scan_path", fatal)
    code, out, err = run(capsys, "scan", tmp_path)
    assert (code, out) == (3, "")
    assert "reliable result" in err


def test_keyboard_interrupt_is_exit_3_without_a_partial_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupt(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "scan_path", interrupt)
    code, out, err = run(capsys, "scan", tmp_path)
    assert (code, out) == (3, "")
    assert "interrupted" in err


def test_closed_stdout_pipe_is_exit_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class ClosedPipe(io.StringIO):
        def write(self, text: str) -> int:
            raise BrokenPipeError

    write(tmp_path, "a.txt", f"{EMAIL}\n")
    monkeypatch.setattr(sys, "stdout", ClosedPipe())
    assert main(["scan", str(tmp_path)]) == 3


def test_non_utf8_console_never_crashes_on_unicode_file_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write(tmp_path, "ফোল্ডার/তথ্য.txt", f"{EMAIL}\n")
    raw = io.BytesIO()
    console = io.TextIOWrapper(raw, encoding="cp437", errors="strict")
    monkeypatch.setattr(sys, "stdout", console)
    assert main(["scan", str(tmp_path)]) == 1
    console.flush()
    text = raw.getvalue().decode("cp437")
    assert "\\u09ab" in text  # escaped, not crashed
    assert "F-0001" in text


@pytest.mark.skipif(
    sys.platform == "win32", reason="control characters are invalid in Windows names"
)
def test_control_characters_in_file_names_are_escaped_on_the_console(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "red\x1b[31m.txt", f"{EMAIL}\n")
    _, out, _ = run(capsys, "scan", tmp_path)
    assert "\x1b" not in out
    assert "red\\x1b[31m.txt" in out


def test_bidi_characters_in_file_names_are_escaped_on_the_console(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "gpj" + chr(0x202E) + "txt.txt", f"{EMAIL}\n")
    _, out, _ = run(capsys, "scan", tmp_path)
    assert chr(0x202E) not in out
    assert "\\u202e" in out


# --------------------------------------------------------------------- privacy canaries


def test_canaries_never_appear_in_any_cli_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    scan, out_dir = tmp_path / "scan", tmp_path / "out"
    scan.mkdir()
    out_dir.mkdir()
    build_canary_tree(scan)
    outputs: list[tuple[str, str]] = []
    with caplog.at_level(logging.DEBUG):
        for argv in (
            ["scan", str(scan), "--max-file-size", "2KiB"],
            ["scan", str(scan), "--max-file-size", "2KiB", "--format", "json"],
            ["scan", str(scan), "--max-file-size", "2KiB", "--output", str(out_dir / "r.txt")],
            ["scan", str(scan), "--max-file-size", "2KiB", "--format", "json", "--output",
             str(out_dir / "r.json")],
            ["scan", str(scan), "--max-file-size", "10"],
            ["scan", str(scan / "missing")],
            ["scan", str(scan), "--max-files", "bad"],
        ):  # fmt: skip
            code = main(argv)
            captured = capsys.readouterr()
            outputs.append(("stdout " + " ".join(argv[-2:]), captured.out))
            outputs.append(("stderr " + " ".join(argv[-2:]), captured.err))
            assert code in {1, 2, 3}
    for name in ("r.txt", "r.json"):
        outputs.append((name, (out_dir / name).read_text(encoding="utf-8")))
    outputs.append(("logs", caplog.text))
    assert caplog.records == []
    for where, blob in outputs:
        assert_clean(blob, where)
    # Not vacuous: the reports really contain findings and issues.
    assert "F-0001" in (out_dir / "r.txt").read_text(encoding="utf-8")
    assert (
        json.loads((out_dir / "r.json").read_text(encoding="utf-8"))["summary"]["total_findings"]
        > 10
    )


def test_canary_file_is_never_modified(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    build_canary_tree(tmp_path)
    before = digest_tree(tmp_path)
    run(capsys, "scan", tmp_path, "--max-file-size", "2KiB")
    assert digest_tree(tmp_path) == before


# ------------------------------------------------------------------------- subprocess


NETWORK_BLOCKER = """
import socket, sys
def refuse(*a, **k):
    raise RuntimeError('network access attempted')
for name in ('connect', 'connect_ex', 'sendto'):
    setattr(socket.socket, name, refuse)
for name in ('getaddrinfo', 'gethostbyname', 'create_connection'):
    setattr(socket, name, refuse)
from datashuddhi.cli import main
raise SystemExit(main(sys.argv[1:]))
"""


def test_cli_process_runs_with_networking_disabled_and_exit_codes_propagate(
    tmp_path: Path,
) -> None:
    write(tmp_path, "a.txt", f"{CANARY_EMAIL} {CANARY_PHONE}\n")
    result = subprocess.run(  # noqa: S603 - fixed arguments, test-only
        [sys.executable, "-c", NETWORK_BLOCKER, "scan", str(tmp_path), "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 1, result.stderr
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert report["summary"]["total_findings"] == 2
    assert_clean(result.stdout, "subprocess stdout")


def test_module_entry_point_reports_exit_codes(tmp_path: Path) -> None:
    clean = write(tmp_path / "clean", "a.txt", "nothing\n")
    expected = {
        (str(clean.parent),): 0,
        (str(tmp_path / "nope"),): 2,
    }
    for (path,), code in expected.items():
        result = subprocess.run(  # noqa: S603 - fixed arguments, test-only
            [sys.executable, "-m", "datashuddhi", "scan", path],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert result.returncode == code, result.stderr


def test_environment_is_not_consulted_for_secrets_or_endpoints() -> None:
    # The CLI reads no environment variables at all (no proxy, token or endpoint settings).
    source = (Path(cli.__file__)).read_text(encoding="utf-8")
    assert "os.environ" not in source
    assert "getenv" not in source

"""Tests for the safe report writer."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

from datashuddhi import output
from datashuddhi.output import OutputError, OutputWriteError, check_output_target, write_report


def check(target: Path | str, root: Path, *, force: bool = False, allow: bool = False) -> str:
    return check_output_target(str(target), str(root), force=force, allow_in_scan_root=allow)


@pytest.fixture
def layout(tmp_path: Path) -> tuple[Path, Path]:
    scan = tmp_path / "scan"
    out = tmp_path / "out"
    scan.mkdir()
    out.mkdir()
    (scan / "a.txt").write_text("hello\n", encoding="utf-8")
    return scan, out


def test_new_file_outside_the_scan_root_is_accepted(layout: tuple[Path, Path]) -> None:
    scan, out = layout
    final = check(out / "report.json", scan)
    assert Path(final) == (out / "report.json").resolve()
    write_report(final, "content ✓\n", replace_existing=False)
    assert (out / "report.json").read_text(encoding="utf-8") == "content ✓\n"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
def test_new_report_is_owner_only(layout: tuple[Path, Path]) -> None:
    scan, out = layout
    final = check(out / "r.txt", scan)
    write_report(final, "x", replace_existing=False)
    assert stat.S_IMODE((out / "r.txt").stat().st_mode) == 0o600


def test_relative_output_path_is_resolved(
    layout: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    scan, out = layout
    monkeypatch.chdir(out)
    assert Path(check("rel.txt", scan)) == (out / "rel.txt").resolve()


@pytest.mark.parametrize("bad", ["", "a\x00b"])
def test_empty_or_nul_output_path_is_rejected(layout: tuple[Path, Path], bad: str) -> None:
    scan, _ = layout
    with pytest.raises(OutputError):
        check(bad, scan)


def test_directory_target_is_rejected(layout: tuple[Path, Path]) -> None:
    scan, out = layout
    (out / "dir").mkdir()
    with pytest.raises(OutputError, match="not a regular file"):
        check(out / "dir", scan, force=True)
    with pytest.raises(OutputError, match="must name a file"):
        check(str(out / "dir") + os.sep, scan)
    with pytest.raises(OutputError):  # ".." resolves to an existing directory
        check(out / "..", scan)


def test_missing_parent_directory_is_rejected_and_not_created(layout: tuple[Path, Path]) -> None:
    scan, out = layout
    with pytest.raises(OutputError, match="does not exist"):
        check(out / "nope" / "r.txt", scan)
    assert not (out / "nope").exists()


def test_parent_that_is_a_file_is_rejected(layout: tuple[Path, Path]) -> None:
    scan, out = layout
    (out / "file.txt").write_text("x", encoding="utf-8")
    with pytest.raises(OutputError, match="does not exist"):
        check(out / "file.txt" / "r.txt", scan)


def test_existing_file_needs_force_and_is_left_untouched(layout: tuple[Path, Path]) -> None:
    scan, out = layout
    target = out / "r.txt"
    target.write_text("precious", encoding="utf-8")
    with pytest.raises(OutputError, match="--force"):
        check(target, scan)
    assert target.read_text(encoding="utf-8") == "precious"


def test_force_replaces_atomically_and_leaves_no_temporary_files(
    layout: tuple[Path, Path],
) -> None:
    scan, out = layout
    target = out / "r.txt"
    target.write_text("old", encoding="utf-8")
    final = check(target, scan, force=True)
    write_report(final, "new", replace_existing=True)
    assert target.read_text(encoding="utf-8") == "new"
    assert sorted(p.name for p in out.iterdir()) == ["r.txt"]


def test_symlink_target_is_refused_even_with_force(layout: tuple[Path, Path]) -> None:
    scan, out = layout
    victim = out / "victim.txt"
    victim.write_text("victim", encoding="utf-8")
    try:
        (out / "link.txt").symlink_to(victim)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(OutputError, match="symbolic link"):
        check(out / "link.txt", scan, force=True)
    assert victim.read_text(encoding="utf-8") == "victim"


def test_dangling_symlink_target_is_refused(layout: tuple[Path, Path]) -> None:
    scan, out = layout
    try:
        (out / "dangling.txt").symlink_to(out / "nowhere.txt")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(OutputError, match="symbolic link"):
        check(out / "dangling.txt", scan, force=True)
    assert not (out / "nowhere.txt").exists()


def test_new_file_inside_the_scan_root_needs_explicit_permission(
    layout: tuple[Path, Path],
) -> None:
    scan, _ = layout
    with pytest.raises(OutputError, match="--allow-output-in-scan-root"):
        check(scan / "report.json", scan)
    (scan / "sub").mkdir()
    with pytest.raises(OutputError, match="--allow-output-in-scan-root"):
        check(scan / "sub" / "x.json", scan)
    final = check(scan / "report.json", scan, allow=True)
    assert Path(final) == (scan / "report.json").resolve()


def test_existing_file_inside_the_scan_root_is_never_overwritten(
    layout: tuple[Path, Path],
) -> None:
    scan, _ = layout
    for force in (False, True):
        for allow in (False, True):
            with pytest.raises(OutputError, match="inside the scanned location"):
                check(scan / "a.txt", scan, force=force, allow=allow)
    assert (scan / "a.txt").read_text(encoding="utf-8") == "hello\n"


def test_output_equal_to_the_scanned_single_file_is_refused(layout: tuple[Path, Path]) -> None:
    scan, _ = layout
    scanned_file = scan / "a.txt"
    for force in (False, True):
        with pytest.raises(OutputError, match="inside the scanned location"):
            check(scanned_file, scanned_file, force=force, allow=True)


def test_new_file_next_to_a_scanned_single_file_is_allowed(layout: tuple[Path, Path]) -> None:
    scan, _ = layout
    final = check(scan / "report.json", scan / "a.txt")
    assert Path(final) == (scan / "report.json").resolve()


def test_dotdot_paths_cannot_escape_the_containment_check(layout: tuple[Path, Path]) -> None:
    scan, out = layout
    sneaky = scan / ".." / "scan" / "a.txt"
    with pytest.raises(OutputError, match="inside the scanned location"):
        check(sneaky, scan, force=True, allow=True)
    outside_via_dotdot = scan / ".." / "out" / "ok.txt"
    assert Path(check(outside_via_dotdot, scan)) == (out / "ok.txt").resolve()


def test_symlinked_directory_into_the_scan_root_is_still_inside(
    layout: tuple[Path, Path],
) -> None:
    scan, out = layout
    try:
        (out / "alias").symlink_to(scan, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(OutputError, match="inside the scanned location"):
        check(out / "alias" / "a.txt", scan, force=True, allow=True)
    with pytest.raises(OutputError, match="--allow-output-in-scan-root"):
        check(out / "alias" / "new.json", scan)


def test_sibling_directory_with_a_common_prefix_is_outside(tmp_path: Path) -> None:
    scan = tmp_path / "scan"
    other = tmp_path / "scan2"
    scan.mkdir()
    other.mkdir()
    assert Path(check(other / "r.txt", scan)) == (other / "r.txt").resolve()


def test_error_messages_do_not_echo_paths(tmp_path: Path) -> None:
    scan = tmp_path / "CANARY-scan"
    scan.mkdir()
    with pytest.raises(OutputError) as info:
        check(scan / "CANARY-sub" / "CANARY-report.json", scan)
    assert "CANARY" not in str(info.value)


def test_exclusive_create_never_overwrites_a_file_that_appears_late(
    layout: tuple[Path, Path],
) -> None:
    scan, out = layout
    final = check(out / "r.txt", scan)
    (out / "r.txt").write_text("appeared", encoding="utf-8")  # created after the check
    with pytest.raises(OutputWriteError, match="nothing was overwritten"):
        write_report(final, "new", replace_existing=False)
    assert (out / "r.txt").read_text(encoding="utf-8") == "appeared"


def test_partial_file_is_removed_if_writing_fails(
    layout: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    scan, out = layout
    final = check(out / "r.txt", scan)
    real_fdopen = os.fdopen

    class Failing:
        def __init__(self, handle: object) -> None:
            self._handle = handle

        def __enter__(self) -> Failing:
            return self

        def __exit__(self, *exc: object) -> None:
            self._handle.close()  # type: ignore[attr-defined]

        def write(self, data: bytes) -> int:
            raise OSError(28, "CANARY disk full")

    monkeypatch.setattr(output.os, "fdopen", lambda *a, **k: Failing(real_fdopen(*a, **k)))
    with pytest.raises(OutputWriteError, match="could not be written") as info:
        write_report(final, "data", replace_existing=False)
    assert "CANARY" not in str(info.value)
    assert not (out / "r.txt").exists()


def test_failed_replace_keeps_the_original_and_removes_the_temporary_file(
    layout: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    scan, out = layout
    target = out / "r.txt"
    target.write_text("original", encoding="utf-8")
    final = check(target, scan, force=True)

    def refuse(src: str, dst: str) -> None:
        raise PermissionError(13, "denied")

    monkeypatch.setattr(output.os, "replace", refuse)
    with pytest.raises(OutputWriteError):
        write_report(final, "new", replace_existing=True)
    assert target.read_text(encoding="utf-8") == "original"
    assert sorted(p.name for p in out.iterdir()) == ["r.txt"]


def test_open_failure_is_reported_as_a_write_error(
    layout: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    scan, out = layout
    final = check(out / "r.txt", scan)

    def refuse(*args: object, **kwargs: object) -> int:
        raise PermissionError(13, "CANARY denied")

    monkeypatch.setattr(output.os, "open", refuse)
    with pytest.raises(OutputWriteError) as info:
        write_report(final, "data", replace_existing=False)
    assert "CANARY" not in str(info.value)


def test_unencodable_text_is_written_safely(layout: tuple[Path, Path]) -> None:
    scan, out = layout
    final = check(out / "r.txt", scan)
    write_report(final, "lone surrogate: \udcff", replace_existing=False)
    assert (out / "r.txt").read_bytes() == b"lone surrogate: \\udcff"

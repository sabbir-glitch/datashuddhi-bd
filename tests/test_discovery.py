"""Tests for file discovery."""

from __future__ import annotations

import builtins
import os
import subprocess
import sys
from pathlib import Path

import pytest

from datashuddhi import discovery
from datashuddhi.config import ScanLimits, ScanOptions
from datashuddhi.discovery import ExcludeMatcher, discover, is_default_excluded_dir, is_link_like
from datashuddhi.errors import InvalidScanRootError
from datashuddhi.issues import IssueKind, IssueLog
from tests.posix_support import FIFO_SKIP_REASON, HAS_MKFIFO, make_fifo


def touch(root: Path, rel: str, data: bytes = b"x") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def run(
    root: Path | str, exclude: tuple[str, ...] = (), max_files: int = 10_000
) -> tuple[discovery.DiscoveryResult, IssueLog]:
    log = IssueLog()
    options = ScanOptions(limits=ScanLimits(max_files=max_files), exclude=exclude)
    return discover(root, options, log), log


def rels(result: discovery.DiscoveryResult) -> list[str]:
    return [f.rel for f in result.files]


def symlink_or_skip(link: Path, target: Path, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be created in this environment")


def test_finds_supported_files_in_sorted_case_insensitive_order(tmp_path: Path) -> None:
    for name in ["b.txt", "A.txt", "c.csv", "sub/z.json", "sub/Y.log", "Sub2/a.yml"]:
        touch(tmp_path, name)
    result, log = run(tmp_path)
    assert rels(result) == ["A.txt", "b.txt", "c.csv", "sub/Y.log", "sub/z.json", "Sub2/a.yml"]
    assert not log.incomplete


def test_relative_paths_use_forward_slashes_and_files_open(tmp_path: Path) -> None:
    touch(tmp_path, "a/b/c.txt", b"hello")
    result, _ = run(tmp_path)
    (found,) = result.files
    assert found.rel == "a/b/c.txt"
    assert "\\" not in found.rel
    assert Path(found.path).read_bytes() == b"hello"


def test_supported_and_unsupported_types_are_counted(tmp_path: Path) -> None:
    for name in ["a.txt", ".env", ".env.local", "prod.env", "x.py", "y.png", "z", "w.html"]:
        touch(tmp_path, name)
    result, log = run(tmp_path)
    assert sorted(rels(result)) == [".env", ".env.local", "a.txt", "prod.env"]
    assert result.unsupported_files == 4
    assert not log.incomplete  # unsupported types are not issues


@pytest.mark.parametrize(
    "directory",
    [".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist", "pkg.egg-info"],
)
def test_default_excluded_directories_are_pruned_and_counted(
    tmp_path: Path, directory: str
) -> None:
    touch(tmp_path, f"{directory}/inner.txt")
    touch(tmp_path, "keep.txt")
    result, log = run(tmp_path)
    assert rels(result) == ["keep.txt"]
    assert result.excluded_dirs == 1
    assert not log.incomplete


def test_default_exclusions_are_case_insensitive() -> None:
    assert is_default_excluded_dir("NODE_MODULES")
    assert is_default_excluded_dir("My.EGG-INFO")
    assert not is_default_excluded_dir("src")
    assert not is_default_excluded_dir("egg-info-notes")


def test_excluded_directory_is_not_entered_at_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    touch(tmp_path, "node_modules/deep/x.txt")
    entered: list[str] = []
    real_scandir = os.scandir

    def spy(path: str) -> object:
        entered.append(os.path.basename(str(path)))
        return real_scandir(path)

    monkeypatch.setattr(discovery.os, "scandir", spy)
    run(tmp_path)
    assert "node_modules" not in entered


def test_scanning_an_excluded_name_explicitly_is_allowed(tmp_path: Path) -> None:
    touch(tmp_path, "venv/a.txt")
    result, _ = run(tmp_path / "venv")
    assert rels(result) == ["a.txt"]


def test_user_exclude_name_patterns_match_at_any_depth(tmp_path: Path) -> None:
    for name in ["a.log", "x/b.log", "x/y/c.log", "keep.txt", "private/s.txt"]:
        touch(tmp_path, name)
    result, log = run(tmp_path, exclude=("*.log", "PRIVATE"))
    assert rels(result) == ["keep.txt"]
    assert result.excluded_files == 3
    assert result.excluded_dirs == 1
    assert not log.incomplete


def test_user_exclude_path_patterns_match_the_relative_path(tmp_path: Path) -> None:
    for name in ["docs/a.txt", "docs/private/b.txt", "other/docs/c.txt", "d.txt"]:
        touch(tmp_path, name)
    result, _ = run(tmp_path, exclude=("docs/private", "./other/docs/*"))
    assert rels(result) == ["d.txt", "docs/a.txt"]


def test_exclude_patterns_accept_backslashes_and_trailing_slashes(tmp_path: Path) -> None:
    touch(tmp_path, "docs/private/b.txt")
    touch(tmp_path, "a.txt")
    result, _ = run(tmp_path, exclude=("docs\\private\\",))
    assert rels(result) == ["a.txt"]


def test_exclude_matcher_is_case_insensitive_and_literal_for_odd_characters() -> None:
    matcher = ExcludeMatcher(("Secret*", "a[b.txt"))
    assert matcher.matches("SECRETS.txt", "SECRETS.txt")
    assert matcher.matches("a[b.txt", "d/a[b.txt")
    assert not matcher.matches("public.txt", "public.txt")


def test_file_limit_stops_discovery_and_is_reported(tmp_path: Path) -> None:
    for i in range(5):
        touch(tmp_path, f"f{i}.txt")
    result, log = run(tmp_path, max_files=3)
    assert rels(result) == ["f0.txt", "f1.txt", "f2.txt"]
    assert log.incomplete
    assert log.counts[IssueKind.FILE_LIMIT_REACHED] == 1


def test_exactly_the_limit_is_not_a_problem(tmp_path: Path) -> None:
    for i in range(3):
        touch(tmp_path, f"f{i}.txt")
    result, log = run(tmp_path, max_files=3)
    assert len(result.files) == 3
    assert not log.incomplete


def test_unsupported_and_excluded_files_do_not_count_toward_the_limit(tmp_path: Path) -> None:
    for name in ["a.txt", "b.py", "c.png", "d.log", "e.txt"]:
        touch(tmp_path, name)
    result, log = run(tmp_path, exclude=("*.log",), max_files=2)
    assert rels(result) == ["a.txt", "e.txt"]
    assert not log.incomplete


def test_single_supported_file_as_root(tmp_path: Path) -> None:
    path = touch(tmp_path, "one.csv")
    result, log = run(path)
    assert rels(result) == ["one.csv"]
    assert not log.incomplete


def test_single_file_root_ignores_exclude_patterns(tmp_path: Path) -> None:
    path = touch(tmp_path, "one.log")
    result, _ = run(path, exclude=("*.log",))
    assert rels(result) == ["one.log"]


def test_unsupported_file_as_root_is_a_usage_error(tmp_path: Path) -> None:
    path = touch(tmp_path, "tool.py")
    with pytest.raises(InvalidScanRootError, match="unsupported type"):
        run(path)


def test_missing_root_is_a_usage_error_that_does_not_echo_the_path(tmp_path: Path) -> None:
    with pytest.raises(InvalidScanRootError) as info:
        run(tmp_path / "CANARY-missing-dir")
    assert "CANARY" not in str(info.value)


def test_empty_directory_is_a_complete_empty_scan(tmp_path: Path) -> None:
    result, log = run(tmp_path)
    assert result.files == []
    assert not log.incomplete


def test_non_ascii_names_are_supported(tmp_path: Path) -> None:
    touch(tmp_path, "ফোল্ডার/তথ্য.txt")
    result, _ = run(tmp_path)
    assert rels(result) == ["ফোল্ডার/তথ্য.txt"]


def test_moderately_deep_nesting_works(tmp_path: Path) -> None:
    rel = "/".join(["d"] * 40) + "/deep.txt"
    touch(tmp_path, rel)
    result, _ = run(tmp_path)
    assert rels(result) == [rel]


def test_discovery_never_opens_file_contents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    touch(tmp_path, "a.txt")
    touch(tmp_path, "sub/b.csv")

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("discovery must not open files")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(discovery.os, "open", forbidden)
    result, _ = run(tmp_path)
    assert len(result.files) == 2


def test_symlinked_file_is_not_followed_and_is_reported(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    scan = tmp_path / "scan"
    touch(outside, "secret.txt", b"alice@example.com")
    touch(scan, "real.txt")
    symlink_or_skip(scan / "link.txt", outside / "secret.txt")
    result, log = run(scan)
    assert rels(result) == ["real.txt"]
    assert log.incomplete
    assert [(i.kind, i.path) for i in log.issues] == [(IssueKind.LINK_NOT_FOLLOWED, "link.txt")]


def test_symlinked_directory_is_not_followed_and_is_reported(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    scan = tmp_path / "scan"
    touch(outside, "secret.txt")
    touch(scan, "real.txt")
    symlink_or_skip(scan / "linkdir", outside, directory=True)
    result, log = run(scan)
    assert rels(result) == ["real.txt"]
    assert [(i.kind, i.path) for i in log.issues] == [(IssueKind.LINK_NOT_FOLLOWED, "linkdir")]


def test_symlink_to_an_inside_directory_is_still_not_followed(tmp_path: Path) -> None:
    touch(tmp_path, "real/a.txt")
    symlink_or_skip(tmp_path / "alias", tmp_path / "real", directory=True)
    result, log = run(tmp_path)
    assert rels(result) == ["real/a.txt"]  # no duplicate through the alias
    assert log.counts[IssueKind.LINK_NOT_FOLLOWED] == 1


def test_symlink_loop_does_not_hang(tmp_path: Path) -> None:
    touch(tmp_path, "a.txt")
    symlink_or_skip(tmp_path / "loop", tmp_path, directory=True)
    result, log = run(tmp_path)
    assert rels(result) == ["a.txt"]
    assert log.counts[IssueKind.LINK_NOT_FOLLOWED] == 1


def test_symlink_to_an_unsupported_file_is_ignored_silently(tmp_path: Path) -> None:
    touch(tmp_path, "tool.py")
    symlink_or_skip(tmp_path / "tool-link", tmp_path / "tool.py")
    result, log = run(tmp_path)
    assert result.files == []
    assert not log.incomplete


def test_excluded_symlinked_directory_is_counted_not_reported(tmp_path: Path) -> None:
    touch(tmp_path / "real", "a.txt")
    symlink_or_skip(tmp_path / "node_modules", tmp_path / "real", directory=True)
    _, log = run(tmp_path)
    assert not log.incomplete


def test_broken_symlink_with_supported_name_is_reported(tmp_path: Path) -> None:
    symlink_or_skip(tmp_path / "dangling.txt", tmp_path / "nowhere.txt")
    result, log = run(tmp_path)
    assert result.files == []
    assert log.counts[IssueKind.LINK_NOT_FOLLOWED] == 1


def test_scan_root_given_as_a_symlink_is_resolved_by_choice(tmp_path: Path) -> None:
    touch(tmp_path / "real", "a.txt")
    symlink_or_skip(tmp_path / "rootlink", tmp_path / "real", directory=True)
    result, _ = run(tmp_path / "rootlink")
    assert rels(result) == ["a.txt"]
    assert result.root_name == "real"


class FakeStat:
    def __init__(self, attributes: int) -> None:
        self.st_file_attributes = attributes


class FakeEntry:
    def __init__(self, symlink: bool, attributes: int | None) -> None:
        self._symlink = symlink
        self._attributes = attributes

    def is_symlink(self) -> bool:
        return self._symlink

    def stat(self, follow_symlinks: bool = True) -> object:
        assert follow_symlinks is False
        if self._attributes is None:
            return object()  # POSIX-like stat result: no st_file_attributes
        return FakeStat(self._attributes)


def test_windows_reparse_points_are_treated_as_links() -> None:
    reparse = 0x400  # FILE_ATTRIBUTE_REPARSE_POINT
    assert is_link_like(FakeEntry(False, reparse))  # type: ignore[arg-type]
    assert is_link_like(FakeEntry(False, reparse | 0x10))  # type: ignore[arg-type]
    assert is_link_like(FakeEntry(True, None))  # type: ignore[arg-type]
    assert not is_link_like(FakeEntry(False, 0x10))  # type: ignore[arg-type]
    assert not is_link_like(FakeEntry(False, None))  # type: ignore[arg-type]


@pytest.mark.skipif(sys.platform != "win32", reason="directory junctions exist on Windows only")
def test_windows_directory_junction_is_not_followed(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    scan = tmp_path / "scan"
    touch(outside, "secret.txt")
    touch(scan, "real.txt")
    junction = scan / "junction"
    completed = subprocess.run(  # noqa: S603 - fixed arguments, test-only
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],  # noqa: S607
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip("could not create a junction")
    result, log = run(scan)
    assert rels(result) == ["real.txt"]
    assert log.counts[IssueKind.LINK_NOT_FOLLOWED] == 1


@pytest.mark.skipif(not HAS_MKFIFO, reason=FIFO_SKIP_REASON)
def test_fifo_with_a_supported_name_is_reported_and_not_opened(tmp_path: Path) -> None:
    make_fifo(tmp_path / "pipe.txt")
    touch(tmp_path, "ok.txt")
    result, log = run(tmp_path)
    assert rels(result) == ["ok.txt"]
    assert [(i.kind, i.path) for i in log.issues] == [(IssueKind.NOT_REGULAR_FILE, "pipe.txt")]


def test_unreadable_directory_is_reported_and_scanning_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    touch(tmp_path, "locked/hidden.txt")
    touch(tmp_path, "open/shown.txt")
    real_scandir = os.scandir

    def selective(path: str) -> object:
        if os.path.basename(str(path)) == "locked":
            raise PermissionError(13, "CANARY denied")
        return real_scandir(path)

    monkeypatch.setattr(discovery.os, "scandir", selective)
    result, log = run(tmp_path)
    assert rels(result) == ["open/shown.txt"]
    assert log.incomplete
    assert [(i.kind, i.path) for i in log.issues] == [(IssueKind.UNREADABLE_DIRECTORY, "locked")]
    assert "CANARY" not in repr(log.issues)


def test_unreadable_root_directory_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    touch(tmp_path, "a.txt")

    def deny(path: str) -> object:
        raise PermissionError(13, "denied")

    monkeypatch.setattr(discovery.os, "scandir", deny)
    result, log = run(tmp_path)
    assert result.files == []
    assert [(i.kind, i.path) for i in log.issues] == [(IssueKind.UNREADABLE_DIRECTORY, ".")]


def test_file_resolving_outside_the_root_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    touch(tmp_path / "scan", "a.txt")
    outside = touch(tmp_path / "other", "b.txt")
    real_realpath = os.path.realpath

    def fake(path: str, *args: object, **kwargs: object) -> str:
        if os.path.basename(str(path)) == "a.txt":
            return str(outside)
        return real_realpath(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(discovery.os.path, "realpath", fake)
    result, log = run(tmp_path / "scan")
    assert result.files == []
    assert [(i.kind, i.path) for i in log.issues] == [(IssueKind.OUTSIDE_SCOPE, "a.txt")]


def test_sibling_directory_with_a_common_prefix_is_not_inside(tmp_path: Path) -> None:
    assert discovery._inside(str(tmp_path / "scan"), str(tmp_path / "scan" / "a.txt"))
    assert not discovery._inside(str(tmp_path / "scan"), str(tmp_path / "scan2" / "a.txt"))


def test_discovery_does_not_modify_the_tree(tmp_path: Path) -> None:
    touch(tmp_path, "a.txt")
    touch(tmp_path, "sub/b.json")
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    mtimes = {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*")}
    run(tmp_path)
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")) == before
    assert {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*")} == mtimes

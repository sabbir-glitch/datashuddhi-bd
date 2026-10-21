"""Tests for bounded, read-only file reading and decoding."""

from __future__ import annotations

import errno
import hashlib
import os
import sys
from pathlib import Path

import pytest

from datashuddhi import reader
from datashuddhi.issues import IssueKind
from datashuddhi.reader import NotRead, TextContent, read_text, split_lines
from tests.posix_support import FIFO_SKIP_REASON, HAS_MKFIFO, make_fifo

LIMIT = 1024 * 1024
# form feed, vertical tab, NEL and U+2028 are *not* line breaks for this tool
_ODD_BREAKS = "a" + chr(0x0C) + "b" + chr(0x2028) + "c" + chr(0x85) + "d" + chr(0x0B) + "e"


def write(tmp_path: Path, name: str, data: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def text_of(result: TextContent | NotRead) -> str:
    assert isinstance(result, TextContent), result
    return result.text


def test_utf8_text(tmp_path: Path) -> None:
    result = read_text(write(tmp_path, "a.txt", "hello বাংলা\n".encode()), LIMIT)
    assert isinstance(result, TextContent)
    assert result.text == "hello বাংলা\n"
    assert result.encoding == "utf-8"
    assert not result.replaced


def test_utf8_bom_is_removed(tmp_path: Path) -> None:
    result = read_text(write(tmp_path, "a.txt", b"\xef\xbb\xbfabc"), LIMIT)
    assert isinstance(result, TextContent)
    assert result.text == "abc"
    assert result.encoding == "utf-8-sig"


@pytest.mark.parametrize("codec", ["utf-16-le", "utf-16-be"])
def test_utf16_with_bom_is_decoded(tmp_path: Path, codec: str) -> None:
    bom = b"\xff\xfe" if codec == "utf-16-le" else b"\xfe\xff"
    content = "বাংলা line one\r\nline two"
    result = read_text(write(tmp_path, "log.txt", bom + content.encode(codec)), LIMIT)
    assert isinstance(result, TextContent)
    assert result.text == content
    assert result.encoding == "utf-16"
    assert not result.replaced


def test_utf16_odd_length_is_replaced_not_crashed(tmp_path: Path) -> None:
    data = b"\xff\xfe" + "ab".encode("utf-16-le") + b"\x41"  # dangling byte
    result = read_text(write(tmp_path, "a.txt", data), LIMIT)
    assert isinstance(result, TextContent)
    assert result.replaced
    assert result.text.startswith("ab")


@pytest.mark.parametrize("bom", [b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff"])
def test_utf32_is_unsupported(tmp_path: Path, bom: bytes) -> None:
    result = read_text(write(tmp_path, "a.txt", bom + b"a\x00\x00\x00"), LIMIT)
    assert result == NotRead(IssueKind.UNSUPPORTED_ENCODING, "utf-32")


def test_nul_byte_without_bom_is_binary(tmp_path: Path) -> None:
    result = read_text(write(tmp_path, "a.txt", b"abc\x00def"), LIMIT)
    assert result == NotRead(IssueKind.BINARY_CONTENT)


def test_utf16_without_bom_is_classified_as_binary(tmp_path: Path) -> None:
    result = read_text(write(tmp_path, "a.txt", "abc".encode("utf-16-le")), LIMIT)
    assert result == NotRead(IssueKind.BINARY_CONTENT)  # documented limitation


def test_nul_only_after_the_sniff_window_is_not_binary(tmp_path: Path) -> None:
    data = b"a" * 9000 + b"\x00" + b"b"
    result = read_text(write(tmp_path, "a.txt", data), LIMIT)
    assert isinstance(result, TextContent)  # documented: only the first 8 KiB is sniffed


def test_invalid_utf8_is_replaced_and_flagged(tmp_path: Path) -> None:
    result = read_text(write(tmp_path, "a.txt", b"ok \xff\xfe bad \xc3("), LIMIT)
    assert isinstance(result, TextContent)
    assert result.replaced
    assert "�" in result.text
    assert result.text.startswith("ok ")


def test_empty_file(tmp_path: Path) -> None:
    result = read_text(write(tmp_path, "a.txt", b""), LIMIT)
    assert isinstance(result, TextContent)
    assert result.text == ""
    assert split_lines(result.text) == [""]


def test_size_limit_is_inclusive_and_enforced(tmp_path: Path) -> None:
    assert isinstance(read_text(write(tmp_path, "ok.txt", b"a" * 100), 100), TextContent)
    assert read_text(write(tmp_path, "big.txt", b"a" * 101), 100) == NotRead(IssueKind.TOO_LARGE)


def test_file_that_grows_after_fstat_is_still_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write(tmp_path, "a.txt", b"a" * 500)
    real_fstat = os.fstat

    class Stale:
        def __init__(self, real: os.stat_result) -> None:
            self.st_mode = real.st_mode
            self.st_size = 10  # lies: pretends the file is small

    monkeypatch.setattr(reader.os, "fstat", lambda fd: Stale(real_fstat(fd)))
    assert read_text(path, 100) == NotRead(IssueKind.TOO_LARGE)


def test_only_max_plus_one_bytes_are_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write(tmp_path, "a.txt", b"a" * 500)
    requested: list[int] = []
    real_fdopen = os.fdopen

    class Spy:
        def __init__(self, handle: object) -> None:
            self._handle = handle

        def __enter__(self) -> Spy:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self, size: int) -> bytes:
            requested.append(size)
            return self._handle.read(size)  # type: ignore[attr-defined]

    monkeypatch.setattr(reader.os, "fdopen", lambda *a, **k: Spy(real_fdopen(*a, **k)))
    monkeypatch.setattr(
        reader.os, "fstat", lambda fd: type("S", (), {"st_mode": 0o100644, "st_size": 1})()
    )
    assert read_text(path, 100) == NotRead(IssueKind.TOO_LARGE)
    assert requested == [101]


def test_missing_file_is_unreadable_with_errno_name(tmp_path: Path) -> None:
    result = read_text(tmp_path / "missing.txt", LIMIT)
    assert result == NotRead(IssueKind.UNREADABLE, "ENOENT")


def test_os_error_details_never_contain_paths_or_messages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def deny(*args: object, **kwargs: object) -> int:
        raise PermissionError(errno.EACCES, "denied: /secret/CANARY-PATH/alice@example.com")

    monkeypatch.setattr(reader.os, "open", deny)
    result = read_text(tmp_path / "a.txt", LIMIT)
    assert result == NotRead(IssueKind.UNREADABLE, "EACCES")
    assert "CANARY" not in repr(result)


def test_error_during_read_is_reported_without_raising(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write(tmp_path, "a.txt", b"abc")

    def boom(fd: int) -> object:
        raise OSError(errno.EIO, "CANARY failure")

    monkeypatch.setattr(reader.os, "fstat", boom)
    result = read_text(path, LIMIT)
    assert result == NotRead(IssueKind.UNREADABLE, "EIO")


def test_directory_is_not_read_as_a_file(tmp_path: Path) -> None:
    result = read_text(tmp_path, LIMIT)
    assert isinstance(result, NotRead)
    assert result.kind in {IssueKind.NOT_REGULAR_FILE, IssueKind.UNREADABLE}


@pytest.mark.skipif(not HAS_MKFIFO, reason=FIFO_SKIP_REASON)
def test_fifo_is_rejected_without_blocking(tmp_path: Path) -> None:
    fifo = tmp_path / "pipe.txt"
    make_fifo(fifo)
    assert read_text(fifo, LIMIT) == NotRead(IssueKind.NOT_REGULAR_FILE)


@pytest.mark.skipif(
    not hasattr(os, "O_NOFOLLOW") or sys.platform == "win32", reason="needs O_NOFOLLOW"
)
def test_a_symlink_swapped_in_after_discovery_is_not_followed(tmp_path: Path) -> None:
    target = write(tmp_path, "target.txt", b"alice@example.com")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert read_text(link, LIMIT) == NotRead(IssueKind.UNREADABLE, "ELOOP")


def test_reading_does_not_modify_the_file(tmp_path: Path) -> None:
    path = write(tmp_path, "a.txt", b"x@example.com\r\n")
    before = (path.stat().st_size, path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()))
    read_text(path, LIMIT)
    after = (path.stat().st_size, path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()))
    assert before[0] == after[0]
    assert before[1] == after[1]
    assert before[2].digest() == after[2].digest()


def test_file_is_not_left_open(tmp_path: Path) -> None:
    path = write(tmp_path, "a.txt", b"abc")
    for _ in range(50):
        read_text(path, LIMIT)
    path.unlink()  # would fail on Windows if a handle were leaked
    assert not path.exists()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a\r\nb\rc\nd", ["a", "b", "c", "d"]),
        ("a\n\r", ["a", "", ""]),
        ("a\r\n\r\nb", ["a", "", "b"]),
        ("one", ["one"]),
        ("", [""]),
        (_ODD_BREAKS, [_ODD_BREAKS]),  # only CR/LF split lines
    ],
)
def test_split_lines_only_splits_on_cr_lf(text: str, expected: list[str]) -> None:
    assert split_lines(text) == expected


def test_decoded_text_of_helper_is_available() -> None:
    assert text_of(reader.decode_bytes(b"abc")) == "abc"

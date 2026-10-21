"""Bounded, read-only reading of one text file.

Safety properties
-----------------
* The file is opened read-only. ``O_NOFOLLOW`` (where the platform has it) refuses a symbolic
  link that appeared after discovery, and ``O_NONBLOCK`` stops a FIFO from blocking the open.
* ``fstat`` on the opened descriptor confirms a regular file before any read.
* At most ``max_bytes + 1`` bytes are read; a larger file is reported, never truncated and
  scanned as if complete.
* The content is decoded, never executed, and never written anywhere.

Encodings: UTF-8, UTF-8 with BOM, and UTF-16 with a BOM (as written by Windows PowerShell 5.1
``Tee-Object``/``Out-File``). UTF-32 BOMs are reported as unsupported. Without a BOM, a NUL
byte in the first 8 KiB is treated as binary content. Invalid UTF-8 is decoded with
replacement characters and reported as a warning; the file is still scanned.
"""

from __future__ import annotations

import errno
import os
import re
import stat
from dataclasses import dataclass

from datashuddhi.issues import IssueKind

_BINARY_SNIFF_BYTES = 8192
_UTF8_BOM = b"\xef\xbb\xbf"
_UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")
_UTF32_BOMS = (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")

_NEWLINE = re.compile(r"\r\n|\r|\n")

_OPEN_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_BINARY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_CLOEXEC", 0)
)


@dataclass(frozen=True, slots=True)
class TextContent:
    text: str
    encoding: str
    replaced: bool  # True if undecodable bytes were replaced with U+FFFD


@dataclass(frozen=True, slots=True)
class NotRead:
    kind: IssueKind
    detail: str = ""


def split_lines(text: str) -> list[str]:
    """Split on ``\\r\\n``, ``\\r`` or ``\\n`` only (not on form feed, U+2028, and so on)."""
    return _NEWLINE.split(text)


def _errno_name(exc: OSError) -> str:
    if exc.errno is None:
        return "OSERROR"
    return errno.errorcode.get(exc.errno, "OSERROR")


def decode_bytes(data: bytes) -> TextContent | NotRead:
    """Decode file bytes according to the rules in the module docstring."""
    if data.startswith(_UTF32_BOMS[0]) or data.startswith(_UTF32_BOMS[1]):
        return NotRead(IssueKind.UNSUPPORTED_ENCODING, "utf-32")
    if data.startswith(_UTF8_BOM):
        encoding = "utf-8-sig"
    elif data.startswith(_UTF16_BOMS):
        encoding = "utf-16"
    else:
        if b"\x00" in data[:_BINARY_SNIFF_BYTES]:
            return NotRead(IssueKind.BINARY_CONTENT)
        encoding = "utf-8"
    try:
        return TextContent(data.decode(encoding), encoding, replaced=False)
    except UnicodeDecodeError:
        return TextContent(data.decode(encoding, errors="replace"), encoding, replaced=True)


def read_text(path: str | os.PathLike[str], max_bytes: int) -> TextContent | NotRead:
    """Read and decode ``path`` (at most ``max_bytes`` bytes). Never raises ``OSError``."""
    try:
        fd = os.open(path, _OPEN_FLAGS)
    except OSError as exc:
        return NotRead(IssueKind.UNREADABLE, _errno_name(exc))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return NotRead(IssueKind.NOT_REGULAR_FILE)
        if info.st_size > max_bytes:
            return NotRead(IssueKind.TOO_LARGE)
        with os.fdopen(fd, "rb", closefd=False) as handle:
            data = handle.read(max_bytes + 1)
    except OSError as exc:
        return NotRead(IssueKind.UNREADABLE, _errno_name(exc))
    finally:
        os.close(fd)
    if len(data) > max_bytes:  # the file grew after fstat
        return NotRead(IssueKind.TOO_LARGE)
    return decode_bytes(data)

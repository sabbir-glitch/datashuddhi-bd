"""Safe report writer - the ONLY module allowed to create or replace files.

The scanned tree is never modified. The report file is written only when the user passes
``--output``, and only after these checks:

* The parent directory must exist (it is not created).
* The target must not be a symbolic link, a directory or another non-regular file.
* A target *inside the scan root* is refused unless ``--allow-output-in-scan-root`` is given,
  and an *existing* file inside the scan root is never overwritten, even with ``--force``.
* An existing file elsewhere is refused unless ``--force`` is given.
* New files are created with ``O_EXCL`` and owner-only permissions (0o600 on POSIX). With
  ``--force`` the report is written to a temporary file next to the target and moved over it
  with ``os.replace``.

Error messages are fixed strings and do not echo the path.
"""

from __future__ import annotations

import contextlib
import os
import stat

from datashuddhi.errors import DataShuddhiError

_CREATE_FLAGS = (
    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
)


class OutputError(DataShuddhiError):
    """The report destination is unsafe (usage error) or could not be written."""


class OutputWriteError(OutputError):
    """The destination passed all checks but writing failed (fatal, not a usage error)."""


def _inside(real_root: str, real_path: str) -> bool:
    root = os.path.normcase(real_root).rstrip(os.sep)
    path = os.path.normcase(real_path)
    return path == root or path.startswith(root + os.sep)


def check_output_target(
    target: str, scan_root: str, *, force: bool, allow_in_scan_root: bool
) -> str:
    """Validate ``target`` and return the absolute path to write. Raises :class:`OutputError`."""
    if not target or "\x00" in target:
        raise OutputError("output path is empty or invalid")
    absolute = os.path.abspath(target)
    name = os.path.basename(absolute)
    if not name or name in {".", ".."} or target.endswith(("/", os.sep)):
        raise OutputError("output path must name a file")
    parent = os.path.dirname(absolute)
    try:
        real_parent = os.path.realpath(parent, strict=True)
        parent_is_dir = stat.S_ISDIR(os.stat(real_parent).st_mode)
    except (OSError, ValueError):
        raise OutputError("output directory does not exist or cannot be accessed") from None
    if not parent_is_dir:
        raise OutputError("output directory does not exist or cannot be accessed")
    final = os.path.join(real_parent, name)

    exists = os.path.lexists(final)
    if exists:
        info = os.lstat(final)
        if stat.S_ISLNK(info.st_mode):
            raise OutputError("output path is a symbolic link; refusing to write through it")
        if not stat.S_ISREG(info.st_mode):
            raise OutputError("output path exists and is not a regular file")

    real_root = os.path.realpath(scan_root)
    root_is_dir = os.path.isdir(real_root)
    same_as_scanned_file = not root_is_dir and os.path.normcase(final) == os.path.normcase(
        real_root
    )
    inside_root = root_is_dir and _inside(real_root, final)
    if same_as_scanned_file or (inside_root and exists):
        raise OutputError("refusing to overwrite a file inside the scanned location")
    if inside_root and not allow_in_scan_root:
        raise OutputError(
            "output is inside the scan root; choose another location or pass "
            "--allow-output-in-scan-root"
        )
    if exists and not force:
        raise OutputError("output file already exists; pass --force to replace it")
    return final


def _write_new(path: str, data: bytes) -> None:
    fd = os.open(path, _CREATE_FLAGS, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(path)  # remove only the partial file this call just created
        raise


def write_report(final_path: str, text: str, *, replace_existing: bool) -> None:
    """Write ``text`` (UTF-8) to a path returned by :func:`check_output_target`."""
    data = text.encode("utf-8", errors="backslashreplace")
    try:
        if not replace_existing or not os.path.lexists(final_path):
            _write_new(final_path, data)
            return
        temporary = f"{final_path}.{os.getpid()}.{os.urandom(4).hex()}.tmp"
        _write_new(temporary, data)
        try:
            os.replace(temporary, final_path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
            raise
    except FileExistsError:
        raise OutputWriteError(
            "output file appeared while writing; nothing was overwritten"
        ) from None
    except OSError:
        raise OutputWriteError("the report could not be written") from None

"""Safe, bounded file discovery.

* Iterative traversal (no recursion), entries sorted case-insensitively, so results and
  limit behaviour are deterministic.
* Symbolic links and Windows reparse points (which include directory junctions) are never
  followed. A link that points to a directory, or that has a supported file name, is
  reported as ``link_not_followed`` so the result is not mistaken for a complete scan.
* Every discovered file is re-checked to resolve inside the scan root.
* Default exclusions (``.git``, ``.venv``, ``node_modules`` ...), user ``--exclude``
  patterns and unsupported file types are counted, not reported as issues.
* Traversal stops at the first supported file beyond the file limit.

Discovery never opens or reads file contents.
"""

from __future__ import annotations

import fnmatch
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

from datashuddhi.config import (
    DEFAULT_EXCLUDED_DIR_GLOBS,
    DEFAULT_EXCLUDED_DIRS,
    ScanOptions,
    is_supported_name,
)
from datashuddhi.errors import InvalidScanRootError
from datashuddhi.issues import IssueKind, IssueLog

_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


@dataclass(frozen=True, slots=True)
class DiscoveredFile:
    path: str  # filesystem path to open
    rel: str  # path relative to the scan root, '/' separators


@dataclass(slots=True)
class DiscoveryResult:
    root_name: str
    files: list[DiscoveredFile] = field(default_factory=list)
    excluded_dirs: int = 0
    excluded_files: int = 0
    unsupported_files: int = 0


def _fold(text: str) -> str:
    return text.casefold()


def _normalise_pattern(pattern: str) -> str:
    pattern = _fold(pattern.strip().replace("\\", "/"))
    while pattern.startswith("./"):
        pattern = pattern[2:]
    return pattern.rstrip("/")


class ExcludeMatcher:
    """Matches user ``--exclude`` patterns (case-insensitive ``fnmatch`` globs).

    A pattern without ``/`` matches a single file or directory *name* at any depth.
    A pattern containing ``/`` is matched against the whole relative path.
    """

    def __init__(self, patterns: tuple[str, ...]) -> None:
        self._name_patterns: list[str] = []
        self._path_patterns: list[str] = []
        for raw in patterns:
            pattern = _normalise_pattern(raw)
            if not pattern:
                continue
            (self._path_patterns if "/" in pattern else self._name_patterns).append(pattern)

    def matches(self, name: str, rel: str) -> bool:
        folded_name, folded_rel = _fold(name), _fold(rel)
        if any(fnmatch.fnmatchcase(folded_name, p) for p in self._name_patterns):
            return True
        return any(fnmatch.fnmatchcase(folded_rel, p) for p in self._path_patterns)


def is_default_excluded_dir(name: str) -> bool:
    folded = _fold(name)
    return folded in DEFAULT_EXCLUDED_DIRS or any(
        fnmatch.fnmatchcase(folded, glob) for glob in DEFAULT_EXCLUDED_DIR_GLOBS
    )


def is_link_like(entry: os.DirEntry[str]) -> bool:
    """Symbolic link, or a Windows reparse point (junction, mount point, ...)."""
    if entry.is_symlink():
        return True
    attributes = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attributes & _REPARSE_POINT)


def _inside(real_root: str, real_path: str) -> bool:
    root = os.path.normcase(real_root)
    path = os.path.normcase(real_path)
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def discover(root: str | os.PathLike[str], options: ScanOptions, log: IssueLog) -> DiscoveryResult:
    """Find supported files under ``root`` (a directory or a single supported file)."""
    root_text = os.fspath(root)
    try:
        real_root = os.path.realpath(root_text, strict=True)
        root_stat = os.stat(real_root)
    except (OSError, ValueError):
        raise InvalidScanRootError("scan path does not exist or cannot be accessed") from None

    result = DiscoveryResult(root_name=Path(real_root).name or real_root)

    if stat.S_ISREG(root_stat.st_mode):
        name = Path(real_root).name
        if not is_supported_name(name):
            raise InvalidScanRootError("scan path is a file of an unsupported type")
        result.files.append(DiscoveredFile(real_root, name))
        return result
    if not stat.S_ISDIR(root_stat.st_mode):
        raise InvalidScanRootError("scan path is neither a regular file nor a directory")

    matcher = ExcludeMatcher(options.exclude)
    max_files = options.limits.max_files

    def listing(directory: str, rel_dir: str) -> list[os.DirEntry[str]] | None:
        try:
            with os.scandir(directory) as iterator:
                return sorted(iterator, key=lambda e: (_fold(e.name), e.name))
        except OSError:
            log.add(IssueKind.UNREADABLE_DIRECTORY, rel_dir or ".")
            return None

    first = listing(real_root, "")
    stack: list[tuple[str, list[os.DirEntry[str]], int]] = []
    if first is not None:
        stack.append(("", first, 0))

    while stack:
        rel_dir, entries, index = stack.pop()
        if index >= len(entries):
            continue
        stack.append((rel_dir, entries, index + 1))
        entry = entries[index]
        rel = f"{rel_dir}/{entry.name}" if rel_dir else entry.name

        try:
            link = is_link_like(entry)
            if link:
                if is_default_excluded_dir(entry.name) or matcher.matches(entry.name, rel):
                    result.excluded_dirs += 1
                elif is_supported_name(entry.name) or entry.is_dir():
                    log.add(IssueKind.LINK_NOT_FOLLOWED, rel)
                continue
            if entry.is_dir(follow_symlinks=False):
                if is_default_excluded_dir(entry.name) or matcher.matches(entry.name, rel):
                    result.excluded_dirs += 1
                    continue
                children = listing(entry.path, rel)
                if children is not None:
                    stack.append((rel, children, 0))
                continue
            supported = is_supported_name(entry.name)
            if not entry.is_file(follow_symlinks=False):
                if supported:
                    log.add(IssueKind.NOT_REGULAR_FILE, rel)
                continue
        except OSError:
            log.add(IssueKind.UNREADABLE, rel)
            continue

        if not supported:
            result.unsupported_files += 1
            continue
        if matcher.matches(entry.name, rel):
            result.excluded_files += 1
            continue
        if len(result.files) >= max_files:
            log.add(IssueKind.FILE_LIMIT_REACHED)
            break
        if not _inside(real_root, os.path.realpath(entry.path)):
            log.add(IssueKind.OUTSIDE_SCOPE, rel)
            continue
        result.files.append(DiscoveredFile(entry.path, rel))

    return result

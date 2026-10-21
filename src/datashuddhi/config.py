"""Scan configuration: limits, supported file types, default exclusions.

All user-supplied values are validated here. Error messages are fixed strings and never
echo the offending value, which keeps odd input (including pasted data) out of logs.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field

from datashuddhi.errors import ConfigError

MIB = 1024 * 1024
GIB = 1024 * MIB

DEFAULT_MAX_FILE_BYTES = 5 * MIB
DEFAULT_MAX_FILES = 10_000
DEFAULT_MAX_FINDINGS = 10_000

MAX_FILE_BYTES_CEILING = 256 * MIB
MAX_FILES_CEILING = 1_000_000
MAX_FINDINGS_CEILING = 1_000_000

MAX_EXCLUDE_PATTERNS = 100
MAX_EXCLUDE_PATTERN_LENGTH = 256

SUPPORTED_EXTENSIONS = frozenset(
    {".txt", ".csv", ".json", ".log", ".ini", ".toml", ".yaml", ".yml", ".env"}
)

DEFAULT_EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".eggs",
        "build",
        "dist",
        "site-packages",
        ".idea",
        ".vscode",
    }
)
DEFAULT_EXCLUDED_DIR_GLOBS = ("*.egg-info",)


class FailOn(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    NEVER = "never"


def is_supported_name(name: str) -> bool:
    """True if a file *name* has a supported type (by extension, ``.env`` or ``.env.*``)."""
    lowered = name.casefold()
    if lowered == ".env" or lowered.startswith(".env."):
        return True
    dot = lowered.rfind(".")
    return dot > 0 and lowered[dot:] in SUPPORTED_EXTENSIONS


def _check_int(value: object, minimum: int, maximum: int, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{what} must be an integer")
    if value < minimum or value > maximum:
        raise ConfigError(f"{what} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class ScanLimits:
    """Hard limits that bound the work and memory of one scan."""

    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_files: int = DEFAULT_MAX_FILES
    max_findings: int = DEFAULT_MAX_FINDINGS

    def __post_init__(self) -> None:
        _check_int(self.max_file_bytes, 1, MAX_FILE_BYTES_CEILING, "maximum file size")
        _check_int(self.max_files, 1, MAX_FILES_CEILING, "maximum number of files")
        _check_int(self.max_findings, 1, MAX_FINDINGS_CEILING, "maximum number of findings")


@dataclass(frozen=True, slots=True)
class ScanOptions:
    limits: ScanLimits = field(default_factory=ScanLimits)
    exclude: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.exclude, tuple):
            raise ConfigError("exclude patterns must be a tuple")
        if len(self.exclude) > MAX_EXCLUDE_PATTERNS:
            raise ConfigError("too many exclude patterns")
        for pattern in self.exclude:
            if not isinstance(pattern, str) or not pattern.strip():
                raise ConfigError("exclude patterns must be non-empty text")
            if len(pattern) > MAX_EXCLUDE_PATTERN_LENGTH:
                raise ConfigError("an exclude pattern is too long")
            if "\x00" in pattern:
                raise ConfigError("exclude patterns must not contain NUL characters")


_SIZE_UNITS = {"": 1, "b": 1, "kib": 1024, "mib": MIB, "gib": GIB}
_SIZE_PATTERN = re.compile(r"([0-9]{1,12}) ?([A-Za-z]{0,3})", re.ASCII)


def parse_size(text: str) -> int:
    """Parse ``5242880``, ``5MiB``, ``512 KiB`` or ``1GiB`` into a byte count.

    Only binary units are accepted (B, KiB, MiB, GiB; case-insensitive) so that "MB" is never
    ambiguous. Raises :class:`ConfigError` with a fixed message (the text is not echoed).
    """
    match = _SIZE_PATTERN.fullmatch(text.strip())
    unit = match.group(2).lower() if match else None
    if match is None or unit not in _SIZE_UNITS:
        raise ConfigError("size must be a whole number of bytes or use B, KiB, MiB or GiB")
    return int(match.group(1)) * _SIZE_UNITS[unit]

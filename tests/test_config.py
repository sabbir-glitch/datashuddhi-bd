"""Tests for limits, options and supported file types."""

from __future__ import annotations

from typing import Any

import pytest

from datashuddhi.config import (
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_MAX_FILES,
    DEFAULT_MAX_FINDINGS,
    MAX_FILE_BYTES_CEILING,
    MIB,
    FailOn,
    ScanLimits,
    ScanOptions,
    is_supported_name,
    parse_size,
)
from datashuddhi.errors import ConfigError


def test_defaults_match_the_approved_limits() -> None:
    limits = ScanLimits()
    assert limits.max_file_bytes == 5 * MIB == DEFAULT_MAX_FILE_BYTES
    assert limits.max_files == 10_000 == DEFAULT_MAX_FILES
    assert limits.max_findings == 10_000 == DEFAULT_MAX_FINDINGS


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_file_bytes": 0},
        {"max_file_bytes": -1},
        {"max_file_bytes": MAX_FILE_BYTES_CEILING + 1},
        {"max_file_bytes": "5"},
        {"max_file_bytes": 1.5},
        {"max_file_bytes": True},
        {"max_files": 0},
        {"max_files": 1_000_001},
        {"max_findings": 0},
        {"max_findings": 1_000_001},
        {"max_findings": None},
    ],
)
def test_invalid_limits_are_rejected(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ConfigError):
        ScanLimits(**kwargs)


def test_boundary_limits_are_accepted() -> None:
    assert ScanLimits(max_file_bytes=1, max_files=1, max_findings=1).max_files == 1
    assert ScanLimits(max_file_bytes=MAX_FILE_BYTES_CEILING).max_file_bytes == 256 * MIB


def test_config_errors_do_not_echo_the_value() -> None:
    with pytest.raises(ConfigError) as info:
        ScanLimits(max_files="CANARY-VALUE")  # type: ignore[arg-type]
    assert "CANARY" not in str(info.value)


@pytest.mark.parametrize(
    "exclude",
    [("",), ("   ",), ("a\x00b",), ("x" * 257,), tuple(f"p{i}" for i in range(101)), ["list"]],
)
def test_invalid_exclude_patterns_are_rejected(exclude: Any) -> None:
    with pytest.raises(ConfigError):
        ScanOptions(exclude=exclude)


def test_valid_options() -> None:
    options = ScanOptions(exclude=("*.log", "docs/private"))
    assert options.exclude == ("*.log", "docs/private")
    assert options.limits == ScanLimits()


@pytest.mark.parametrize(
    ("name", "supported"),
    [
        ("a.txt", True),
        ("A.TXT", True),
        ("data.csv", True),
        ("data.json", True),
        ("app.log", True),
        ("settings.ini", True),
        ("pyproject.toml", True),
        ("c.yaml", True),
        ("c.yml", True),
        ("prod.env", True),
        (".env", True),
        (".ENV", True),
        (".env.local", True),
        (".env.production", True),
        ("script.py", False),
        ("page.html", False),
        ("archive.zip", False),
        ("image.png", False),
        ("notes", False),
        (".txt", False),
        ("env", False),
        ("a.txt.bak", False),
        ("a.txt~", False),
        ("envfile", False),
        (".environment", False),
    ],
)
def test_supported_names(name: str, supported: bool) -> None:
    assert is_supported_name(name) is supported


def test_fail_on_values() -> None:
    assert [f.value for f in FailOn] == ["low", "medium", "high", "never"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0", 0),
        ("1", 1),
        ("5242880", 5242880),
        ("512B", 512),
        ("512 b", 512),
        ("1KiB", 1024),
        ("5MiB", 5 * MIB),
        ("5mib", 5 * MIB),
        ("5 MiB", 5 * MIB),
        ("1GiB", 1024 * MIB),
        ("  64KiB  ", 64 * 1024),
    ],
)
def test_parse_size_accepts_documented_forms(text: str, expected: int) -> None:
    assert parse_size(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", " ", "MiB", "5MB", "5KB", "5GB", "5 M", "-1", "1.5MiB", "1e3", "5MiBB", "0x10",
     "১০", "5  MiB", "1" * 13, "five"],
)  # fmt: skip
def test_parse_size_rejects_everything_else(text: str) -> None:
    with pytest.raises(ConfigError) as info:
        parse_size(text)
    assert "B, KiB, MiB or GiB" in str(info.value)


def test_parse_size_error_does_not_echo_the_value() -> None:
    with pytest.raises(ConfigError) as info:
        parse_size("CANARY-SIZE")
    assert "CANARY" not in str(info.value)

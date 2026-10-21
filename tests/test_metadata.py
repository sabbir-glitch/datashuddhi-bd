"""Tests that keep package metadata and project policy consistent."""

from __future__ import annotations

import importlib.metadata
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

from datashuddhi import __version__

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_pyproject() -> dict[str, Any]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_version_looks_like_a_pep440_version() -> None:
    # Deliberately simple check (release segment plus optional .devN/aN/bN/rcN suffix).
    assert re.fullmatch(r"\d+\.\d+\.\d+((a|b|rc)\d+)?(\.dev\d+)?", __version__)


def test_version_is_single_sourced_from_the_package() -> None:
    project = _load_pyproject()["project"]
    assert "version" in project["dynamic"]
    assert "version" not in project  # no second, static copy that could drift


def test_installed_metadata_matches_module_version() -> None:
    try:
        installed = importlib.metadata.version("datashuddhi-bd")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("package is not installed; run `pip install -e .[dev]`")
    # If this fails after you changed __version__, re-run `pip install -e .[dev]`.
    assert installed == __version__


def test_runtime_has_no_third_party_dependencies() -> None:
    # Project decision D2: standard library only at runtime for v0.1.0.
    assert _load_pyproject()["project"]["dependencies"] == []


def test_python_floor_is_3_11() -> None:
    assert _load_pyproject()["project"]["requires-python"] == ">=3.11"


def test_console_script_points_at_cli_main() -> None:
    scripts = _load_pyproject()["project"]["scripts"]
    assert scripts == {"datashuddhi": "datashuddhi.cli:main"}


def test_licence_file_is_mit() -> None:
    text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("MIT License")
    assert "Permission is hereby granted, free of charge" in text

"""Tests for the M1 command-line skeleton."""

from __future__ import annotations

import subprocess
import sys

import pytest

from datashuddhi import __version__
from datashuddhi.cli import EXIT_OK, EXIT_USAGE, main


def test_version_flag_prints_version_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--version"])
    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert captured.out == f"datashuddhi {__version__}\n"
    assert captured.err == ""


def test_no_arguments_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([])
    captured = capsys.readouterr()
    assert code == EXIT_USAGE
    assert captured.out == ""
    assert "usage: datashuddhi" in captured.err


def test_unknown_option_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--no-such-option"])
    captured = capsys.readouterr()
    assert code == EXIT_USAGE
    assert captured.out == ""
    assert "unrecognized arguments" in captured.err


def test_module_invocation_prints_version() -> None:
    # Runs `python -m datashuddhi --version` in a separate process, using the same
    # interpreter that runs the tests. The arguments are fixed, not user-controlled.
    result = subprocess.run(
        [sys.executable, "-m", "datashuddhi", "--version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0
    assert result.stdout == f"datashuddhi {__version__}\n"
    assert result.stderr == ""

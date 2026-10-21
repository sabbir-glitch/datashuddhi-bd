"""Command-line interface.

``datashuddhi scan PATH`` scans a file or directory you are authorised to inspect and
prints a report containing *masked* values only. Nothing is uploaded, no file is modified,
and the only file ever written is the optional ``--output`` report.

Exit codes: 0 clean, 1 findings reached ``--fail-on``, 2 usage error, 3 fatal or
incomplete scan. See :mod:`datashuddhi.exit_codes`.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import TextIO

from datashuddhi import __version__
from datashuddhi.config import (
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_MAX_FILES,
    DEFAULT_MAX_FINDINGS,
    FailOn,
    ScanLimits,
    ScanOptions,
    parse_size,
)
from datashuddhi.errors import ConfigError, InvalidScanRootError, ScanFatalError
from datashuddhi.exit_codes import EXIT_FATAL, EXIT_OK, EXIT_USAGE, decide_exit
from datashuddhi.output import OutputError, OutputWriteError, check_output_target, write_report
from datashuddhi.reporting.console import encodable_for, render_summary, render_text
from datashuddhi.reporting.json_report import build_report, render_json
from datashuddhi.scanner import scan_path

__all__ = ["EXIT_OK", "EXIT_USAGE", "build_parser", "main"]


def _size_argument(text: str) -> int:
    try:
        return parse_size(text)
    except ConfigError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _count_argument(text: str) -> int:
    if not text.isascii() or not text.isdigit() or len(text) > 12:
        raise argparse.ArgumentTypeError("must be a whole number")
    return int(text)


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="datashuddhi",
        description=(
            "Find potential personal data before you share it. Scans local files you are "
            "authorised to inspect for potential email addresses and Bangladeshi mobile "
            "numbers. Local only: no telemetry, no uploads, no file is modified."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    scan = commands.add_parser(
        "scan",
        help="scan a file or directory",
        description=(
            "Scan PATH (a directory or one supported file: .txt .csv .json .log .ini .toml "
            ".yaml .yml .env). Findings are potential matches; values are always masked."
        ),
        epilog=(
            "exit codes: 0 complete and below --fail-on; 1 findings reached --fail-on; "
            "2 usage error; 3 fatal or incomplete scan"
        ),
        allow_abbrev=False,
    )
    scan.add_argument("path", metavar="PATH", help="file or directory to scan")
    scan.add_argument("--format", choices=("text", "json"), default="text", help="report format")
    scan.add_argument("--output", metavar="FILE", help="write the report to FILE (not stdout)")
    scan.add_argument(
        "--exclude",
        metavar="PATTERN",
        action="append",
        default=[],
        help="skip files/directories matching this case-insensitive glob (repeatable)",
    )
    scan.add_argument(
        "--max-file-size",
        metavar="SIZE",
        type=_size_argument,
        default=DEFAULT_MAX_FILE_BYTES,
        help="largest file to scan, e.g. 5MiB (default 5MiB; B, KiB, MiB, GiB; max 256MiB)",
    )
    scan.add_argument(
        "--max-files",
        metavar="N",
        type=_count_argument,
        default=DEFAULT_MAX_FILES,
        help=f"most files to scan (default {DEFAULT_MAX_FILES})",
    )
    scan.add_argument(
        "--max-findings",
        metavar="N",
        type=_count_argument,
        default=DEFAULT_MAX_FINDINGS,
        help=f"most findings to collect (default {DEFAULT_MAX_FINDINGS})",
    )
    scan.add_argument(
        "--fail-on",
        choices=[f.value for f in FailOn],
        default=FailOn.LOW.value,
        help="lowest severity that gives exit code 1 (default low; 'never' disables only this)",
    )
    scan.add_argument(
        "--force",
        action="store_true",
        help="replace an existing --output file (outside the scan root)",
    )
    scan.add_argument(
        "--allow-output-in-scan-root",
        action="store_true",
        help="permit a new --output file inside the directory being scanned",
    )
    return parser


def _write(stream: TextIO, text: str) -> None:
    stream.write(encodable_for(text, stream))
    stream.flush()


def _error(message: str) -> None:
    _write(sys.stderr, f"datashuddhi: error: {message}\n")


def _scan_command(args: argparse.Namespace) -> int:
    try:
        options = ScanOptions(
            limits=ScanLimits(
                max_file_bytes=args.max_file_size,
                max_files=args.max_files,
                max_findings=args.max_findings,
            ),
            exclude=tuple(args.exclude),
        )
    except ConfigError as exc:
        _error(str(exc))
        return EXIT_USAGE

    target: str | None = None
    if args.output is not None:
        try:
            target = check_output_target(
                args.output,
                args.path,
                force=args.force,
                allow_in_scan_root=args.allow_output_in_scan_root,
            )
        except OutputError as exc:
            _error(str(exc))
            return EXIT_USAGE

    try:
        result = scan_path(args.path, options)
    except InvalidScanRootError as exc:
        _error(str(exc))
        return EXIT_USAGE
    except ScanFatalError as exc:
        _error(str(exc))
        return EXIT_FATAL
    except Exception as exc:  # report only the class name: the text could hold file content
        _error(f"internal error ({type(exc).__name__}); no result was produced")
        return EXIT_FATAL

    fail_on = FailOn(args.fail_on)
    code = decide_exit(findings=result.findings, complete=result.complete, fail_on=fail_on)
    if args.format == "json":
        report = render_json(build_report(result, fail_on, code))
    else:
        report = render_text(result, fail_on, code)

    if target is not None:
        try:
            write_report(target, report, replace_existing=args.force)
        except OutputWriteError as exc:
            _error(str(exc))
            return EXIT_FATAL
        _write(sys.stdout, render_summary(result, code))
        _write(sys.stdout, "Report written to the requested output file.\n")
    else:
        _write(sys.stdout, report)

    if not result.complete and (args.format == "json" or target is not None):
        _write(
            sys.stderr,
            "datashuddhi: warning: the scan is INCOMPLETE; this is not a complete clean scan.\n",
        )
    return code


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface and return the process exit code.

    argparse reports usage errors by raising ``SystemExit``; that is converted into a
    plain integer here so callers and tests always receive a return value.
    """
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return EXIT_OK
        return code if isinstance(code, int) else EXIT_USAGE

    if args.command != "scan":
        parser.print_help(sys.stderr)
        return EXIT_USAGE
    try:
        return _scan_command(args)
    except KeyboardInterrupt:
        _write(sys.stderr, "datashuddhi: interrupted; no complete result was produced.\n")
        return EXIT_FATAL
    except BrokenPipeError:
        return EXIT_FATAL

# DataShuddhi BD

> Find potential personal data before you share it.

**Status: pre-alpha, not released (version `0.1.0.dev0`).** The `datashuddhi scan` command works
and is tested, but the project is unpublished and has no release. See "What has and has not been
verified" below for exactly what was run where.

DataShuddhi BD is an independent, open-source project. It is not affiliated with or endorsed by
any government agency, bank, telecom operator or company.

## What it does

A local-first command-line tool that scans files **you are authorised to inspect** and reports
**potential** personal data. Values are always masked in the output; there is no "reveal" mode.

| What it looks for | Example mask |
| --- | --- |
| Email addresses (ASCII) | `a***@***.com` |
| Bangladeshi mobile numbers (013-019 prefixes; `01...`, `+880...`, `00880...`, `+88 01...`; ASCII and Bengali digits) | `*********78` |

Supported file types: `.txt .csv .json .log .ini .toml .yaml .yml .env` (and `.env.*` names).
Files are read line by line as text; CSV and JSON are not parsed. UTF-8, UTF-8 with BOM and
UTF-16 with BOM (as written by Windows PowerShell 5.1) are supported.

## Important limits (read before relying on it)

- Findings are **potential matches from pattern rules, not verified facts.** A phone-shaped
  number may be an order ID; a matching email may belong to a role account or a service.
- A scan with no findings does **not** prove a file contains no personal data. Names, addresses,
  national ID numbers, obfuscated values, images and many other formats are not detected.
- **Version 0.1.0 does not detect passwords, API keys, tokens or other secrets.** Use a
  dedicated secret scanner for that.
- Bangladeshi number matching is syntactic. No official BTRC numbering plan was found, so a
  match does not mean the number is assigned or active.
- This tool cannot prevent a data breach. It helps you notice some personal data before you
  share a file.

## Usage

```text
datashuddhi scan PATH [--format text|json] [--output FILE]
                      [--exclude PATTERN]... [--max-file-size SIZE]
                      [--max-files N] [--max-findings N]
                      [--fail-on low|medium|high|never]
                      [--force] [--allow-output-in-scan-root]
```

Defaults: 5 MiB per file, 10,000 files, 10,000 findings; `--fail-on low`. Sizes accept bytes
or `B`, `KiB`, `MiB`, `GiB` (maximum 256 MiB).

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | The scan was complete and no finding reached the `--fail-on` threshold |
| 1 | At least one finding reached the threshold (the report also says if the scan was incomplete) |
| 2 | Usage or configuration error (bad option, missing path, unsafe output path) |
| 3 | Fatal error, interrupt, or **incomplete scan** with no finding at the threshold |

A scan is *incomplete* if anything that should have been scanned was not: a file was too large,
binary, in an unsupported encoding or unreadable; a symbolic link or junction was not followed;
or the file or finding limit was reached. `--fail-on never` disables only the finding-based
failure; an incomplete scan still exits with 3. Default exclusions (`.git`, `.venv`,
`node_modules`, ...), `--exclude` patterns and unsupported file types are counted in the report
but are not treated as problems.

## Privacy and safety properties

- Local only: no network access, no telemetry, no uploads, no subprocesses. Tests enforce this.
- Scanned files are only read, never modified, deleted or executed.
- Raw matched values are never stored in findings, reports, logs or error messages.
- The only file ever written is the optional `--output` report: it is refused inside the scan
  root unless you pass `--allow-output-in-scan-root`, an existing file needs `--force`, and a
  scanned file is never overwritten.
- Reports contain file *paths* (relative to the scan root). A file name can itself contain
  personal data, so treat reports as sensitive too.

## What has and has not been verified

M11-rc2 (candidate; see the M11-rc2 section of the [release notes](docs/release-notes.md)):

- **Linux Python matrix (observed):** the full pytest suite on Python 3.11.17, 3.12.15, 3.13.16,
  3.14.8 and 3.15.0 gave 1696 collected, 1695 passed, 0 failed, 1 skipped on each (pytest 9.1.1;
  the skip is the Windows-only directory-junction test, `tests/test_discovery.py:330`). The matrix
  was not repeated after four documentation tests were added; on Python 3.13.16 the current tree
  collects 1700 tests (1699 passed, 1 skipped).
- **Static checks:** Ruff lint, Ruff format and Pyright (normal and Windows platform) passed on
  Python 3.13.16 only.
- **Packaging (Linux):** the sdist and wheel build and the clean-environment checks passed on
  Python 3.13.16 only. A separate Windows packaging run is recorded below.
- **Windows (owner-observed, Windows 10, elevated Administrator PowerShell, Python 3.13.1,
  pytest 9.1.1) for the temporary candidate `datashuddhi-bd-M11-rc2-windows-test.zip`:**
  1700 collected, 1690 passed, 10 skipped, 0 failed; `scripts\check.ps1` passed all four checks;
  the sdist and wheel built and `scripts/check_dist.py` passed (version 0.1.0.dev0); manual
  console and JSON scans of synthetic data gave exit code 1, two masked findings, no raw values,
  and an unchanged input hash, and a clean file gave exit code 0. The two Linux `VmHWM` memory
  tests skip on Windows (the measurement needs `/proc/self/status`), so **peak-memory behaviour
  was not tested on Windows**. Details and the skip list are in the
  [release notes](docs/release-notes.md).
- **Not observed:** macOS and GitHub Actions. The Linux and Windows results above do not show
  that the GitHub Actions workflow passes; it has never run.

M11-rc1 (historical evidence, not M11-rc2 results): Linux (cloud development environment, Python 3.11,
3.12, 3.13, 3.14 and 3.15.0), Ruff lint, Ruff format, Pyright and pytest were run; see
[release notes](docs/release-notes.md) for the versions and test counts.

**Windows observations** (reported by the project owner). Environment for both runs: Windows 10,
Windows PowerShell 5.1, Python 3.13.1, pytest 9.1.1, Ruff 0.17.0, Pyright 1.1.414.

| Archive tested | SHA-256 | Tests | Result |
| --- | --- | --- | --- |
| `datashuddhi-bd-M10.zip` | `52bdafe1472974f67509cfa30d1f60e2efbd030aef7016f20e0dd37fa1e0fcf3` | 1611 | 1602 passed, 9 skipped; all four checks passed; manual console and JSON scans as documented |
| `datashuddhi-bd-M10-final.zip` | `b08501ed084d4f79853d60a5f0aefeccf795ec83b0ef1d04adc0a115e84a9ff9` | 1617 | 1608 passed, 9 skipped; `scripts\check.ps1`: all 4 checks passed |

- In both runs Ruff lint and format passed, Pyright reported 0 errors, 0 warnings and 0 informations,
  and the real directory-junction test was not among the skips, so it ran and passed.
- The manual scan check (console and JSON, exit code 1, masked values, no raw values in the JSON,
  input file hash unchanged) was done on the earlier `M10` archive only.
- The privilege context (elevated or not) of these sessions is **unconfirmed**; non-elevated runs
  are therefore not claimed as verified.
- The nine skipped tests in those earlier runs are POSIX-specific (see [testing](docs/testing.md)); those behaviours are
  **not verified on Windows**. Long paths, alternate data streams, real console encodings and
  Windows memory use (the memory test is POSIX-only) are also unverified.
- These results describe the named archives only. Windows verification of any later archive is
  recorded in the acceptance report that accompanies that archive, not in this file.

GitHub Actions has **not** been run: the workflow is checked only by static tests, and no remote
CI result exists.

## Documentation

- [Architecture](docs/architecture.md) and [threat model](docs/threat-model.md)
- [Data-detection limitations](docs/data-detection-limitations.md) (read this first)
- [Responsible use](docs/responsible-use.md)
- [Testing](docs/testing.md) and [development](docs/development.md)
- [Dependencies and licences](docs/dependencies.md)
- [Gitleaks guidance](docs/gitleaks-integration.md) (documentation only)
- [Release notes](docs/release-notes.md)
- [Contributing](CONTRIBUTING.md), [security policy](SECURITY.md), [changelog](CHANGELOG.md)

## Development (Windows PowerShell)

Run these in PowerShell from the project folder.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" -c constraints-dev.txt
.\scripts\check.ps1
.\.venv\Scripts\python.exe -m datashuddhi scan .\some-folder
```

The scripts call the virtual environment's Python directly, so you do not need to activate it
and you do not need to change your PowerShell execution policy.

## Licence

MIT. Copyright (c) 2026 Sabbir Ahammed (see `LICENSE`).

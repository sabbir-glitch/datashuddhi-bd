# Release notes - 0.1.0 (unreleased, release candidate of the M10 snapshot)

Nothing has been published: no Git repository was initialised from this project, nothing was pushed
to GitHub, nothing was uploaded to PyPI, and no release was created.

## What this snapshot contains

A local-first command-line tool, `datashuddhi scan PATH`, that reports **potential** email
addresses and Bangladeshi mobile numbers with masked values, in text or JSON (schema v1), with
documented exit codes (0, 1, 2, 3), file-size/file-count/finding limits, no following of
symbolic links or junctions, and an output writer that refuses to overwrite scanned files.
Runtime dependencies: none (Python 3.11 or newer).

## Not in this snapshot

- **Credential and secret detection** (passwords, keys, tokens). Use a dedicated tool; see
  [gitleaks-integration.md](gitleaks-integration.md) (documentation only, never run by this project).
- Names, addresses, national ID numbers, financial data, documents, images, archives.
- Presidio or any machine-learning component; any network feature; any telemetry.

## M11-rc2 changes (recovery rebuild)

Relative to M11-rc1: the memory test measures `VmHWM`, `MANIFEST.in` (`prune tests`),
`scripts/check_dist.py` (which also requires the installed CLI to print exactly
`datashuddhi <declared version>`), `tests/test_packaging.py`, a required Python 3.15 CI job and a
package job that runs the checker. `src/` is unchanged.

M11-rc2 results, kept in separate categories:

1. **Linux Python matrix (observed, all passed).** `python -m pytest -rs`, pytest 9.1.1, each
   interpreter in its own virtual environment installed with `constraints-dev.txt`:

   | Python | Collected | Passed | Failed | Skipped |
   | --- | --- | --- | --- | --- |
   | 3.11.17 | 1696 | 1695 | 0 | 1 |
   | 3.12.15 | 1696 | 1695 | 0 | 1 |
   | 3.13.16 | 1696 | 1695 | 0 | 1 |
   | 3.14.8 | 1696 | 1695 | 0 | 1 |
   | 3.15.0 | 1696 | 1695 | 0 | 1 |

   This matrix ran on the tree before four documentation tests were added; the five-version
   matrix was not repeated afterwards. The current tree, checked on Python 3.13.16 only, collects
   1700 tests: 1699 passed, 1 skipped.

   The one skip is `tests/test_discovery.py:330`, "directory junctions exist on Windows only". The
   collected count was 1696 both from a clean tree and with `.pytest_cache/README.md` present, and
   the memory tests ran and passed on every version. Python 3.12.15, 3.14.8 and 3.15.0 were
   installed with `uv`; 3.11.17 and 3.13.16 were the system interpreters. None came from GitHub
   runners.
2. **Static checks (Python 3.13.16 only, not run on each interpreter):** Ruff lint, Ruff format
   check, Pyright and Pyright with the Windows platform setting all passed.
3. **Packaging.** On Linux (Python 3.13.16 only, not repeated per interpreter) a fresh
   `python -m build --outdir dist-check` succeeded and `scripts/check_dist.py` passed, including
   clean-environment installs of the sdist and the wheel. A separate Windows build and
   `scripts/check_dist.py` run is recorded in item 5.
4. **M11-rc1 results** below are historical evidence, not M11-rc2 results.
5. **Windows testing of M11-rc2 (owner-observed; separate from the Linux results above):**
   Observed on Windows by the project owner, testing the temporary candidate
   `datashuddhi-bd-M11-rc2-windows-test.zip` (SHA-256
   `21345adf4df93518b85255b96d8a79a2d5c3a5e22f811f912077290b5a3bac53`). Environment: Windows 10,
   Windows PowerShell in an elevated Administrator session, Python 3.13.1, pytest 9.1.1, Ruff 0.17.0,
   Pyright 1.1.414, build 1.6.1, setuptools 84.2.1 (isolated build environment).

   - Full suite: 1700 collected, 1690 passed, 10 skipped, 0 failed, and it passed repeatedly.
   - `scripts/check.ps1`: all four checks passed (Ruff lint; Ruff format, 64 files already
     formatted; Pyright, 0 errors and 0 warnings; pytest, 1690 passed and 10 skipped, exit code 0).
   - The sdist and wheel built on Windows, and `python scripts/check_dist.py --dist-dir dist-check`
     reported both packages passed with version 0.1.0.dev0.
   - Manual scans of synthetic data (`alice@example.com` and `01712345678`): the console scan
     exited 1 with two findings, masked as `a***@***.com` and `*********78`, and neither raw value
     appeared in the output. The JSON scan exited 1, parsed, held exactly two findings, both
     masked, with neither raw value present. The input file's SHA-256 was identical before and
     after scanning (`AEE18670FE9AD33AD8E2E73D213E160E80BA728CED6BE6D0926DF32FB6EED30C`). A scan of
     a clean file exited 0 with zero findings.
   - The ten skips: three POSIX-only adversarial tests (reason in the code: "POSIX-only
     behaviour"); the two Linux `VmHWM` memory tests; the control-characters test ("control
     characters are invalid in Windows names"); the two FIFO tests ("FIFOs need a POSIX
     platform"); the permission-bits test ("POSIX permission bits"); and the `O_NOFOLLOW` test
     ("needs O_NOFOLLOW"). The owner reported the count (10) and the totals; the individual skip
     lines were not supplied, so this list and its reasons come from the skip conditions in the
     test code, not from a line-by-line reading of the Windows output.
   - The two memory tests skip on Windows because the Linux `VmHWM` measurement from
     `/proc/self/status` is unavailable there (the skip reason says it needs a readable `VmHWM`
     in `/proc/self/status`, Linux). **Peak-memory behaviour was therefore not tested on Windows.**
   - The directory-junction test is not a Windows skip: it ran there, as the totals imply.
   - The privilege context was an elevated session; non-elevated Windows is unverified. Windows
     Python versions other than 3.13.1 are unverified.
6. **macOS testing: not yet observed.** The temporary ZIP was not tested on macOS.
7. **GitHub Actions (owner-reported; separate from the local results above):** see the GitHub
   Actions paragraph under "Windows" below; the local Linux and Windows results are not CI
   results.

## Verification record

Cloud (Linux, development environment), M11-rc1 package (historical; not re-run for M11-rc2): Ruff lint, Ruff format
check, Pyright and pytest on Python 3.11.17, 3.12.3, 3.13.16, 3.14.6 and 3.15.0: all passed.
pytest: 1637 passed, 1 skipped on each version (1638 tests; the skip is the Windows-only junction
test), both from a clean tree and again after pytest had created `.pytest_cache/README.md`. Pyright also reports 0 errors with its platform set to Windows. For comparison, the cloud runs
of the earlier archives were 1610 passed, 1 skipped (`datashuddhi-bd-M10.zip`, 1611 tests),
1616 passed, 1 skipped (`datashuddhi-bd-M10-final.zip`, 1617 tests), 1622 passed, 1 skipped
(`datashuddhi-bd-M10-rc2.zip`, 1623 tests in a clean tree) and 1631 passed, 1 skipped
(`datashuddhi-bd-M10-rc3.zip`, 1632 tests).

### Windows (owner-observed; separate from the cloud results above)

Environment for both runs: Windows 10, Windows PowerShell 5.1, Python 3.13.1, pytest 9.1.1,
Ruff 0.17.0 and Pyright 1.1.414.

| Check | `datashuddhi-bd-M10.zip` (earlier archive) | `datashuddhi-bd-M10-final.zip` (corrected archive) |
| --- | --- | --- |
| SHA-256 | `52bdafe1472974f67509cfa30d1f60e2efbd030aef7016f20e0dd37fa1e0fcf3` | `b08501ed084d4f79853d60a5f0aefeccf795ec83b0ef1d04adc0a115e84a9ff9` |
| Ruff lint | passed | passed |
| Ruff format | passed (62 files) | passed (62 files) |
| Pyright | 0 errors | 0 errors, 0 warnings, 0 informations |
| pytest | 1611 collected: 1602 passed, 9 skipped | 1617 collected: 1608 passed, 9 skipped |
| `scripts\check.ps1` | all 4 checks passed | `RESULT: PASSED - all 4 checks passed.` |
| Manual console and JSON scans | done (see below) | not done; only `check.ps1` output was supplied |

- Owner-observed Windows run of the earlier `datashuddhi-bd-M10-rc2.zip` (SHA-256
  `87b47c99eb8ec3950efc39fde373e90b5c527e899e68acde893ede991707495b`): all four checks passed,
  1624 collected, 1615 passed, 9 skipped. The one test above the clean-tree count of 1623 was the
  Markdown-link test collecting pytest's own `.pytest_cache/README.md`; this package selects only
  the project's own Markdown files, so the count no longer depends on prior pytest runs.
- The directory-junction test was not among the skips in either run: it ran and passed on Windows.
- Manual scans on the earlier archive: a synthetic file returned exit code 1 with two masked
  findings; the JSON report parsed, held no raw email or phone value, and the input file's SHA-256
  was unchanged.
- Privilege context (elevated or not): **unconfirmed**. Non-elevated verification is not claimed.
- The nine skips, all POSIX-specific and therefore **unverified on Windows**: four POSIX-only
  adversarial tests (invalid-UTF-8 file names, control/bidi characters in file names, the memory
  regression test, the hard-link test); control characters in Windows file names; the FIFO
  discovery test; the FIFO reader test; POSIX permission bits; `O_NOFOLLOW` support.
- An earlier owner-reported Windows run (M7 snapshot) had failed Pyright on `os.mkfifo` in two
  tests. That was fixed with a typed helper (`tests/posix_support.py`); both M10 runs passed Pyright.
- These results describe the named archives only. Windows verification of any later archive,
  including the release candidate that carries this file, is recorded in the separate acceptance
  report for that archive and is not claimed here.

GitHub Actions has run in the project's GitHub repository (<https://github.com/sabbir-glitch/datashuddhi-bd>). An earlier run failed because `tests/test_packaging.py` compared the bytes of `MANIFEST.in` with LF line endings while the Windows runner checked the file out with CRLF. The fix, commit `77aa31e` ("Make packaging manifest test line-ending independent"), triggered the run that the owner reports as successful (a green success indicator in an owner-provided screenshot). This is owner-reported evidence: the run ID, the individual job results and the test counts were not inspected for this record, so it supports only that the run was shown as successful, not that every job's output was reviewed. It says nothing about macOS, which has not been tested.

`pip-audit` on the pinned development tools: no known vulnerabilities at the time of one local run
(scope described in [dependencies.md](dependencies.md)).

## Known limitations

See [data-detection-limitations.md](data-detection-limitations.md) and
[threat-model.md](threat-model.md). In short: pattern matching only (false positives and
negatives); BD operator prefixes 013-019 are a documented assumption without an official BTRC
source; a scan with no findings is not proof of absence; hard links are scanned; the memory
regression test is POSIX-only; non-elevated Windows runs, long paths and real console encodings
are unverified.

## Open items before any public release

1. Inspect every job of the GitHub Actions run (its job-level results were not inspected for this
   record); the Python 3.15 job and the package job in particular. The pinned action SHAs (`actions/checkout`, `actions/setup-python`) have been checked against their
   upstream commit and release pages, which is separate from running the workflow.
2. Enable private vulnerability reporting on the repository once it exists (the advisory link in
   `SECURITY.md` and `.github/ISSUE_TEMPLATE/config.yml` works only then).
3. Decide on the source-distribution contents (it currently includes `tests/` but not `docs/`).
4. Run the full checks on Windows with the exact final tree, and non-elevated (the privilege
   context of earlier runs is unconfirmed).
5. Obtain an official source for Bangladeshi numbering prefixes, if one exists.

# Testing guide

## Test layers

- **Unit tests** per module (`tests/test_<module>.py`): masking, normalisation, findings,
  detectors, reader, discovery, config, issues, output, reporting.
- **Detector corpus** (`tests/corpus.py`, `tests/test_detector_corpus.py`): labelled lines tagged
  `TP`, `TN`, `KNOWN_FP`, `KNOWN_FN`. Known limits are executable tests, so a change in behaviour is
  visible.
- **End-to-end CLI tests** (`tests/test_cli_scan.py`): exit codes 0/1/2/3, `--fail-on`, output
  safety.
- **Privacy regression tests** (`tests/test_privacy.py`, `tests/test_detector_safety.py`): canary
  values must not appear in any report, console output, exception text or log.
- **Repository guards** (`tests/test_repo_hygiene.py`): every phone/email-shaped string in the
  repository (including these docs) must be an approved synthetic value; the source must import no
  network/subprocess/dynamic-code modules and only `output.py` may write.
- **Workflow and documentation checks** (`tests/test_workflows.py`, `tests/test_docs.py`): static
  checks of the CI file and docs. They do not prove that CI runs.

## Synthetic data

All data comes from `tests/synthetic.py`: reserved email domains (example.com/.net/.org, `.test`,
`.example`, `.invalid`, `.localhost`) and eight fixed patterned phone numbers. No official
reserved range for Bangladeshi numbers was found, so even patterned numbers could in theory
coincide with a real subscriber; hence the short, fixed, enforced list. **Never add real data to
tests, fixtures or docs.**

## Running

Windows PowerShell, from the project folder (no activation or execution-policy change needed):

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" -c constraints-dev.txt
.\scripts\check.ps1
```

`check.ps1` runs Ruff lint, Ruff format check, Pyright and pytest, and reports every failure.
Individual commands:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pyright
.\.venv\Scripts\python.exe -m pytest -q
```

Linux/macOS: the same commands with `.venv/bin/python`.

## Skipped tests

Some tests depend on the platform and skip elsewhere; a skip is not a pass for that behaviour.

| Test | Skipped when | Why |
| --- | --- | --- |
| Windows directory junction not followed | not Windows | Junctions exist only on Windows |
| FIFO not opened (reader, discovery) | Windows | `os.mkfifo` is POSIX-only |
| Control characters in file names | Windows | Invalid in Windows file names |
| POSIX permission bits | Windows | Windows has no POSIX mode bits |
| Symlink swapped in after discovery | no `O_NOFOLLOW` | Platform lacks the flag |
| Adversarial: invalid-UTF-8 names, control/bidi names, hard link (3 tests) | Windows | POSIX-only file-system features |
| Memory tests (2: pathological domain, heavy parent) | not Linux, or no readable `VmHWM` in `/proc/self/status` | No trustworthy peak-memory measurement; skipped with a reason, never replaced by `ru_maxrss` |

**Windows, historical (M11-rc1 and earlier; owner-observed, Python 3.13.1):** exactly nine tests
skipped. They were four POSIX-only adversarial tests (invalid-UTF-8 file names, control and bidi
characters in file names, the memory regression test, and the hard-link test), the control
characters test, the two FIFO tests (reader and discovery), the permission-bits test and the
`O_NOFOLLOW` test. The junction test did not skip there; it ran and passed. In M11-rc1 the memory
test was one of the POSIX-only adversarial tests; from M11-rc2 it is replaced by the two memory
tests in the table above, which are grouped separately.

**Windows, M11-rc2 (owner-observed, Python 3.13.1, the temporary Windows-test candidate):** 1700
collected, 1690 passed, **10 skipped**, 0 failed. The ten are the three POSIX-only adversarial
tests in the table, the two memory tests, the control characters test, the two FIFO tests, the
permission-bits test and the `O_NOFOLLOW` test (nine, minus the one M11-rc1 memory test, plus
two). The count is observed; the composition and the reasons come from the skip conditions in the
test code, because the individual skip lines were not supplied. The two memory tests skip on
Windows because the Linux `VmHWM` measurement from `/proc/self/status` is unavailable, so peak
memory behaviour was **not tested on Windows**. macOS has not been observed.

## Platform notes on the hostile-input tests

- **Termination/timing** (`tests/test_adversarial.py`, `tests/test_detector_safety.py`): run on
  every platform; they assert that hostile lines finish within a generous time bound.
- **Memory**: `test_pathological_domain_does_not_amplify_memory` runs the detector on a 4 MB
  pathological line in a separate Python process (`python -I`) and reads that process's own
  `VmHWM` (resident-set high-water mark, kB meaning 1024 bytes) from `/proc/self/status`. The
  parser accepts exactly one `VmHWM: <digits> kB` line. `ru_maxrss` is deliberately not used: on
  Linux a child inherits its parent's peak across `execve`, so inside a large pytest process it can
  report memory the probe never used. A second test runs the probe from a parent that first holds
  and frees 200 MiB and asserts that the probe's own peak is still under 150 MiB. Where no
  trustworthy measurement exists (not Linux, or no readable `VmHWM`) both tests skip with a
  stated reason; macOS and Windows have not been verified. `VmHWM` is a coarse, Linux-only,
  whole-kB resident-page peak that includes the interpreter and imports, not an exact or portable
  measure. The 150 MiB limit is a regression tripwire (healthy about 20 MiB, the old defect about
  450 MiB), not a guarantee. `tracemalloc` is not used because it does not reliably see
  regex-engine allocations.
- Tests with hostile file names (invalid UTF-8, control characters) are POSIX-only because Windows
  does not allow those names.

## Packaging checks

`MANIFEST.in` contains `prune tests`, so the source distribution holds the package source and
metadata but not `tests/`; the full test suite is run from a repository checkout.
`scripts/check_dist.py` (stdlib only) lists the sdist and wheel without extracting them, requires
`src/`, `README.md`, `LICENSE` and metadata in the sdist, rejects any `tests/` path, installs each
archive into its own clean virtual environment (not editable), runs `datashuddhi --version` and a
synthetic JSON scan, and fails on an unexpected exit code, a missing mask or a raw email in the
output. The expected version is read from the project (`pyproject.toml` declares it dynamic; the
checker follows that to `__version__` in `src/datashuddhi/__init__.py` without importing it) and the
installed command must print exactly `datashuddhi <version>`. Build output goes to `dist-check/`
(ignored by Git):

```powershell
python -m pip install "build==1.6.1"
python -m build --outdir dist-check
python scripts/check_dist.py --dist-dir dist-check
```

`tests/test_packaging.py` tests the checker logic with fake archives. The CI `package` job runs
the same commands; that job has not been run on GitHub.

## Python matrix record (M11-rc2, Linux)

The full suite was run on Python 3.11.17, 3.12.15, 3.13.16, 3.14.8 and 3.15.0 (1696 collected,
1695 passed, 1 skipped on each; see the [release notes](release-notes.md)). 3.12.15, 3.14.8 and
3.15.0 were installed with `uv`. This is a local Linux record; it does not show that the GitHub
Actions workflow passes. The owner's separate Windows run of M11-rc2 is recorded under "Skipped
tests" above and in the release notes; macOS has not been observed.

## Reproducibility

Development tool versions are pinned in `constraints-dev.txt`; the runtime has no dependencies.
Tests use no randomness and no network. The only timing-dependent test is a regex stress test with a generous bound (`tests/test_detector_safety.py`); it could in principle flake on a very slow machine. `filterwarnings = ["error"]` turns
any warning into a failure.

The collected test count is deterministic: the Markdown-link test is parametrised over the project's
own Markdown files only (top-level `*.md`, `docs/` and `.github/`), never over `.pytest_cache`,
virtual environments or build output, so running pytest twice in the same directory collects the
same tests. The only intentional platform difference is the skip set (one skip on Linux; nine on
Windows up to M11-rc1 and ten observed for M11-rc2 (owner-run), because the memory tests now skip
there as well; see above).

## What the tests do not prove

- They do not prove detection quality on real data; the corpus is small and synthetic.
- Passing on one platform does not prove another. See the verification record in the README and
  CHANGELOG for what was actually run where.
- The GitHub Actions workflow is checked statically; a green remote run has not been observed.

# Development guide

## Set-up (Windows PowerShell, from the project folder)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" -c constraints-dev.txt
.\.venv\Scripts\python.exe -m datashuddhi --version
```

Calling `.venv\Scripts\python.exe` directly avoids activation scripts and execution-policy changes.
On Linux/macOS use `python3 -m venv .venv` and `.venv/bin/python`.

## Checks before every change

```powershell
.\scripts\check.ps1
```

This runs Ruff (lint and format check), Pyright and pytest and prints a summary. Do not modify
`scripts/check.ps1` without a deliberate decision: it must stay ASCII with CRLF line endings
(guarded by a test).

## Layout

```
src/datashuddhi/   package (see architecture.md for module responsibilities)
tests/             unit, corpus, CLI, privacy and repository-guard tests
docs/              documentation
scripts/check.ps1  Windows quality-check runner
.github/           CI workflow, templates, Dependabot
```

## Adding a detector

1. Add a module in `src/datashuddhi/detectors/` that returns `RawMatch` objects and builds findings
   through a `Rule` (see `detectors/email.py`), with a masking function in `redaction.py`.
2. Add the detector to `default_detectors()` in `detectors/__init__.py`; give the rule a stable id
   (`DS-<NAME>-NNN`).
3. Add labelled `TP/TN/KNOWN_FP/KNOWN_FN` cases to `tests/corpus.py`, using only synthetic data.
4. Add masking tests: the mask must never contain more than the policy reveals.
5. Add the limits to `docs/data-detection-limitations.md` and an entry to `CHANGELOG.md`.
6. Keep bounded regex quantifiers; add an input-length stress test.

## Rules for contributors

- No runtime dependencies without a recorded decision (`docs/dependencies.md`).
- Never print, log, store or put into an exception any matched raw value.
- Only `output.py` may write files; nothing may open a file for writing in a scanned location.
- No network, subprocess or dynamic-code imports in `src/` (tested).
- Error messages are fixed strings; do not echo user-supplied values.

## Checking the built package

`MANIFEST.in` keeps `tests/` out of the source distribution. After a build, run
`python scripts/check_dist.py --dist-dir dist-check` (see [testing](testing.md)); it reads the
expected version from the project and requires the installed command to print exactly
`datashuddhi <version>`.

## Versioning and release

The version lives in `src/datashuddhi/__init__.py`. The CHANGELOG heading for the unreleased
version must match it (tested). Releasing, tagging and publishing are manual, owner-approved
steps and are not automated.

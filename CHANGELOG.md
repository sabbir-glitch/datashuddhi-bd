# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The project has not been released.

## 0.1.0 – unreleased

### Pre-CI fixes (M11-rc2)

- Memory regression test now reads the probe's own `VmHWM` from `/proc/self/status` instead of
  `ru_maxrss` (which a child inherits from its parent's peak); the 150 MiB limit is unchanged; the
  tests skip with a reason where no trustworthy measurement exists; a heavy-parent test and parser
  tests were added.
- `MANIFEST.in` (`prune tests`), `scripts/check_dist.py` and `tests/test_packaging.py`: the source
  distribution excludes `tests/`, and sdist and wheel are installed and smoke-tested.
- CI: Python 3.15.0 (stable) is a required job; the `package` job runs the distribution checker.
  (When this entry was first written no GitHub Actions run had occurred; see the entry below.)
- Verified on Linux across Python 3.11.17, 3.12.15, 3.13.16, 3.14.8 and 3.15.0 (see the release
  notes). Owner-observed on Windows 10 (Python 3.13.1) for the temporary candidate: 1700 collected,
  1690 passed, 10 skipped, 0 failed, `scripts\check.ps1` passed, packaging checked. macOS is
  not observed.
- GitHub Actions: an earlier run failed because `tests/test_packaging.py` compared `MANIFEST.in`
  bytes with LF while Windows checked the file out with CRLF. Commit `77aa31e` made that test
  line-ending independent, and the run it triggered is reported by the owner as successful (a green
  indicator in a screenshot). The run ID and job-level results were not inspected, and this does
  not show macOS support.

### Added

- `datashuddhi scan PATH` command with text and JSON (schema v1) reports and the options
  `--output`, `--exclude`, `--max-file-size`, `--max-files`, `--max-findings`, `--fail-on`,
  `--force`, `--allow-output-in-scan-root`.
- Exit codes: 0 complete and below threshold, 1 findings reached threshold, 2 usage or
  configuration error, 3 fatal error or incomplete scan.
- Rule `DS-EMAIL-001` (ASCII email-address shapes) and `DS-BDPHONE-001` (Bangladeshi mobile-number
  shapes, prefixes 013-019, ASCII and Bengali digits). Always-masked output; no reveal mode.
- Safe, read-only file handling: size, file-count and finding limits; no following of symbolic
  links or junctions; binary and unsupported-encoding detection; guarded `--output` writer.
- Completeness model: an incomplete scan is never presented as clean.
- Synthetic labelled detector corpus, privacy-regression tests and repository guards.
- Documentation: architecture, threat model, detection limitations, responsible use, testing,
  development, dependencies, Gitleaks guidance (documentation only).
- GitHub Actions workflow, issue/PR templates, Dependabot for actions (see the GitHub Actions entry
  under M11-rc2 for what has been observed).

### Security hardening

- Email domains are bounded (at most 126 labels, 253 characters, 63 per label). A pathological
  4 MB line previously made the regex engine use about 470 MB; regression tests guard this.

### Owner metadata and repository preparation

- `LICENSE` names the copyright holder; `SECURITY.md` names the security contact and the advisory
  link; the issue-template link points at the intended repository. No placeholders remain.
- The repository-wide email hygiene test now allows exactly the approved security contact, and only
  in `SECURITY.md`; every other non-reserved address is still rejected.
- `.gitignore` also ignores `dist-check/`. The CI workflow comment records that the pinned action
  SHAs were checked against upstream (the workflow had not run at that point).

### Testing

- The Markdown-link test now selects only top-level, `docs/` and `.github/` Markdown files, so
  the collected test count no longer changes when `.pytest_cache/README.md` exists.

### Not included

- Credential and secret detection. Presidio and Gitleaks are not integrated.
- Parsing of CSV/JSON structure, PDF, office documents, images or archives.

### Verification status

See the README section "What has and has not been verified" for the exact record.

# Threat model

Scope: the `datashuddhi` command-line program (version 0.1.0 development) running on a
developer's or administrator's machine, scanning files that the user is authorised to read.

## Assets

1. **Personal data inside scanned files.** The tool must not leak it, alter it, or copy it.
2. **The scanned files themselves** (integrity and availability).
3. **The user's machine and terminal** (the tool must not be a vector for code execution or
   terminal manipulation).
4. **Reports.** Masked, but file paths and the existence of findings are still sensitive.

## Trust boundaries and assumptions

* The user running the tool is authorised to read the scan root. The tool does not enforce
  authorisation; see `responsible-use.md`.
* **Scanned content is untrusted.** Files may be malformed, enormous, binary, adversarial, or
  crafted to attack the scanner or the person reading its output.
* The operating system, Python interpreter and file system are trusted. The tool does not defend
  against a compromised machine or a malicious Python installation.
* Other local users or processes may be able to change the file system while a scan runs.

## Threats and mitigations

| # | Threat | Mitigation | Evidence (tests) |
| --- | --- | --- | --- |
| T1 | Raw personal data leaks into a report, log or error | `Finding` has no raw field; masks applied at once; no logging; fixed-string errors; fail-closed on mask error | `test_privacy.py`, `test_cli_scan.py` canary tests, `test_findings.py` |
| T2 | Data is exfiltrated over the network (telemetry, upload) | No network code or imports in `src/`; no environment/proxy settings read | `test_repo_hygiene.py` import ban; scans run with sockets patched, in-process and in a subprocess |
| T3 | The tool modifies or deletes scanned files | Read-only opens; only `output.py` can write; exclusive create; refuses to write inside scan root by default and never overwrites a scanned file | no-modification snapshot tests; AST write ban; `test_output.py` |
| T4 | `--output` overwrites an important file or follows a symlink | Symlink/directory targets refused; existing file needs `--force`; temp file + `os.replace`; `O_EXCL` | `test_output.py` |
| T5 | Symlink or junction escape (scan reads outside the intended tree) | Links and reparse points are never followed and are reported; per-file realpath containment check; `O_NOFOLLOW` where available | `test_discovery.py` (junction test runs on Windows only) |
| T6 | Resource exhaustion: huge file, huge tree, huge output, deep nesting | Per-file byte limit with bounded read; file limit; findings limit; iterative walk; capped issue lists | limit tests; hostile 1 MiB line tests |
| T7 | Regular-expression denial of service | Bounded quantifiers; lookbehind anchors so each run is examined once; time-bounded adversarial tests | `test_detector_safety.py` |
| T8 | Hostile file names or content corrupt the terminal (control sequences, bidi spoofing) | Control, format (bidi) and unassigned characters are escaped in text output; JSON is ASCII-escaped | `test_reporting.py`, `test_cli_scan.py` |
| T9 | A partial scan is mistaken for a clean scan | Completeness model; exit code 3; prominent "INCOMPLETE" label; `--fail-on never` cannot hide it | exit-code tests |
| T10 | Special files block or confuse the scan (FIFOs, devices) | `fstat` regular-file check; `O_NONBLOCK`; non-regular files reported | reader and discovery tests (POSIX) |
| T11 | Supply-chain compromise of the tool | No runtime dependencies; development tools pinned in `constraints-dev.txt`; `pip-audit` in CI; GitHub Actions pinned to SHAs; Dependabot for Actions | `test_workflows.py`, `test_metadata.py` |
| T12 | Test data contains real personal data | Synthetic-data policy enforced by a repository-wide guard test | `test_repo_hygiene.py` |
| T13 | Malicious bytes cause code execution when read | Files are decoded as text, never executed or imported; no `eval`/`exec`/`pickle`/`subprocess` in `src/` | AST bans |

## Residual risks (not eliminated)

* **File names are reported.** A path such as `customers/alice-smith-export.csv` appears in the
  report. Treat reports as sensitive and do not post them publicly.
* **Time-of-check/time-of-use races.** A file or directory can change between discovery and read.
  The reader re-checks with `fstat` and a bounded read, and refuses a link swapped in at open
  time (where `O_NOFOLLOW` exists), but a local attacker with write access can still influence what is scanned.
  The output path check has a similar window; `O_EXCL` prevents overwriting a file that appears late.
* **Masked values still reveal a little**: the last two phone digits, or the first email character
  and the final domain label. This is a deliberate trade-off for locating findings; there is no reveal mode.
* **Privileged runs.** Running as Administrator/root widens what can be read. Run with the least
  privilege that can read the target.
* **Memory.** Each file (default at most 5 MiB, configurable to 256 MiB) is held in memory as bytes
  and as decoded text.
* **Hard links.** A hard link is indistinguishable from a regular file, so content of an outside
  file that is hard-linked into the scan root is scanned (read-only; output stays masked).
* **Windows behaviour is only partly verified.** The directory-junction test ran and passed on
  Windows 10 / Python 3.13.1 (owner-observed, on the M10 and M10-final archives). The privilege
  context of those runs is unconfirmed, and non-elevated runs, long paths, alternate data streams and
  real console encodings have not been verified.
* **Names that are not valid Unicode.** Invalid file-name bytes on POSIX are reported with
  surrogate escapes (`\udcXX`) in JSON; a strict JSON consumer may reject lone surrogates.
* **Larger limits mean more memory.** Raising `--max-file-size` toward the 256 MiB ceiling can use
  several times that in memory. Defaults are conservative.
* **Detection is incomplete** (see `data-detection-limitations.md`); a clean report is not proof.

## Out of scope

Network attackers, malicious Python or OS, physical access, authorisation decisions, protecting
data from the user who already has read access, and any claim of breach prevention.

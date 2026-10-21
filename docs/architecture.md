# Architecture

DataShuddhi BD is a small, dependency-free Python package (`src/datashuddhi`) with a command-line
front end. This page describes how a scan flows through it and why it is built this way.

## Data flow

```text
datashuddhi scan PATH
        |
   cli.py  --- validates options (config.py) and the --output target (output.py) ---+
        |                                                                          |
   scanner.scan_path()                                                             |
        |                                                                          |
   discovery.discover()   safe, bounded, sorted file discovery (never reads files) |
        |  list of files + counts + issues                                         |
   reader.read_text()     bounded read, BOM-aware decoding, line splitting         |
        |  text, or an issue (too_large, binary_content, ...)                      |
   detectors (email, bd_phone)   RawMatch(start, end, raw, confidence) per line    |
        |                                                                          |
   Rule.build_finding()   applies the mask, creates a Finding  (raw value dropped) |
        |                                                                          |
   ScanResult  -> reporting/console.py or reporting/json_report.py                 |
        |                                                                          |
   exit_codes.decide_exit()   0 / 1 / 3          output.write_report() <-----------+
```

## Modules

| Module | Responsibility |
| --- | --- |
| `cli.py` | argparse front end; maps outcomes to exit codes; prints reports. Reads no environment variables. |
| `config.py` | `ScanLimits`, `ScanOptions`, supported file types, default exclusions, size parsing. Validates everything; error messages never echo the value. |
| `discovery.py` | Iterative directory walk. Skips symlinks and Windows reparse points, applies exclusions, enforces the file limit, and re-checks that each file resolves inside the scan root. |
| `reader.py` | Opens files read-only, refuses non-regular files, reads at most `max_bytes + 1` bytes, decodes UTF-8 / UTF-8 BOM / UTF-16 BOM, splits lines on CR, LF and CRLF only. |
| `normalize.py` | Maps Bengali digits to ASCII digits with a same-length copy (columns stay valid). |
| `detectors/` | `Detector` interface, `Rule`, `RawMatch`, and the two v0.1.0 detectors. |
| `redaction.py` | The masking policy (`mask_email`, `mask_phone`). |
| `findings.py` | The immutable `Finding` model, `Severity`, `Confidence`. It has no field for a raw value. |
| `issues.py` | `IssueKind`, `IssueLog`: the completeness model (see below). |
| `scanner.py` | Orchestration; fail-closed handling of detector and masking errors; limits. |
| `exit_codes.py` | `decide_exit` and the documented exit codes. |
| `reporting/` | Text and JSON renderers. Text output escapes control and bidi characters. |
| `output.py` | The **only** module allowed to create or replace files (the `--output` report). A test enforces this. |

## Completeness model

A scan result is **complete** only if nothing that should have been scanned was skipped.

* *Issues* make a scan **incomplete**: `too_large`, `binary_content`, `unsupported_encoding`,
  `unreadable`, `unreadable_directory`, `link_not_followed`, `outside_scope`,
  `not_regular_file`, `file_limit_reached`, `finding_limit_reached`, `internal_error`.
* *Warnings* do not: `decode_replaced` (invalid UTF-8 bytes were replaced; the file was still scanned).
* *Intentional skips* (default exclusions, `--exclude`, unsupported file types) are counted in the
  report and are neither issues nor warnings.

An incomplete scan with no finding at the `--fail-on` threshold exits with code 3, never 0.

## Privacy by construction

* A detector yields `RawMatch` objects whose `raw` field is excluded from `repr`. The scanner
  applies the rule's mask immediately and builds a `Finding`; the raw text is not kept.
* `Finding` validates that its masked value contains `*`, is short, and printable, so a broken
  mask function that returns the raw value is rejected.
* If a detector or mask raises, the scanner records `internal_error` (fixed text, no exception
  message) and the scan is incomplete. It never falls back to an unmasked value.
* OS errors are reported as an errno name such as `EACCES`, never as the OS message (which can
  contain paths).

## Safe file handling

* Reading: `os.open` with `O_RDONLY` (+ `O_NOFOLLOW`, `O_NONBLOCK` where available), then `fstat`
  to confirm a regular file, then a bounded read. Opening a FIFO cannot block the scan.
* Discovery never opens file contents and never follows links.
* Writing: only `--output`, created with `O_EXCL` and owner-only permissions; see the threat model.

## Detection design

Each detector works on a single line. Matches may overlap between detectors (for example the
digits of a phone-like local part inside an email address); both are reported. Phone detection
runs on a digit-normalised, same-length copy of the line, so reported columns are 1-based
**Unicode code-point** offsets in the original line. Columns are not byte offsets or grapheme
clusters.

Adding a detector means: a `Rule` (id, category, severity, explanation, remediation, mask), a
`Detector.find(line)` generator, a masking function with tests, entries in the labelled corpus
(`tests/corpus.py`), a hostile-input timing test, and an update to
`data-detection-limitations.md`.

## Decisions (approved)

| # | Decision |
| --- | --- |
| D1 | Python 3.11 or newer |
| D2 | `argparse`; no runtime dependencies |
| D3 | No secret detection in v0.1.0; Gitleaks integration is documentation only |
| D4 | File types `.txt .csv .json .log .ini .toml .yaml .yml .env`; line-by-line text scanning, no CSV/JSON parsing |
| D5 | MIT licence |
| D6 | Limits: 5 MiB per file, 10,000 files, 10,000 findings (configurable, validated) |
| D7 | Bengali digit support without modifying the source; correct line and column |
| D8 | No reveal mode |
| D9 | `--fail-on {low,medium,high,never}`; exit codes 0, 1, 2, 3 |
| D14 | Phone mask `*********NN`; email mask `a***@***.tld`; email severity LOW, phone MEDIUM (provisional) |

## Presidio

Microsoft Presidio is **not** used in v0.1.0. `presidio-analyzer` 2.2.364 (MIT licence;
`Requires-Python >=3.10,<3.15`, so it does not support Python 3.15) pulls in `spacy`, `numpy`,
`pydantic`, `phonenumbers` and others, and needs a language model download for NLP-based
recognisers. For two regular-expression rules that cost is not justified. It remains a candidate
for an optional extra if name or address detection is added later. See `dependencies.md`.

# Data-detection limitations

DataShuddhi BD 0.1.0 reports **potential** matches from two pattern rules. It does not verify
anything. Read this page before relying on a result.

## What is (and is not) detected

| Rule | Detects | Does not detect |
| --- | --- | --- |
| `DS-EMAIL-001` | ASCII email-address shapes | Obfuscated or encoded addresses, non-ASCII local parts, addresses without a dotted domain |
| `DS-BDPHONE-001` | Bangladeshi mobile-number shapes with operator prefixes 013-019 | Numbers with other separators or parentheses, spelled-out numbers, prefixes 010-012, landlines |

**Version 0.1.0 does not detect credentials or secrets** (passwords, API keys, tokens, private
keys). It also does not detect names, postal addresses, national ID or passport numbers, bank or
card numbers, dates of birth, health data, photographs or anything inside images, PDFs,
spreadsheets, archives or databases. A scan with no findings does **not** show that a file is free
of personal data. See [gitleaks-integration.md](gitleaks-integration.md) for secret scanning.

## Potential versus verified

A finding means "this text has the shape of an email address / mobile number". It does not mean
the value is real, assigned, active, personal, or sensitive. Severity (LOW for email, MEDIUM for
phone) and confidence are provisional labels for triage, not risk assessments.

## Bangladeshi mobile numbers

Accepted forms (ASCII or Bengali digits U+09E6-U+09EF): `01X XXXXXXXX`, `+880 1X...`,
`00880 1X...`, `+88 01X...`, and bare `8801X...`, with a single space or hyphen in the groupings
3+8, 5+6 (national form) and 2+4+4, 4+6 (international form). Confidence is HIGH only with an
explicit `+` or `00` international prefix; otherwise MEDIUM.

**Operator prefixes.** Only 013, 014, 015, 016, 017, 018 and 019 are matched. Sources:

- The Daily Star, 21 Aug 2016, "GP gets new number series 013"
  (<https://www.thedailystar.net/business/gp-gets-new-number-series-013-1273441>): 013 for
  Grameenphone; 010, 012 and 014 were then unallocated; 011 belonged to Citycell (it would only be
  freed if its licence were cancelled); 015 Teletalk, 016 Airtel, 018 Robi, 019 Banglalink.
- The Daily Star, 25 Aug 2018 (<https://www.thedailystar.net/node/1624651>): BTRC approved 013 for
  Grameenphone and 014 for Banglalink.
- Wikipedia, "Telephone numbers in Bangladesh": a secondary source, used only for cross-checking.
- ITU's national numbering-plan document is a 2007 `.doc` file that could not be read here.

**No official BTRC numbering plan was found.** The prefix list is therefore a documented
assumption. Consequences:

- `010`, `011` and `012` are deliberately **not** matched; a number that is genuinely in use on
  such a prefix would be a false negative.
- Operators change through number portability and re-allocation, so a prefix does not identify the
  current operator. The tool never reports an operator name.
- A match means "right shape", not "assigned or active".

## Known false positives (reported, but probably not personal data)

From the labelled test corpus (`tests/corpus.py`, cases tagged `KNOWN_FP`):

- An identifier shaped like a mobile number (`order_id=01712345678`).
- Service or role addresses (`git@example.com`, `noreply@example.com`).
- Any synthetic or placeholder number or address that is syntactically valid.

## Known false negatives (personal data that is missed)

Cases tagged `KNOWN_FN` in the corpus; each is a documented limit, not a bug being hidden:

- Email domains longer than 253 characters, or with a label over 63 characters, are not valid DNS
  names and are dropped whole (never reported as a partial match). The regex also bounds a domain
  to 126 dot-separated labels to keep matching memory small; with the 253-character check this
  never rejects a valid name (the densest valid name has 125 one-letter labels plus a TLD).
- Obfuscated emails: `alice at example dot com`, `alice[at]example.com`, `alice%40example.com`.
- Non-ASCII local part (`ব্যবহারকারী@example.com`) and domains with no dot (`root@localhost`).
- Phone numbers with irregular spacing (`01 7 1234 5678`), parentheses
  (`+880 (17) 1234-5678`), a no-break space, dots (`017.1234.5678`), or spelled out in words.
- Arabic-Indic digits (U+0660-U+0669). They are deliberately not normalised: Bangladeshi numbers
  use ASCII or Bengali digits.
- Values split across lines, or inside base64, compressed or encrypted data.
- Deliberate suppression: a digit run that is part of a longer digit sequence is not matched, and
  image-asset names such as `logo@2x.png` are not reported as emails.

## Files, encodings and lines

- Supported names: `.txt .csv .json .log .ini .toml .yaml .yml .env` and `.env.*`. Other types are
  counted as "unsupported" and are not scanned. The extension is trusted, not content-sniffed.
- CSV and JSON are scanned as plain text, line by line; they are not parsed.
- Encodings: UTF-8, UTF-8 with BOM, UTF-16 with BOM. A UTF-32 BOM is reported as an unsupported
  encoding. UTF-16 without a BOM contains NUL bytes, so it is treated as binary. Both make the scan
  incomplete. A NUL byte in the first 8 KiB marks a file as binary. Invalid UTF-8 is decoded with
  replacement characters, scanned, and reported as a warning (the scan stays complete).
- Lines split on CR, LF and CRLF only. **Columns are 1-based Unicode code points**, not bytes or
  grapheme clusters, so they may differ from an editor's display column.
- Limits (defaults): 5 MiB per file (maximum 256 MiB), 10,000 files, 10,000 findings. Files
  over the limit are reported and not scanned. Reaching a limit makes the scan *incomplete*.
- Symbolic links and Windows junctions/reparse points are never followed; each is reported.
- A file that changes while it is being read can be scanned partly or not at all.

## Incomplete scans

If anything that should have been scanned was not, the scan status is `incomplete` and the exit
code is 3 (or 1 if findings reached the threshold). Never treat an incomplete scan as clean.

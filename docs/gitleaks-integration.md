# Using Gitleaks alongside DataShuddhi BD

**Version 0.1.0 does not detect credentials or secrets.** Gitleaks is a dedicated secret scanner.
This page is documentation only: DataShuddhi BD does not call Gitleaks, bundle it, or pass
findings to it, and none of the commands below have been run as part of this project's tests.
They are based on the Gitleaks README (<https://github.com/gitleaks/gitleaks>, MIT licence);
check `gitleaks --help` for your installed version.

## Principles

1. **Run the tools separately.** Each reads your files itself. Do not pipe one tool's output into
   the other.
2. **Never auto-feed findings.** DataShuddhi findings contain masked values and must not be handed
   to another program or service. The integration is "run both", not "chain them".
3. **Gitleaks reports can contain real secrets.** Unless redacted, its report holds the matched
   secret. Treat the report as a secret, keep it out of the repository and out of shared folders,
   and delete it after use.
4. **Check `--redact` on your version.** The README describes `--redact` as redacting secrets "from
   logs and stdout", with an optional percentage; it does not say whether report files are
   covered. Inspect a report from a synthetic test before assuming it is redacted.
5. **Install from the official project** and verify what you download. Review its licence and
   release notes before use in your organisation.

## Example commands (Windows PowerShell)

Scan a directory (the `dir` command; `files` and `directory` are aliases) and a Git repository
(the `git` command) with Gitleaks, writing reports outside the scanned folder:

```powershell
# Run from any folder. $target is the folder you are authorised to inspect.
$target = "C:\path\to\your\project"
gitleaks dir $target --redact --report-format json --report-path "$env:TEMP\gitleaks-report.json"
gitleaks git $target --redact --report-format json --report-path "$env:TEMP\gitleaks-git-report.json"
```

Then run DataShuddhi BD separately:

```powershell
.\.venv\Scripts\python.exe -m datashuddhi scan $target --fail-on never --format json --output "$env:TEMP\datashuddhi-report.json"
```

Review both reports yourself and delete them afterwards:

```powershell
Remove-Item "$env:TEMP\gitleaks-report.json", "$env:TEMP\gitleaks-git-report.json", "$env:TEMP\datashuddhi-report.json"
```

Notes:

- `detect` and `protect` are deprecated in Gitleaks since v8.19.0 in favour of `git` and `dir`.
- `--exit-code` (default 1 when leaks are found) lets CI fail on findings; set it deliberately.
- Gitleaks exit codes are independent of DataShuddhi's (0/1/2/3). Do not combine them without
  documenting what each means.

## What is not provided

No wrapper, no plugin, no shared report format, and no verified end-to-end test with Gitleaks.
If an integration is added in future it must stay opt-in, local, and documented here first.

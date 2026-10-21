## What does this change?

<!-- A short description and the reason for the change. -->

## Checklist

- [ ] `scripts/check.ps1` (or ruff, ruff format, pyright and pytest) passes locally
- [ ] Tests were added or updated for changed behaviour
- [ ] **All test data is synthetic**: no real emails, phone numbers, names, credentials,
      tokens, keys or documents (use `example.com`-style domains and the numbers in
      `tests/synthetic.py`)
- [ ] No raw matched value can reach a finding, report, log or error message
- [ ] No new network access, subprocess use, telemetry, or file writes outside `output.py`
- [ ] No new runtime dependency (or the decision and licence check are described below)
- [ ] Documentation and `CHANGELOG.md` updated where behaviour changed

## Notes for the reviewer

<!-- Anything unverified, platform-specific, or risky. -->

# Contributing

Thank you for helping. DataShuddhi BD is a small, security-sensitive project, so a few rules matter
more than usual.

## Ground rules

- **Synthetic data only.** Never put real personal data, customer records, leaked data, passwords,
  tokens, keys or ID documents in code, tests, fixtures, issues, pull requests or docs. Use the
  values in `tests/synthetic.py` (reserved email domains and the approved patterned phone numbers);
  a test fails if another phone- or email-shaped value appears anywhere in the repository.
- **Raw matched values must never leave a detector** (no logs, reports, exceptions, reprs).
- **Read-only scanning.** Only `output.py` may write, and only the user's `--output` report.
- **No new runtime dependency** without a written assessment in `docs/dependencies.md`.
- **Be honest about limits.** Document false positives/negatives; do not claim guaranteed
  detection or breach prevention; keep "potential" wording.
- Do not report vulnerabilities in public issues: see [SECURITY.md](SECURITY.md).

## Workflow

1. Open an issue (bug, false positive, or feature) using the templates. For a false positive or
   negative, describe the *shape* of the text with a synthetic example.
2. Set up as in [docs/development.md](docs/development.md) and make a small, focused change.
3. Add or update tests first or alongside. A detector change needs corpus cases.
4. Run `.\scripts\check.ps1` (Windows) or the four commands in [docs/testing.md](docs/testing.md).
   All must pass; do not disable rules, weaken assertions, or hide failures.
5. Update the docs and `CHANGELOG.md` when behaviour changes.
6. Open a pull request using the template and state exactly what you ran and on which platform.

## Style

Python 3.11+, type-annotated, formatted and linted with Ruff, checked with Pyright (see
`pyproject.toml`). Prefer small modules, clear names and fixed-string error messages.

## Conduct

Be respectful and constructive. Assume good faith, and keep discussion technical.

## Licence

By contributing you agree that your contribution is licensed under the project's MIT licence.

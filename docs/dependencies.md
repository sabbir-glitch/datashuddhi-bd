# Dependency and licence assessment

## Runtime

**None.** The package uses only the Python standard library (Python 3.11 or newer). A test
(`tests/test_metadata.py`) fails if a runtime dependency is added without a deliberate decision.
This keeps installation simple and the supply-chain exposure of the scanner itself minimal.

## Development tools

Pinned in `constraints-dev.txt` (known-good versions, generated on Linux with Python 3.13).
They are used for checks only and are not shipped.

| Package | Version | Licence | Purpose |
| --- | --- | --- | --- |
| pytest | 9.1.1 | MIT | tests |
| ruff | 0.17.0 | MIT | lint and format |
| pyright | 1.1.414 | MIT | static types (pip wrapper downloads the Node-based checker) |
| iniconfig | 2.3.1 | MIT | pytest dependency |
| pluggy | 1.6.0 | MIT | pytest dependency |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | pytest dependency |
| pygments | 2.21.0 | BSD-2-Clause | pytest dependency |
| nodeenv | 1.11.0 | BSD | pyright wrapper dependency |
| typing-extensions | 4.16.0 | PSF-2.0 | pyright wrapper dependency |

All are permissive licences compatible with an MIT-licensed project. Licences were recorded from
package metadata when the pins were chosen; re-check on upgrade. Platform-specific helpers
(for example `colorama` on Windows) are intentionally left unpinned.

`pyright` needs network access at first run to fetch its Node.js checker through `nodeenv` (a
property of the pip package; see its documentation). Offline machines should install the tools
beforehand.

**Scope of `pip-audit`.** The audit command is
`pip-audit -r constraints-dev.txt --no-deps --disable-pip`. It checks only the nine pinned
development-tool versions listed above against the vulnerability data its default service returns
at the time of the run. It does not audit the project's own code, the Node.js checker that Pyright
downloads, GitHub Actions, or the operating system, and a clean result means "no known
vulnerability in that data at that time", not "secure". One local run on 2026-10-15 (pip-audit in
the cloud environment) reported "No known vulnerabilities found"; the CI job has not run remotely.

CI additionally uses `pip-audit` (pinned in the workflow) to check the pinned development tools
against known-vulnerability data. This sends package names and versions, not scanned content, to
the vulnerability service, and runs only in CI or when you run it yourself.

## Evaluated and not adopted

| Candidate | Decision | Reason |
| --- | --- | --- |
| Microsoft Presidio (`presidio-analyzer` 2.2.364) | Not used in 0.1.0 | MIT licence, but `Requires-Python >=3.10,<3.15` (would block the required Python 3.15 job), and its core dependencies (click, numpy, phonenumbers, pydantic, pyyaml, regex, spacy, tldextract) plus a language model are heavy for two regex rules. It targets free-text NER, not the Bangladeshi formats. Could be an optional extra later if a measured need appears. |
| `phonenumbers` | Not used | Would add a dependency for one country; its validation (assigned ranges) would give a stronger-sounding claim than this project can document. Worth re-evaluating with real-world false-positive data. |
| Gitleaks | Documentation only | Separate tool; see [gitleaks-integration.md](gitleaks-integration.md). |
| coverage, build | Ad hoc / CI only | Not in the `[dev]` extra to keep it small. |

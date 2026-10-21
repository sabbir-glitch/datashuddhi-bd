# Security policy

## Supported versions

The project is pre-alpha (`0.1.0.dev0`) and unreleased. Only the latest development state is
supported.

## Reporting a vulnerability

**Please do not open a public issue for a security problem.**

Report privately by email to: **sabbirahamedmail@gmail.com**.

Once the repository exists on GitHub and the maintainer has enabled private vulnerability
reporting, you can also use the advisory form:
<https://github.com/sabbir-glitch/datashuddhi-bd/security/advisories/new>. That link works only
after the repository has been created and the feature enabled; until then, use the email address.

Please include: the affected version, steps to reproduce using **synthetic** data only, the
expected and actual behaviour, and the impact. Do not attach real personal data or secrets.

The maintainer aims to acknowledge reports promptly and to discuss a fix and disclosure timeline
with the reporter; this is a volunteer project and no response time is guaranteed.

## Scope

In scope: ways the tool could leak a raw matched value, write to or modify scanned files, follow a
link outside the scan scope, execute content, make a network connection, or be forced into
unbounded time or memory by a crafted file.

Out of scope: detection misses and false positives (use the public false-positive template;
they are documented in [docs/data-detection-limitations.md](docs/data-detection-limitations.md)),
and the absence of secret detection (a documented non-goal for 0.1.0).

See [docs/threat-model.md](docs/threat-model.md) for the assets, threats and residual risks.

## Safe harbour and use

Test only on files you own or are authorised to inspect. This policy does not grant permission to
access anyone else's systems or data.

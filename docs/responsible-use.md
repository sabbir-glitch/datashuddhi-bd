# Responsible use

DataShuddhi BD is for finding **your own** exposure of personal data, or data you have been
authorised to inspect, before you share it.

## Do

- Scan only files and folders you own or are explicitly authorised to inspect.
- Treat reports as **sensitive**: masked values still reveal that personal data exists, and file
  paths and names can themselves contain personal data. Store them with care and delete them when
  no longer needed.
- Use findings as prompts for review. Confirm each by hand; many will be false positives.
- Replace real data with synthetic data in examples, tests and bug reports.
- Use a dedicated secret scanner as well (see [gitleaks-integration.md](gitleaks-integration.md)).

## Do not

- Do not use it to collect, search, or analyse leaked, stolen or otherwise illegally obtained
  datasets.
- Do not use it to profile, locate or target individuals.
- Do not paste real findings, real personal data or real customer files into issues, pull requests
  or chats. Use synthetic examples.
- Do not rely on it as a compliance check. It makes no statement about any law or regulation, and
  nothing in this project is legal advice. Consult a qualified professional for obligations such
  as those arising from data-protection law.
- Do not claim a file is "clean" because a scan found nothing.

## What the tool will not do

No reveal mode (raw values are never printed), no network access, no telemetry, no changes to
scanned files. Any report file is written only because you asked for one with `--output`.

## Independence

DataShuddhi BD is an independent open-source project. It is not affiliated with or endorsed by any
government agency, regulator, bank, telecom operator or company.

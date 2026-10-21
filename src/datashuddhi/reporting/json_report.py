"""Machine-readable report (JSON, schema version 1).

The report contains masked values only. It deliberately has no timestamp (so identical scans
produce identical reports) and never contains the absolute scan path, only the name of the
scan root. File names are included as relative paths; a file *name* can itself contain
personal data, which the documentation points out.
"""

from __future__ import annotations

import json
from typing import Any

from datashuddhi import __version__
from datashuddhi.config import DEFAULT_EXCLUDED_DIR_GLOBS, DEFAULT_EXCLUDED_DIRS, FailOn
from datashuddhi.exit_codes import threshold_reached
from datashuddhi.reporting import DISCLAIMER
from datashuddhi.scanner import ScanResult

SCHEMA_VERSION = "1"


def build_report(result: ScanResult, fail_on: FailOn, exit_code: int) -> dict[str, Any]:
    log = result.log
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": "datashuddhi-bd", "version": __version__},
        "scan": {
            "root_name": result.root_name,
            "status": result.status,
            "limits": {
                "max_file_size_bytes": result.limits.max_file_bytes,
                "max_files": result.limits.max_files,
                "max_findings": result.limits.max_findings,
            },
            "exclusions": {
                "default_directories": sorted(DEFAULT_EXCLUDED_DIRS),
                "default_directory_patterns": list(DEFAULT_EXCLUDED_DIR_GLOBS),
                "user_patterns": list(result.exclude),
            },
            "rules": list(result.rule_ids),
            "files": {
                "discovered": result.files_discovered,
                "scanned": result.files_scanned,
                "not_scanned": result.files_not_scanned,
                "excluded_directories": result.excluded_dirs,
                "excluded_files": result.excluded_files,
                "unsupported_type": result.unsupported_files,
            },
            "findings_truncated": result.findings_truncated,
        },
        "summary": {
            "total_findings": len(result.findings),
            "by_severity": result.count_by_severity(),
            "by_rule": result.count_by_rule(),
        },
        "findings": [finding.to_dict() for finding in result.findings],
        "issues": {
            "total": log.issue_total,
            "omitted": log.issues_omitted,
            "by_kind": {
                kind.value: count
                for kind, count in sorted(log.counts.items(), key=lambda item: item[0].value)
                if kind.value not in {w.kind.value for w in log.warnings}
            },
            "items": [issue.to_dict() for issue in log.issues],
        },
        "warnings": {
            "total": log.warning_total,
            "omitted": log.warnings_omitted,
            "items": [warning.to_dict() for warning in log.warnings],
        },
        "outcome": {
            "fail_on": fail_on.value,
            "threshold_reached": threshold_reached(result.findings, fail_on),
            "exit_code": exit_code,
        },
        "disclaimer": DISCLAIMER,
    }


def render_json(report: dict[str, Any]) -> str:
    """Serialise as ASCII-only JSON (non-ASCII and control characters are escaped)."""
    return json.dumps(report, indent=2, ensure_ascii=True) + "\n"

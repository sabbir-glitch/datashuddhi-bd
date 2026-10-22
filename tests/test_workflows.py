"""Static checks of the GitHub configuration.

These tests inspect the workflow text only. They prove the file follows the project's security
rules; they do NOT prove the workflow runs: no GitHub run has been observed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
CI = ROOT / ".github" / "workflows" / "ci.yml"
WEB = ROOT / ".github" / "workflows" / "web.yml"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def code(path: Path) -> str:
    """Workflow text without full-line comments (comments may legitimately name banned words)."""
    lines = text(path).splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def test_workflows_exist() -> None:
    assert CI in WORKFLOWS


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_every_action_is_pinned_to_a_full_commit_sha(workflow: Path) -> None:
    uses = re.findall(r"^\s*-?\s*uses:\s*(\S+)(.*)$", text(workflow), flags=re.MULTILINE)
    assert uses, "expected at least one action"
    for reference, rest in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", reference), reference
        assert re.search(r"#\s*v\d+(\.\d+)*", rest), f"{reference} needs a version comment"


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_security_rules(workflow: Path) -> None:
    content = code(workflow)
    assert re.search(r"^permissions:\s*\n\s+contents: read\s*$", content, flags=re.MULTILINE)
    assert "pull_request_target" not in content
    assert "workflow_run" not in content
    assert "secrets." not in content
    assert "GITHUB_TOKEN" not in content
    assert "write-all" not in content
    assert not re.search(r"permissions:[^\n]*\n(\s+[\w-]+: write)", content)
    assert "curl " not in content
    assert "wget " not in content
    assert "| sh" not in content
    assert "| bash" not in content
    checkouts = content.count("actions/checkout@")
    assert checkouts == content.count("persist-credentials: false")


def job_count(content: str) -> int:
    """Number of top-level jobs in workflow text (comments already removed)."""
    jobs_section = content.split("\njobs:\n", 1)[1]
    return len(re.findall(r"^  [\w-]+:\s*$", jobs_section, flags=re.MULTILINE))


def every_job_has_a_timeout(content: str) -> bool:
    """True if the workflow has at least one job and exactly one timeout per job."""
    jobs = job_count(content)
    return jobs >= 1 and content.count("timeout-minutes:") == jobs


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_every_job_has_a_timeout(workflow: Path) -> None:
    # Applies to every workflow file. It must not assume how many jobs a workflow has: the number
    # of jobs is a property of each workflow, not of the rule (web.yml deliberately has one).
    assert every_job_has_a_timeout(code(workflow))


def test_python_ci_workflow_keeps_its_multi_job_structure() -> None:
    # Specific to ci.yml, which runs several independent Python jobs. Other workflows, such as
    # web.yml, are separate pipelines and are not required to have this many jobs.
    assert job_count(code(CI)) >= 5


@pytest.mark.skipif(not WEB.exists(), reason="web.yml is not present on this branch")
def test_web_workflow_is_a_single_job_with_a_timeout() -> None:
    content = code(WEB)
    assert job_count(content) == 1
    assert content.count("timeout-minutes:") == 1
    assert every_job_has_a_timeout(content)


_ONE_JOB = "name: x\njobs:\n  only:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n"


def test_timeout_rule_accepts_a_single_job_workflow() -> None:
    assert job_count(_ONE_JOB) == 1
    assert every_job_has_a_timeout(_ONE_JOB)


def test_timeout_rule_still_rejects_missing_timeouts() -> None:
    no_timeout = _ONE_JOB.replace("    timeout-minutes: 5\n", "")
    assert not every_job_has_a_timeout(no_timeout)
    two_jobs_one_timeout = _ONE_JOB + "  second:\n    runs-on: ubuntu-latest\n"
    assert job_count(two_jobs_one_timeout) == 2
    assert not every_job_has_a_timeout(two_jobs_one_timeout)


def test_pull_requests_and_pushes_trigger_ci_and_no_other_events() -> None:
    on_block = text(CI).split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    events = re.findall(r"^  ([a-z_]+):", on_block, flags=re.MULTILINE)
    assert events == ["push", "pull_request", "workflow_dispatch"]


def job_block(content: str, job: str) -> str:
    """The text of one top-level job, up to the next job."""
    block = content.split(f"\n  {job}:\n", 1)[1]
    return re.split(r"\n  [\w-]+:\n", block, maxsplit=1)[0]


def test_python_matrix_is_3_11_to_3_14_and_3_15_is_a_separate_required_job() -> None:
    content = text(CI)
    assert 'python: ["3.11", "3.12", "3.13", "3.14"]' in content
    assert "os: [ubuntu-latest, windows-latest]" in content
    block = job_block(content, "python-3-15")
    assert 'python-version: "3.15"' in block
    assert "continue-on-error" not in content
    assert "allow-prereleases" not in content
    assert "informational" not in content
    assert "beta" not in content.lower()
    # 3.15 stays out of the main matrix; it is its own required job.
    assert '"3.15"' not in content.split("python-3-15:", 1)[0]


def test_python_support_declaration_matches_the_required_3_15_job() -> None:
    pyproject = text(ROOT / "pyproject.toml")
    assert 'requires-python = ">=3.11"' in pyproject
    assert "<3.15" not in pyproject


def test_package_job_runs_the_distribution_checker_on_dist_check() -> None:
    content = text(CI)
    block = job_block(content, "package")
    assert 'python -m pip install "build==1.6.1"' in block
    assert "python -m build --outdir dist-check" in block
    assert "python scripts/check_dist.py --dist-dir dist-check" in block
    assert "dist-check/" in text(ROOT / ".gitignore")


def test_ci_uses_pinned_constraints_and_never_installs_unpinned_tools() -> None:
    content = text(CI)
    installs = re.findall(r"pip install (.+)", content)
    assert installs
    for command in installs:
        assert "-c constraints-dev.txt" in command or "==" in command or ".whl" in command, command


def test_ci_runs_the_required_checks() -> None:
    content = text(CI)
    for command in (
        "python -m ruff check .",
        "python -m ruff format --check .",
        "python -m pyright",
        "python -m pytest -rs",
        ".\\scripts\\check.ps1",
        "pip_audit",
        "python -m build",
    ):
        assert command in content, command


def test_ci_file_makes_no_unverified_support_claims() -> None:
    content = text(CI)
    # The header must not hard-code a run result, and must say where results are tracked...
    assert "NOT yet been run" not in content
    assert "tracked through GitHub Actions runs" in content
    # ...and must say where the action pins came from and what has been checked about them.
    assert "git ls-remote" in content
    assert "checked against the" in content
    assert "upstream commit and release pages" in content
    assert "says nothing about whether this workflow passes" in content
    # The old "still to be confirmed" wording must not come back.
    assert "confirm each one" not in content


def test_issue_template_config_points_at_the_intended_repository() -> None:
    config = text(ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml")
    assert "https://github.com/sabbir-glitch/datashuddhi-bd/security/advisories/new" in config
    assert "OWNER" not in config
    assert "REPO/" not in config


def test_dependabot_covers_github_actions_only() -> None:
    content = text(ROOT / ".github" / "dependabot.yml")
    assert "package-ecosystem: github-actions" in content
    assert content.count("package-ecosystem") == 1


def test_issue_templates_warn_against_real_data() -> None:
    folder = ROOT / ".github" / "ISSUE_TEMPLATE"
    for name in ("bug_report.yml", "false_positive.yml"):
        body = text(folder / name).lower()
        assert "real" in body
        assert "synthetic" in body
    assert "blank_issues_enabled: false" in text(folder / "config.yml")
    pull_request = text(ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md")
    assert "synthetic" in pull_request

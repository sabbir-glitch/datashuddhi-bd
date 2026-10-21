"""Documentation checks: required files, key honesty statements, links and placeholders."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import datashuddhi
from tests.synthetic import APPROVED_CONTACT_EMAIL

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "docs/architecture.md",
    "docs/threat-model.md",
    "docs/data-detection-limitations.md",
    "docs/responsible-use.md",
    "docs/testing.md",
    "docs/development.md",
    "docs/dependencies.md",
    "docs/gitleaks-integration.md",
]
DOC_LOCATIONS = ("docs", ".github")


def project_markdown(root: Path) -> list[Path]:
    """Return the project's own Markdown files, in a stable order.

    Only top-level ``*.md`` files and ``*.md`` files under ``docs/`` and ``.github/`` are
    included. Caches (``.pytest_cache``), virtual environments, build output and any other
    generated directory are never searched, so the set does not depend on what has been
    run in the working directory before.
    """
    found = [p for p in root.glob("*.md") if p.is_file()]
    for location in DOC_LOCATIONS:
        base = root / location
        if base.is_dir():
            found.extend(p for p in base.rglob("*.md") if p.is_file())
    return sorted(found)


MARKDOWN = project_markdown(ROOT)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize("rel", REQUIRED)
def test_required_documents_exist_and_are_not_empty(rel: str) -> None:
    assert len(read(rel).strip()) > 200


@pytest.mark.parametrize("rel", ["README.md", "docs/data-detection-limitations.md"])
def test_secret_detection_is_disclosed_as_not_implemented(rel: str) -> None:
    text = read(rel).lower()
    assert "does not detect" in text
    assert "secret" in text


def test_limitations_cite_sources_and_admit_the_missing_official_plan() -> None:
    text = read("docs/data-detection-limitations.md")
    assert "thedailystar.net/business/gp-gets-new-number-series-013-1273441" in text
    assert "thedailystar.net/node/1624651" in text
    assert "No official BTRC numbering plan was found" in text
    assert "code points" in text


def test_gitleaks_page_is_documentation_only() -> None:
    text = read("docs/gitleaks-integration.md")
    assert "documentation only" in text
    assert "Never auto-feed" in text
    assert "have been run" in text  # states the commands were not run by the project


EARLIER_ARCHIVE_SHA = "52bdafe1472974f67509cfa30d1f60e2efbd030aef7016f20e0dd37fa1e0fcf3"
FINAL_ARCHIVE_SHA = "b08501ed084d4f79853d60a5f0aefeccf795ec83b0ef1d04adc0a115e84a9ff9"
WINDOWS_DOCS = ["README.md", "docs/release-notes.md"]


def flat(rel: str) -> str:
    """Document text with markup emphasis and line wrapping removed."""
    return " ".join(read(rel).replace("**", "").split())


@pytest.mark.parametrize("rel", WINDOWS_DOCS)
def test_windows_results_are_recorded_per_archive_with_exact_numbers(rel: str) -> None:
    text = read(rel)
    for sha in (EARLIER_ARCHIVE_SHA, FINAL_ARCHIVE_SHA):
        assert sha in text
    assert "1602 passed, 9 skipped" in text  # earlier archive, 1611 tests
    assert "1608 passed, 9 skipped" in text  # corrected final archive, 1617 tests
    assert "1611" in text
    assert "1617" in text
    assert "Windows 10" in text
    assert "Windows PowerShell 5.1" in text
    assert "Python 3.13.1" in text
    assert "0 warnings" in text
    assert "0 informations" in text


@pytest.mark.parametrize("rel", WINDOWS_DOCS)
def test_windows_record_states_its_limits(rel: str) -> None:
    text = flat(rel)
    assert "junction" in text
    assert "ran and passed" in text
    assert "unconfirmed" in text  # the privilege context is not claimed
    assert "unverified on Windows" in text or "not verified on Windows" in text
    assert "named archives only" in text or "named archives" in text


def test_readme_attributes_the_manual_scan_check_to_the_earlier_archive_only() -> None:
    text = flat("README.md")
    assert re.search(r"manual scan check .{0,200}done on the earlier `M10` archive only", text)


def test_release_notes_attribute_the_manual_scans_to_the_earlier_archive_only() -> None:
    text = flat("docs/release-notes.md")
    assert "Manual scans on the earlier archive:" in text
    assert "not done; only check.ps1 output was supplied" in text.replace("`", "")


def test_documents_make_no_claim_about_the_windows_status_of_the_archive_they_ship_in() -> None:
    # A file inside an archive cannot know whether that archive was tested, so it must not say so
    # in either direction; the per-archive record lives in the acceptance report.
    for rel in WINDOWS_DOCS:
        text = flat(rel)
        assert "has not itself been run on Windows" not in text
        assert "not been run on Windows" not in text
        assert "passed on Windows" not in text.replace("ran and passed on Windows", "")
    assert "recorded in the" in flat("docs/release-notes.md")
    assert "acceptance report" in flat("docs/release-notes.md")


def test_markdown_emphasis_is_balanced_in_each_paragraph() -> None:
    for rel in ("README.md", "docs/release-notes.md"):
        for number, block in enumerate(read(rel).split("\n\n"), start=1):
            prose = re.sub(r"`[^`\n]*`", "", block)  # masked values such as a***@***.com are code
            assert "****" not in prose, f"{rel}: block {number}"
            assert prose.count("**") % 2 == 0, f"{rel}: block {number}"


@pytest.mark.parametrize("rel", ["README.md", "docs/release-notes.md"])
def test_documents_do_not_claim_a_remote_ci_result(rel: str) -> None:
    text = " ".join(read(rel).split())
    assert "GitHub Actions" in text
    assert "77aa31e" in text
    assert "owner-reported" in text
    assert "individual job results" in text
    assert "macOS, which has not been tested" in text
    lowered = text.lower()
    for claim in ("ci is green", "ci passed", "workflow passed", "passed on github"):
        assert claim not in lowered


def test_obsolete_pending_windows_statements_are_gone() -> None:
    for rel in ("README.md", "docs/release-notes.md"):
        text = flat(rel)
        assert "not yet been re-run on Windows" not in text
        assert "Windows results for it are pending" not in text
        assert "final tree has not been run on Windows" not in text


def test_cloud_and_windows_results_are_kept_separate_in_the_release_notes() -> None:
    text = read("docs/release-notes.md")
    assert "Cloud (Linux" in text
    assert "1637 passed, 1 skipped" in text
    assert "separate from the cloud results" in text


def test_testing_guide_documents_the_windows_skips() -> None:
    text = " ".join(read("docs/testing.md").split())
    assert "exactly nine tests skip" in text
    assert "The junction test did not skip there" in text


def test_changelog_heading_matches_the_package_version() -> None:
    base = datashuddhi.__version__.split(".dev")[0]
    en_dash = chr(0x2013)  # built with chr() so formatters cannot rewrite it
    assert f"## {base} {en_dash} unreleased" in read("CHANGELOG.md")


def test_security_policy_names_the_approved_contact_and_has_no_placeholder() -> None:
    text = read("SECURITY.md")
    assert "PLACEHOLDER" not in text.upper()
    assert APPROVED_CONTACT_EMAIL in text
    assert "https://github.com/sabbir-glitch/datashuddhi-bd/security/advisories/new" in text
    # No address other than the approved contact (the general hygiene test also enforces this).
    found = {m.group(0).lower() for m in re.finditer(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)}
    assert found == {APPROVED_CONTACT_EMAIL}


def test_license_names_the_copyright_holder_and_has_no_placeholder() -> None:
    text = read("LICENSE")
    assert "Copyright (c) 2026 Sabbir Ahammed" in text
    assert "TO BE CONFIRMED" not in text
    assert "[" not in text.splitlines()[2]


def test_no_owner_repo_or_contact_placeholders_remain_anywhere() -> None:
    for path in [*MARKDOWN, ROOT / "LICENSE", ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml"]:
        content = path.read_text(encoding="utf-8")
        assert "OWNER/REPO" not in content, path.name
        assert "[COPYRIGHT HOLDER" not in content, path.name
        assert "SECURITY CONTACT PLACEHOLDER" not in content, path.name


LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def broken_links(path: Path) -> list[str]:
    """Return the relative link targets in ``path`` that do not exist on disk."""
    broken: list[str] = []
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        file_part = target.split("#", 1)[0]
        if not (path.parent / file_part).exists():
            broken.append(file_part)
    return broken


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_markdown_links_resolve(path: Path) -> None:
    assert not broken_links(path), f"{path.name}: broken link(s) {broken_links(path)}"


# --- Regression tests for the Markdown selection itself -------------------------------------


def _touch(root: Path, rel: str, text: str = "# x\n") -> Path:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def test_selected_markdown_is_only_in_the_intended_locations() -> None:
    assert MARKDOWN, "no project documentation was found"
    for path in MARKDOWN:
        rel = path.relative_to(ROOT)
        top_level = len(rel.parts) == 1
        assert top_level or rel.parts[0] in DOC_LOCATIONS, f"unexpected location: {rel}"


def test_selection_covers_the_known_project_documents() -> None:
    rels = {p.relative_to(ROOT).as_posix() for p in MARKDOWN}
    assert {r for r in REQUIRED if r.endswith(".md")} <= rels
    assert "docs/release-notes.md" in rels
    assert ".github/PULL_REQUEST_TEMPLATE.md" in rels


def test_pytest_cache_readme_is_never_selected(tmp_path: Path) -> None:
    _touch(tmp_path, "README.md")
    _touch(tmp_path, ".pytest_cache/README.md")
    rels = {p.relative_to(tmp_path).as_posix() for p in project_markdown(tmp_path)}
    assert rels == {"README.md"}
    assert all(".pytest_cache" not in p.parts for p in MARKDOWN)


def test_selection_ignores_caches_environments_and_build_output(tmp_path: Path) -> None:
    kept = [
        _touch(tmp_path, "README.md"),
        _touch(tmp_path, "docs/a.md"),
        _touch(tmp_path, "docs/nested/b.md"),
        _touch(tmp_path, ".github/PULL_REQUEST_TEMPLATE.md"),
        _touch(tmp_path, ".github/ISSUE_TEMPLATE/bug.md"),
    ]
    for rel in (
        ".pytest_cache/README.md",
        ".ruff_cache/README.md",
        ".mypy_cache/README.md",
        ".venv/lib/pkg/README.md",
        "venv/README.md",
        "build/README.md",
        "dist/README.md",
        "node_modules/pkg/README.md",
        "src/datashuddhi/NOTES.md",
        "tests/NOTES.md",
        "scripts/NOTES.md",
        "docs.md.bak",
    ):
        _touch(tmp_path, rel)
    assert project_markdown(tmp_path) == sorted(kept)


def test_creating_or_removing_the_pytest_cache_does_not_change_the_parameter_set(
    tmp_path: Path,
) -> None:
    _touch(tmp_path, "README.md")
    _touch(tmp_path, "docs/a.md")
    before = project_markdown(tmp_path)
    cache = _touch(tmp_path, ".pytest_cache/README.md")
    with_cache = project_markdown(tmp_path)
    cache.unlink()
    cache.parent.rmdir()
    after = project_markdown(tmp_path)
    assert before == with_cache == after


def test_selection_is_stable_and_sorted(tmp_path: Path) -> None:
    for rel in ("docs/z.md", "README.md", "docs/a.md", "CHANGELOG.md", ".github/p.md"):
        _touch(tmp_path, rel)
    first = project_markdown(tmp_path)
    assert first == project_markdown(tmp_path)
    assert first == sorted(first)


def test_selection_handles_missing_documentation_directories(tmp_path: Path) -> None:
    _touch(tmp_path, "README.md")
    assert [p.name for p in project_markdown(tmp_path)] == ["README.md"]


def test_broken_links_in_project_documentation_are_still_detected(tmp_path: Path) -> None:
    _touch(tmp_path, "docs/good.md", "# good\n")
    page = _touch(
        tmp_path,
        "docs/page.md",
        "[ok](good.md) [anchor](good.md#top) [web](https://example.com/x) [self](#here)"
        " [bad](missing.md) [bad2](../nope/other.md#frag)\n",
    )
    assert broken_links(page) == ["missing.md", "../nope/other.md"]
    assert [p.name for p in project_markdown(tmp_path) if broken_links(p)] == ["page.md"]


def test_broken_links_in_top_level_and_github_documents_are_detected(tmp_path: Path) -> None:
    top = _touch(tmp_path, "README.md", "[bad](docs/gone.md)\n")
    gh = _touch(tmp_path, ".github/PULL_REQUEST_TEMPLATE.md", "[bad](../CONTRIBUTING.md)\n")
    flagged = [p for p in project_markdown(tmp_path) if broken_links(p)]
    assert flagged == sorted([top, gh])


def test_m11_rc2_matrix_is_recorded_and_kept_apart_from_other_evidence() -> None:
    notes = read("docs/release-notes.md")
    for version in ("3.11.17", "3.12.15", "3.13.16", "3.14.8", "3.15.0"):
        assert f"| {version} | 1696 | 1695 | 0 | 1 |" in notes
    flat_notes = " ".join(notes.split())
    assert "installed with `uv`" in flat_notes
    assert "1700 tests: 1699 passed, 1 skipped" in flat_notes
    assert "None came from GitHub runners" in flat_notes
    assert "Static checks (Python 3.13.16 only" in flat_notes
    assert "**Packaging.** On Linux (Python 3.13.16 only" in flat_notes
    assert (
        "Windows testing of M11-rc2 (owner-observed; separate from the Linux results" in flat_notes
    )
    assert "1700 collected, 1690 passed, 10 skipped, 0 failed" in flat_notes
    assert "Peak-memory behaviour was therefore not tested on Windows" in flat_notes
    assert "the individual skip lines were not supplied" in flat_notes
    assert "macOS testing: not yet observed" in flat_notes
    assert "the local Linux and Windows results are not CI results" in flat_notes
    assert "GitHub Actions (owner-reported; separate from the local results above)" in flat_notes
    assert "historical evidence, not M11-rc2 results" in flat_notes
    readme = " ".join(read("README.md").split())
    assert "1696 collected, 1695 passed, 0 failed, 1 skipped" in readme
    assert "Not observed:** macOS." in readme
    assert "peak-memory behaviour was not tested on Windows" in readme


@pytest.mark.parametrize("rel", ["README.md", "docs/release-notes.md", "docs/testing.md"])
def test_obsolete_rc2_progress_statements_are_gone(rel: str) -> None:
    text = " ".join(read(rel).split())
    for stale in (
        "matrix have not been observed",
        "Python 3.13.16 only (not the full matrix)",
        "verification still in progress",
        "Not run for M11-rc2: the Python 3.11-3.15 matrix",
        "workflow has never run",
        "has **not** been run",
        "No remote CI result exists",
        "that job has not been run on GitHub",
        "a green remote run has not been observed",
        "has been checked on Linux with Python 3.13.16 only",
        "Windows testing of M11-rc2: not yet observed",
        "an expectation, not an observation",
        "Windows, M11-rc2: not yet observed",
    ):
        assert stale not in text

"""Repository-wide guards: no real-looking personal data, no forbidden capabilities."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from datashuddhi.config import DEFAULT_EXCLUDED_DIRS
from datashuddhi.detectors import BangladeshiPhoneDetector
from datashuddhi.normalize import normalize_digits
from tests.synthetic import (
    APPROVED_CONTACT_EMAIL,
    APPROVED_NATIONAL_NUMBERS,
    is_approved_contact,
    is_reserved_domain,
)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "datashuddhi"

TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".ps1", ".cfg", ".ini",
    ".csv", ".log", ".env", ".gitignore", ".gitattributes", ".typed",
}  # fmt: skip
TEXT_NAMES = {"LICENSE", ".gitignore", ".gitattributes", "CODEOWNERS"}


def repo_text_files() -> list[Path]:
    files = []
    for path in sorted(ROOT.rglob("*")):
        rel_parts = path.relative_to(ROOT).parts
        if any(part in DEFAULT_EXCLUDED_DIRS or part.endswith(".egg-info") for part in rel_parts):
            continue
        if path.is_file() and (path.suffix in TEXT_SUFFIXES or path.name in TEXT_NAMES):
            files.append(path)
    return files


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_repository_files_were_found() -> None:
    names = {p.name for p in repo_text_files()}
    assert {"pyproject.toml", "synthetic.py", "scanner.py"} <= names


def test_every_phone_shaped_value_in_the_repository_is_an_approved_synthetic_number() -> None:
    detector = BangladeshiPhoneDetector()
    approved = set(APPROVED_NATIONAL_NUMBERS)
    offenders = []
    for path in repo_text_files():
        for number, line in enumerate(read(path).splitlines(), start=1):
            for match in detector.find(line):
                digits = "".join(ch for ch in normalize_digits(match.raw) if ch.isdigit())
                national = "0" + digits[-10:]
                if national not in approved:
                    offenders.append(f"{path.relative_to(ROOT)}:{number}")
    assert offenders == []


_EMAIL_LIKE = re.compile(r"[A-Za-z0-9._%+\-]{1,64}@((?:[A-Za-z0-9\-]+\.)+[A-Za-z]{2,24})")


def email_offenders(relative_path: str, text: str) -> list[str]:
    """Return ``path:line`` for each email-shaped value that is neither reserved nor approved.

    A value passes if its domain is a reserved documentation/testing domain, or if it is the
    approved security contact appearing in an approved file (see ``tests/synthetic.py``).
    """
    offenders = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in _EMAIL_LIKE.finditer(line):
            if is_reserved_domain(match.group(1)) or is_approved_contact(
                match.group(0), relative_path
            ):
                continue
            offenders.append(f"{relative_path}:{number}")
    return offenders


def test_every_email_shaped_value_in_the_repository_uses_a_reserved_domain() -> None:
    offenders = []
    for path in repo_text_files():
        relative = path.relative_to(ROOT).as_posix()
        offenders.extend(email_offenders(relative, read(path)))
    assert offenders == []


def test_the_approved_contact_is_allowed_only_in_the_security_policy() -> None:
    line = f"Report to {APPROVED_CONTACT_EMAIL} please\n"
    assert email_offenders("SECURITY.md", line) == []
    assert email_offenders("SECURITY.md", line.upper()) == []  # case-insensitive address
    for other in ("README.md", "docs/responsible-use.md", "tests/test_cli.py", "pyproject.toml"):
        assert email_offenders(other, line) == [f"{other}:1"], other


def test_other_real_looking_addresses_are_still_rejected_even_in_the_security_policy() -> None:
    domain = APPROVED_CONTACT_EMAIL.split("@", 1)[1]
    for address in (
        "someone.else@" + domain,  # same provider, different person
        "x" + APPROVED_CONTACT_EMAIL,  # approved address with an extra prefix
        APPROVED_CONTACT_EMAIL.split("@", 1)[0] + "@example.org.evil.io",
        "alice@" + "real-company.com",
    ):
        assert email_offenders("SECURITY.md", f"{address}\n") == ["SECURITY.md:1"], address
    assert email_offenders("README.md", "alice@example.com\n") == []  # reserved domains pass


def test_the_security_policy_contains_the_approved_contact_and_no_other_address() -> None:
    text = read(ROOT / "SECURITY.md")
    assert APPROVED_CONTACT_EMAIL in text
    assert email_offenders("SECURITY.md", text) == []
    found = {m.group(0).lower() for m in _EMAIL_LIKE.finditer(text)}
    assert found == {APPROVED_CONTACT_EMAIL}


def test_gitignore_excludes_the_ci_package_build_output() -> None:
    lines = {ln.strip() for ln in read(ROOT / ".gitignore").splitlines()}
    assert {"dist/", "dist-check/", "build/", ".venv/", ".pytest_cache/"} <= lines


FORBIDDEN_IMPORTS = {
    "socket", "ssl", "http", "urllib", "urllib3", "requests", "httpx", "aiohttp", "ftplib",
    "smtplib", "poplib", "imaplib", "telnetlib", "xmlrpc", "socketserver", "webbrowser",
    "subprocess", "multiprocessing", "ctypes", "pickle", "marshal", "shelve", "importlib",
    "tempfile", "shutil", "sqlite3",
}  # fmt: skip
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}
FORBIDDEN_OS_ATTRS = {
    "system", "popen", "remove", "unlink", "rmdir", "removedirs", "rename", "renames",
    "replace", "chmod", "chown", "utime", "truncate", "symlink", "link", "mkdir", "makedirs",
    "startfile", "execv", "execl", "spawnl", "spawnv", "fork", "kill",
}  # fmt: skip
PATH_WRITE_ATTRS = {
    "write_text", "write_bytes", "touch", "unlink", "rmdir", "mkdir", "chmod",
    "symlink_to", "hardlink_to",
}  # fmt: skip
# The only module allowed to create files is the report writer (added in the CLI milestone).
WRITER_MODULES = {"output.py"}


def source_modules() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def test_source_modules_were_found() -> None:
    assert len(source_modules()) >= 12


def test_source_has_no_network_process_or_dynamic_code_imports() -> None:
    offenders = []
    for path in source_modules():
        tree = ast.parse(read(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".")[0] in FORBIDDEN_IMPORTS and path.name not in WRITER_MODULES:
                    offenders.append(f"{path.name}: import {name}")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in FORBIDDEN_CALLS
            ):
                offenders.append(f"{path.name}: call {node.func.id}")
    assert offenders == []


def _open_mode(call: ast.Call) -> str:
    mode = ""
    if len(call.args) > 1 and isinstance(call.args[1], ast.Constant):
        mode = str(call.args[1].value)
    for keyword in call.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            mode = str(keyword.value.value)
    return mode


def test_only_the_report_writer_can_modify_the_filesystem() -> None:
    offenders = []
    for path in source_modules():
        if path.name in WRITER_MODULES:
            continue
        tree = ast.parse(read(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "os"
                and node.attr in FORBIDDEN_OS_ATTRS
            ):
                offenders.append(f"{path.name}: os.{node.attr}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                mode = _open_mode(node) if node.func.id == "open" else ""
                if set(mode) & set("wax+"):
                    offenders.append(f"{path.name}: open(mode={mode!r})")
            if isinstance(node, ast.Attribute) and node.attr in PATH_WRITE_ATTRS:
                offenders.append(f"{path.name}: .{node.attr}")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"replace", "rename"}
                and len(node.args) + len(node.keywords) == 1  # Path.replace(target), not str
            ):
                offenders.append(f"{path.name}: .{node.func.attr}(...)")
    assert offenders == []


def test_os_open_in_source_is_read_only_except_in_the_report_writer() -> None:
    # reader.py opens scanned files and its flags must be read-only.
    reader = read(SRC / "reader.py")
    assert "os.O_RDONLY" in reader
    for flag in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND"):
        assert flag not in reader
    for path in source_modules():
        if path.name not in {"reader.py", *WRITER_MODULES}:
            text = read(path)
            assert "os.open(" not in text, path.name
            assert "O_WRONLY" not in text, path.name
    # The writer only ever creates files exclusively: it can never truncate an existing file.
    writer = read(SRC / "output.py")
    assert "os.O_EXCL" in writer
    assert "O_TRUNC" not in writer
    assert "O_APPEND" not in writer


def test_only_the_cli_uses_the_report_writer() -> None:
    importers = sorted(
        path.name
        for path in source_modules()
        if path.name != "output.py" and "datashuddhi.output" in read(path)
    )
    assert importers == ["cli.py"]


def test_check_script_stays_ascii_crlf_and_free_of_the_known_defect() -> None:
    raw = (ROOT / "scripts" / "check.ps1").read_bytes()
    raw.decode("ascii")  # raises if any non-ASCII byte slipped in
    assert raw.count(b"\r\n") == raw.count(b"\n"), "check.ps1 must use CRLF line endings"
    text = raw.decode("ascii")
    code_lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    assert not any("Out-Host" in ln or "Write-Host" in ln for ln in code_lines)

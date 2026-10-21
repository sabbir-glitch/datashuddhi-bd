"""Tests of the source-distribution rules and of ``scripts/check_dist.py``.

These tests use small fake archives and a fake command runner. They do not build the package;
``scripts/check_dist.py`` does that check for real (locally and in the CI ``package`` job).
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_dist", ROOT / "scripts" / "check_dist.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_dist"] = module
    spec.loader.exec_module(module)
    return module


check_dist = load_checker()

VERSION = "0.1.0.dev0"

GOOD_SDIST = [
    "datashuddhi_bd-0.1.0.dev0/README.md",
    "datashuddhi_bd-0.1.0.dev0/LICENSE",
    "datashuddhi_bd-0.1.0.dev0/pyproject.toml",
    "datashuddhi_bd-0.1.0.dev0/PKG-INFO",
    "datashuddhi_bd-0.1.0.dev0/src/datashuddhi/__init__.py",
    "datashuddhi_bd-0.1.0.dev0/src/datashuddhi/cli.py",
]
GOOD_WHEEL = [
    "datashuddhi/__init__.py",
    "datashuddhi/cli.py",
    "datashuddhi/py.typed",
    "datashuddhi_bd-0.1.0.dev0.dist-info/METADATA",
    "datashuddhi_bd-0.1.0.dev0.dist-info/entry_points.txt",
]


def test_manifest_prunes_tests_and_nothing_else() -> None:
    assert (ROOT / "MANIFEST.in").read_text(encoding="utf-8") == "prune tests\n"


def test_good_sdist_has_no_problems() -> None:
    assert check_dist.sdist_problems(GOOD_SDIST) == []


@pytest.mark.parametrize("missing", check_dist.SDIST_REQUIRED)
def test_sdist_missing_a_required_file_is_reported(missing: str) -> None:
    members = [m for m in GOOD_SDIST if not m.endswith("/" + missing)]
    problems = check_dist.sdist_problems(members)
    assert any(missing in problem for problem in problems)


def test_sdist_containing_tests_is_rejected() -> None:
    members = [*GOOD_SDIST, "datashuddhi_bd-0.1.0.dev0/tests/test_cli.py"]
    assert any("tests/" in p for p in check_dist.sdist_problems(members))


def test_a_file_merely_named_like_tests_elsewhere_is_not_rejected() -> None:
    members = [*GOOD_SDIST, "datashuddhi_bd-0.1.0.dev0/src/datashuddhi/tests_helper.py"]
    assert check_dist.sdist_problems(members) == []


@pytest.mark.parametrize("name", ["/etc/passwd", "../x", "a/../../x", "a\\b"])
def test_unsafe_member_names_are_rejected(name: str) -> None:
    assert any("unsafe" in p for p in check_dist.sdist_problems([*GOOD_SDIST, name]))
    assert any("unsafe" in p for p in check_dist.wheel_problems([*GOOD_WHEEL, name]))


def test_good_wheel_has_no_problems() -> None:
    assert check_dist.wheel_problems(GOOD_WHEEL) == []


def test_wheel_missing_metadata_or_marker_is_reported() -> None:
    assert check_dist.wheel_problems(GOOD_WHEEL[:-1])
    assert check_dist.wheel_problems([m for m in GOOD_WHEEL if not m.endswith("py.typed")])


def test_wheel_containing_tests_is_rejected() -> None:
    assert check_dist.wheel_problems([*GOOD_WHEEL, "tests/test_cli.py"])


def make_archives(directory: Path, sdist: Sequence[str], wheel: Sequence[str]) -> None:
    with tarfile.open(directory / "datashuddhi_bd-0.1.0.dev0.tar.gz", "w:gz") as tar:
        for name in sdist:
            info = tarfile.TarInfo(name)
            tar.addfile(info, io.BytesIO(b""))
    with zipfile.ZipFile(directory / "datashuddhi_bd-0.1.0.dev0-py3-none-any.whl", "w") as zf:
        for name in wheel:
            zf.writestr(name, "")


def test_archives_are_listed_without_extracting(tmp_path: Path) -> None:
    make_archives(tmp_path, GOOD_SDIST, GOOD_WHEEL)
    sdist, wheel = check_dist.find_archives(tmp_path)
    assert check_dist.sdist_members(sdist) == GOOD_SDIST
    assert check_dist.wheel_members(wheel) == GOOD_WHEEL
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([sdist.name, wheel.name])


def test_find_archives_requires_exactly_one_of_each(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        check_dist.find_archives(tmp_path)
    make_archives(tmp_path, GOOD_SDIST, GOOD_WHEEL)
    (tmp_path / "other.whl").write_bytes(b"")
    with pytest.raises(SystemExit):
        check_dist.find_archives(tmp_path)


def test_main_passes_good_archives_and_fails_bad_ones(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    good = tmp_path / "good"
    good.mkdir()
    make_archives(good, GOOD_SDIST, GOOD_WHEEL)
    assert check_dist.main(["--dist-dir", str(good), "--skip-smoke"]) == 0
    assert "OK:" in capsys.readouterr().out
    bad = tmp_path / "bad"
    bad.mkdir()
    make_archives(bad, [*GOOD_SDIST, "datashuddhi_bd-0.1.0.dev0/tests/x.py"], GOOD_WHEEL)
    assert check_dist.main(["--dist-dir", str(bad), "--skip-smoke"]) == 1
    assert "FAIL:" in capsys.readouterr().out


class FakeRunner:
    """Pretends to be pip and the installed command; records every command it is given."""

    def __init__(
        self,
        scan_code: int = 1,
        masked: str = "a***@***.com",
        raw_leak: bool = False,
        version_code: int = 0,
        version_output: str = "datashuddhi 0.1.0.dev0\n",
        pip_code: int = 0,
        valid_json: bool = True,
    ) -> None:
        self.calls: list[list[str]] = []
        self.scan_code = scan_code
        self.masked = masked
        self.raw_leak = raw_leak
        self.version_code = version_code
        self.version_output = version_output
        self.pip_code = pip_code
        self.valid_json = valid_json

    def __call__(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        args = list(command)
        self.calls.append(args)
        done = subprocess.CompletedProcess(args, 0, "", "")
        if "venv" in args:
            return done
        if "pip" in args:
            return subprocess.CompletedProcess(args, self.pip_code, "", "pip said no")
        if "--version" in args:
            return subprocess.CompletedProcess(args, self.version_code, self.version_output, "")
        if "scan" in args:
            if not self.valid_json:
                return subprocess.CompletedProcess(args, self.scan_code, "not json", "")
            body = json.dumps({"findings": [{"masked_value": self.masked}]})
            if self.raw_leak:
                body += check_dist.SYNTHETIC_EMAIL
            return subprocess.CompletedProcess(args, self.scan_code, body, "")
        raise AssertionError(args)


def test_smoke_test_passes_and_never_installs_editable(tmp_path: Path) -> None:
    runner = FakeRunner()
    assert check_dist.smoke_test(Path("a.whl"), tmp_path, "wheel", VERSION, runner) == []
    installs = [c for c in runner.calls if "pip" in c]
    assert len(installs) == 1
    assert "-e" not in installs[0]
    assert "--editable" not in installs[0]


@pytest.mark.parametrize(
    ("runner", "expected"),
    [
        (FakeRunner(scan_code=0), "exit code"),
        (FakeRunner(scan_code=3), "exit code"),
        (FakeRunner(masked="alice@example.com"), "masked value"),
        (FakeRunner(raw_leak=True), "raw synthetic email"),
        (FakeRunner(version_code=1), "--version"),
        (FakeRunner(version_output="datashuddhi 0.2.0\n"), "expected 'datashuddhi 0.1.0.dev0'"),
        (FakeRunner(version_output="datashuddhi 0.1.0.dev0.post1\n"), "--version"),
        (FakeRunner(version_output="other 0.1.0.dev0\n"), "--version"),
        (FakeRunner(version_output=""), "--version"),
        (FakeRunner(pip_code=1), "pip install failed"),
        (FakeRunner(valid_json=False), "not valid JSON"),
    ],
    ids=[
        "exit0",
        "exit3",
        "unmasked",
        "raw-leak",
        "version-exit",
        "wrong-version",
        "suffix",
        "wrong-name",
        "empty",
        "pip",
        "bad-json",
    ],
)
def test_smoke_test_fails_on_any_unexpected_result(
    tmp_path: Path, runner: FakeRunner, expected: str
) -> None:
    problems = check_dist.smoke_test(Path("a.tar.gz"), tmp_path, "sdist", VERSION, runner)
    assert any(expected in p for p in problems), problems


def test_expected_version_is_read_from_the_project_not_a_second_constant() -> None:
    from datashuddhi import __version__

    assert check_dist.expected_version() == __version__ == "0.1.0.dev0"


def test_expected_version_follows_the_dynamic_attr_declaration(tmp_path: Path) -> None:
    package = tmp_path / "src" / "demo"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndynamic = ["version"]\n'
        '[tool.setuptools.dynamic]\nversion = { attr = "demo.__version__" }\n',
        encoding="utf-8",
    )
    assert check_dist.expected_version(tmp_path) == "9.9.9"


def test_expected_version_rejects_a_static_or_unreadable_declaration(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "1.0"\n', encoding="utf-8"
    )
    with pytest.raises(SystemExit):
        check_dist.expected_version(tmp_path)

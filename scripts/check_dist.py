"""Verify the built source distribution and wheel (standard library only).

Usage (from the project folder, after ``python -m build --outdir dist-check``)::

    python scripts/check_dist.py --dist-dir dist-check

It lists each archive WITHOUT extracting it, checks required and forbidden members, then installs
the sdist and the wheel into two separate clean virtual environments (never editable) and runs the
installed ``datashuddhi`` command against a synthetic file. Any unexpected result exits non-zero.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath

SDIST_REQUIRED = (
    "README.md",
    "LICENSE",
    "pyproject.toml",
    "PKG-INFO",
    "src/datashuddhi/__init__.py",
    "src/datashuddhi/cli.py",
)
WHEEL_REQUIRED = ("datashuddhi/__init__.py", "datashuddhi/cli.py", "datashuddhi/py.typed")
WHEEL_REQUIRED_SUFFIXES = (".dist-info/METADATA", ".dist-info/entry_points.txt")

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_EMAIL = "alice@example.com"
EXPECTED_MASK = "a***@***.com"

Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


def expected_version(root: Path = ROOT) -> str:
    """The project's declared version, read without importing the package.

    ``pyproject.toml`` declares the version as dynamic, read from an attribute such as
    ``datashuddhi.__version__``. This follows that declaration to the ``__version__`` string
    literal under ``src/``, so the version is defined in one place only.
    """
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    if "version" in config["project"] or "version" not in config["project"].get("dynamic", []):
        raise SystemExit("pyproject.toml must declare the version as dynamic")
    attr = config["tool"]["setuptools"]["dynamic"]["version"]["attr"]
    module, _, name = str(attr).rpartition(".")
    source = (root / "src" / Path(*module.split(".")) / "__init__.py").read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if (
            isinstance(node, ast.Assign)
            and [t.id for t in node.targets if isinstance(t, ast.Name)] == [name]
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    raise SystemExit(f"could not read {attr} as a string literal")


def _unsafe(name: str) -> bool:
    path = PurePosixPath(name)
    return path.is_absolute() or ".." in path.parts or "\\" in name


def _relative_to_root(name: str) -> str:
    """Strip the single top-level folder of an sdist member name."""
    parts = PurePosixPath(name).parts
    return "/".join(parts[1:])


def sdist_problems(members: Sequence[str]) -> list[str]:
    """Return what is wrong with an sdist's member list (empty means good)."""
    problems = [f"unsafe member name: {name!r}" for name in members if _unsafe(name)]
    relative = {_relative_to_root(name) for name in members}
    problems += [f"sdist is missing {item}" for item in SDIST_REQUIRED if item not in relative]
    problems += [
        f"sdist contains a tests/ path: {name}"
        for name in members
        if "tests" in PurePosixPath(_relative_to_root(name)).parts[:1]
    ]
    return problems


def wheel_problems(members: Sequence[str]) -> list[str]:
    problems = [f"unsafe member name: {name!r}" for name in members if _unsafe(name)]
    problems += [f"wheel is missing {item}" for item in WHEEL_REQUIRED if item not in members]
    problems += [
        f"wheel has no member ending {suffix}"
        for suffix in WHEEL_REQUIRED_SUFFIXES
        if not any(name.endswith(suffix) for name in members)
    ]
    problems += [f"wheel contains a tests/ path: {n}" for n in members if n.startswith("tests/")]
    return problems


def sdist_members(path: Path) -> list[str]:
    with tarfile.open(path, "r:gz") as archive:
        return archive.getnames()


def wheel_members(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return archive.namelist()


def find_archives(dist_dir: Path) -> tuple[Path, Path]:
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    wheels = sorted(dist_dir.glob("*.whl"))
    if len(sdists) != 1 or len(wheels) != 1:
        raise SystemExit(
            f"expected exactly one .tar.gz and one .whl in {dist_dir}, "
            f"found {len(sdists)} and {len(wheels)}"
        )
    return sdists[0], wheels[0]


def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  (arguments are built here, never from scanned content)
        list(command), capture_output=True, text=True, timeout=300, check=False
    )


def smoke_test(
    artifact: Path, workdir: Path, label: str, version: str, run: Runner = _run
) -> list[str]:
    """Install ``artifact`` (not editable) into a clean venv and scan a synthetic file."""
    problems: list[str] = []
    venv = workdir / f"venv-{label}"
    if run([sys.executable, "-m", "venv", str(venv)]).returncode != 0:
        return [f"{label}: could not create a virtual environment"]
    scripts = venv / ("Scripts" if sys.platform == "win32" else "bin")
    python = scripts / ("python.exe" if sys.platform == "win32" else "python")
    installed = run([str(python), "-m", "pip", "install", "--no-input", str(artifact)])
    if installed.returncode != 0:
        return [f"{label}: pip install failed: {installed.stderr.strip()[-300:]}"]
    exe = scripts / ("datashuddhi.exe" if sys.platform == "win32" else "datashuddhi")
    version_run = run([str(exe), "--version"])
    expected = f"datashuddhi {version}"
    if version_run.returncode != 0 or version_run.stdout.strip() != expected:
        problems.append(
            f"{label}: --version gave exit {version_run.returncode} and "
            f"{version_run.stdout.strip()!r}, expected {expected!r}"
        )
    sample = workdir / f"sample-{label}"
    sample.mkdir()
    (sample / "a.txt").write_text(f"contact: {SYNTHETIC_EMAIL}\n", encoding="utf-8")
    scan = run([str(exe), "scan", str(sample), "--format", "json"])
    if scan.returncode != 1:
        problems.append(f"{label}: scan exit code {scan.returncode}, expected 1")
    if SYNTHETIC_EMAIL in scan.stdout or SYNTHETIC_EMAIL in scan.stderr:
        problems.append(f"{label}: raw synthetic email leaked into the output")
    try:
        report = json.loads(scan.stdout)
    except json.JSONDecodeError:
        return [*problems, f"{label}: scan output is not valid JSON"]
    findings = report.get("findings") if isinstance(report, dict) else None
    if not isinstance(findings, list) or len(findings) != 1:
        problems.append(f"{label}: expected exactly one finding")
    elif findings[0].get("masked_value") != EXPECTED_MASK:
        problems.append(f"{label}: masked value is not {EXPECTED_MASK}")
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--dist-dir", type=Path, default=Path("dist-check"))
    parser.add_argument("--skip-smoke", action="store_true", help="only check archive contents")
    args = parser.parse_args(argv)
    sdist, wheel = find_archives(args.dist_dir)
    version = expected_version()
    problems = sdist_problems(sdist_members(sdist)) + wheel_problems(wheel_members(wheel))
    if not args.skip_smoke and not problems:
        with tempfile.TemporaryDirectory() as tmp:
            problems += smoke_test(sdist, Path(tmp), "sdist", version)
            problems += smoke_test(wheel, Path(tmp), "wheel", version)
    for problem in problems:
        print(f"FAIL: {problem}")
    if problems:
        return 1
    print(f"OK: {sdist.name} and {wheel.name} passed (version {version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

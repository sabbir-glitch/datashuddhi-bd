"""M9 adversarial tests: hostile file names, hostile content and resource exhaustion."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from datashuddhi.cli import main
from datashuddhi.detectors.email import EmailDetector
from tests.synthetic import CANARY_EMAIL

EMAIL = EmailDetector()
POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only behaviour")


def scan_json(capsys: pytest.CaptureFixture[str], root: Path) -> tuple[int, dict[str, object]]:
    code = main(["scan", str(root), "--format", "json"])
    return code, json.loads(capsys.readouterr().out)


# -- resource exhaustion ---------------------------------------------------------------------


def test_domain_with_more_labels_than_dns_allows_is_not_matched() -> None:
    assert list(EMAIL.find("a@" + "b." * 127 + "com")) == []


def test_densest_valid_domain_is_still_matched() -> None:
    # One-character labels are the densest valid names: 125 of them plus a 2-letter TLD is
    # 252 characters, under the 253 limit, so the 126-label regex bound never rejects a valid name.
    assert len(list(EMAIL.find("a@" + "b." * 125 + "co"))) == 1


def _domain_of_length(length: int) -> str:
    """A syntactically valid domain with exactly ``length`` characters (5-char labels)."""
    labels: list[str] = []
    remaining = length - len("com")  # the final label
    while remaining > 0:
        take = min(5, remaining - 1)  # label chars, leaving room for its dot
        if take < 1:
            raise ValueError("unsupported length")
        labels.append("d" * take)
        remaining -= take + 1
    domain = ".".join([*labels, "com"])
    assert len(domain) == length
    return domain


def test_domain_of_253_characters_is_matched_but_254_is_not() -> None:
    assert len(list(EMAIL.find("a@" + _domain_of_length(253)))) == 1
    assert list(EMAIL.find("a@" + _domain_of_length(254))) == []


def test_over_length_domain_is_dropped_whole_not_reported_as_a_partial_match() -> None:
    # 5-char labels: 100 labels stay under the 126-label bound but exceed 253 characters.
    line = "a@" + "ddddd." * 100 + "com"
    assert list(EMAIL.find(line)) == []
    assert [m.raw for m in EMAIL.find(line + " ok@example.com")] == ["ok@example.com"]


def test_label_longer_than_63_characters_is_not_matched_even_partly() -> None:
    assert len(list(EMAIL.find("a@" + "b" * 63 + ".com"))) == 1
    assert list(EMAIL.find("a@" + "b" * 64 + ".com")) == []


def test_millions_of_labels_finish_quickly() -> None:
    line = "a@" + "b." * 2_000_000
    started = time.perf_counter()
    assert list(EMAIL.find(line)) == []
    assert time.perf_counter() - started < 5


# -- memory regression -----------------------------------------------------------------------
#
# The probe measures its OWN peak resident set size by reading ``VmHWM`` from
# ``/proc/self/status`` (the kernel reports it in kB, where 1 kB = 1024 bytes, so it is read as
# KiB). ``VmHWM`` is the high-water mark of the resident set (RSS) of the current process image.
# ``resource.getrusage(...).ru_maxrss`` is deliberately NOT used: on Linux a child keeps the
# parent's peak across ``execve``, so inside a large pytest process it can report memory the
# probe never used. ``VmHWM`` limits: it is a resident-page peak in whole kB, includes the
# interpreter and imported modules, exists only on Linux, and is not an exact or portable
# measure. The 150 MiB limit is a tripwire far from the healthy value (about 20 MiB) and the
# defect value (about 450 MiB), not a precise bound.

_MEMORY_LIMIT_MIB = 150
_HEAVY_PARENT_MIB = 200
_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
_PROC_STATUS = Path("/proc/self/status")
_VMHWM_LINE = re.compile(r"^VmHWM:[ \t]+(\d+)[ \t]+kB[ \t]*$", re.MULTILINE)


def parse_vmhwm_kib(status_text: str) -> int:
    """Return ``VmHWM`` in KiB from the text of ``/proc/<pid>/status``; reject anything else."""
    matches = _VMHWM_LINE.findall(status_text)
    if len(matches) != 1 or status_text.count("VmHWM:") != 1:
        raise ValueError("expected exactly one well-formed 'VmHWM: <digits> kB' line")
    return int(matches[0])


def peak_memory_measurable(platform: str, status_path: Path) -> bool:
    """True only on Linux with a readable, parseable ``VmHWM`` (no other platform is trusted)."""
    if not platform.startswith("linux"):
        return False
    try:
        parse_vmhwm_kib(status_path.read_text(encoding="ascii"))
    except (OSError, ValueError):
        return False
    return True


LINUX_PEAK_MEMORY_ONLY = pytest.mark.skipif(
    not peak_memory_measurable(sys.platform, _PROC_STATUS),
    reason=(
        "needs a readable VmHWM in /proc/self/status (Linux); there is no trustworthy "
        "peak-memory measurement here and ru_maxrss is deliberately not used. "
        "Not verified on Windows or macOS."
    ),
)

# argv[1] = the checkout's src directory. Isolated mode (-I) ignores PYTHONPATH, so the probe
# puts src on sys.path itself and refuses to run against any other copy of the package.
_PROBE = """\
import sys
from pathlib import Path

src = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(src))
import datashuddhi

if not Path(datashuddhi.__file__).resolve().is_relative_to(src):
    raise SystemExit("datashuddhi was imported from outside " + str(src))
from datashuddhi.detectors.email import EmailDetector

list(EmailDetector().find("a@" + "b." * 2_000_000))
sys.stdout.write(Path("/proc/self/status").read_text())
"""

# Holds and frees a large block so ITS peak is high, then runs the probe as a child.
# argv[1] = src, argv[2] = probe source, argv[3] = block size in MiB.
_HEAVY_PARENT = """\
import json
import subprocess
import sys
from pathlib import Path

block = bytearray(int(sys.argv[3]) * 1024 * 1024)
for index in range(0, len(block), 4096):
    block[index] = 1
del block
child = subprocess.run(
    [sys.executable, "-I", "-c", sys.argv[2], sys.argv[1]],
    capture_output=True, text=True, check=True, timeout=60,
)
print(json.dumps({"parent": Path("/proc/self/status").read_text(), "probe": child.stdout}))
"""


def _probe_peak_mib() -> float:
    done = subprocess.run(  # noqa: S603  (fixed arguments; no untrusted input)
        [sys.executable, "-I", "-c", _PROBE, str(_SRC_DIR)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return parse_vmhwm_kib(done.stdout) / 1024


@LINUX_PEAK_MEMORY_ONLY
def test_pathological_domain_does_not_amplify_memory() -> None:
    # Regression: an unbounded ``(label.)+`` repeat used ~470 MB of regex backtracking state
    # for a 4 MB line. The probe's own peak must stay near the baseline.
    assert _probe_peak_mib() < _MEMORY_LIMIT_MIB


@LINUX_PEAK_MEMORY_ONLY
def test_probe_peak_is_not_contaminated_by_a_parent_with_a_high_peak() -> None:
    done = subprocess.run(  # noqa: S603  (fixed arguments; no untrusted input)
        [sys.executable, "-I", "-c", _HEAVY_PARENT, str(_SRC_DIR), _PROBE, str(_HEAVY_PARENT_MIB)],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    result = json.loads(done.stdout)
    parent_mib = parse_vmhwm_kib(result["parent"]) / 1024
    probe_mib = parse_vmhwm_kib(result["probe"]) / 1024
    assert parent_mib >= _HEAVY_PARENT_MIB  # the parent really did have a high peak
    assert probe_mib < _MEMORY_LIMIT_MIB  # and the probe's own measurement ignores it


def test_memory_limit_is_still_150_mib() -> None:
    assert _MEMORY_LIMIT_MIB == 150


def test_memory_test_does_not_use_ru_maxrss_or_the_resource_module() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] != "resource" for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] != "resource"
        elif isinstance(node, ast.Attribute):
            assert node.attr not in {"ru_maxrss", "getrusage"}
        elif isinstance(node, ast.Name):
            assert node.id not in {"ru_maxrss", "getrusage"}


@pytest.mark.parametrize(
    ("text", "kib"),
    [
        ("VmHWM:\t   20480 kB\n", 20480),
        ("Name:\tpython\nVmHWM:   1 kB\nVmRSS:\t5 kB\n", 1),
        ("VmHWM:\t0 kB", 0),
        ("VmPeak: 9 kB\nVmHWM:\t 123456 kB \nThreads: 1\n", 123456),
        ("VmHWM:\t7\tkB\n", 7),
    ],
)
def test_parse_vmhwm_accepts_the_proc_format(text: str, kib: int) -> None:
    assert parse_vmhwm_kib(text) == kib


@pytest.mark.parametrize(
    "text",
    [
        "",
        "VmRSS: 5 kB\n",
        "VmHWM: 5 MB\n",
        "VmHWM: 5\n",
        "VmHWM: five kB\n",
        "VmHWM: -5 kB\n",
        "VmHWM: 5.5 kB\n",
        "VmHWM: 5 kB extra\n",
        "VmHWM: 5 kB\nVmHWM: 6 kB\n",
        "xVmHWM: 5 kB\n",
        "VmHWM:5 kB\n",
        "VmHWM: 5kB\n",
    ],
)
def test_parse_vmhwm_rejects_anything_else(text: str) -> None:
    with pytest.raises(ValueError, match="VmHWM"):
        parse_vmhwm_kib(text)


def test_peak_memory_is_not_measurable_without_linux_and_a_good_proc_file(tmp_path: Path) -> None:
    good = tmp_path / "status"
    good.write_text("VmHWM: 10 kB\n", encoding="ascii")
    bad = tmp_path / "bad"
    bad.write_text("VmRSS: 10 kB\n", encoding="ascii")
    assert peak_memory_measurable("linux", good)
    assert not peak_memory_measurable("darwin", good)
    assert not peak_memory_measurable("win32", good)
    assert not peak_memory_measurable("linux", bad)
    assert not peak_memory_measurable("linux", tmp_path / "missing")


# -- hostile file names ----------------------------------------------------------------------


@POSIX_ONLY
def test_invalid_utf8_file_names_are_reported_without_crashing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    raw = os.fsencode(tmp_path) + b"/bad\xff\xfename.txt"
    try:
        Path(os.fsdecode(raw)).write_text(CANARY_EMAIL, encoding="utf-8")
    except OSError:
        pytest.skip("file system rejects non-UTF-8 names")
    code, report = scan_json(capsys, tmp_path)
    assert code == 1
    assert CANARY_EMAIL not in json.dumps(report)
    findings = report["findings"]
    assert isinstance(findings, list)
    assert len(findings) == 1


@POSIX_ONLY
def test_control_and_bidi_characters_in_names_never_reach_the_console_raw(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    name = "ctl\x1b[31m‮evil.txt"
    try:
        (tmp_path / name).write_text(CANARY_EMAIL, encoding="utf-8")
    except OSError:
        pytest.skip("file system rejects these names")
    code = main(["scan", str(tmp_path)])
    out = capsys.readouterr()
    assert code == 1
    for stream in (out.out, out.err):
        assert "\x1b" not in stream
        assert "‮" not in stream
        assert CANARY_EMAIL not in stream


# -- hostile content -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        b"\x00" * 100,
        b"\xff\xfe\x00\x00" + b"a\x00\x00\x00",
        b"\xef\xbb\xbf" + b"\xff" * 50,
        b"\r" * 10_000,
        b"@" * 10_000,
        b"+880 " * 10_000,
        ("১" * 5_000).encode(),
    ],
    ids=["nul", "utf32-bom", "bom-then-invalid", "cr-only", "at-signs", "plus-880", "bengali"],
)
def test_hostile_content_never_crashes_the_scan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], payload: bytes
) -> None:
    (tmp_path / "x.txt").write_bytes(payload)
    code = main(["scan", str(tmp_path), "--format", "json"])
    report = json.loads(capsys.readouterr().out)
    assert code in {0, 1, 3}
    assert report["scan"]["status"] in {"complete", "incomplete"}
    assert report["outcome"]["exit_code"] == code


# -- boundaries ------------------------------------------------------------------------------


@POSIX_ONLY
def test_hard_link_to_an_outside_file_is_scanned_as_a_regular_file(tmp_path: Path) -> None:
    # Documented residual risk: a hard link is indistinguishable from a regular file, so
    # content reachable through one is scanned. Output is still masked and read-only.
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text(CANARY_EMAIL, encoding="utf-8")
    scan = tmp_path / "scan"
    scan.mkdir()
    os.link(outside / "secret.txt", scan / "linked.txt")
    before = (outside / "secret.txt").read_bytes()
    assert main(["scan", str(scan), "--output", str(tmp_path / "r.json"), "--format", "json"]) == 1
    assert (outside / "secret.txt").read_bytes() == before
    assert CANARY_EMAIL not in (tmp_path / "r.json").read_text(encoding="utf-8")

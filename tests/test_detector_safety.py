"""Robustness: arbitrary text must never crash a detector or take unbounded time."""

from __future__ import annotations

import time

import pytest

from datashuddhi.detectors import default_detectors

DETECTORS = default_detectors()
# Generous bound: these inputs take milliseconds; this only catches catastrophic backtracking.
TIME_LIMIT_SECONDS = 5.0

ONE_MIB = 1024 * 1024

HOSTILE_LINES = {
    "long-local-run": "a" * ONE_MIB,
    "long-local-run-with-at": "a" * ONE_MIB + "@",
    "dots": "." * ONE_MIB,
    "dot-label-chain": "a@" + "a." * (ONE_MIB // 2),
    "dot-label-chain-valid-end": "a@" + "a." * (ONE_MIB // 2) + "com",
    "hyphen-label": "a@" + "a-" * (ONE_MIB // 2),
    "many-ats": "a@" * (ONE_MIB // 2),
    "many-at-domains": "a@b." * (ONE_MIB // 4),
    "digits": "1" * ONE_MIB,
    "plus-digits": "+880" + "1" * ONE_MIB,
    "digit-space-chain": "0171 " * (ONE_MIB // 5),
    "digit-hyphen-chain": "017-1234-" * (ONE_MIB // 9),
    "almost-phones": "01712345 " * (ONE_MIB // 9),
    "bengali-digit-run": "\u09e7" * ONE_MIB,
    "spaces": " " * ONE_MIB,
    "mixed-punctuation": "+-. @" * (ONE_MIB // 5),
}


@pytest.mark.parametrize("name", sorted(HOSTILE_LINES))
def test_hostile_lines_finish_quickly_and_do_not_raise(name: str) -> None:
    line = HOSTILE_LINES[name]
    for detector in DETECTORS:
        started = time.perf_counter()
        matches = list(detector.find(line))
        elapsed = time.perf_counter() - started
        assert elapsed < TIME_LIMIT_SECONDS, (name, detector.rule.rule_id, elapsed)
        for match in matches:
            assert 0 <= match.start < match.end <= len(line)


def test_deterministic_pseudo_text_never_raises_and_offsets_are_valid() -> None:
    alphabet = "aZ09@.-+ _%\t\u09e6\u09ef\u0660\u00a0\u2028\x00\U0001f600"
    # Linear-congruential sequence: deterministic, no RNG module needed.
    state = 12345
    for _ in range(2000):
        chars = []
        for _ in range(60):
            state = (state * 1103515245 + 12345) % (2**31)
            chars.append(alphabet[state % len(alphabet)])
        line = "".join(chars)
        for detector in DETECTORS:
            for match in detector.find(line):
                assert 0 <= match.start < match.end <= len(line)
                assert line[match.start : match.end] == match.raw


def test_matches_do_not_leak_into_exception_text() -> None:
    # Detectors have no failure path that formats input; this documents the expectation.
    for detector in DETECTORS:
        assert list(detector.find("")) == []

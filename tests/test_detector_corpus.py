"""Run the labelled corpus through the default detectors."""

from __future__ import annotations

import pytest

from datashuddhi.detectors import default_detectors
from tests.corpus import CASES, Case

DETECTORS = default_detectors()


def reported_rules(line: str) -> list[str]:
    hits: list[tuple[int, str]] = []
    for detector in DETECTORS:
        hits.extend((m.start, detector.rule.rule_id) for m in detector.find(line))
    return [rule_id for _, rule_id in sorted(hits)]


@pytest.mark.parametrize("case", CASES, ids=[c.case_id for c in CASES])
def test_corpus_case(case: Case) -> None:
    assert tuple(reported_rules(case.line)) == case.expected


def test_corpus_labels_are_consistent_with_expectations() -> None:
    for case in CASES:
        if case.label in {"TN", "KNOWN_FN"}:
            assert case.expected == (), case.case_id
        else:
            assert case.expected, case.case_id


def test_corpus_covers_every_label_and_has_unique_ids() -> None:
    assert {c.label for c in CASES} == {"TP", "TN", "KNOWN_FP", "KNOWN_FN"}
    ids = [c.case_id for c in CASES]
    assert len(ids) == len(set(ids))

"""Tests for digit normalisation."""

from __future__ import annotations

from datashuddhi.normalize import normalize_digits
from tests.synthetic import to_bengali_digits


def test_ascii_text_is_returned_unchanged() -> None:
    text = "call 01700000000 now"
    assert normalize_digits(text) == text


def test_all_bengali_digits_map_to_ascii() -> None:
    bengali = "".join(chr(0x09E6 + i) for i in range(10))
    assert normalize_digits(bengali) == "0123456789"


def test_length_is_preserved_so_columns_stay_correct() -> None:
    text = "নাম: " + to_bengali_digits("+8801700000000") + " ok"
    normalized = normalize_digits(text)
    assert len(normalized) == len(text)
    # Non-digit characters (here Bengali letters) are untouched and keep their position.
    assert normalized[:5] == text[:5]
    assert normalized.index("+880") == text.index("+")


def test_other_scripts_and_letters_are_not_changed() -> None:
    # U+0660/U+0661 are ARABIC-INDIC digits (not Bengali U+09E6..U+09EF). They are
    # deliberately NOT normalised: Bangladeshi numbers use Bengali or ASCII digits.
    text = "abc \u0660\u0661 \u06f0\u06f1 xyz"
    assert normalize_digits(text) == text


def test_normalisation_returns_a_copy_and_leaves_the_source_text_untouched() -> None:
    source = to_bengali_digits("01700000000")
    normalized = normalize_digits(source)
    assert normalized == "01700000000"
    # The input string (the scanned text) still holds the original Bengali digits, so
    # reports and columns refer to the unmodified source.
    assert source != normalized
    assert source == to_bengali_digits("01700000000")
    assert all("\u09e6" <= ch <= "\u09ef" for ch in source)

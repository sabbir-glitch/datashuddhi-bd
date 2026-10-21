"""Text normalisation used before matching.

Only Bengali digits are normalised. The mapping is strictly one code point to one code
point, so every position in the normalised text is the same position in the original
text. That keeps line and column numbers correct and never modifies the scanned file.
"""

from __future__ import annotations

# Bengali digits are U+09E6 .. U+09EF.
_BENGALI_DIGITS = "".join(chr(0x09E6 + i) for i in range(10))
_TABLE = str.maketrans(_BENGALI_DIGITS, "0123456789")


def normalize_digits(text: str) -> str:
    """Return ``text`` with Bengali digits replaced by ASCII digits (same length)."""
    if text.isascii():
        return text
    return text.translate(_TABLE)

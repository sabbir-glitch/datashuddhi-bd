"""Masking of matched values.

Policy (documented, deliberately aggressive):

* Bangladeshi mobile number: always ``*********NN``. The value is first reduced to the
  11-digit national form, then nine asterisks are followed by its last two digits. The
  input format (``+880``, separators, Bengali digits, ...) is not visible in the result.
* Email address: ``X***@***.tld`` where ``X`` is the first character of the local part and
  ``tld`` is the final domain label in lower case. Everything else is replaced.

There is no "reveal" mode. These functions raise ``ValueError`` for input that does not
look like the expected value, and the error message never contains that input.
"""

from __future__ import annotations

from datashuddhi.normalize import normalize_digits

_NATIONAL_LENGTH = 11


def mask_phone(raw: str) -> str:
    """Mask a Bangladeshi mobile number (any documented input format)."""
    normalized = normalize_digits(raw)
    digits = "".join(ch for ch in normalized if "0" <= ch <= "9")
    if len(digits) == 15 and digits.startswith("00"):  # 00 + 880 + 10 digits
        digits = digits[2:]
    if len(digits) == 13 and digits.startswith("880"):  # 880 + 10 digits
        digits = "0" + digits[3:]
    if len(digits) != _NATIONAL_LENGTH or not digits.startswith("01"):
        raise ValueError("value is not a supported Bangladeshi mobile number shape")
    return "*" * 9 + digits[-2:]


def mask_email(raw: str) -> str:
    """Mask an email address."""
    local, separator, domain = raw.rpartition("@")
    if not separator or not local or "." not in domain:
        raise ValueError("value is not a supported email address shape")
    tld = domain.rsplit(".", 1)[1].lower()
    if not tld or not tld.isascii() or not tld.isalpha():
        raise ValueError("value is not a supported email address shape")
    return f"{local[0]}***@***.{tld}"

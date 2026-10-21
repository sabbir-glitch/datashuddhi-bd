"""Synthetic data shared by the tests.

Nothing here is real personal data.

* Email addresses use only domains reserved for documentation and testing (RFC 2606 and
  RFC 6761): example.com, example.net, example.org, and the .test, .example, .invalid and
  .localhost top-level domains.
* Phone numbers are deliberately patterned (repeated or sequential digits). No official
  reserved range for Bangladeshi mobile numbers was found, so a patterned value *could*
  coincide with a real subscriber. The approved list below is therefore short, fixed, and
  enforced by ``tests/test_repo_hygiene.py`` across the whole repository.
"""

from __future__ import annotations

# One patterned national number per assigned-looking prefix (013-019).
APPROVED_NATIONAL_NUMBERS: tuple[str, ...] = (
    "01311111111",
    "01444444444",
    "01555555555",
    "01666666666",
    "01700000000",
    "01712345678",
    "01887654321",
    "01911111111",
)

RESERVED_SECOND_LEVEL = ("example.com", "example.net", "example.org")
RESERVED_TLDS = ("test", "example", "invalid", "localhost")
IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "gif", "svg", "webp", "bmp", "ico", "avif")

# Values used as "canaries": unique strings that must never appear in any output.
CANARY_PHONE = "01700000000"
CANARY_EMAIL = "canary.zq7x@example.com"

_ASCII_TO_BENGALI = str.maketrans("0123456789", "".join(chr(0x09E6 + i) for i in range(10)))


def to_bengali_digits(text: str) -> str:
    """Replace ASCII digits with Bengali digits (separators and signs stay)."""
    return text.translate(_ASCII_TO_BENGALI)


# The one real address the repository is allowed to contain: the maintainer's security contact,
# and only in the files listed below. It is assembled at run time so that this module, which the
# repository-wide email scan also reads, does not itself contain an email-shaped literal.
APPROVED_CONTACT_EMAIL = "sabbirahamedmail" + "@" + "gmail.com"
APPROVED_CONTACT_FILES = frozenset({"SECURITY.md"})


def is_approved_contact(address: str, relative_path: str) -> bool:
    """True only for the approved security contact, and only inside an approved file."""
    return (
        address.lower() == APPROVED_CONTACT_EMAIL
        and relative_path.replace("\\", "/") in APPROVED_CONTACT_FILES
    )


def is_reserved_domain(domain: str) -> bool:
    """True if ``domain`` is a documentation/testing domain (or an image file extension)."""
    domain = domain.lower().rstrip(".")
    labels = domain.split(".")
    if labels[-1] in RESERVED_TLDS or labels[-1] in IMAGE_EXTENSIONS:
        # Image extensions are not real top-level domains: "logo@2x.png" is a file name.
        return True
    return any(domain == base or domain.endswith("." + base) for base in RESERVED_SECOND_LEVEL)


def phone_variants(national: str) -> dict[str, tuple[str, str]]:
    """Return documented formats of one national number.

    Maps a variant name to ``(text, expected_confidence)``. ``national`` must be an
    11-digit number starting with 01.
    """
    if len(national) != 11 or not national.startswith("01"):
        raise ValueError("national must be an 11-digit number starting with 01")
    n = national[1:]  # 10 digits, e.g. 1712345678
    return {
        "national_bare": (national, "medium"),
        "national_3_8_hyphen": (f"{national[:3]}-{national[3:]}", "medium"),
        "national_3_8_space": (f"{national[:3]} {national[3:]}", "medium"),
        "national_5_6_hyphen": (f"{national[:5]}-{national[5:]}", "medium"),
        "national_5_6_space": (f"{national[:5]} {national[5:]}", "medium"),
        "national_3_4_4_space": (f"{national[:3]} {national[3:7]} {national[7:]}", "medium"),
        "national_3_4_4_hyphen": (f"{national[:3]}-{national[3:7]}-{national[7:]}", "medium"),
        "plus880_bare": (f"+880{n}", "high"),
        "plus880_space": (f"+880 {n}", "high"),
        "plus880_hyphen": (f"+880-{n}", "high"),
        "plus880_4_6": (f"+880 {n[:4]}-{n[4:]}", "high"),
        "plus880_2_4_4": (f"+880 {n[:2]} {n[2:6]} {n[6:]}", "high"),
        "zero_zero_880": (f"00880{n}", "high"),
        "bare_880": (f"880{n}", "medium"),
        "bare_880_space": (f"880 {n}", "medium"),
        "plus88_space_zero": (f"+88 {national}", "high"),
        "plus88_hyphen_zero": (f"+88-{national}", "high"),
        "zero_zero_88_space_zero": (f"0088 {national}", "high"),
    }


def all_phone_variants() -> list[tuple[str, str, str, str]]:
    """Every variant of every approved number, ASCII and Bengali digits.

    Returns tuples ``(test_id, national, text, expected_confidence)``.
    """
    rows: list[tuple[str, str, str, str]] = []
    for national in APPROVED_NATIONAL_NUMBERS:
        for name, (text, confidence) in phone_variants(national).items():
            rows.append((f"{national}-{name}-ascii", national, text, confidence))
            bengali = to_bengali_digits(text)
            rows.append((f"{national}-{name}-bengali", national, bengali, confidence))
    return rows

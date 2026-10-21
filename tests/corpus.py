"""Labelled synthetic corpus describing detector behaviour, including known mistakes.

Labels
------
TP        personal-data-shaped value that is correctly reported
TN        text that is correctly NOT reported
KNOWN_FP  reported although it is not personal data (documented false positive)
KNOWN_FN  personal-data-like value that is NOT reported (documented false negative)

The corpus is a behavioural specification, not a benchmark: its size is far too small to
estimate real-world precision or recall, and the project makes no such claim.
All values are synthetic (see tests/synthetic.py).
"""

from __future__ import annotations

from dataclasses import dataclass

EMAIL = "DS-EMAIL-001"
PHONE = "DS-BDPHONE-001"


@dataclass(frozen=True)
class Case:
    case_id: str
    line: str
    label: str
    expected: tuple[str, ...]  # rule ids the detectors are expected to report (in order)
    note: str = ""


CASES: tuple[Case, ...] = (
    Case("tp-log-email", "2026-10-14 INFO login user=alice@example.com ok", "TP", (EMAIL,)),
    Case("tp-csv-phone", "101,Test Person,01712345678", "TP", (PHONE,)),
    Case("tp-both", "alice@example.org called +8801700000000", "TP", (EMAIL, PHONE)),
    Case("tp-json-email", '{"contact": "bob@example.net"}', "TP", (EMAIL,)),
    Case("tp-env-phone", "SUPPORT_PHONE=01887654321", "TP", (PHONE,)),
    Case(
        "tp-bengali-digits",
        "ফোন: \u09e6\u09e7\u09ed\u09e7\u09e8\u09e9\u09ea\u09eb\u09ec\u09ed\u09ee",
        "TP",
        (PHONE,),
    ),
    Case("tn-plain", "this line has nothing sensitive in it", "TN", ()),
    Case("tn-short-digits", "build 20261014 revision 12345", "TN", ()),
    Case("tn-long-digit-run", "serial 1701712345678 end", "TN", (), "digit before 017..."),
    Case("tn-image-asset", "<img src='logo@2x.png'>", "TN", (), "retina asset name"),
    Case("tn-unallocated-prefix", "call 01212345678", "TN", (), "012 is not matched"),
    Case("tn-version", "release v1.2.3 build 4", "TN", ()),
    Case("tn-decorator", "@property def name(self): pass", "TN", ()),
    Case(
        "fp-order-id",
        "order_id=01712345678 status=shipped",
        "KNOWN_FP",
        (PHONE,),
        "digits shaped like a mobile number but used as an identifier",
    ),
    Case(
        "fp-git-ssh",
        "url = git@example.com:team/repo.git",
        "KNOWN_FP",
        (EMAIL,),
        "service account style address, not a person",
    ),
    Case(
        "fp-noreply",
        "from: noreply@example.com",
        "KNOWN_FP",
        (EMAIL,),
        "role address; still reported because it is syntactically an address",
    ),
    Case("fn-obfuscated-email", "alice at example dot com", "KNOWN_FN", (), "obfuscated"),
    Case("fn-bracket-email", "alice[at]example.com", "KNOWN_FN", (), "obfuscated"),
    Case("fn-percent-encoded", "alice%40example.com", "KNOWN_FN", (), "URL-encoded @"),
    Case("fn-non-ascii-email", "ব্যবহারকারী@example.com", "KNOWN_FN", (), "non-ASCII local part"),
    Case("fn-localhost-email", "root@localhost", "KNOWN_FN", (), "domain without a dot"),
    Case("fn-phone-irregular-spacing", "01 7 1234 5678", "KNOWN_FN", (), "irregular grouping"),
    Case("fn-phone-parentheses", "+880 (17) 1234-5678", "KNOWN_FN", (), "parentheses"),
    Case("fn-phone-nbsp", "017\u00a012345678", "KNOWN_FN", (), "no-break space separator"),
    Case("fn-phone-dots", "017.1234.5678", "KNOWN_FN", (), "dot separators"),
    Case(
        "fn-phone-words",
        "zero one seven one two three four five six seven eight",
        "KNOWN_FN",
        (),
        "spelled out",
    ),
    Case(
        "fn-arabic-indic",
        "\u0660\u0661\u0667\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668",
        "KNOWN_FN",
        (),
        "Arabic-Indic digits are not normalised",
    ),
)

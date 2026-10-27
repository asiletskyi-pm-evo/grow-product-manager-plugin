#!/usr/bin/env python3
"""Grow PM — what the context store never keeps (since v3.21.0, concept §5.5).

A secret or a state or financial identifier is refused before it reaches a record, the inbox or the journal —
by its form, deterministically; the categories a pattern cannot tell (health, religion, politics, …) are a rule
of the protocol for skills (references/context-protocol.md §5i, data-policy.md). Semantics: context-protocol.md.

- scan(text)       the kinds found in a text, sorted — never the values: card · iban · rnokpp · passport · secret
- check(*texts)    raise NeverStore naming the kinds when any text holds one
- message(kinds)   the one Ukrainian sentence a refusal says

A kind is found only by a form that is hard to hit by chance:
- card      13–19 digits (single spaces or hyphens between groups) whose first digit is a card network's (2–6, 9),
            passing Luhn; a 13-digit 978/979… (an ISBN) is not a card
- iban      two capitals, two digits, 11–30 capitals or digits (spaces between groups of four), passing mod 97
- rnokpp    10 digits passing the РНОКПП checksum, with ІПН / РНОКПП / ідентифікаційний / tax id within 40 characters
- passport  two Cyrillic capitals and six digits (a Ukrainian passport book), or nine digits with паспорт / ID-картка
            / passport within 40 characters
- secret    the forms of keys and tokens (sk-…, gh?_…, github_pat_…, glpat-…, xox?-…, AKIA…, AIza…, a JWT, a private
            key block), and `password|пароль|token|secret|api key: <value>` whose value is 12+ characters of letters
            and digits both — an environment variable's NAME (ALL_CAPS_WITH_UNDERSCORES) is what a record should hold

Stdlib only.
"""
import re

KINDS = ("card", "iban", "rnokpp", "passport", "secret")
NAMES = {"card": "номер банківської картки", "iban": "IBAN", "rnokpp": "РНОКПП (ІПН)",
         "passport": "номер паспорта", "secret": "секрет (ключ, токен чи пароль)"}


class NeverStore(Exception):
    """A text holds what the store never keeps (exit 4); the message names the kinds, never the values."""

    def __init__(self, kinds):
        self.kinds = list(kinds)
        Exception.__init__(self, message(self.kinds))


def message(kinds):
    return "не збережено: схоже на %s — такі дані не зберігаються" % ", ".join(NAMES[k] for k in kinds)


_CARD = re.compile(r"(?<![\w.,/+-])\d(?:[ -]?\d){12,18}(?![\w.,/-])")
_IBAN = re.compile(r"(?<![A-Za-z0-9])[A-Z]{2}\d{2}(?: ?[A-Z0-9]){11,30}(?![A-Za-z0-9])")
_TEN = re.compile(r"(?<![\d.,/-])\d{10}(?![\d.,/-])")
_NINE = re.compile(r"(?<![\d.,/-])\d{9}(?![\d.,/-])")
_PASSBOOK = re.compile(r"(?<![А-ЯІЇЄҐа-яіїєґA-Za-z])[А-ЯІЇЄҐ]{2} ?\d{6}(?![\d])")
_RNOKPP_WORD = re.compile(r"ІПН|РНОКПП|ідентифікаційн|податков\w* номер|tax[ _-]?id|\bTIN\b|\bINN\b", re.I)
_PASSPORT_WORD = re.compile(r"паспорт|passport|ID[- ]?карт|id[- ]?card", re.I)
_TOKENS = re.compile(r"(?<![A-Za-z0-9])(?:sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}"
                     r"|github_pat_[A-Za-z0-9_]{30,}|glpat-[A-Za-z0-9_-]{20,}|xox[abpr]-[A-Za-z0-9-]{10,}"
                     r"|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}"
                     r"|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})"
                     r"|-----BEGIN [A-Z ]*PRIVATE KEY-----")
_LABELLED = re.compile(r"(?:password|passwd|пароль|token|токен|secret|api[ _-]?key)\s*[:=][*_\s`\"']*"
                       r"([A-Za-z0-9_+/=.\-]{12,})", re.I)
_ENV_NAME = re.compile(r"^\$?\{?[A-Z][A-Z0-9_]*\}?$")


def _luhn(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d *= 2
            d -= 9 if d > 9 else 0
        total += d
    return total % 10 == 0


def _card(text):
    for m in _CARD.finditer(text):
        raw = m.group(0)
        if re.search(r"[ -]{2}", raw):
            continue
        digits = re.sub(r"\D", "", raw)
        if not 13 <= len(digits) <= 19 or digits[0] not in "234569":
            continue
        if len(digits) == 13 and digits[:3] in ("978", "979"):
            continue
        if _luhn(digits):
            return True
    return False


def _iban(text):
    for m in _IBAN.finditer(text):
        s = m.group(0).replace(" ", "")
        if not 15 <= len(s) <= 34:
            continue
        n = "".join(str(int(ch, 36)) for ch in s[4:] + s[:4])
        if int(n) % 97 == 1:
            return True
    return False


def _rnokpp_ok(d):
    w = (-1, 5, 7, 9, 4, 6, 10, 5, 7)
    return sum(int(d[i]) * w[i] for i in range(9)) % 11 % 10 == int(d[9])


def _near(text, m, word, span=40):
    return bool(word.search(text[max(0, m.start() - span):m.end() + span]))


def _rnokpp(text):
    return any(_rnokpp_ok(m.group(0)) and _near(text, m, _RNOKPP_WORD) for m in _TEN.finditer(text))


def _passport(text):
    if _PASSBOOK.search(text):
        return True
    return any(_near(text, m, _PASSPORT_WORD) for m in _NINE.finditer(text))


def _secret(text):
    if _TOKENS.search(text):
        return True
    for m in _LABELLED.finditer(text):
        v = m.group(1)
        if _ENV_NAME.match(v):
            continue
        if re.search(r"[A-Za-z]", v) and re.search(r"\d", v):
            return True
    return False


_FINDERS = (("card", _card), ("iban", _iban), ("rnokpp", _rnokpp), ("passport", _passport), ("secret", _secret))


def scan(text):
    """The kinds `text` holds, in KINDS order — never the values."""
    if not text:
        return []
    return [k for k, find in _FINDERS if find(text)]


def check(*texts):
    kinds = []
    for t in texts:
        for k in scan(t or ""):
            if k not in kinds:
                kinds.append(k)
    if kinds:
        raise NeverStore([k for k in KINDS if k in kinds])

#!/usr/bin/env python3
"""Grow PM — what the context store never keeps (since v3.21.0, concept §5.5).

A secret or a state or financial identifier is refused before it reaches a record, the inbox or the journal —
by its form, deterministically; the categories a pattern cannot tell (health, religion, politics, …) are a rule
of the protocol for skills (references/context-protocol.md §5i, data-policy.md). Semantics: context-protocol.md.

- scan(text)       the kinds found in a text, in KINDS order — never the values: card · iban · rnokpp · passport · secret
- check(*texts)    raise NeverStore naming the kinds when any text holds one
- message(kinds)   the sentence a refusal says; warning(kinds) the one `validate` says about a record you typed

A kind is found only by a form that is hard to hit by chance:
- card      13–19 digits (single spaces or hyphens between groups; a sentence's `.` or `,` may follow) of a card
            network's number range and length — Visa 4 (13, 16, 19), Mastercard 51–55 and 2221–2720 (16), Amex 34/37
            (15), Discover/UnionPay/Maestro 6 (16–19), Maestro 50/56–59 (16–19), ПРОСТІР 9804 (16) — passing Luhn
- iban      two capitals, two digits, 11–30 capitals or digits (spaces between groups of four), passing mod 97; a
            lower-case one only as ua + 27 digits (a commit hash must not pass by the 1 in 97 chance)
- rnokpp    10 digits passing the РНОКПП checksum, with ІПН / РНОКПП / ИНН / ідентифікаційний / tax id within 40 characters
- passport  two Cyrillic capitals and six digits (a passport book) or nine digits (an ID card), with паспорт / ID-картка
            / passport within 40 characters — «ТЗ 202610» or «КП 100500» alone is ordinary text
- secret    the forms of keys and tokens (sk-…, sk_live_…, gh?_…, github_pat_…, glpat-…, xox?-…, AKIA…, AIza…, ya29.…, a
            Telegram bot token, a JWT, a private key block), `Bearer <token>`, a URL with a password or a key in it,
            and `password|pass|pwd|пароль|token|secret|api key …: <value>` (also as "key": "value" and a table row)
            whose value is 8+ characters with a digit, or with a symbol and both cases — not an environment
            variable's NAME, not a snake_case name, not a version or a date

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


def _names(kinds):
    return ", ".join(NAMES[k] for k in kinds)


def message(kinds):
    return "не збережено: схоже на %s — такі дані не зберігаються" % _names(kinds)


def warning(kinds):
    return "схоже на %s — таке не варто тримати в контексті, прибери це з запису" % _names(kinds)


_SPACES = re.compile("[   ]")
_CARD = re.compile(r"(?<![\w/+=-])(?<!\d[.,])\d(?:[ -]?\d){12,18}(?![\w/-]|[.,]\d)")
_IBAN = re.compile(r"(?<![A-Za-z0-9])(?:[A-Z]{2}\d{2}(?: ?[A-Z0-9]){11,30}|ua\d{27})(?![A-Za-z0-9])")
_TEN = re.compile(r"(?<![\d.,/-])\d{10}(?![\d]|[.,/-]\d)")
_PASS = re.compile(r"(?<![А-ЯІЇЄҐа-яіїєґA-Za-z0-9])(?:[А-ЯІЇЄҐ]{2} ?№? ?\d{6}|\d{9})(?!\d|[.,]\d)")
_RNOKPP_WORD = re.compile(r"ІПН|РНОКПП|ИНН|ідентифікаційн|податков\w* номер|tax[ _-]?id|\bTIN\b|\bINN\b", re.I)
_PASSPORT_WORD = re.compile(r"паспорт(?!\w*\s+(?:продукт|проєкт|проект|фіч|команд|ініціатив|метрик|сервіс|модул))"
                            r"|passport(?!\s+(?:of|for)\b)|ID[- ]?карт|id[- ]?card", re.I)   # «паспорт продукту» is a PM term
_TOKENS = re.compile(r"(?<![A-Za-z0-9_-])(?:sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}|[sr]k_(?:live|test)_[A-Za-z0-9]{16,}"
                     r"|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|glpat-[A-Za-z0-9_-]{20,}"
                     r"|xox[abpr]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|ya29\.[A-Za-z0-9_-]{20,}"
                     r"|\d{8,10}:AA[A-Za-z0-9_-]{33}"
                     r"|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})"
                     r"|-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----"
                     r"|\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"
                     r"|://[^/\s:@]+:[^/\s@]{3,}@"
                     r"|[?&](?:key|api_?key|apikey|token|access_token|secret|password|passwd|sig)=[^&\s#]{8,}", re.I)
_LABEL = r"(?:password|passwd|pass|pwd|пароль|token|токен|secret|client[ _-]?secret|api[ _-]?key|access[ _-]?key)"
_LABELLED = re.compile(r"(?<![A-Za-z0-9_])" + _LABEL + r"(?![A-Za-z0-9_])"
                       r"(?:[\"'`*_]*\s*[:=]|\s*\|)[*_\s`\"']*([^\s\"'`|,;]{8,})", re.I)
_ENV_NAME = re.compile(r"^\$?\{?[A-Z][A-Z0-9_]*\}?$")
_IDENT = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")          # a snake_case name, e.g. zorg_api_token_v2
_NOT_SECRET = re.compile(r"^v?\d+(?:\.\d+){1,3}(?:[-+][\w.]+)?$|^\d{4}-\d{2}-\d{2}(?:[T ][\d:.+Z-]*)?$")


def _luhn(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d *= 2
            d -= 9 if d > 9 else 0
        total += d
    return total % 10 == 0


def _network(d):
    n = len(d)
    if d[0] == "4":
        return n in (13, 16, 19)
    if "51" <= d[:2] <= "55" or "2221" <= d[:4] <= "2720":
        return n == 16
    if d[:2] in ("34", "37"):
        return n == 15
    if d[0] == "6" or d[:2] == "50" or "56" <= d[:2] <= "59":
        return 16 <= n <= 19
    return d[:4] == "9804" and n == 16


def _card(text):
    for m in _CARD.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))       # the pattern itself allows one separator between digits
        if 13 <= len(digits) <= 19 and _network(digits) and _luhn(digits):
            return True
    return False


def _iban(text):
    for m in _IBAN.finditer(text):
        s = m.group(0).replace(" ", "").upper()     # 15–34 characters by the pattern
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
    return any(_near(text, m, _PASSPORT_WORD) for m in _PASS.finditer(text))


def _secret(text):
    if _TOKENS.search(text):
        return True
    for m in _LABELLED.finditer(text):
        v = m.group(1).rstrip(".")
        if len(v) < 8 or _ENV_NAME.match(v) or _IDENT.match(v) or _NOT_SECRET.match(v):
            continue
        if re.search(r"\d", v) or (re.search(r"[^\w]", v) and re.search(r"[a-z]", v) and re.search(r"[A-Z]", v)):
            return True
    return False


_FINDERS = (("card", _card), ("iban", _iban), ("rnokpp", _rnokpp), ("passport", _passport), ("secret", _secret))


def scan(text):
    """The kinds `text` holds, in KINDS order — never the values."""
    if not text:
        return []
    text = _SPACES.sub(" ", text)
    return [k for k, find in _FINDERS if find(text)]


def check(*texts):
    kinds = []
    for t in texts:
        for k in scan(t if isinstance(t, str) else ""):
            if k not in kinds:
                kinds.append(k)
    if kinds:
        raise NeverStore([k for k in KINDS if k in kinds])

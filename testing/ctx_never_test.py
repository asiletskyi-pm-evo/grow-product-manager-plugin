#!/usr/bin/env python3
"""TC-ctx-3210-never — scripts/ctx_never.py, what the context store never keeps (v3.21.0, concept §5.5).

Every value below is generated here so that it passes its checksum — no real number appears in the repository.
The kinds a write refuses (card, IBAN, РНОКПП, passport, secret), the look-alikes it must let through (task keys,
dates, sums, phones, ISBNs, order numbers, UUIDs, commit hashes, prices, environment variable names), and the
command line: `set`, `append`, `add` refuse with exit 4 and the value appears nowhere — not in the output, the
journal, a record or a snapshot; `validate` names a record and a kind for a value you typed yourself.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_never_test.py
"""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
import ctx_never as cn  # noqa: E402
from ctx_testenv import Env, read  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def luhn_complete(prefix, length):
    for d in "0123456789":
        s = prefix + "0" * (length - len(prefix) - 1) + d
        if cn._luhn(s):
            return s


def iban(country, bban):
    n = "".join(str(int(ch, 36)) for ch in bban + country + "00")
    return country + "%02d" % (98 - int(n) % 97) + bban


def rnokpp(nine):
    w = (-1, 5, 7, 9, 4, 6, 10, 5, 7)
    return nine + str(sum(int(nine[i]) * w[i] for i in range(9)) % 11 % 10)


CARD = luhn_complete("4" + "1" * 7, 16)


def spaced(n):
    return " ".join(n[i:i + 4] for i in range(0, len(n), 4))


def isbn_passing_luhn():
    """A valid ISBN-13 (978…) that Luhn takes for a card — the exclusion, not luck, lets it through."""
    for n in range(100000000, 100100000):
        body = "978" + str(n)
        chk = (10 - sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(body)) % 10) % 10
        if cn._luhn(body + str(chk)):
            return body + str(chk)


ISBN = isbn_passing_luhn()
IBAN = iban("UA", "3052990000026007233566001")
TAX = rnokpp("314159265")
# --------------------------------------------------------------------------- 1. the kinds
print("--- 1. what is refused")
check("1.1 a card number (16 digits, Luhn) → card", cn.scan("картка " + CARD) == ["card"], cn.scan(CARD))
check("1.2 the same with spaces and with hyphens → card",
      cn.scan(" ".join(CARD[i:i + 4] for i in range(0, 16, 4))) == ["card"]
      and cn.scan("-".join(CARD[i:i + 4] for i in range(0, 16, 4))) == ["card"])
check("1.3 a card that fails Luhn → nothing", cn.scan(CARD[:-1] + str((int(CARD[-1]) + 1) % 10)) == [])
check("1.4 an IBAN (UA, 29 chars, mod 97) → iban", cn.scan("рахунок " + IBAN) == ["iban"], IBAN)
check("1.5 the IBAN in groups of four → iban", cn.scan(" ".join(IBAN[i:i + 4] for i in range(0, len(IBAN), 4))) == ["iban"])
check("1.6 an IBAN with a wrong check → nothing", cn.scan(IBAN[:2] + "00" + IBAN[4:]) == [])
check("1.7 РНОКПП with the word → rnokpp", cn.scan("ІПН: " + TAX) == ["rnokpp"])
check("1.8 the same ten digits without the word → nothing", cn.scan("замовлення " + TAX) == [])
check("1.9 a passport book (two Cyrillic capitals + 6 digits) beside its word → passport; «МК №…» too",
      cn.scan("паспорт МК 123456") == ["passport"] and cn.scan("Паспорт: МК №123456") == ["passport"])
check("1.10 nine digits beside «ID-картка» → passport; alone → nothing",
      cn.scan("ID-картка 004512345") == ["passport"] and cn.scan("лот 004512345") == [])
secrets = ["sk-ant-" + "a1B2" * 8, "ghp_" + "Zx9" * 12, "github_pat_" + "Q1w2E3" * 6, "glpat-" + "r4T5" * 6,
           "xoxb-1234-5678-abcdEFGH", "AKIA" + "ABCDEFGH23456789", "AIza" + "Sy" + "b7" * 16 + "Xyz",
           "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.c2lnbmF0dXJlMTIz",
           "-----BEGIN OPENSSH PRIVATE KEY-----", "password: Zorg2026secretPass", "**Token:** `a9f3k2m8x7q1w5e4`"]
bad = [s for s in secrets if cn.scan(s) != ["secret"]]
check("1.11 every form of a key or token, and a labelled password → secret", not bad, bad)
more = {"card": ["Картка " + spaced(CARD) + ".", "картка " + CARD + ", термін 12/28", "card:" + CARD,
                  "картка\u00a0" + "\u00a0".join(CARD[i:i + 4] for i in range(0, 16, 4))],
        "iban": [IBAN.lower(), "IBAN:" + IBAN + "."],
        "rnokpp": ["ИНН " + TAX],
        "secret": ["password: Zorg!2026#Pass", "password: Abc12345", '"api_key": "abcd1234efgh5678ijkl"',
                   "| token | Zorg2026secretPass |", "https://zorg.example/api?key=abcd1234efgh5678",
                   "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456", "https://zorg:Pa55word@git.zorg.example",
                   "pass: hunter2abc", "pwd = Zorg!Pass#Word", "sk_live_" + "a1b2c3d4" * 3, "ya29." + "a0B1" * 6,
                   "123456789:AA" + "b" * 33, "-----BEGIN PGP PRIVATE KEY BLOCK-----"]}
bad = [(k, t) for k, ts in more.items() for t in ts if cn.scan(t) != [k]]
check("1.12a the forms a review found slipping through — each caught as its kind", not bad,
      [(k, t, cn.scan(t)) for k, t in bad])
check("1.12 several kinds at once — in order, once each", cn.scan(CARD + " " + IBAN + " " + CARD) == ["card", "iban"])
# --------------------------------------------------------------------------- 2. the look-alikes
print("--- 2. what passes")
fine = ["PROJ-1234", "PROJ-1234, PROJ-98765", "2026-10-27", "27.10.2026 10:00", "1 250 000 грн", "₴12 499,00",
        "+380 67 123 45 67", "+380671234567", "ISBN 978-0-306-40615-7", "9780306406157",
        "замовлення №3141592653", "1698765432123", "550e8400-e29b-41d4-a716-446655440000",
        "commit d97beba", "a9d402c1b2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7", "token: GROW_PM_API_TOKEN", "token: ZORG_API_TOKEN_V2", ISBN,
        "**Token:** stored in Keychain", "api key: ${ZORG_API_KEY}", "PROJ-10452.3", "Q4 2026 OKR 3.2",
        "конверсія 3,14159265 %", "версія 3.21.0", "https://zorg.example/dash/123456789012345",
        "Секція ТП 12", "Members: 22 профілі"]
fine += ["ТЗ 202610", "КП 100500", "ПН 091025", "ВК 123456 переглядів", "МК 123456", "паспорт продукту, ARR 123456789",
         "ТТН " + luhn_complete("2045", 14), "ТТН " + luhn_complete("59", 14),
         "конверсія 0," + CARD, "token: zorg_api_token_v2", "secret: v3.21.0-beta1", "token: 2026-10-27T10:00:00+03:00",
         "**Token:** stored-in-keychain", "password: see Keychain",
         # each look-alike below passes by one guard alone (a mutation of that guard turns it red)
         luhn_complete("1" * 8, 16), luhn_complete("7" * 8, 16), "  ".join(CARD[i:i + 4] for i in range(0, 16, 4)),  # two spaces: no card
         "ID" + CARD, CARD + "x", "XK05" + "1212",
         "ІПН " + TAX[:9] + str((int(TAX[9]) + 1) % 10), "паспортZМК123456", "password: abcdefghijkl"]
bad = [s for s in fine if cn.scan(s)]
check("2.1 task keys, dates, sums, phones, ISBNs, order numbers, UUIDs, hashes, env names, URLs → nothing", not bad,
      [(s, cn.scan(s)) for s in bad])
try:
    cn.check("ok", "картка " + CARD)
    check("2.2 check() raises NeverStore naming the kind, never the value", False, "no raise")
except cn.NeverStore as e:
    check("2.2 check() raises NeverStore naming the kind, never the value",
          e.kinds == ["card"] and CARD not in str(e) and "банківської картки" in str(e), str(e))
# --------------------------------------------------------------------------- 3. the command line
print("--- 3. ctx set / append / add / validate")
d = tempfile.mkdtemp(prefix="ctx-never-")
try:
    env = Env(d)
    rc, out, res = env.run("migrate", "--apply")
    check("3.0 a store to write into", rc == 0, out[-400:])
    rid = "profile"
    before = sorted(os.listdir(os.path.join(env.store, "records")))
    rc, out, res = env.run("set", rid, "Role label", "Card " + CARD)
    check("3.1 set with a card number → exit 4, the kind said, the value nowhere in the output",
          rc == 4 and "банківської картки" in out and CARD not in out, (rc, out[-500:]))
    rc, out, res = env.run("append", rid, "--text", "- IBAN " + IBAN)
    check("3.2 append with an IBAN → exit 4", rc == 4 and IBAN not in out and "IBAN" in out, (rc, out[-500:]))
    body = os.path.join(d, "body.md")
    open(body, "w", encoding="utf-8").write("- **Token:** sk-ant-" + "a1B2" * 8 + "\n")
    rc, out, res = env.run("add", "custom", "Zorg secrets", "--body-file", body)
    check("3.3 add whose body holds a key → exit 4, no record added",
          rc == 4 and sorted(os.listdir(os.path.join(env.store, "records"))) == before, (rc, out[-500:]))
    rc, out, res = env.run("add", "custom", "ІПН " + TAX)
    check("3.4 add whose title holds a РНОКПП with its word → exit 4", rc == 4, (rc, out[-300:]))
    rc, out, res = env.run("set", rid, "Role label", "Zorg PM", "--reason", "token: Zorg2026secretPass")
    check("3.5 a secret in --reason → exit 4 (the reason goes to the journal)", rc == 4, (rc, out[-300:]))
    rc, out, res = env.run("append", rid, "--text", "- Zorg", "--reason", "pwd: Zorg!Pass#Word")
    rc2, out2, res2 = env.run("add", "custom", "Zorg notes", "--reason", "token: Zorg2026secretPass")
    check("3.5a a secret in --reason of append and of add → exit 4", rc == 4 and rc2 == 4, (rc, rc2, out2[-300:]))
    rc, out, res = env.run("invalidate", "product.zorg-lite", "--reason", "token: Zorg2026secretPass")
    rc2, out2, res2 = env.run("archive", "product.zorg-lite", "--reason", "pwd: Zorg!Pass#Word")
    rc3, out3, res3 = env.run("set", rid, "Role label", "Zorg PM", "--source", "token: Zorg2026secretPass")
    check("3.5b invalidate --reason, archive --reason, --source → exit 4 (one guard over every writing command)",
          rc == 4 and rc2 == 4 and rc3 == 4, (rc, rc2, rc3, out[-300:]))
    leaked = []
    for root, _, files in os.walk(d):
        for f in files:
            p = os.path.join(root, f)
            try:
                t = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if f != "body.md" and any(v in t for v in (CARD, IBAN, TAX, "Zorg2026secretPass", "Zorg!Pass#Word", "a1B2" * 8)):
                leaked.append(os.path.relpath(p, d))
    check("3.6 no value in any file — records, journal, copies, snapshots", not leaked, leaked)
    rc, out, res = env.run("set", rid, "Role label", "Zorg PM")
    check("3.7 an ordinary value is still written", rc == 0 and "Zorg PM" in env.record(rid), (rc, out[-300:]))
    env.edit(env.ctx, "Zorg PM", "Zorg PM — картка " + CARD)
    rc, out, res = env.run("sync")
    check("3.8 your own edit is imported (the filter guards writes, not your typing)",
          rc == 0 and CARD in env.record(rid), (rc, out[-300:]))
    rc, out, res = env.run("validate")
    warn = [w for w in (res or {}).get("warnings", []) if "банківської картки" in w]
    check("3.9 validate warns: the record and the kind, never the value",
          warn and rid in warn[0] and CARD not in out, (out[-600:], res))
    env.edit(env.ctx, "- **Jira Team ID:** <team-uuid-2>",
             "<!-- zorg-core:begin id=team v=1 -->\n- card " + CARD + "\n<!-- zorg-core:end id=team -->")
    env.run("sync")
    rc, out, res = env.run("validate")
    check("3.10 a value inside a provider's block → no warning (not yours to clean)",
          not [w for w in res.get("warnings", []) if w.startswith("team.beta-b:")], res.get("warnings"))
finally:
    shutil.rmtree(d, ignore_errors=True)

import time  # noqa: E402
t = time.time()
cn.scan("-eyJ" * 40000)
cn.scan("4" * 200000)
check("4.1 long hostile lines scan in well under a second each", time.time() - t < 2.0, time.time() - t)

print("\n%s — %d failure(s)" % ("GREEN" if not fails else "RED", fails))
sys.exit(1 if fails else 0)

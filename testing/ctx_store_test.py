#!/usr/bin/env python3
"""TC-ctx-3110-store — scripts/ctx_store.py: the context store's model (since v3.11.0).

Split rules, record ids, the record file format and the compile that must give back the
original file byte for byte; store I/O and field edits; the context card. Fixtures are
fictional (testing/fixtures/ctx/, "Zorg"); semantics: references/context-protocol.md.
Stdlib only; run from the repo root.
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_store as cs  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "ctx")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:600]))


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


# --- Task 2: split rules, ids, record format, compile
for name in ("minimal", "typical", "rich"):
    t = read(FIX, name + ".md")
    check(name + " round trip", "".join(f["text"] for f in cs.split_sections(t)) == t)
ex = read(ROOT, "local-context.example.md")
check("example round trip", "".join(f["text"] for f in cs.split_sections(ex)) == ex)
crlf = read(FIX, "rich.md").replace("\n", "\r\n")
check("CRLF round trip", "".join(f["text"] for f in cs.split_sections(crlf)) == crlf)
crlf_ids = [f["id"] for f in cs.assign_ids(cs.split_sections(crlf))]
bom = "﻿" + read(FIX, "minimal.md")
frags = cs.split_sections(bom)
check("BOM stays in the header", frags[0]["type"] == "header" and frags[0]["text"].startswith("﻿"), frags[0])
ids = [f["id"] for f in cs.assign_ids(cs.split_sections(read(FIX, "typical.md")))]
check("typical ids", ids == ["header", "profile", "onboarding", "org.zorg", "product.zorg-app", "product.zorg-lite",
                             "team.alpha-a", "team.beta-b", "setting.cjm-configuration", "setting.templates",
                             "setting.obsidian-vaults-optional", "setting.planning-planning-suite",
                             "setting.focus-focus-advisor", "setting.custom-sections"], ids)
ids = [f["id"] for f in cs.assign_ids(cs.split_sections(read(FIX, "rich.md")))]
expected_rich = ["header", "profile", "org.zorg", "product.zorg-app", "team.alpha-a", "custom.zorg-core-context",
                 "custom.group-structure", "custom.struktura-komandy",
                 "custom.design-toolkit-zorg-kit-managed-by-the-zorg-kit-setup", "setting.people-optional",
                 "setting.landscape", "setting.release-release-manager"]
check("rich ids: regions, landscape, fence, wrapped section", ids == expected_rich, ids)
check("CRLF gives the same ids", crlf_ids == expected_rich, crlf_ids)
ex_ids = [f["id"] for f in cs.assign_ids(cs.split_sections(ex))]
check("example: two products, one team, judgment is a setting",
      sum(i.startswith("product.") for i in ex_ids) == 2 and sum(i.startswith("team.") for i in ex_ids) == 1
      and "setting.judgment" in ex_ids, ex_ids)
recs = cs.assign_ids(cs.split_sections(read(FIX, "typical.md")))
check("parents", {r["id"]: r["parent"] for r in recs}["team.beta-b"] == "org.zorg"
      and {r["id"]: r["parent"] for r in recs}["profile"] is None)
rec = dict(recs[4], ctx=1, owner="user", source="migrated", modified="2026-10-20T10:00:00+03:00", body=recs[4]["text"])
rec["sha"] = cs.sha_text(rec["body"])
back = cs.parse_record(cs.render_record(rec))
check("record round trip", back["body"] == rec["body"] and back["id"] == "product.zorg-app" and back["order"] == 50
      and back["parent"] == "org.zorg" and back["title"] == "Product: Zorg App" and back["sha"] == rec["sha"], back)
check("compile = original", cs.compile_records(list(reversed([dict(r, body=r["text"]) for r in recs])))
      == read(FIX, "typical.md"))

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)

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

# --- Task 3: store I/O, atomic writes, field edits
import tempfile  # noqa: E402

def records_of(name, now="2026-10-20T10:00:00+03:00"):
    return [dict(r, ctx=1, owner="user", source="migrated", modified=now, body=r["text"])
            for r in cs.assign_ids(cs.split_sections(read(FIX, name + ".md")))]

with tempfile.TemporaryDirectory() as d:
    st = cs.Store(os.path.join(d, "store"))
    check("a new store does not exist", not st.exists())
    for r in records_of("typical"):
        st.write(r)
    st.save_state({"compiled_at": "x"})
    loaded = st.load()
    check("write/load round trip", st.exists() and [r["id"] for r in loaded] == [r["id"] for r in records_of("typical")]
          and cs.compile_records(loaded) == read(FIX, "typical.md")
          and all(r["sha"] == cs.sha_text(r["body"]) for r in loaded), [r["id"] for r in loaded])
    p = os.path.join(st.records_dir, "product.zorg-app.md")
    before = read(p)
    real_replace = cs.os.replace
    def boom(*a, **k):
        raise OSError("disk full")
    cs.os.replace = boom
    try:
        cs.atomic_write(p, "garbage")
    except OSError:
        pass
    finally:
        cs.os.replace = real_replace
    check("an interrupted atomic write leaves the old file", read(p) == before
          and not [f for f in os.listdir(st.records_dir) if f.startswith(".")], os.listdir(st.records_dir))
    open(os.path.join(st.records_dir, "product.zorg-app 2.md"), "w", encoding="utf-8").write(before)
    check("stray files are ignored and listed", [r["id"] for r in st.load()].count("product.zorg-app") == 1
          and st.stray_files() == ["product.zorg-app 2.md"], st.stray_files())
    st.journal({"op": "test", "ids": ["profile"]})
    check("journal appends JSON lines", st.journal_entries()[-1]["op"] == "test")
    open(os.path.join(st.records_dir, "profile.md"), "w", encoding="utf-8").write("---\nid: profile\n")
    try:
        st.load(); err = ""
    except cs.StoreError as e:
        err = str(e)
    check("broken frontmatter names the file", "profile.md" in err, err)

body = records_of("typical")[4]["body"]
check("field_get", cs.field_get(body, "Jira Project Key") == "PROJ" and cs.field_get(body, "Nope") is None)
check("field_set changes exactly that line", cs.field_set(body, "Jira Project Key", "NEW")
      == body.replace("- **Jira Project Key:** PROJ", "- **Jira Project Key:** NEW"))
check("field_set of an absent field lands after the first list", cs.field_set(body, "Locales", "uk, en")
      == body.replace("- **Confluence Space:** ZAPP\n", "- **Confluence Space:** ZAPP\n- **Locales:** uk, en\n"))
crlf_body = body.replace("\n", "\r\n")
check("field_set keeps CRLF", cs.field_set(crlf_body, "Locales", "uk") ==
      crlf_body.replace("- **Confluence Space:** ZAPP\r\n", "- **Confluence Space:** ZAPP\r\n- **Locales:** uk\r\n"))
team = records_of("rich")[4]["body"]
try:
    cs.field_set(team, "Lead", "X"); raised = False
except cs.RegionError:
    raised = True
check("field_set inside a managed region is refused", raised and cs.field_get(team, "Lead") is None)
once = cs.append_line(body, "- note")
check("append_line once, at the last non-empty line", once == body.replace("- iOS\n", "- iOS\n- note\n")
      and cs.append_line(once, "- note") == once, once)
org = records_of("typical")[3]["body"]
check("append_line under a subsection", cs.append_line(org, "- **Site:** zorg", under="#### Tableau") ==
      org.replace("- **Server:** https://tableau.zorg.example\n", "- **Server:** https://tableau.zorg.example\n- **Site:** zorg\n"))

# --- Task 4: the context card (INDEX.md)
import re  # noqa: E402

typ = records_of("typical")
card = cs.build_card(typ, read(FIX, "typical.md"), now="2026-10-20")
golden = read(FIX, "typical.card.md")
check("card matches the golden", card == golden,
      "\n".join(l for l in card.splitlines() if l not in golden.splitlines())[:600])
many = "# Local Context\n\n" + "".join("## Section %d\n\n- line %d\n\n" % (k, k) for k in range(249))
big = [dict(r, ctx=1, owner="user", source="migrated", modified="2026-10-20T10:00:00+03:00", body=r["text"])
       for r in cs.assign_ids(cs.split_sections(many))]
big_card = cs.build_card(big, many, now="2026-10-20").splitlines()
check("a long card stops at 200 lines", len(big_card) <= 200
      and re.match(r"^\| … \| \+\d+ more — ctx list \| \| \|$", big_card[-1]) is not None, (len(big_card), big_card[-1:]))
rich_card = cs.build_card(records_of("rich"), read(FIX, "rich.md"), now="2026-10-20")
check("no people or member names on the card", "Bea Two" not in rich_card and "Alex One" in rich_card, rich_card)

# --- Final review: append never lands inside a managed region; reads have a time budget
import tempfile, time  # noqa: E402

core = ("### Team: Beta (B)\n\n<!-- zorg-core:begin id=team v=0.4 -->\n#### Members (core)\n| Alex | PM |\n"
        "#### Rituals (core)\n- daily\n<!-- zorg-core:end id=team -->\n- **Lead:** Alex\n")
try:
    cs.append_line(core, "- mine", under="#### Members (core)"); raised = False
except cs.RegionError:
    raised = True
check("append_line under a heading inside a managed region is refused", raised)
check("append_line after a region's end is allowed", cs.append_line(core, "- mine") == core + "- mine\n")
tail_region = "### Team: Gamma (G)\n<!-- zorg-core:begin id=g -->\n- core\n<!-- zorg-core:end id=g -->\n"
check("append_line after a closing end marker is allowed", cs.append_line(tail_region, "- mine") == tail_region + "- mine\n")

with tempfile.TemporaryDirectory() as d:
    fifo = os.path.join(d, "product.zorg-slow.md")
    os.mkfifo(fifo)                    # open() blocks like an iCloud-evicted file that never downloads
    t0 = time.time()
    try:
        cs.read_text(fifo, timeout=0.5); err = ""
    except cs.StoreError as e:
        err = str(e)
    took = time.time() - t0
    try:
        os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))   # release the blocked reader
    except OSError:
        pass
    check("a file that does not arrive in time is a StoreError naming it", "product.zorg-slow.md" in err
          and "not available locally" in err and took < 3, (err, took))

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""TC-ctx-4000-normalize — `ctx vault normalize` (scripts/ctx_normalize.py) and its `ctx undo` (since v4.0.0).

The fictional Zorg vault of testing/fixtures/audit/, with a store: a dry run writes nothing and reports rows and a code;
`--apply` with another code writes nothing; with the code it adds the missing `type`/`created` (never changing a value
there or removing a key), points an ambiguous link and a moved note's link at one note (the text a reader sees kept, a
code block untouched), lists the orphans in the hub of their type, writes «Пов'язане» from the Jira keys a note mentions,
the region of AGENTS.md (your text kept) and a .base of a folder of 5 notes; never the core, the evicted note, a region
of your own scripts or a .base of yours. After it the audit finds no orphan and no ambiguous link; a second run has
nothing to do; `ctx undo` brings every file back byte for byte and takes the new ones away; `--skip` and `--only`
narrow it; no store — a report only. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_normalize_test.py
"""
import os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "testing"))
from ctx_vaultenv import VaultEnv, read, write  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "scripts"))
try:
    import ctx_normalize as cnz  # noqa: E402
except ImportError:
    cnz = None
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


if cnz is None:
    check("v4.0.0 scripts/ctx_normalize.py exists", False, "no module ctx_normalize")
    print("RESULT: RED ❌")
    sys.exit(1)


def lines_kept(old, new):
    """Is every line of `old` in `new`, in the same order (only lines added)?"""
    it = iter(new.split("\n"))
    return all(any(l == m for m in it) for l in old.split("\n"))


STANDUP = "Notes/Meetings/Standup 2026-10-01.md"


def _derived(k):
    """The store and its mirror of local-context.md: `ctx undo` rebuilds them (its own business, tested elsewhere)."""
    return "/_System/context/" in "/" + k or k == "Notes/_System/local-context.md"


with tempfile.TemporaryDirectory() as d:
    env = VaultEnv(d)
    rc, out, _ = env.run("migrate", "--apply")
    check("(set-up) a store in the vault", rc == 0, out[-400:])
    before = env.tree()
    core = env.tree(os.path.join(env.vault, "ZorgCore"))
    rc, out, res = env.run("vault", "normalize", "--json")
    ops = {}
    for r in (res or {}).get("rows", []):
        ops.setdefault(r["op"], []).append(r)
    check("v4.0.0 a dry run: rows of every operation and a code — nothing written",
          rc == 0 and set(ops) == set(cnz.OPS) and len(res["code"]) == 8 and env.tree() == before, (rc, out[-900:]))
    fm = {r["path"]: r["add"] for r in ops.get("frontmatter", [])}
    check("v4.0.0 frontmatter rows: what the audit derived, nothing else",
          fm == {"Notes/Meetings/Sync 2026-10-09.md": {"type": "meeting-notes", "created": "2026-10-09"},
                 "Notes/Meetings/Pricing review.md": {"created": "2026-09-30"},
                 "Notes/Meetings/Retro 2026-10-05.md": {"created": "2026-10-05"}}, fm)
    lk = {(r["path"], r["target"]): r["new"] for r in ops.get("links", [])}
    check("v4.0.0 link rows: an ambiguous name → your layer's note, even when the core's path is shorter; the moved note "
          "→ the one note of its name",
          lk == {(STANDUP, "bea"): "Notes/People/bea", (STANDUP, "Notes/Old/Roadmap"): "Notes/Roadmap",
                 ("Notes/Region link.md", "bea"): "Notes/People/bea",
                 ("Notes/Region link.md", "plan"): "Notes/Projects/Archive/plan"}, lk)
    check("…a note with no frontmatter whose type cannot be derived gets none",
          "Notes/Notes 2026-10-07.md" not in fm, fm)
    hubs = {r["path"]: (r["new_file"], r["add"]) for r in ops.get("hubs", [])}
    check("v4.0.0 hub rows: each orphan in a new hub of its type (no moc links three of them)",
          hubs == {"Notes/_MOC/research — хаб.md": (True, ["Notes/Mention only.md"]),
                   "Notes/_MOC/note — хаб.md": (True, ["Notes/Orphan.md"])}, hubs)
    rel = {r["path"]: [t for t, _ in r["links"]] for r in ops.get("related", [])}
    check("v4.0.0 «Пов'язане» rows: the work card of a key a note mentions — not where it links the card already, "
          "not where your own scripts keep «related»",
          rel == dict({p: ["Notes/Epics/Epic — PROJ-1234"] for p in ("Notes/Meetings/Standup 2026-10-08.md",
                                                                      "Notes/Mention only.md", STANDUP)},
                      **{"Notes/Meetings/Pricing review.md": ["ZorgCore/People/bea"]}), rel)
    pr_row = [r for r in ops.get("related", []) if r["path"] == "Notes/Meetings/Pricing review.md"]
    check("…a participant the registry knows by an e-mail links its person card (the entity's id), a name alone never",
          pr_row and pr_row[0]["links"] == [["ZorgCore/People/bea", "Bea Two"]], pr_row)
    check("…AGENTS.md (there, without the region) and Meetings.base (5 meetings) are rows",
          [r["path"] for r in ops.get("agents", [])] == ["Notes/_System/AGENTS.md"]
          and [(r["path"], r["new_file"]) for r in ops.get("bases", [])] == [("Notes/Meetings/Meetings.base", True)],
          (ops.get("agents"), ops.get("bases")))
    check("…the lines: each row numbered, the command with the code",
          "ctx vault normalize --apply --code %s" % res["code"] in env.run("vault", "normalize")[1], "")

    rc, out, _ = env.run("vault", "normalize", "--apply", "--code", "00000000")
    check("v4.0.0 --apply with another code: refused (exit 4), nothing written", rc == 4 and env.tree() == before, (rc, out[-300:]))

    rc, out, done = env.run("vault", "normalize", "--apply", "--code", res["code"], "--json")
    check("v4.0.0 --apply with the code: every row written, one snapshot", rc == 0 and len(done["written"]) == len(res["rows"])
          and done["snapshot"], (rc, out[-600:]))
    sync = read(env.note("Notes/Meetings/Sync 2026-10-09.md"))
    check("…a note with no frontmatter gets one with the two fields, its text after it",
          sync.startswith("---\ntype: meeting-notes\ncreated: 2026-10-09\n---\n# Sync 2026-10-09\n"), sync[:120])
    pr = read(env.note("Notes/Meetings/Pricing review.md"))
    check("…a value there is never changed, a key never removed: `date` stays, `created` is added",
          "  - Bea\ncreated: 2026-09-30\n---" in pr and "date: 2026-09-30\n" in pr, pr[:200])
    st = read(env.note(STANDUP))
    check("…the links: `[[Notes/People/bea|bea]]` (the text a reader sees kept), the label of a moved note's link kept, "
          "a link in a code block untouched",
          '"[[Notes/People/bea|bea]]"' in st and "[[Notes/Roadmap|the roadmap]]" in st and "[[Not a link in code]]" in st,
          st)
    rl = read(env.note("Notes/Region link.md"))
    check("…a link inside a region another script owns is left as written; the same link outside it is fixed",
          "See [[Notes/People/bea|bea]] and [[Notes/Projects/Archive/plan|plan]]." in rl
          and "<!-- generated:begin id=x -->\n- [[bea]]\n<!-- generated:end id=x -->" in rl, rl)
    check("…the evicted note, the core, a note with your own «related» region (it mentions a key): untouched",
          env.tree(os.path.join(env.vault, "ZorgCore")) == core
          and env.tree()["Notes/Evicted note.md"] == before["Notes/Evicted note.md"]
          and env.tree()["Notes/Two related.md"] == before["Notes/Two related.md"])
    hub = read(env.note("Notes/_MOC/research — хаб.md"))
    check("…a new hub: type moc, the region hub-research listing the orphan",
          hub.startswith("---\ntype: moc\n") and "<!-- ctx:begin id=hub-research -->" in hub
          and "[[Notes/Mention only|Mention only]]" in hub, hub)
    ag = read(env.note("Notes/_System/AGENTS.md"))
    check("…AGENTS.md: your text kept, the region added", ag.startswith("# Agents\n\nNo links here") and
          "<!-- ctx:begin id=agents -->" in ag and "`meeting-notes` → `Meetings/`" in ag, ag[:300])
    base = read(env.note("Notes/Meetings/Meetings.base"))
    check("…Meetings.base: the marker first, the folder's filter", base.startswith(cnz.BASE_MARK)
          and 'file.inFolder("Notes/Meetings")' in base, base[:200])
    last = __import__("json").loads(read(env.home, ".grow-pm", "audit", "last.json"))
    check("review M-3: --apply leaves the audit's last result up to date (no orphan there)",
          last["counts"]["orphan"] == 0, last["counts"])
    rc, out, aud = env.run("audit", "--json")
    amb = [f for f in aud["findings"] if f["kind"] == "ambiguous"]
    check("v4.0.0 after --apply the audit finds no orphan and no ambiguous link a writer may fix in your layer — the one "
          "left lies inside another script's region (not fixable, `where: region`)",
          rc == 0 and aud["counts"]["orphan"] == 0
          and [(f["path"], f["detail"].get("where"), f["fixable"]) for f in amb] == [("Notes/Region link.md", "region", False)]
          and [f["detail"]["target"] for f in aud["findings"] if f["kind"] == "dead"] == ["Nowhere at all"],
          aud and aud["counts"])
    rc, out, again = env.run("vault", "normalize", "--json")
    check("v4.0.0 a second run has nothing to do (the hubs keep what they listed)", rc == 0 and again["rows"] == [],
          [(r["op"], r["path"]) for r in (again or {}).get("rows", [])])
    write(env.note("Notes/Lonely.md"), "# Lonely\n")
    rc, out, more = env.run("vault", "normalize", "--only", "hubs", "--json")
    hub_row = (more or {}).get("rows", [{}])[0]
    check("v4.0.0 a new orphan later: the hub of its type keeps what it listed and adds it",
          rc == 0 and hub_row.get("path") == "Notes/_MOC/note — хаб.md" and not hub_row.get("new_file")
          and [t for t, _ in hub_row.get("links", [])] == ["Notes/Orphan", "Notes/Lonely"], hub_row)
    os.remove(env.note("Notes/Lonely.md"))
    after = env.tree()
    rc, out, _ = env.run("undo")
    last_undo = __import__("json").loads(read(env.home, ".grow-pm", "audit", "last.json"))
    check("final review: `ctx undo` of a normalisation leaves the audit's last result true again (fixable > 0)",
          last_undo["counts"]["fixable"] > 0, last_undo["counts"])
    now_ = env.tree()
    check("v4.0.0 `ctx undo`: every file back byte for byte, the new ones gone",
          rc == 0 and {k: v for k, v in now_.items() if not _derived(k)}
          == {k: v for k, v in before.items() if not _derived(k)}, (rc, out[-500:],
          sorted(set(now_) ^ set(before))[:6]))
    rc, out, _ = env.run("undo")
    check("…and `ctx undo` of that undo puts the normalisation back, the new files too",
          rc == 0 and {k: v for k, v in env.tree().items() if not _derived(k)}
          == {k: v for k, v in after.items() if not _derived(k)}, out[-500:])

with tempfile.TemporaryDirectory() as d:
    env = VaultEnv(d)
    env.run("migrate", "--apply")
    write(env.note("Notes/Meetings/Meetings.base"), "filters: mine\n")
    rc, out, res = env.run("vault", "normalize", "--only", "links,bases", "--json")
    check("v4.0.0 --only: those operations alone; a .base without the marker is yours (skipped, named)",
          rc == 0 and {r["op"] for r in res["rows"]} == {"links"}
          and any("Meetings.base" in p for ps in res["skipped"].values() for p in ps), res and res["skipped"])
    first = [r for r in res["rows"] if r["target"] == "bea"][0]["n"]
    rc, out, done = env.run("vault", "normalize", "--only", "links,bases", "--apply", "--code", res["code"],
                            "--skip", str(first), "--json")
    st = read(env.note(STANDUP))
    check("v4.0.0 --skip N: that row is not written, the others are",
          rc == 0 and '"[[bea]]"' in st and "[[Notes/Roadmap|the roadmap]]" in st, st)
    rc, out, _ = env.run("vault", "normalize", "--only", "nonsense")
    check("…an unknown operation is a usage error (exit 3)", rc == 3 and "--only takes" in out, out[-200:])

with tempfile.TemporaryDirectory() as d:                 # the review of tasks 4–6: each defect it reproduced
    env = VaultEnv(d)
    env.run("migrate", "--apply")
    write(env.note("Notes/Table.md"), "---\ntype: research\ncreated: 2026-10-10\n---\n# Table\n\nWith [[bea]].\n\n"
                                      "| who | link |\n|---|---|\n| a | [[bea]] |\n| b | [[bea\\|Bea Two]] |\n\n"
                                      "Old: [[Notes/Old/Roadmap#Next]].\n")
    write(env.note("Notes/Meetings/Empty 2026-10-11.md"), "---\ntype:\n  - meeting\n  - weekly\ncreated:\n---\n"
                                                         "# Empty\n\nTo [[Roadmap]].\n")
    write(env.note("Notes/Meetings/Tab 2026-10-12.md"), "---\n\tweird line\n---\n# Tab\n\nTo [[Roadmap]].\n")
    write(env.note("Notes/Fence.md"), "---\ntype: research\ncreated: 2026-10-13\n---\n# Fence\n\nPROJ-1234 [[Roadmap]]\n"
                                      "```\nopen code\n")
    write(env.note("Notes/Lonely ru.md"), "---\ntype: зустріч\ncreated: 2026-10-14\n---\n# Lonely ru\n")
    write(env.note("Notes/Odd type.md"), "---\ntype: ../Templates/x\ncreated: 2026-10-14\n---\n# Odd\n")
    write(env.note("Notes/People/review.md"), "---\ntype: performance-review\ncreated: 2026-10-14\n---\n# Review\n")
    p_ = env.note("Notes/Broken region.md")
    write(p_, read(p_).replace("Mine. [[Roadmap]]", "Mine. [[Roadmap]] PROJ-1234 [[bea]]"))
    write(env.note("Notes/People/zed.md"), "# Zed\n")
    write(env.note("Notes/Gfm.md"), "---\ntype: research\ncreated: 2026-10-17\n---\n# Gfm\n\nwho | link\n--- | ---\n"
                                    "a | [[plan]]\n")
    write(env.note("Notes/Meetings/Brackets 2026-10-18.md"), "---\ntype: []\n\"created\": \"\"\n---\n# Brackets\n\n[[Roadmap]]\n")
    rc, out, res = env.run("vault", "normalize", "--json")
    rows = (res or {}).get("rows", [])
    hubs = {r["path"]: r for r in rows if r["op"] == "hubs"}
    check("review I-3: a Cyrillic type gets a hub whose id the parser reads; a type with a path in it a safe file name",
          "Notes/_MOC/зустріч — хаб.md" in hubs and "Notes/_MOC/templates-x — хаб.md" in hubs
          and not any("/Templates/" in h for h in hubs), sorted(hubs))
    check("review M-6: a People note is never listed in a hub (named among the skipped)",
          not any("Notes/People/review.md" in r.get("add", []) for r in hubs.values())
          and "Notes/People/review.md" in res["skipped"].get(cnz.SKIP["sensitive"], []), res["skipped"])
    check("review I-2/I-4: no «Пов'язане» into a note that ends inside an open code block, or whose own region is broken",
          not any(r["op"] == "related" and r["path"] in ("Notes/Fence.md", "Notes/Broken region.md") for r in rows)
          and "Notes/Fence.md" in res["skipped"].get(cnz.SKIP["fence"], [])
          and "Notes/Broken region.md" in res["skipped"].get(cnz.SKIP["broken"], []), res["skipped"])
    check("review I6/I7 (tasks 7–9): an untyped note of People/ never lands in a hub; a link in a note with broken "
          "regions is no row", not any("Notes/People/zed.md" in r.get("add", []) for r in hubs.values())
          and not any(r["op"] == "links" and r["path"] == "Notes/Broken region.md" for r in rows), sorted(hubs))
    check("review I-1: a frontmatter the reader does not trust gets no row",
          not any(r["path"] == "Notes/Meetings/Tab 2026-10-12.md" and r["op"] == "frontmatter" for r in rows))
    rc, out, done = env.run("vault", "normalize", "--apply", "--code", res["code"], "--json")
    tb = read(env.note("Notes/Table.md"))
    check("review B-1: a link in a table keeps the table — `\\|` there, `|` in the text; an anchor's visible text kept",
          "| a | [[Notes/People/bea\\|bea]] |" in tb and "| b | [[Notes/People/bea\\|Bea Two]] |" in tb
          and "With [[Notes/People/bea|bea]]." in tb and "[[Notes/Roadmap#Next|Notes/Old/Roadmap > Next]]" in tb, tb)
    gf = read(env.note("Notes/Gfm.md"))
    check("review (tasks 7–9): a GFM table without leading pipes keeps its columns — `\\|`",
          "a | [[Notes/Projects/Archive/plan\\|plan]]" in gf, gf)
    br = read(env.note("Notes/Meetings/Brackets 2026-10-18.md"))
    check("…`type: []` and `\"created\": \"\"` are filled in place — one key each",
          br.count("type:") == 1 and br.count("created") == 1 and "type: meeting-notes" in br
          and "created: 2026-10-18" in br, br)
    em = read(env.note("Notes/Meetings/Empty 2026-10-11.md"))
    check("review I-1: an empty `created:` is filled in place (one key), a list `type` left as it is",
          em.count("created:") == 1 and "created: 2026-10-11\n" in em and "type:\n  - meeting\n  - weekly\n" in em, em)
    ru = read(env.note("Notes/_MOC/зустріч — хаб.md"))
    write(env.note("Notes/Lonely ru 2.md"), "---\ntype: зустріч\ncreated: 2026-10-15\n---\n# Lonely ru 2\n")
    os.remove(env.note("Notes/Lonely ru.md"))
    rc, out, more = env.run("vault", "normalize", "--only", "hubs", "--json")
    hr = [r for r in (more or {}).get("rows", []) if r["op"] == "hubs" and "зустріч" in r["path"]]
    check("review I-3/M-10: the next run finds that hub again (no «(ctx)» twin) and drops the note gone from it",
          hr and hr[0]["path"] == "Notes/_MOC/зустріч — хаб.md" and [t for t, _ in hr[0]["links"]] == ["Notes/Lonely ru 2"],
          (hr, ru))

import ctx_regions as rg  # noqa: E402
ids = [cnz.hub_id(t) for t in ("зустріч", "нарада", "meeting-notes", "Weekly Sync")]
check("review I-3: two types the id cannot spell get two ids, each read back by the region parser",
      len(set(ids)) == 4 and ids[2] == "hub-meeting-notes"
      and all(rg.parse("<!-- ctx:begin id=%s -->\n<!-- ctx:end id=%s -->\n" % (i, i))[0][0]["id"] == i for i in ids), ids)

with tempfile.TemporaryDirectory() as d:                 # review I-5: two vaults — a fix never points into the other
    env = VaultEnv(d)
    v2 = os.path.join(d, "vault2")
    write(os.path.join(v2, "Notes2", "bob.md"), "---\ntype: person\n---\n# Bob\n")
    env.text = env.text.replace("| 1 | %s | Notes | all | auto | never |" % env.vault,
                                "| 1 | %s | Notes | all | auto | never |\n| 2 | %s | Notes2 | all | auto | never |"
                                % (env.vault, v2))
    write(env.ctx, env.text)
    env.run("migrate", "--apply")
    write(env.note("Notes/Bob link.md"), "---\ntype: research\ncreated: 2026-10-16\n---\n# Bob link\n\n[[bob]]\n")
    rc, out, aud = env.run("audit", "--json")
    bob = [f for f in (aud or {}).get("findings", []) if f["kind"] in ("dead", "ambiguous") and f["detail"]["target"] == "bob"]
    rc, out, res = env.run("vault", "normalize", "--only", "links", "--json")
    check("review I-5: a name only another vault holds is no fix (not fixable, no row)",
          bob and not bob[0]["fixable"] and not any(r.get("target") == "bob" for r in (res or {}).get("rows", [])), (bob, res))

with tempfile.TemporaryDirectory() as d:                 # a file changed after the report: never overwritten
    import ctx_search as cs_
    env = VaultEnv(d)
    env.run("migrate", "--apply")
    rc, out, res = env.run("vault", "normalize", "--only", "frontmatter", "--json")
    p = env.note("Notes/Meetings/Retro 2026-10-05.md")
    write(p, read(p) + "\nEdited in Obsidian meanwhile.\n")
    sctx = cs_.context_for(env.home, env.text, store_root=os.path.join(env.vault, "Notes", "_System", "context"))
    lines = []
    done = cnz.apply(sctx, res, [], lambda notes: None, lines.append, "2026-10-29T10:00:00+02:00")
    check("v4.0.0 a file changed between the report and the write: skipped as moved, the others written",
          "Notes/Meetings/Retro 2026-10-05.md" in done["skipped"].get(cnz.MOVED, [])
          and read(p).endswith("Edited in Obsidian meanwhile.\n") and "created:" not in read(p)
          and any(r["path"] == "Notes/Meetings/Sync 2026-10-09.md" for r in done["written"]), done["skipped"])

with tempfile.TemporaryDirectory() as d:
    env = VaultEnv(d)
    before = env.tree()
    rc, out, res = env.run("vault", "normalize")
    check("v4.0.0 no store: the report, and a line that it will not write", rc == 0 and "немає сховища" in out
          and env.tree() == before, out[-300:])
    rc, out, _ = env.run("vault", "normalize", "--apply", "--code", "deadbeef")
    check("…--apply without a store: exit 3, nothing written", rc == 3 and env.tree() == before, (rc, out[-200:]))

print("RESULT:", "GREEN ✅ — 0 failure(s)" if not fails else "RED ❌ — %d failure(s)" % fails)
sys.exit(1 if fails else 0)

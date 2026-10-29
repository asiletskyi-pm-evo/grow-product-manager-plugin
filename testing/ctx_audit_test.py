#!/usr/bin/env python3
"""TC-ctx-4000-audit — `ctx audit` (scripts/ctx_audit.py) and its line in `ctx health` (since v4.0.0).

The fictional Zorg vault of testing/fixtures/audit/ — one of each fault in the plugin folder Notes/: an orphan, a link to
nothing, a link to a path that is not there (one note of its name elsewhere — fixable), a name the core shares (an
ambiguous link), a region with no end, two regions of one namespace without an id with an unknown namespace and a heading
both inside and outside, notes missing `type` or `created` (fixable when the folder or a date says), a type outside the
taxonomy, a `.bak` and a `_backup_*` folder, an evicted note — and nothing else wrong: `_System/` and `Templates/` are
the plugin's own. The audit reads only: the vault and the store are the same after it; it keeps its last result in
~/.grow-pm/audit/last.json and counts what is new since; `--all` adds the cores as counts. Stdlib only; run from the
repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_audit_test.py
"""
import json, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "testing"))
from ctx_vaultenv import VaultEnv, read, write  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "scripts"))
try:
    import ctx_audit as ca  # noqa: E402
except ImportError:
    ca = None
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


if ca is None:
    check("v4.0.0 scripts/ctx_audit.py exists", False, "no module ctx_audit")
    print("RESULT: RED ❌")
    sys.exit(1)

STANDUP = "Notes/Meetings/Standup 2026-10-01.md"


def by_kind(res, kind):
    return [f for f in res["findings"] if f["kind"] == kind]


with tempfile.TemporaryDirectory() as d:
    env = VaultEnv(d)
    before = env.tree()
    rc, out, res = env.run("audit", "--json")
    check("v4.0.0 `ctx audit` runs (exit 0) over your layer", rc == 0 and res and res["scope"] == "own", (rc, out[-800:]))
    f = {k: by_kind(res, k) for k in ("orphan", "dead", "ambiguous", "region", "schema", "backup")}
    check("v4.0.0 orphan: the notes with no link either way — a Jira key's mention is no link — not _System/, not "
          "Templates/, not the evicted one",
          [x["path"] for x in f["orphan"]] == ["Notes/Mention only.md", "Notes/Orphan.md"]
          and all(x["fixable"] for x in f["orphan"]), f["orphan"])
    dead = {x["detail"]["target"]: x for x in f["dead"]}
    check("v4.0.0 dead: a link to nothing — not fixable; a path that is not there with one note of its name — fixable",
          set(dead) == {"Nowhere at all", "Notes/Old/Roadmap"} and dead["Nowhere at all"]["fixable"] is False
          and dead["Notes/Old/Roadmap"]["fixable"] is True
          and dead["Notes/Old/Roadmap"]["detail"]["candidates"] == ["Notes/Roadmap.md"]
          and all(x["path"] == STANDUP for x in f["dead"]), f["dead"])
    check("v4.0.0 ambiguous: `[[bea]]` names your card and the core's, `[[plan]]` too — fixable (a full path)",
          [(x["path"], x["detail"]["target"]) for x in f["ambiguous"]] == [(STANDUP, "bea"), ("Notes/Region link.md", "bea"),
                                                                           ("Notes/Region link.md", "plan")]
          and f["ambiguous"][0]["fixable"] and len(f["ambiguous"][0]["detail"]["candidates"]) == 2, f["ambiguous"])
    regs = sorted((x["path"], x["detail"]["why"]) for x in f["region"])
    check("v4.0.0 region: a begin with no end; two without an id, an unknown namespace, a heading inside and outside — "
          "none fixable", regs == [("Notes/Broken region.md", "unclosed"), ("Notes/Two related.md", "heading-twice"),
                                   ("Notes/Two related.md", "no-id"), ("Notes/Two related.md", "unknown-ns")]
          and not any(x["fixable"] for x in f["region"]), regs)
    sch = {x["path"]: x for x in f["schema"]}
    check("v4.0.0 schema: a meeting with no frontmatter — type by its folder and created by its name, fixable",
          sch.get("Notes/Meetings/Sync 2026-10-09.md", {}).get("detail") == {
              "missing": ["type", "created"], "derived": {"type": "meeting-notes", "created": "2026-10-09"}}
          and sch["Notes/Meetings/Sync 2026-10-09.md"]["fixable"], sch.get("Notes/Meetings/Sync 2026-10-09.md"))
    check("…`created` from the note's `date`, from a date in its name — fixable",
          sch.get("Notes/Meetings/Pricing review.md", {}).get("detail", {}).get("derived") == {"created": "2026-09-30"}
          and sch.get("Notes/Meetings/Retro 2026-10-05.md", {}).get("detail", {}).get("derived") == {"created": "2026-10-05"},
          [sch.get("Notes/Meetings/Pricing review.md"), sch.get("Notes/Meetings/Retro 2026-10-05.md")])
    check("…a note at the top with no frontmatter: nothing to derive — not fixable",
          sch.get("Notes/Orphan.md", {}).get("fixable") is False
          and sch["Notes/Orphan.md"]["detail"]["missing"] == ["type", "created"], sch.get("Notes/Orphan.md"))
    check("…a folder of several types (Research/): the type is not derived — not fixable",
          sch.get("Notes/Research/Market notes.md", {}).get("fixable") is False
          and sch["Notes/Research/Market notes.md"]["detail"] == {"missing": ["type"], "derived": {}},
          sch.get("Notes/Research/Market notes.md"))
    check("…_System/, Templates/ and the evicted note are not checked",
          not any(p.startswith(("Notes/_System/", "Notes/Templates/")) or p == "Notes/Evicted note.md" for p in sch),
          sorted(sch))
    check("…a type outside the taxonomy is information: meeting 1, research 4",
          res["info"]["types"].get("meeting") == 1 and res["info"]["types"].get("research") == 4
          and "meeting-notes" not in res["info"]["types"], res["info"])
    bk = sorted(x["path"] for x in f["backup"])
    check("v4.0.0 backup: a `_backup_*` folder of the vault and a `.bak` in your layer — named, not fixable",
          bk == ["Notes/Roadmap.md.bak", "_backup_before_cleanup"] and not any(x["fixable"] for x in f["backup"]), bk)
    check("v4.0.0 information: names shared with the core (bea.md, plan.md), notes no link reaches, the evicted note unchecked",
          res["info"]["shared_names"] == ["bea.md", "plan.md"] and res["info"]["no_inbound"] >= 1 and res["counts"]["unchecked"] == 1,
          res["info"])
    check("v4.0.0 counts: every kind, the fixable ones together",
          res["counts"]["orphan"] == 2 and res["counts"]["dead"] == 2 and res["counts"]["ambiguous"] == 3
          and res["counts"]["region"] == 4 and res["counts"]["fixable"] == sum(1 for x in res["findings"] if x["fixable"]),
          res["counts"])
    check("v4.0.0 the audit reads only: the vault is the same after it", env.tree() == before)
    cache = os.path.join(env.home, ".grow-pm", "audit", "last.json")
    data = json.loads(read(cache)) if os.path.isfile(cache) else {}
    check("v4.0.0 the last result is kept in ~/.grow-pm/audit/last.json (context-audit/1): when, the counts, the signatures",
          data.get("schema") == "context-audit/1" and data.get("counts") == res["counts"]
          and len(data.get("sigs") or []) == len(res["findings"]) and res["new"] is None, data)
    rc, out, res2 = env.run("audit", "--json")
    check("…a second audit with nothing changed: 0 new since the last", rc == 0 and res2["new"] == 0, res2 and res2["new"])
    write(env.note("Notes/Meetings/Standup 2026-10-08.md"),
          read(env.note("Notes/Meetings/Standup 2026-10-08.md")) + "\nAlso [[Gone note]].\n")
    rc, out, res3 = env.run("audit")
    check("…one new dead link: «нових від минулого аудиту: 1», and the lines name each kind with the fix",
          rc == 0 and res3["new"] == 1 and "нових від минулого аудиту: 1" in out and "мертві лінки" in out
          and "ctx vault normalize" in out and "не перевірено (iCloud): 1" in out, out[-1500:])
    rc, out, res4 = env.run("audit", "--all", "--json")
    check("v4.0.0 --all: the cores as counts — notes, orphans, dead and ambiguous links — never as findings",
          rc == 0 and res4["scope"] == "all" and res4["cores"].get("zorg-core", {}).get("notes", 0) >= 3
          and not any(x["path"].startswith("ZorgCore/") for x in res4["findings"]), res4.get("cores"))

with tempfile.TemporaryDirectory() as d:                 # a note indexed, then evicted: never opened again
    env = VaultEnv(d, evicted=())
    env.run("audit")
    env.evicted = ("Notes/Roadmap.md", "Two related.md")
    opened, real_open = [], open

    def spy(path, *a, **k):
        opened.append(str(path))
        return real_open(path, *a, **k)

    ca.open = spy
    try:
        rc, out, res = env.run("audit", "--json")
    finally:
        del ca.open
    check("v4.0.0 a note iCloud evicted after it was indexed is never opened by the audit (its regions unchecked)",
          rc == 0 and not any(p.endswith(("Roadmap.md", "Two related.md")) for p in opened)
          and not any(f["path"] == "Notes/Two related.md" for f in res["findings"] if f["kind"] == "region")
          and any(p.endswith("Broken region.md") for p in opened), [p for p in opened if p.endswith(".md")][:8])

with tempfile.TemporaryDirectory() as d:                 # final review B1: a sensitive note's links never said
    env = VaultEnv(d)
    write(env.note("Notes/Meetings/1-1 Bea 2026-10-20.md"), "---\ntype: meeting-notes\ncreated: 2026-10-20\n"
                                                            "concern_owner: \"[[Severance terms]]\"\n---\n# 1-1 Bea\n\n"
                                                            "See [[Layoff plan Q4]] and [[bea]].\n")
    rc, out, res = env.run("audit", "--json")
    mine = [f for f in res["findings"] if f["path"] == "Notes/Meetings/1-1 Bea 2026-10-20.md"]
    text = env.run("audit")[1]
    check("v4.0.0 final review B1: a 1-1 note's dead and ambiguous links are counted, never named — no target, no "
          "field, no candidates, not fixable; the lines say «· sensitive»",
          mine and all(f["detail"].get("sensitive") and not f["detail"]["target"] and not f["detail"]["field"]
                       and not f["fixable"] for f in mine if f["kind"] in ("dead", "ambiguous"))
          and "Severance" not in out + text and "Layoff" not in out + text and "concern_owner" not in out + text
          and "Notes/Meetings/1-1 Bea 2026-10-20.md · sensitive" in text, (mine, text[-600:]))

with tempfile.TemporaryDirectory() as d:                 # the line in `ctx health`
    env = VaultEnv(d)
    rc, out, _ = env.run("migrate", "--apply")
    rc, out, res = env.run("health", "--json")
    lines = [l for l in (res or {}).get("lines", []) if "аудит" in l["text"]]
    check("v4.0.0 health before any audit: «аудит вейлта ще не запускався» ⚠ with the command",
          rc == 0 and len(lines) == 1 and lines[0]["level"] == "warn" and "ще не запускався" in lines[0]["text"]
          and lines[0]["fix"] == "ctx audit", (rc, lines, out[-500:]))
    env.run("audit")
    rc, out, res = env.run("health", "--json")
    lines = [l for l in (res or {}).get("lines", []) if "аудит" in l["text"]]
    check("v4.0.0 health after the audit: the fixable findings ⚠ → ctx vault normalize; broken regions ✋",
          any(l["level"] == "warn" and "виправних" in l["text"] and l["fix"] == "ctx vault normalize" for l in lines)
          and any(l["level"] == "act" and "регіони" in l["text"] for l in lines), lines)

FA = read(ROOT, "skills", "focus-advisor", "SKILL.md")
CM = read(ROOT, "commands", "context.md")
check("v4.0.0 the health lines reach the morning brief: focus-advisor names the two prefixes ctx_audit.health writes "
      "(«аудит вейлта», «регіони зламані») and the command, and /context takes `audit`",
      "begins `аудит вейлта`" in FA and "`регіони зламані`" in FA and "/grow-product-manager:context audit" in FA
      and "`audit`" in CM)
import ctx_show as csh  # noqa: E402
lines = ca.health(os.path.join(tempfile.gettempdir(), "no-such-home"), True, "2026-10-29")
check("…and ctx_audit.health's lines begin so", all(t.startswith(("аудит вейлта", "регіони зламані")) for _, t, _ in lines)
      and lines, lines)

print("RESULT:", "GREEN ✅ — 0 failure(s)" if not fails else "RED ❌ — %d failure(s)" % fails)
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""TC-ctx-4000-facts — the facts of a card and the trust of a source (scripts/ctx_facts.py, ctx_trust.py; v4.0.0).

The trust formula at its edges (each source kind, within the TTL, between one and three TTLs, past them, no date, a
`last_verified` later than the note's day, superseded and draft); the facts the walk keeps from a metric card's
frontmatter (a value with its period and its day — the text of a note never), an index of v3.24.0 reading its cards
once more for them; `ctx entity` showing them with their trust and ⚠ where your card and the core's disagree; the
`facts` finding of `ctx audit`; `ctx search --get` with the trust line under the provenance line and `trust` in its
result. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_facts_test.py
"""
import os, sqlite3, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "testing"))
from ctx_vaultenv import VaultEnv, read, write  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "scripts"))
try:
    import ctx_trust as ct  # noqa: E402
    import ctx_facts as cf  # noqa: E402
except ImportError:
    ct = cf = None
import ctx_index as ci  # noqa: E402
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


if ct is None:
    check("v4.0.0 scripts/ctx_trust.py and ctx_facts.py exist", False, "no module")
    print("RESULT: RED ❌")
    sys.exit(1)

T = "2026-10-29"
check("v4.0.0 trust: the source weights — record 1, own 0.9, core 0.85, local 0.8, mcp 0.75, confluence 0.7",
      [ct.score(k, T, 30, "", "", T)["score"] for k in ("record", "own", "core", "local", "mcp", "confluence")]
      == [1.0, 0.9, 0.85, 0.8, 0.75, 0.7])
check("…freshness: 1 within the TTL, 0.75 half way to three TTLs, 0.5 at three and after, 0.6 without a day",
      [ct.freshness(d, 30, T) for d in ("2026-09-29", "2026-08-30", "2026-07-31", "2025-01-01", None)]
      == [1.0, 0.75, 0.5, 0.5, 0.6], [ct.freshness(d, 30, T) for d in ("2026-09-29", "2026-08-30", "2026-07-31")])
check("…no class TTL: a year", ct.freshness("2025-11-01", None, T) == 1.0 and ct.freshness("2025-10-01", None, T) < 1)
check("…a `last_verified` later than the note's day dates the freshness",
      ct.score("own", "2025-01-01", 30, "", "2026-10-20", T)["parts"]["freshness"] == 1.0)
check("…state: superseded/archived/застаріле 0.3, draft 0.8, else 1",
      [ct.score("own", T, 30, s_, "", T)["parts"]["state"] for s_ in ("superseded", "archived", "застаріле", "draft", "active")]
      == [0.3, 0.3, 0.3, 0.8, 1.0])
t = ct.score("core", "2026-08-30", 30, "draft", "", T)
check("…the line: «довіра 0,51 (джерело 0,85 · свіжість 0,75 · стан 0,8)»",
      ct.line(t) == "довіра 0,51 (джерело 0,85 · свіжість 0,75 · стан 0,8)", ct.line(t))
check("v4.0.0 facts_of: the fact fields with their period and day; nothing else, never a list",
      ci.facts_of({"type": "metric", "actual": "33.1%", "actual_period": "W36", "actual_updated": "2026-09-10",
                   "target": "40%", "period": "Q3", "snapshot": "2026-09-01", "owner": "x", "value": ["a"]})
      == [("actual", "33.1%", "W36", "2026-09-10", "actual"), ("target", "40%", "Q3", "2026-09-01", "target")])

OWN = "Notes/Metrics/conversion.md"
CORE = "ZorgCore/Metrics/conversion.md"
with tempfile.TemporaryDirectory() as d:
    env = VaultEnv(d, fixture="graph")
    write(env.note(CORE), "---\ntype: metric\nname: Conversion\nactual: 3.4%\nactual_period: Q3 2026\n"
                          "actual_updated: 2026-10-01\ntarget: 4%\n---\n# Conversion\n\nThe text says 9% — never a fact.\n")
    write(env.note(OWN), "---\ntype: metric\nsame_as: \"[[ZorgCore/Metrics/conversion|Conversion]]\"\nactual: 3.2%\n"
                         "actual_period: Q3 2026\nupdated: 2026-09-20\n---\n# conversion\n")
    rc, out, res = env.run("entity", "ZorgCore/Metrics/conversion.md", "--json")
    facts = (res or {}).get("entities", [{}])[0].get("facts") or []
    by = {(f["path"], f["attribute"]): f for f in facts}
    check("v4.0.0 `ctx entity` on a metric: the facts of both its cards with period, day and trust",
          rc == 0 and set(by) == {(CORE, "actual"), (CORE, "target"), (OWN, "actual")}
          and by[(CORE, "actual")]["value"] == "3.4%" and by[(CORE, "actual")]["observed_at"] == "2026-10-01"
          and by[(CORE, "actual")]["trust"]["kind"] == "core" and by[(OWN, "actual")]["trust"]["kind"] == "own"
          and by[(OWN, "actual")]["observed_at"] == "2026-09-20", (rc, facts, out[-500:]))
    check("…the two `actual` of Q3 2026 disagree (⚠), the target alone does not",
          by[(CORE, "actual")]["conflict"] and by[(OWN, "actual")]["conflict"] and not by[(CORE, "target")]["conflict"])
    rc, out, _ = env.run("entity", "ZorgCore/Metrics/conversion.md")
    check("…the lines: «факти:», each with its trust, the ⚠ line",
          "факти:" in out and "⚠ actual: 3.4% · Q3 2026 · станом на 2026-10-01" in out and "довіра 0," in out
          and "картки дають різні значення" in out, out[-900:])
    rc, out, aud = env.run("audit", "--json")
    ff = [f for f in (aud or {}).get("findings", []) if f["kind"] == "facts"]
    check("v4.0.0 `ctx audit`: one `facts` finding on your card, both values named, not fixable",
          rc == 0 and len(ff) == 1 and ff[0]["path"] == OWN and not ff[0]["fixable"]
          and sorted(v["value"] for v in ff[0]["detail"]["values"]) == ["3.2%", "3.4%"], ff)
    db = os.path.join(env.home, ".grow-pm", "index", "sections.sqlite")
    con = sqlite3.connect(db)                        # an index of v3.24.0: no facts, no facts_version
    con.executescript("DELETE FROM facts; DELETE FROM meta WHERE key = 'facts_version';")
    con.commit()
    con.close()
    rc, out, res = env.run("entity", "ZorgCore/Metrics/conversion.md", "--json")
    check("v4.0.0 an index of v3.24.0 reads its cards once more for their facts",
          rc == 0 and len(res["entities"][0]["facts"]) == 3, res and res["entities"][0].get("facts"))
    rc, out, res = env.run("search", "--get", "ZorgCore/Metrics/conversion.md", "--json")
    check("v4.0.0 `ctx search --get`: `trust` in the result — a core's card, 0,85 × its freshness",
          rc == 0 and res["trust"]["kind"] == "core" and res["trust"]["parts"]["source"] == 0.85, res)
    rc, out, _ = env.run("search", "--get", "Notes/Roadmap.md")
    lines = out.splitlines()
    check("…the lines: the provenance line as it was, the trust line right under it",
          lines[0].startswith("> [own · Notes/Roadmap.md · ") and lines[1].startswith("> довіра 0,9"), lines[:3])

with tempfile.TemporaryDirectory() as d:
    import ctx_search as cs_
    env = VaultEnv(d, fixture="graph")
    sctx = cs_.context_for(env.home, env.text)
    check("v4.0.0 kind_of: a core's page mirrored from Confluence (a page id in its name) 0.7; a core's card 0.85; a "
          "source no registration names — a local index",
          ct.kind_of(sctx, "zorg-core", "ZorgCore/Pages/Delivery slots (900100200).md") == "confluence"
          and ct.kind_of(sctx, "zorg-core", "ZorgCore/Teams/team-alpha.md") == "core"
          and ct.kind_of(sctx, "zorg-brain", "Partner/x.md") == "local" and ct.kind_of(sctx, "own", "Notes/x.md") == "own")


class _Reg:
    entities = [{"id": "ZorgCore/M/c.md", "cards": [{"path": "ZorgCore/M/c.md"}, {"path": "Notes/M/c.md"}]}]


real_rows = cf.rows
cf.rows = lambda idx, paths: [
    {"path": "ZorgCore/M/c.md", "attribute": "actual", "value": "1", "period": "Q3"},
    {"path": "Notes/M/c.md", "attribute": "actual", "value": "2", "period": "Q3"}]
try:
    got = cf.audit_findings(None, _Reg(), [("Notes", "/vault/Notes")])
finally:
    cf.rows = real_rows
check("v4.0.0 a `facts` finding stands on the card of your layer even when the core's comes first",
      [g["path"] for g in got] == ["Notes/M/c.md"], got)

print("RESULT:", "GREEN ✅ — 0 failure(s)" if not fails else "RED ❌ — %d failure(s)" % fails)
sys.exit(1 if fails else 0)

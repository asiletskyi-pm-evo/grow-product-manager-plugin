#!/usr/bin/env python3
"""TC-ctx-3231-overlay-merge — the declared overlay inside `ctx provider plan | apply | sync` (since v3.23.0).

On a migrated store of the fictional "Zorg" (testing/fixtures/ctx-repos/context.md, a temp HOME): an overlay file is
put beside the store, and `ctx_blocks.plan` / `apply` write `overlay(theirs)` into the regions while the base stays the
core's text. The point of the release: the core moves on and the overlay is applied again with no question; a region
you edited by hand is never rewritten; an operation whose `expects` no longer holds is held (the core's text for its
part), the others still apply; a file that cannot be read holds every block that carries the overlay; without a file
nothing differs from v3.22; `ctx undo` takes it all back. Semantics: references/context-protocol.md §5n,
references/context-provider-protocol.md §12.6. Stdlib only; run from the repo root.
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_blocks as cb  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_overlay as ov  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_store as cs  # noqa: E402
import ctx_synced as sy  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "ctx-repos")
NOW = "2026-10-20T10:00:00+03:00"
LATER = "2026-10-21T10:00:00+03:00"
NS = "zorg-core"
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def region(bid, v, body):
    return "<!-- %s:begin id=%s v=%s -->\n%s\n<!-- %s:end id=%s -->" % (NS, bid, v, body, NS, bid)


REPO = crp.normalise({"id": "zorg-core", "kind": "bundle", "paths": ["/zorg/core"], "team": "team-alpha", "skip_blocks": ["product"]})
OWN_MEMBERS = ("- **Jira Team ID:** <team-uuid>\n",
               "- **Jira Team ID:** <team-uuid>\n\n#### Team Members\n\n| Name | Role |\n|---|---|\n| Alex One | PM |\n| Bea Two | Analyst |\n| Cid Three | QA |\n")
SCOPE = region("scope", "0.4", "### Scope of work\nThe user works on Zorg App only.")
TEAMS = region("teams", "0.4", "### Teams map\n- Alpha, Beta")


def migrated(d):
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    os.makedirs(os.path.join(home, ".grow-pm"))
    os.makedirs(os.path.join(vault, "Notes", "_System"))
    text = open(os.path.join(FIX, "context.md"), encoding="utf-8", newline="").read().replace("{{VAULT}}", vault)
    text = text.replace(*OWN_MEMBERS, 1)
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    for p in (ctxp, os.path.join(vault, "Notes", "_System", "local-context.md")):
        open(p, "w", encoding="utf-8", newline="").write(text)
    copies = co.copies_for(ctxp, text, home=home)
    store = cs.Store(co.store_root_for(text, home=home))
    co.migrate(ctxp, store.root, copies, home, apply=True, now=NOW)
    return home, text, copies, store, ctxp


def core_team(store):
    """The core's team region: the base when there is one (your region may carry the overlay), else your region."""
    entry = cb.load_state(store, "zorg-core")["blocks"].get("team")
    if entry and entry.get("base_sha"):
        return cb.get_base(store, "zorg-core", entry["base_sha"])
    return cb.find_regions(store.load(), NS)[0]["team"]["text"]


def published(store, **blocks):
    team = core_team(store)
    b = {"scope": SCOPE, "teams": TEAMS}
    b.update({k: v for k, v in blocks.items() if k != "team"})
    return {"source": "folder", "version": "0.4", "blocks": b, "team": blocks.get("team", team), "team_source": "folder",
            "team_error": None, "error": None, "checked": NOW}


def guard(home, text):
    return cs.guard_roots(co.allowed_roots(home, text))


def adopt(home, text, copies, store, f):
    with guard(home, text):
        return cb.adopt(store, copies, home, REPO, f, NOW, True)


def apply_of(home, text, copies, store, f, choose=None, now=NOW, **kw):
    with guard(home, text):
        return cb.apply(store, copies, home, REPO, f, choose or {}, [], now, **kw)


def plan_of(store, copies, f, now=NOW):
    return cb.plan(store, copies, REPO, f, now)


def regions(store):
    return {k: v["text"] for k, v in cb.find_regions(store.load(), NS)[0].items()}


def journal(store):
    p = os.path.join(store.state_dir, "journal.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.isfile(p) else []


def tree(store):
    out = {}
    for base, _, files in os.walk(store.root):
        for f in files:
            p = os.path.join(base, f)
            out[os.path.relpath(p, store.root)] = open(p, "rb").read()
    return out


def put_overlay(home, text, store, ops):
    with guard(home, text):
        ov.save(store.root, "zorg-core", {"schema": ov.SCHEMA, "repo": "zorg-core", "ops": ov.parse(ov.dump(
            {"schema": ov.SCHEMA, "repo": "zorg-core", "ops": ops}))["ops"]})


def op(oid, block, path, kind, expects=1, **k):
    d = {"id": oid, "target": {"block": block, "path": path} if path else {"block": block}, "op": kind, "expects": expects,
         "reason": "r-" + oid, "created": "2026-10-20"}
    d.update(k)
    return d


OPS = [op("members", "team", "#Members", "replace", value_ref="team.alpha-a#Team Members"),
       op("gamma", "teams", "", "append", value=["- Gamma (overlay)"]),
       op("only", "scope", 'match:"Zorg App only"', "ignore")]


def ctx(home, ctxp, *args):
    env = {k: v for k, v in os.environ.items() if k not in ("GROW_PM_CONTEXT_PATH", "GROW_PM_PROVIDER_PATHS")}
    env["HOME"] = home
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ctx.py")] + list(args) + ["--context", ctxp, "--home", home],
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


# ------------------------------------------------------------------ refs_in
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store, ctxp = migrated(d)
    refs = ov.refs_in(store.load())
    check("refs_in: your own subsection is found, a block's subsection and a missing one are not",
          refs("team.alpha-a#Team Members") and not refs("team.alpha-a#Members") and not refs("team.nope#Team Members"),
          [r["id"] for r in store.load()])

# ------------------------------------------------------------------ no file: v3.22 behaviour
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store, ctxp = migrated(d)
    f = published(store)
    adopt(home, text, copies, store, f)
    before = tree(store)
    p = plan_of(store, copies, f)
    res = apply_of(home, text, copies, store, f)
    check("no overlay file: plan unchanged, apply changes nothing but the time of the check",
          p["changes"] == 0 and p["questions"] == 0 and not res["changed"] and p.get("overlay_error") is None
          and not any(r.get("reoverlay") for r in p["rows"]), (p, res["changed"]))
    after = tree(store)
    check("…and every file but the block state is byte for byte", {k: v for k, v in after.items() if "blocks" not in k}
          == {k: v for k, v in before.items() if "blocks" not in k}, set(after) ^ set(before))
    mask = lambda t: json.dumps({b: {k: v for k, v in e.items() if k != "checked"} for b, e in json.loads(t)["blocks"].items()})
    check("…and the block state has no overlay key (the times of the check aside)",
          mask(after[".state/blocks/zorg-core.json"]) == mask(before[".state/blocks/zorg-core.json"])
          and b"overlay" not in after[".state/blocks/zorg-core.json"], "")

# ------------------------------------------------------------------ first application, then a core release
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store, ctxp = migrated(d)
    f = published(store)
    adopt(home, text, copies, store, f)
    put_overlay(home, text, store, OPS)
    p = plan_of(store, copies, f)
    check("plan with a new overlay: team and teams are '=' to be overlaid (2 records), no question",
          {r["block"]: (r["sign"], bool(r.get("reoverlay"))) for r in p["rows"]} ==
          {"team": ("=", True), "scope": ("=", False), "teams": ("=", True)} and p["questions"] == 0 and p["changes"] == 2,
          [(r["block"], r["sign"], r.get("reoverlay"), r["note"]) for r in p["rows"]])
    res = apply_of(home, text, copies, store, f)
    rg = regions(store)
    check("apply writes the overlay: your table in place of the core's members (one pointer line), Gamma appended",
          "Bea Two ◌" not in rg["team"] and "> [оверлей members: замінено на team.alpha-a › Team Members — r-members]" in rg["team"]
          and rg["teams"].endswith("- Alpha, Beta\n- Gamma (overlay)\n<!-- zorg-core:end id=teams -->") and rg["scope"] == SCOPE,
          rg)
    st = cb.load_state(store, "zorg-core")["blocks"]
    check("the bases stay the core's text; the state remembers what the overlay wrote",
          cb.get_base(store, "zorg-core", st["teams"]["base_sha"]) == TEAMS and st["teams"]["overlay_sha"] == cs.sha_text(cb.norm(rg["teams"]))
          and st["teams"]["overlay_of"] == st["teams"]["base_sha"] and "overlay_sha" not in st["scope"], st["teams"])
    j = journal(store)[-1]
    check("one journal line names what the overlay did", j["op"] == "provider-apply" and j.get("overlay") ==
          {"team": ["members"], "teams": ["gamma"], "scope": ["only"]} and "overlay_held" not in j, j)
    p2 = plan_of(store, copies, f)
    check("…and the next plan has nothing to do", p2["changes"] == 0 and p2["questions"] == 0
          and all(r["sign"] == "=" and not r.get("reoverlay") for r in p2["rows"]), [(r["block"], r["sign"], r.get("reoverlay")) for r in p2["rows"]])
    snap_after_first = tree(store)

    # the core moves on: teams v0.5 and scope v0.5 — 1 confirmation, 0 questions, the overlay applied again
    T5 = region("teams", "0.5", "### Teams map\n- Alpha, Beta, Delta")
    S5 = region("scope", "0.5", "### Scope of work\nThe user works on Zorg App only, and on Zorg Lite.")
    f5 = published(store, teams=T5, scope=S5)
    p5 = plan_of(store, copies, f5)
    check("a core release over overlaid regions: '~' for both, no question",
          {r["block"]: r["sign"] for r in p5["rows"]} == {"team": "=", "scope": "~", "teams": "~"} and p5["questions"] == 0,
          [(r["block"], r["sign"], r["note"]) for r in p5["rows"]])
    res5 = apply_of(home, text, copies, store, f5, now=LATER)
    rg = regions(store)
    check("…apply takes the core's text and applies the overlay again; the members stay yours",
          rg["teams"] == region("teams", "0.5", "### Teams map\n- Alpha, Beta, Delta\n- Gamma (overlay)") and rg["scope"] == S5
          and "Bea Two ◌" not in rg["team"] and res5["pending"] == [], rg)
    check("…the bases are the core's v0.5 texts", cb.get_base(store, "zorg-core", cb.load_state(store, "zorg-core")["blocks"]["teams"]["base_sha"]) == T5, "")
    st5 = cb.load_state(store, "zorg-core")["blocks"]["teams"]
    check("…the state remembers the new overlaid text, and the next plan has nothing to do",
          st5["overlay_sha"] == cs.sha_text(cb.norm(rg["teams"])) and st5["overlay_of"] == st5["base_sha"]
          and plan_of(store, copies, f5, now=LATER)["changes"] == 0, st5)
    state = cb.load_state(store, "zorg-core")
    for e in state["blocks"].values():
        e.pop("overlay_sha", None); e.pop("overlay_of", None)
    with guard(home, text):
        cb.save_state(store, "zorg-core", state)
    p5b = plan_of(store, copies, f5, now=LATER)
    check("a state that lost what the overlay wrote: the overlaid region is still read as the base's (no ✎, no rewrite)",
          all(r["sign"] == "=" and not r.get("reoverlay") for r in p5b["rows"]) and p5b["changes"] == 0,
          [(r["block"], r["sign"], r.get("reoverlay")) for r in p5b["rows"]])

    # you edit an overlaid region by hand: it is yours, the overlay does not touch it
    rec = [r for r in store.load() if "zorg-core:begin id=teams" in r["body"]][0]
    store.write(dict(rec, body=rec["body"].replace("- Gamma (overlay)", "- Gamma (overlay)\n- my own line")))
    with guard(home, text):
        co.apply_sync(store, co.plan_sync(store, copies), copies, home, None, "", LATER)
    T6 = region("teams", "0.6", "### Teams map\n- Alpha, Beta, Delta, Eps")
    p6 = plan_of(store, copies, published(store, teams=T6, scope=S5), now=LATER)
    row = [r for r in p6["rows"] if r["block"] == "teams"][0]
    check("a hand edit in an overlaid region: '⚠' when the core moved too, and the note says the overlay waits",
          row["sign"] == "⚠" and "оверлей не накладено" in row["note"], (row["sign"], row["note"]))
    res6 = apply_of(home, text, copies, store, published(store, teams=T6, scope=S5), now=LATER)
    check("…apply leaves your region as it is (pending)", "- my own line" in regions(store)["teams"] and res6["pending"] == ["teams"], res6["pending"])
    res6b = apply_of(home, text, copies, store, published(store, teams=T6, scope=S5), choose={"teams": "theirs"}, now=LATER)
    check("…theirs takes the core's text with the overlay on it", regions(store)["teams"] ==
          region("teams", "0.6", "### Teams map\n- Alpha, Beta, Delta, Eps\n- Gamma (overlay)"), regions(store)["teams"])

# ------------------------------------------------------------------ held operations
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store, ctxp = migrated(d)
    f = published(store)
    adopt(home, text, copies, store, f)
    put_overlay(home, text, store, OPS)
    apply_of(home, text, copies, store, f)
    # the core fixes scope (the ignored line is gone) and renames the team's Members heading
    S5 = region("scope", "0.5", "### Scope of work\nThe user works on Zorg App and Zorg Lite.")
    team5 = regions(store)["team"]
    base_team = cb.get_base(store, "zorg-core", cb.load_state(store, "zorg-core")["blocks"]["team"]["base_sha"])
    T5team = base_team.replace("v=0.2", "v=0.3").replace("#### Members (registry", "#### People (registry")
    f5 = published(store, scope=S5, team=T5team)
    p5 = plan_of(store, copies, f5)
    held = {b: [r["id"] for r in rs if r["state"] == "held"] for b, rs in p5["overlay"].items()}
    check("held: the ignore that no longer finds its line and the replace whose heading is gone",
          held == {"team": ["members"], "teams": [], "scope": ["only"]} and p5["questions"] == 0, p5["overlay"])
    res5 = apply_of(home, text, copies, store, f5, now=LATER)
    rg = regions(store)
    check("…apply writes the core's text where the operation is held (the core's members are back), the rest applies",
          "#### People (registry" in rg["team"] and "Bea Two ◌" in rg["team"] and "> [оверлей members" not in rg["team"]
          and rg["teams"].endswith("- Gamma (overlay)\n<!-- zorg-core:end id=teams -->") and rg["scope"] == S5, rg)
    j = journal(store)[-1]
    check("…the journal line names the held ones", j.get("overlay_held") == {"team": ["members"], "scope": ["only"]}, j)
    sec = sy.render_section(dict(sy._result(LATER, "changed", **sy._counts(res5, cb._theirs(f5)[0])), repo="zorg-core"), apply=res5)
    check("…the sync's report has a part for the held corrections", "### Оверлей чекає рішення" in sec
          and "members (team)" in sec and "/context overlay" in sec, sec)
    check("…the apply's result carries them for the question", sorted(x["id"] for rs in res5["overlay"].values() for x in rs
                                                                      if x["state"] == "held") == ["members", "only"], res5["overlay"])

# ------------------------------------------------------------------ an unreadable overlay holds what carries it
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store, ctxp = migrated(d)
    f = published(store)
    adopt(home, text, copies, store, f)
    put_overlay(home, text, store, OPS)
    apply_of(home, text, copies, store, f)
    p = ov.path_of(store.root, "zorg-core")
    open(p, "w", encoding="utf-8").write("schema: context-overlay/1\nrepo: zorg-core\nops:\n  - op: hide\n")
    T5 = region("teams", "0.5", "### Teams map\n- Alpha, Beta, Delta")
    f5 = published(store, teams=T5)
    p5 = plan_of(store, copies, f5)
    row = [r for r in p5["rows"] if r["block"] == "teams"][0]
    check("an unreadable overlay: the plan says so, the overlaid block is held, not rewritten without it",
          p5["overlay_error"] and "zorg-core.yaml" in p5["overlay_error"] and row.get("overlay_blocked") and row["sign"] == "~"
          and not any(r.get("reoverlay") for r in p5["rows"]), (p5.get("overlay_error"), row))
    res = apply_of(home, text, copies, store, f5, now=LATER)
    check("…apply holds it: your overlaid text stays, the file is untouched", "- Gamma (overlay)" in regions(store)["teams"]
          and "teams" in res["held"] and open(p, encoding="utf-8").read().endswith("op: hide\n"), (res["held"], regions(store)["teams"]))

# ------------------------------------------------------------------ the file removed: the core's text comes back
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store, ctxp = migrated(d)
    f = published(store)
    adopt(home, text, copies, store, f)
    put_overlay(home, text, store, OPS)
    apply_of(home, text, copies, store, f)
    os.remove(ov.path_of(store.root, "zorg-core"))
    p = plan_of(store, copies, f)
    res = apply_of(home, text, copies, store, f)
    check("no overlay any more: the overlaid regions go back to the core's text, no question",
          p["questions"] == 0 and regions(store)["teams"] == TEAMS and "Bea Two ◌" in regions(store)["team"]
          and "overlay_sha" not in cb.load_state(store, "zorg-core")["blocks"]["teams"], regions(store)["teams"])

# ------------------------------------------------------------------ the daily sync applies it, undo takes it back
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store, ctxp = migrated(d)
    f = published(store)
    adopt(home, text, copies, store, f)
    put_overlay(home, text, store, OPS)
    before = tree(store)
    p = plan_of(store, copies, f)
    ans = sy.decide(p, cb._theirs(f)[0])
    res = apply_of(home, text, copies, store, f, op="provider-sync", hold=ans["hold"])
    check("the sync's answers hold nothing an overlay rewrites; the pass writes it", ans["hold"] == [] and res["changed"]
          and "- Gamma (overlay)" in regions(store)["teams"], ans)
    code, out = ctx(home, ctxp, "undo")
    after = tree(store)
    check("ctx undo: the records, the state and the overlay file as before the pass",
          code == 0 and {k: v for k, v in after.items() if k.startswith(("records", ".state/blocks", "overlays"))}
          == {k: v for k, v in before.items() if k.startswith(("records", ".state/blocks", "overlays"))}, out[-600:])

# ------------------------------------------------------------------ review v3.23.0 tasks 1–2
def overlaid_store(d):
    home, text, copies, store, ctxp = migrated(d)
    f = published(store)
    adopt(home, text, copies, store, f)
    put_overlay(home, text, store, OPS)
    apply_of(home, text, copies, store, f)
    return home, text, copies, store, ctxp, f


def edit_teams(store, copies, home, text, old, new):
    rec = [r for r in store.load() if "zorg-core:begin id=teams" in r["body"]][0]
    store.write(dict(rec, body=rec["body"].replace(old, new)))
    with guard(home, text):
        co.apply_sync(store, co.plan_sync(store, copies), copies, home, None, "", NOW)


with tempfile.TemporaryDirectory() as d:                          # I2: you take the overlay's line out by hand
    home, text, copies, store, ctxp, f = overlaid_store(d)
    edit_teams(store, copies, home, text, "- Alpha, Beta\n- Gamma (overlay)", "- Alpha, Beta")
    p = plan_of(store, copies, f)
    row = [r for r in p["rows"] if r["block"] == "teams"][0]
    check("a hand revert to the core's text: '=' (it is the core's text) with the note, not laid again",
          row["sign"] == "=" and not row.get("reoverlay")
          and "оверлей не накладено" in row["note"] and p["changes"] == 0, (row["sign"], row.get("reoverlay"), row["note"]))
    apply_of(home, text, copies, store, f)
    check("…apply leaves it as you wrote it", regions(store)["teams"] == TEAMS, regions(store)["teams"])
    rv = cb.reoverlay(store, copies, home, REPO, NOW, ov.load(store.root, "zorg-core")["ops"])
    check("…and ctx overlay plan calls it yours too", [r["state"] for r in rv["rows"] if r["block"] == "teams"] == ["edited"], rv["rows"])
    T5 = region("teams", "0.5", "### Teams map\n- Alpha, Beta, Delta")
    p5 = plan_of(store, copies, published(store, teams=T5))
    check("…a core release then asks (⚠), it does not overwrite your revert",
          [r["sign"] for r in p5["rows"] if r["block"] == "teams"] == ["⚠"], [(r["block"], r["sign"]) for r in p5["rows"]])
    res = apply_of(home, text, copies, store, published(store, teams=T5), choose={"teams": "both"})
    check("both: one region with the core's text and yours, no overlay inside it", "- Gamma (overlay)" not in regions(store)["teams"]
          and "<!-- ctx:both theirs -->" in regions(store)["teams"], regions(store)["teams"])
    j = journal(store)[-1]
    check("the journal names no overlay applied to the block kept as yours", "teams" not in (j.get("overlay") or {}), j)

with tempfile.TemporaryDirectory() as d:                          # M3: rm after a hand revert forgets the overlay
    home, text, copies, store, ctxp, f = overlaid_store(d)
    edit_teams(store, copies, home, text, "- Alpha, Beta\n- Gamma (overlay)", "- Alpha, Beta")
    doc = ov.load(store.root, "zorg-core")
    doc["ops"] = [o for o in doc["ops"] if o["id"] != "gamma"]
    with guard(home, text):
        res = cb.reoverlay(store, copies, home, REPO, NOW, doc["ops"], doc=doc, apply=True, action="rm", what="gamma")
    check("rm of the operation of a reverted region: the state forgets what the overlay wrote",
          "overlay_sha" not in cb.load_state(store, "zorg-core")["blocks"]["teams"], cb.load_state(store, "zorg-core")["blocks"]["teams"])
    T5 = region("teams", "0.5", "### Teams map\n- Alpha, Beta, Delta")
    check("…and a core release is '~' again, no question", [r["sign"] for r in plan_of(store, copies, published(store, teams=T5))["rows"]
                                                           if r["block"] == "teams"] == ["~"], "")

with tempfile.TemporaryDirectory() as d:                          # M5: no alias → the records are not loaded
    home, text, copies, store, ctxp = migrated(d)
    put_overlay(home, text, store, OPS)
    real, calls = cs.Store.load, []
    cs.Store.load = lambda self: calls.append(1) or real(self)
    try:
        got = ov.store_aliases(store.root, [{"id": "zorg-core", "namespace": NS}])
    finally:
        cs.Store.load = real
    check("store_aliases with no alias operation does not load the records", got == [] and calls == [], (got, calls))

with tempfile.TemporaryDirectory() as d:                          # a new block of the core gets the overlay; − has no note
    home, text, copies, store, ctxp, f = overlaid_store(d)
    put_overlay(home, text, store, OPS + [op("okr", "okr", "", "append", value=["- mine"])])
    OKR = region("okr", "0.1", "### OKR\n- grow")
    f2 = dict(published(store), blocks={"scope": SCOPE, "okr": OKR})
    p2 = plan_of(store, copies, f2)
    signs = {r["block"]: (r["sign"], r["note"]) for r in p2["rows"]}
    check("a block the core removed: '−' with no word about your edits", signs["teams"][0] == "−"
          and "твої правки" not in signs["teams"][1], signs)
    with guard(home, text):
        res = cb.apply(store, copies, home, REPO, f2, {}, ["okr"], NOW)
    check("a new block (+, --add) is written with the overlay on it", regions(store).get("okr") ==
          region("okr", "0.1", "### OKR\n- grow\n- mine") and "teams" not in regions(store), regions(store))
    check("…its state remembers the overlay", cb.load_state(store, "zorg-core")["blocks"]["okr"].get("overlay_sha"), "")

with tempfile.TemporaryDirectory() as d:                          # M1: a pending block is not «applied» in the journal
    home, text, copies, store, ctxp, f = overlaid_store(d)
    edit_teams(store, copies, home, text, "- Gamma (overlay)", "- Gamma (overlay)\n- mine")
    S5 = region("scope", "0.5", "### Scope of work\nThe user works on Zorg App only, and Lite.")
    T5 = region("teams", "0.5", "### Teams map\n- Alpha, Beta, Delta")
    res = apply_of(home, text, copies, store, published(store, scope=S5, teams=T5))
    j = journal(store)[-1]
    check("a pending ⚠ block is in no overlay key of the journal", res["pending"] == ["teams"] and "teams" not in (j.get("overlay") or {})
          and "teams" not in (j.get("overlay_held") or {}) and j.get("overlay", {}).get("scope") == ["only"], j)

with tempfile.TemporaryDirectory() as d:                          # M5: a lagging source holds the overlay laid again
    home, text, copies, store, ctxp, f = overlaid_store(d)
    put_overlay(home, text, store, OPS + [op("delta", "teams", "", "append", value=["- Delta (overlay)"])])
    S3 = region("scope", "0.3", "### Scope of work\nThe user works on Zorg App only.")
    lag = dict(published(store), blocks={"scope": S3, "teams": TEAMS}, version="0.3")
    p = plan_of(store, copies, lag)
    ans = sy.decide(p, cb._theirs(lag)[0])
    check("a source behind your bases: the sync holds the row the overlay would rewrite", p["lagging"] and "teams" in ans["hold"]
          and "teams" in ans["held_behind"], (p["lagging"], ans))

with tempfile.TemporaryDirectory() as d:                          # M10: restore keeps your hidden files in overlays/
    home, text, copies, store, ctxp = migrated(d)
    put_overlay(home, text, store, OPS)
    with guard(home, text):
        snap = co.snapshot(store, copies, home, "x")
    open(os.path.join(store.overlays_dir, ".zorg-core.yaml.swp"), "w").write("swap")
    with guard(home, text):
        co.restore(snap, store, copies)
    check("restore leaves a hidden file in overlays/ as it is", os.path.isfile(os.path.join(store.overlays_dir, ".zorg-core.yaml.swp"))
          and os.path.isfile(ov.path_of(store.root, "zorg-core")), os.listdir(store.overlays_dir))

# ------------------------------------------------------------------ snapshots keep the overlay file
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store, ctxp = migrated(d)
    with guard(home, text):
        snap0 = co.snapshot(store, copies, home, "before-overlay")
    put_overlay(home, text, store, OPS)
    first = open(ov.path_of(store.root, "zorg-core"), encoding="utf-8").read()
    with guard(home, text):
        snap1 = co.snapshot(store, copies, home, "with-overlay")
        put_overlay(home, text, store, OPS[:1])
        co.restore(snap1, store, copies)
    check("restore puts the overlay file back as the snapshot holds it",
          open(ov.path_of(store.root, "zorg-core"), encoding="utf-8").read() == first, "")
    with guard(home, text):
        co.restore(snap0, store, copies)
    check("restore of a snapshot taken before any overlay removes the file made since",
          not os.path.exists(ov.path_of(store.root, "zorg-core")), os.listdir(store.root))
    put_overlay(home, text, store, OPS)
    m = json.load(open(os.path.join(snap0, "manifest.json"), encoding="utf-8"))
    m.pop("overlays_known", None)                       # a snapshot of v3.22, which knew no overlay
    json.dump(m, open(os.path.join(snap0, "manifest.json"), "w", encoding="utf-8"))
    with guard(home, text):
        co.restore(snap0, store, copies)
    check("restore of a v3.22 snapshot (no overlays in it) leaves the overlay file as it is",
          os.path.exists(ov.path_of(store.root, "zorg-core")), "")

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)

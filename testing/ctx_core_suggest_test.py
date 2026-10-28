#!/usr/bin/env python3
"""TC-ctx-3234-core-suggest — the core's changes proposed into your own sections (since v3.23.0).

When `ctx provider apply` (or the daily sync) takes a block the core changed and you did not ("~"), the old base and
the new text are compared: a field line `- **Label:** old` → `- **Label:** new`, and any changed whole line of 12+
characters. Where your own text — outside every managed region — holds the same label with the old value, or the
very old line, a `REPLACE` delta goes into the inbox from the source `ctx-provider` (a ctx source, not a skill:
`propose --skill ctx-provider` is refused). Not proposed: a line inside a region, a line an operation of your overlay
touches, a proposal you rejected (the inbox remembers it), a value shorter than 3 characters. The proposals ride the
apply's journal line, so `ctx undo` takes them back with it. On the fictional "Zorg" fixture. Semantics:
references/context-protocol.md §5o. Stdlib only; run from the repo root.
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_blocks as cb  # noqa: E402
import ctx_inbox as ci  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_overlay as ov  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_store as cs  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "ctx-repos")
NOW = "2026-10-20T10:00:00+03:00"
NS = "zorg-core"
REPO = crp.normalise({"id": "zorg-core", "kind": "bundle", "paths": ["/zorg/core"], "team": "team-alpha"})
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def region(bid, v, body):
    return "<!-- %s:begin id=%s v=%s -->\n%s\n<!-- %s:end id=%s -->" % (NS, bid, v, body, NS, bid)


SCOPE = region("scope", "0.4", "### Scope of work\nThe user works on Zorg App only.\n- **Owner:** Alex One\n- **Board:** PROJ-board-7")
TEAMS = region("teams", "0.4", "### Teams map\n- Alpha, Beta")
MINE = ("- **Jira Project Key:** PROJ\n",
        "- **Jira Project Key:** PROJ\n- **Owner:** Alex One\n- **Board:** PROJ-board-7\n- **Size:** XS\n"
        "- The user works on Zorg App only.\n")
OLD_REGIONS = ("<!-- zorg-core:begin id=scope v=0.4 -->\n### Scope of work\nThe user works on Zorg App only.\n<!-- zorg-core:end id=scope -->",
               SCOPE)


def migrated(d):
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    os.makedirs(os.path.join(home, ".grow-pm"))
    os.makedirs(os.path.join(vault, "Notes", "_System"))
    text = open(os.path.join(FIX, "context.md"), encoding="utf-8", newline="").read().replace("{{VAULT}}", vault)
    for old, new in (MINE, OLD_REGIONS):
        assert old in text, old
        text = text.replace(old, new, 1)
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    for p in (ctxp, os.path.join(vault, "Notes", "_System", "local-context.md")):
        open(p, "w", encoding="utf-8", newline="").write(text)
    copies = co.copies_for(ctxp, text, home=home)
    store = cs.Store(co.store_root_for(text, home=home))
    co.migrate(ctxp, store.root, copies, home, apply=True, now=NOW)
    return home, text, copies, store, ctxp


def published(store, **blocks):
    team = cb.find_regions(store.load(), NS)[0]["team"]["text"]
    b = {"scope": SCOPE, "teams": TEAMS}
    b.update(blocks)
    return {"source": "folder", "version": "0.4", "blocks": b, "team": team, "team_source": "folder", "team_error": None,
            "error": None, "checked": NOW}


def guard(home, text):
    return cs.guard_roots(co.allowed_roots(home, text))


def apply_of(home, text, copies, store, f, **kw):
    with guard(home, text):
        return cb.apply(store, copies, home, REPO, f, {}, [], NOW, **kw)


def inbox(store):
    return ci.load(store)["entries"]


def journal(store):
    p = os.path.join(store.state_dir, "journal.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.isfile(p) else []


S5 = region("scope", "0.5", "### Scope of work\nThe user works on Zorg App and Zorg Lite.\n- **Owner:** Bea Two\n- **Board:** PROJ-board-9")

# ------------------------------------------------------------------ the pure part
props = cb.core_suggestions(SCOPE, S5, [{"id": "product.zorg-app", "body": "- **Owner:** Alex One\n- **owner:**  Alex One \n"
                                         "- **Board:** PROJ-board-7\n- The user works on Zorg App only.\n" + SCOPE}],
                            [], "zorg-core", "0.4", "0.5", "2026-10-20")
check("core_suggestions: the field with the same label and the old value (case and spaces aside), the whole line — "
      "never the lines inside the region", sorted((p["text"], p["value"]) for p in props) == sorted([
          ("- **Owner:** Alex One", "- **Owner:** Bea Two"), ("- **owner:**  Alex One", "- **owner:** Bea Two"),
          ("- **Board:** PROJ-board-7", "- **Board:** PROJ-board-9"),
          ("- The user works on Zorg App only.", "- The user works on Zorg App and Zorg Lite.")]), props)
p0 = props[0]
check("…each a REPLACE from repo:zorg-core with the versions and the block in its reason and ref",
      p0["op"] == "REPLACE" and p0["record"] == "product.zorg-app" and p0["source"]["kind"] == "repo:zorg-core"
      and "v0.4→v0.5" in p0["reason"] and "scope" in p0["source"]["ref"] and p0["source"]["at"] == "2026-10-20", p0)
props = cb.core_suggestions(SCOPE, S5, [{"id": "product.zorg-app", "body": "- **Owner:** Alex One\n- **Board:** PROJ-board-7\n"}],
                            [{"id": "o", "target": {"block": "scope", "path": "field:Owner"}, "op": "ignore", "expects": 1}],
                            "zorg-core", "0.4", "0.5", "2026-10-20")
check("core_suggestions: a field your overlay touches is not proposed", [p["text"] for p in props] == ["- **Board:** PROJ-board-7"], props)
props = cb.core_suggestions(SCOPE, S5, [{"id": "p", "body": "- **Board:** PROJ-board-7\n\n- **Board:** PROJ-board-7\n"}], [],
                            "zorg-core", "0.4", "0.5", "2026-10-20")
check("core_suggestions: the same line twice in a record is one proposal", len(props) == 1, props)
SHORT_OLD = region("scope", "0.4", "### Scope\n- **Size:** XS\nshort line")
SHORT_NEW = region("scope", "0.5", "### Scope\n- **Size:** S\nshorter line")
check("core_suggestions: a value shorter than 3 characters and a line shorter than 12 — nothing",
      cb.core_suggestions(SHORT_OLD, SHORT_NEW, [{"id": "p", "body": "- **Size:** XS\nshort line\n"}], [], "zorg-core", "0.4",
                          "0.5", "2026-10-20") == [], "")

# ------------------------------------------------------------------ through apply
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store, ctxp = migrated(d)
    f = published(store)
    with guard(home, text):
        cb.adopt(store, copies, home, REPO, f, NOW, True)
    res = apply_of(home, text, copies, store, published(store, scope=S5))
    ents = inbox(store)
    check("apply of a '~' block: the proposals are in the inbox from ctx-provider, nothing of your text changed",
          sorted(e["delta"]["text"] for e in ents) == sorted(["- **Owner:** Alex One", "- **Board:** PROJ-board-7",
                                                               "- The user works on Zorg App only."])
          and all(e["skills"] == ["ctx-provider"] for e in ents)
          and "- **Owner:** Alex One" in [r for r in store.load() if r["id"] == "product.zorg-app"][0]["body"], ents)
    j = journal(store)[-1]
    check("…the apply's journal line carries the proposals' sigs", j["op"] == "provider-apply" and sorted(j.get("proposed") or [])
          == sorted(e["sig"] for e in ents), j)
    check("…ci.who names the source «provider»", ci.who(["ctx-provider"]) == "provider", ci.who(["ctx-provider"]))
    env = {k: v for k, v in os.environ.items() if k not in ("GROW_PM_CONTEXT_PATH", "GROW_PM_PROVIDER_PATHS")}
    env["HOME"] = home
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ctx.py"), "undo", "--context", ctxp, "--home", home],
                       capture_output=True, text=True, env=env)
    check("ctx undo of the apply takes the proposals back with it", r.returncode == 0 and inbox(store) == [], r.stdout[-400:])

    # a proposal you rejected is not proposed again
    res = apply_of(home, text, copies, store, published(store, scope=S5))
    box = ci.load(store)
    n = [e["n"] for e in box["entries"] if e["delta"]["text"] == "- **Owner:** Alex One"]
    ci.reject(box, ci.pick(box, [str(x) for x in n]), "2026-10-20", "not mine")
    with guard(home, text):
        ci.save(store, box, "2026-10-20")
    S6 = region("scope", "0.6", "### Scope of work\nThe user works on Zorg App and Zorg Lite.\n- **Owner:** Bea Two\n- **Board:** PROJ-board-9\n- x")
    with guard(home, text):
        st = cb.load_state(store, "zorg-core")
        st["blocks"]["scope"]["base_sha"] = cb.put_base(store, "zorg-core", SCOPE)
        cb.save_state(store, "zorg-core", st)
    rec = [r for r in store.load() if "zorg-core:begin id=scope" in r["body"]][0]
    with guard(home, text):
        store.write(dict(rec, body=rec["body"].replace(cb.find_regions([rec], NS)[0]["scope"]["text"], SCOPE)))
        co.apply_sync(store, co.plan_sync(store, copies), copies, home, None, "", NOW)
    res = apply_of(home, text, copies, store, published(store, scope=S6))
    owners = [e for e in inbox(store) if e["delta"]["text"] == "- **Owner:** Alex One"]
    check("a rejected proposal does not come back", owners == [], [e["delta"] for e in inbox(store)])

with tempfile.TemporaryDirectory() as d:                          # an edited block (✎) proposes nothing
    home, text, copies, store, ctxp = migrated(d)
    f = published(store)
    with guard(home, text):
        cb.adopt(store, copies, home, REPO, f, NOW, True)
    res = apply_of(home, text, copies, store, published(store, teams=region("teams", "0.5", "### Teams map\n- Alpha, Beta, Gamma")))
    check("a block whose change touches nothing of yours proposes nothing", inbox(store) == [] and "proposed" not in journal(store)[-1],
          inbox(store))

# ------------------------------------------------------------------ propose refuses the source
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store, ctxp = migrated(d)
    env = {k: v for k, v in os.environ.items() if k not in ("GROW_PM_CONTEXT_PATH", "GROW_PM_PROVIDER_PATHS")}
    env["HOME"] = home
    delta = json.dumps({"op": "REPLACE", "record": "product.zorg-app", "text": "- **Owner:** Alex One", "value": "- **Owner:** X",
                        "reason": "r", "source": {"kind": "repo:zorg-core"}})
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ctx.py"), "propose", "--skill", "ctx-provider", "--delta", delta,
                        "--context", ctxp, "--home", home], capture_output=True, text=True, env=env)
    check("propose --skill ctx-provider is refused (a ctx source, not a skill)", r.returncode == 3 and "ctx-provider" in r.stdout, r.stdout[-300:])

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)

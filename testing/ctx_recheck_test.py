#!/usr/bin/env python3
"""TC-ctx-3220-recheck — `ctx validate --recheck`: records against the connectors, 0 false INVALIDATE (plan C9).

The fictional typical context, migrated. The first recheck only notices; a second one fewer than 6 days later still
only notices; one at least 6 days later turns the finding into a delta: a product whose every anchor is gone →
INVALIDATE; one anchor gone with a project of the product's name → UPDATE to its key; one anchor gone and no candidate →
«перевір сам», no delta; a member no longer active → REPLACE of their row; the provider's role → UPDATE. A connector
that did not answer, or a list that was cut, checks nothing and forgets nothing. Something fixed meanwhile is forgotten.
Writes only the inbox, `.state/recheck.json` and a journal line; the records stay as they were.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_recheck_test.py
"""
import json, os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "testing"))
from ctx_testenv import Env, read  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def observed(path, at, atl="ok", jira_complete=True, visible=None, spaces=None, inactive=("Bea Two",), role=None,
             unknown=()):
    o = {"schema": "context-observed/1", "at": at,
         "connectors": {"atlassian": atl, "provider:zorg-brain": "ok"},
         "facts": ([{"type": "profile", "field": "Role", "value": role, "from": "provider:identity"}] if role else []),
         "checks": {"jira:visible": {"complete": jira_complete, "values": visible if visible is not None else
                                     [{"key": "PROJ", "name": "Zorg App"}, {"key": "LITE2", "name": "Zorg Lite"}]},
                    "confluence:visible": {"complete": True, "values": spaces if spaces is not None else []},
                    "atlassian:people": {"complete": True, "active": ["Alex One"], "inactive": list(inactive),
                                         "unknown": list(unknown)}}}
    json.dump(o, open(path, "w", encoding="utf-8"))
    return path


def records(env):
    return {f: read(env.store, "records", f) for f in sorted(os.listdir(os.path.join(env.store, "records")))}


def inbox(env):
    p = os.path.join(env.store, ".state", "inbox.json")
    return json.load(open(p, encoding="utf-8"))["entries"] if os.path.exists(p) else []


d = tempfile.mkdtemp(prefix="ctx-recheck-")
try:
    env = Env(d)
    env.run("migrate", "--apply")
    env.run("compile")
    look = lambda at, **kw: observed(os.path.join(d, "o-%s.json" % at), at, **dict({"role": "head_of_product"}, **kw))
    obs = look("2026-10-27")
    r0 = records(env)
    rc, out, res = env.run("validate", "--recheck", "--observed", obs)
    check("1.1 the first look only notices: ZAPP (Confluence), LITE (Jira), Bea Two, the role — no delta",
          rc == 0 and len(res["noticed"]) == 4 and not res["confirmed"] and not inbox(env) and "помічено:" in out,
          (rc, out[-700:]))
    check("1.2 the records are untouched; recheck.json remembers the day", records(env) == r0
          and json.loads(read(env.store, ".state", "recheck.json"))["last_run"] == "2026-10-27")
    rc, out, res = env.run("validate", "--recheck", "--observed", look("2026-10-31"))
    check("1.3 four days later: still only noticed", not res["confirmed"] and not inbox(env), res["confirmed"])

    rc, out, res = env.run("validate", "--recheck", "--observed", observed(os.path.join(d, "x.json"), "2026-11-03", atl="absent"))
    check("2.1 atlassian did not answer: nothing checked, nothing forgotten, nothing proposed",
          rc == 0 and {"jira", "confluence", "member", "role"} <= set(res["unchecked"])
          and not inbox(env) and len(json.loads(read(env.store, ".state", "recheck.json"))["seen"]) == 4, res)
    rc, out, res = env.run("validate", "--recheck", "--observed",
                           observed(os.path.join(d, "y.json"), "2026-11-03", jira_complete=False, role="head_of_product"))
    seen = json.loads(read(env.store, ".state", "recheck.json"))["seen"]
    check("2.2 a Jira list that was cut checks no key: LITE is not confirmed, not forgotten",
          "jira" in res["unchecked"] and any("|jira|LITE" in k for k in seen)
          and not any(f["check"] == "jira" for f in res["confirmed"]), (res["unchecked"], seen))
    check("2.3 … the other checks ran: ZAPP, Bea Two and the role confirmed after 7 days",
          sorted(f["check"] for f in res["confirmed"]) == ["confluence", "member", "role"], res["confirmed"])
    ib = inbox(env)
    ops = sorted((e["delta"]["op"], e["delta"]["record"]) for e in ib)
    check("2.4 ZAPP alone gone (Jira still has PROJ): no INVALIDATE — one anchor, no candidate → «перевір сам»",
          ("INVALIDATE", "product.zorg-app") not in ops and "перевір сам: product.zorg-app" in out, (ops, out[-500:]))
    check("2.5 Bea Two → REPLACE of her row (urgent: a team); the role → UPDATE (urgent)",
          ("REPLACE", "team.alpha-a") in ops and ("UPDATE", "profile") in ops
          and all(e["urgent"] for e in ib) and all(e["skills"] == ["ctx-recheck"] for e in ib), ib)

    rc, out, res = env.run("validate", "--recheck", "--observed", look("2026-11-03"))
    ib = inbox(env)
    lite = [e for e in ib if e["delta"]["record"] == "product.zorg-lite"]
    check("3.1 the full list again: LITE gone 7 days, «Zorg Lite» is LITE2 now → UPDATE of the key, no INVALIDATE",
          lite and lite[0]["delta"]["op"] == "UPDATE" and lite[0]["delta"]["value"] == "LITE2", lite)
    check("3.2 the same findings again → merged, not doubled", len(ib) == 3, [e["delta"] for e in ib])
    check("3.3 the records still untouched (only the inbox)", records(env) == r0)

    rc, out, res = env.run("validate", "--recheck", "--observed",
                           observed(os.path.join(d, "z.json"), "2026-11-03", visible=[{"key": "LITE2", "name": "Zorg Lite"}], role="head_of_product"))
    rc, out, res = env.run("validate", "--recheck", "--observed",
                           observed(os.path.join(d, "z.json"), "2026-11-10", visible=[{"key": "LITE2", "name": "Zorg Lite"}], role="head_of_product"))
    inv = [e for e in inbox(env) if e["delta"]["op"] == "INVALIDATE"]
    check("4.1 PROJ and ZAPP both gone, each twice 6+ days apart → INVALIDATE of Zorg App", len(inv) == 1
          and inv[0]["delta"]["record"] == "product.zorg-app", [e["delta"] for e in inbox(env)])

    rc, out, res = env.run("validate", "--recheck", "--observed", look("2026-11-11", inactive=(), spaces=["ZAPP"]))
    seen = json.loads(read(env.store, ".state", "recheck.json"))["seen"]
    check("5.1 fixed meanwhile (Bea active, ZAPP back): forgotten", not any("Bea" in k or "ZAPP" in k for k in seen), seen)
    check("5.2 the records that check out are named for ctx verify", "ctx verify" in out and "team.alpha-a" in res["fine"],
          (res["fine"], out[-300:]))

    rc, out, res = env.run("health")
    check("5.3 health names the last recheck and what waits for a second look",
          "звірка з конекторами:" in out and "помічено при звірці" not in out, out[-800:])

    # review I2: the same look run again is no second look
    env4 = Env(os.path.join(d, "four"))
    env4.run("migrate", "--apply")
    one = look("2026-12-01")
    env4.run("validate", "--recheck", "--observed", one)
    rc, out, res = env4.run("validate", "--recheck", "--observed", one)
    check("7.1 the same observation (the same at) twice → nothing confirmed, whatever the clock says",
          rc == 0 and not res["confirmed"] and not inbox(env4), res["confirmed"])
    o = json.load(open(one, encoding="utf-8"))
    del o["at"]
    json.dump(o, open(os.path.join(d, "noat.json"), "w", encoding="utf-8"))
    rc, out, _ = env4.run("validate", "--recheck", "--observed", os.path.join(d, "noat.json"))
    check("7.2 an observation without at → exit 3", rc == 3 and "at" in out, out[-200:])
    # review I1, I3: keys as written by hand, a space by its title, unknown names, headers, two people in a line
    env5 = Env(os.path.join(d, "five"))
    env5.edit(env5.ctx, "- **Jira Project Key:** PROJ\n- **Confluence Space:** ZAPP",
              "- **Jira Project Key:** [proj](https://zorg.atlassian.example/browse/PROJ)\n- **Confluence Space:** Zorg App Docs")
    env5.edit(env5.ctx, "- **Jira Project Key:** LITE", "- **Jira Project Key:** lite")
    env5.edit(env5.ctx, "| Name | Role |\n|---|---|\n| Alex One | PM |\n| Bea Two | Eng |",
              "| Ім\u2019я | Роль |\n|---|---|\n| Alex One | PM |\n| Bea Two | Eng |\n| Cid Three / Dee Four | QA |\n| Ева Ф. | Des |")
    env5.run("migrate", "--apply")
    def look5(at):
        p5 = os.path.join(d, "five-%s.json" % at)
        o = {"schema": "context-observed/1", "at": at, "connectors": {"atlassian": "ok"}, "facts": [],
             "checks": {"jira:visible": {"complete": True, "values": [{"key": "PROJ", "name": "Zorg App"},
                                                                       {"key": "LITE", "name": "Zorg Lite"}]},
                        "confluence:visible": {"complete": True, "values": [{"key": "ZAD", "name": "Zorg App Docs"}]},
                        "atlassian:people": {"complete": True, "active": ["Alex One", "Bea Two"],
                                             "inactive": ["Ім\u2019я", "Cid Three / Dee Four"], "unknown": ["Ева Ф."]}}}
        json.dump(o, open(p5, "w", encoding="utf-8"), ensure_ascii=False)
        return p5
    env5.run("validate", "--recheck", "--observed", look5("2026-12-01"))
    rc, out, res = env5.run("validate", "--recheck", "--observed", look5("2026-12-09"))
    check("8.1 a key in lower case, a key inside a link, a space by its title: all found — nothing noticed",
          not any(f["check"] in ("jira", "confluence") for f in res["noticed"] + res["confirmed"]), res)
    check("8.2 the header, a line of two people and an unknown name are never a member finding; the unknown is «перевір сам»",
          not res["confirmed"] and not res["noticed"] and not inbox(env5) and "Ева Ф." in out, (res, out[-500:]))
    check("8.3 the team counts as checked; the product's key in a link and its space by title count as checked too",
          "team.alpha-a" in res["checked"] and sorted(res["checked"].get("product.zorg-app", [])) == ["confluence", "jira"],
          res["checked"])
    o = json.load(open(look5("2026-12-20"), encoding="utf-8"))
    del o["checks"]["atlassian:people"]["complete"]
    json.dump(o, open(os.path.join(d, "nocomplete.json"), "w", encoding="utf-8"), ensure_ascii=False)
    rc, out, res = env5.run("validate", "--recheck", "--observed", os.path.join(d, "nocomplete.json"))
    check("8.4 a people check that does not say it is complete checks no member", "member" in res["unchecked"], res)

    env2 = Env(os.path.join(d, "two"))
    env2.run("migrate", "--apply")
    rc, out, _ = env2.run("health")
    check("6.0 health before any recheck: «ще не звірялись»", "ще не звірялись" in out, out[-500:])
    rc, out, _ = env.run("validate", "--recheck", "--observed", look("2026-11-12", inactive=("Bea Two",)))
    rc, out, _ = env.run("health")
    check("5.4 a fresh sighting waits: health says «помічено при звірці»", "помічено при звірці:" in out, out[-600:])
    o = json.load(open(look("2026-11-20"), encoding="utf-8"))
    o["checks"]["atlassian:people"]["active"].append("Bea Two")
    json.dump(o, open(os.path.join(d, "both.json"), "w", encoding="utf-8"))
    rc, out, res = env.run("validate", "--recheck", "--observed", os.path.join(d, "both.json"))
    check("5.5 a name both active and inactive (a namesake, an old account) → active wins: no finding, forgotten",
          not any(f["check"] == "member" for f in res["noticed"] + res["confirmed"]), res)
    rc, out, _ = env2.run("validate", "--recheck")
    check("6.1 --recheck without --observed → exit 3", rc == 3, out[-200:])
    p = os.path.join(env2.store, ".state", "recheck.json")
    open(p, "w").write('{"schema": "context-recheck/1", "seen": {}, "extra": 1}')
    rc, out, _ = env2.run("validate", "--recheck", "--observed", obs)
    check("6.2 a memory of an unknown shape → exit 3, kept", rc == 3 and '"extra"' in read(p), (rc, out[-200:]))
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)

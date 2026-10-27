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


def observed(path, atl="ok", jira_complete=True, visible=None, spaces=None, inactive=("Bea Two",), role=None):
    o = {"schema": "context-observed/1", "at": "2026-10-27",
         "connectors": {"atlassian": atl, "provider:zorg-brain": "ok"},
         "facts": ([{"type": "profile", "field": "Role", "value": role, "from": "provider:identity"}] if role else []),
         "checks": {"jira:visible": {"complete": jira_complete, "values": visible if visible is not None else
                                     [{"key": "PROJ", "name": "Zorg App"}, {"key": "LITE2", "name": "Zorg Lite"}]},
                    "confluence:visible": {"complete": True, "values": spaces if spaces is not None else []},
                    "atlassian:people": {"complete": True, "active": ["Alex One"], "inactive": list(inactive)}}}
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
    obs = observed(os.path.join(d, "o.json"), role="head_of_product")
    r0 = records(env)
    rc, out, res = env.run("validate", "--recheck", "--observed", obs, "--now", "2026-10-27")
    check("1.1 the first look only notices: ZAPP (Confluence), LITE (Jira), Bea Two, the role — no delta",
          rc == 0 and len(res["noticed"]) == 4 and not res["confirmed"] and not inbox(env) and "помічено:" in out,
          (rc, out[-700:]))
    check("1.2 the records are untouched; recheck.json remembers the day", records(env) == r0
          and json.loads(read(env.store, ".state", "recheck.json"))["last_run"] == "2026-10-27")
    rc, out, res = env.run("validate", "--recheck", "--observed", obs, "--now", "2026-10-31")
    check("1.3 four days later: still only noticed", not res["confirmed"] and not inbox(env), res["confirmed"])

    rc, out, res = env.run("validate", "--recheck", "--observed", observed(os.path.join(d, "x.json"), atl="absent"),
                           "--now", "2026-11-03")
    check("2.1 atlassian did not answer: nothing checked, nothing forgotten, nothing proposed",
          rc == 0 and {"jira", "confluence", "member", "role"} <= set(res["unchecked"])
          and not inbox(env) and len(json.loads(read(env.store, ".state", "recheck.json"))["seen"]) == 4, res)
    rc, out, res = env.run("validate", "--recheck", "--observed",
                           observed(os.path.join(d, "y.json"), jira_complete=False, role="head_of_product"), "--now", "2026-11-03")
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

    rc, out, res = env.run("validate", "--recheck", "--observed", obs, "--now", "2026-11-03")
    ib = inbox(env)
    lite = [e for e in ib if e["delta"]["record"] == "product.zorg-lite"]
    check("3.1 the full list again: LITE gone 7 days, «Zorg Lite» is LITE2 now → UPDATE of the key, no INVALIDATE",
          lite and lite[0]["delta"]["op"] == "UPDATE" and lite[0]["delta"]["value"] == "LITE2", lite)
    check("3.2 the same findings again → merged, not doubled", len(ib) == 3, [e["delta"] for e in ib])
    check("3.3 the records still untouched (only the inbox)", records(env) == r0)

    rc, out, res = env.run("validate", "--recheck", "--observed",
                           observed(os.path.join(d, "z.json"), visible=[{"key": "LITE2", "name": "Zorg Lite"}], role="head_of_product"),
                           "--now", "2026-11-03")
    rc, out, res = env.run("validate", "--recheck", "--observed",
                           observed(os.path.join(d, "z.json"), visible=[{"key": "LITE2", "name": "Zorg Lite"}], role="head_of_product"),
                           "--now", "2026-11-10")
    inv = [e for e in inbox(env) if e["delta"]["op"] == "INVALIDATE"]
    check("4.1 PROJ and ZAPP both gone, each twice 6+ days apart → INVALIDATE of Zorg App", len(inv) == 1
          and inv[0]["delta"]["record"] == "product.zorg-app", [e["delta"] for e in inbox(env)])

    rc, out, res = env.run("validate", "--recheck", "--observed", observed(os.path.join(d, "f.json"), inactive=(),
                                                                          spaces=["ZAPP"], role="head_of_product"), "--now", "2026-11-11")
    seen = json.loads(read(env.store, ".state", "recheck.json"))["seen"]
    check("5.1 fixed meanwhile (Bea active, ZAPP back): forgotten", not any("Bea" in k or "ZAPP" in k for k in seen), seen)
    check("5.2 the records that check out are named for ctx verify", "ctx verify" in out and "team.alpha-a" in res["fine"],
          (res["fine"], out[-300:]))

    rc, out, res = env.run("health")
    check("5.3 health names the last recheck and what waits for a second look",
          "звірка з конекторами:" in out and ("помічено при звірці" in out or not json.loads(
              read(env.store, ".state", "recheck.json"))["seen"]), out[-800:])

    env2 = Env(os.path.join(d, "two"))
    env2.run("migrate", "--apply")
    rc, out, _ = env2.run("health")
    check("6.0 health before any recheck: «ще не звірялись»", "ще не звірялись" in out, out[-500:])
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

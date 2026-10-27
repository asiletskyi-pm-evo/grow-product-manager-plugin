#!/usr/bin/env python3
"""TC-ctx-3220-replace — the inbox's REPLACE delta and ctx's own proposers (v3.22.0, plan C10, C11).

The fictional typical context in a temp HOME + vault, migrated: a REPLACE changes one line or removes it; a line of a
field is urgent as an UPDATE of that field would be, any line of a team always; a line inside a provider's block is
refused; a line already gone is «уже так» at propose and taken quietly at accept; the shape of a REPLACE (a heading, a
marker, the same line, no value) is refused; `propose --skill ctx-recheck` is refused — those names are ctx's own;
`inbox list` names them bootstrap, recheck, consolidate; accept notes the new line's source; undo byte for byte.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_replace_test.py
"""
import json, os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
import ctx_inbox as ci_  # noqa: E402
from ctx_testenv import Env, read  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


SRC = {"kind": "derived:atlassian", "ref": "lookupJiraAccountId", "at": "2026-10-27"}


def rep(record, text, value, **kw):
    return json.dumps(dict({"op": "REPLACE", "record": record, "text": text, "value": value, "reason": "checked",
                            "source": SRC}, **kw), ensure_ascii=False)


# ------------------------------------------------------------------ 1. the shape
for name, raw in (("a heading as the new line", {"text": "- web", "value": "## Product: Evil"}),
                  ("a region marker as the old line", {"text": "<!-- ns:end x -->", "value": ""}),
                  ("the same line", {"text": "- web", "value": "- web"}),
                  ("no value", {"text": "- web"}),
                  ("two lines", {"text": "- web", "value": "- a - b"})):
    try:
        ci_.normalize(dict({"op": "REPLACE", "record": "product.zorg-app", "reason": "x", "source": SRC}, **raw))
        ok = False
    except ValueError:
        ok = True
    check("1.x a REPLACE of another shape is refused: %s" % name, ok)
d0 = ci_.normalize({"op": "REPLACE", "record": "team.alpha-a", "text": "| Bea Two | Eng |", "value": "", "reason": "x",
                    "source": SRC})
check("1.6 value \"\" removes; what() says «− …»", d0["value"] == "" and ci_.what(d0).startswith("− «"), d0)

d = tempfile.mkdtemp(prefix="ctx-replace-")
try:
    env = Env(d)
    env.edit(env.ctx, "- **Jira Team ID:** <team-uuid-2>",
             "<!-- zorg-core:begin id=team v=1 -->\n- **Jira Team ID:** <team-uuid-2>\n<!-- zorg-core:end id=team -->")
    env.run("migrate", "--apply")
    env.run("compile")
    rc, out, res = env.run("propose", "--skill", "ctx-recheck", "--delta", rep("team.alpha-a", "| Bea Two | Eng |", ""))
    check("2.1 propose --skill ctx-recheck → refused: ctx's own name", rc == 3 and "джерело самого ctx" in out,
          (rc, out[-300:]))
    rc, out, res = env.run("propose", "--skill", "product-analysis", "--delta",
                           rep("product.zorg-app", "- **Confluence Space:** ZAPP", "- **Confluence Space:** ZAP2"),
                           "--delta", rep("product.zorg-app", "- iOS", "- iOS (iPad)"),
                           "--delta", rep("team.alpha-a", "| Bea Two | Eng |", ""),
                           "--delta", rep("team.beta-b", "- **Jira Team ID:** <team-uuid-2>", ""),
                           "--delta", rep("product.zorg-app", "- Android", "- Android TV"))
    st = [r["status"] for r in res["results"]]
    check("2.2 a field's line → urgent; a plain line → not; a team's line → urgent",
          st[:3] == ["added", "added", "added"] and res["urgent"] == [1, 3], (st, res["urgent"]))
    check("2.3 a line inside a provider's block → refused (exit 4); a line not there → уже так",
          st[3] == "provider-block" and st[4] == "already" and rc == 4, st)
    rc, out, res = env.run("inbox", "list")
    check("2.4 inbox list shows «→» and «−»", "«- iOS» → «- iOS (iPad)»" in out and "− «| Bea Two | Eng |»" in out,
          out[-600:])

    # ctx's own proposer, named without the prefix
    ib = json.load(open(os.path.join(env.store, ".state", "inbox.json"), encoding="utf-8"))
    ib["entries"][0]["skills"] = ["ctx-recheck"]
    open(os.path.join(env.store, ".state", "inbox.json"), "w", encoding="utf-8").write(json.dumps(ib))
    rc, out, res = env.run("inbox", "list")
    shown = out.split("CTX_RESULT")[0]
    check("2.5 inbox list names ctx's own proposer «recheck»", " · recheck · " in shown and "ctx-recheck" not in shown,
          out[-600:])

    before = {f: read(env.store, "records", f) for f in os.listdir(os.path.join(env.store, "records"))}
    src0 = read(env.store, ".state", "inbox.json")
    env.edit(env.ctx, "- iOS\n", "- iOS (iPad)\n")          # the iOS line changed by hand before the accept
    env.run("sync")
    before = {f: read(env.store, "records", f) for f in os.listdir(os.path.join(env.store, "records"))}
    team0 = env.record("team.alpha-a")
    rc, out, res = env.run("inbox", "list")
    rc, out, res = env.run("inbox", "accept", "all", "--code", res["code"])
    check("3.0 a removed line leaves no empty line behind",
          env.record("team.alpha-a").split("\n---\n", 1)[1].count("\n") == team0.split("\n---\n", 1)[1].count("\n") - 1,
          env.record("team.alpha-a"))
    app, team = env.record("product.zorg-app"), env.record("team.alpha-a")
    check("3.1 accept: the field's line replaced, the member's row removed, the line already gone taken quietly",
          rc == 0 and "- **Confluence Space:** ZAP2" in app and "Bea Two" not in team and res["accepted"] == [1, 2, 3]
          and "- iOS (iPad)" in app and app.count("iOS") == 1, (rc, out[-400:]))
    srcs = json.load(open(os.path.join(env.store, ".state", "sources.json"), encoding="utf-8"))["records"]
    check("3.2 the new line's source is the delta's", srcs["product.zorg-app"]["field:Confluence Space"]["kind"]
          == "derived:atlassian", srcs.get("product.zorg-app"))
    rc, out, _ = env.run("undo")
    after = {f: read(env.store, "records", f) for f in os.listdir(os.path.join(env.store, "records"))}
    check("3.3 ctx undo → the records byte for byte", rc == 0 and after == before,
          [k for k in before if before[k] != after.get(k)])
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)

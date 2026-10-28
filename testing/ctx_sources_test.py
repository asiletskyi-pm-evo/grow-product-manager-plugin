#!/usr/bin/env python3
"""TC-ctx-3220-sources — scripts/ctx_sources.py, where each field came from (v3.22.0, plan C7).

The fictional typical context in a temp HOME + vault, migrated: `set`, `append`, `add` and an accepted inbox delta leave
a source per field or line in `.state/sources.json`; `ctx show <id>` prints it beside each field; a field nobody noted
falls back to its record's source; a value changed in the file (an import) no longer carries the old entry; `ctx undo`
brings the file back; a file that cannot be read stops a write and is never reset.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_sources_test.py
"""
import json, os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
import ctx_sources as csrc  # noqa: E402
from ctx_testenv import Env, read  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def sources(env):
    p = os.path.join(env.store, ".state", "sources.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


d = tempfile.mkdtemp(prefix="ctx-sources-")
try:
    env = Env(d)
    rc, out, _ = env.run("migrate", "--apply")
    env.run("compile")
    check("0.1 a store", rc == 0, out[-300:])
    rc, out, res = env.run("show", "product.zorg-app")
    check("1.1 before any write: every field falls back to its record's source (migrated)",
          rc == 0 and "Jira Project Key ← migrated (джерело запису)" in out and sources(env) is None, out[-600:])

    rc, out, _ = env.run("set", "product.zorg-app", "URL", "https://app.zorg.example", "--source", "derived:jira")
    s = sources(env)
    e = (s or {}).get("records", {}).get("product.zorg-app", {}).get("field:URL")
    check("1.2 set → field:URL noted with its kind and today", rc == 0 and e and e["kind"] == "derived:jira"
          and e["at"] and len(e["v"]) == 12, (out[-300:], s))
    rc, out, _ = env.run("set", "profile", "Language", "uk")
    e = sources(env)["records"]["profile"]["field:Language"]
    check("1.3 set without --source → user", e["kind"] == "user", e)
    rc, out, _ = env.run("append", "product.zorg-app", "--text", "- web-admin", "--under", "#### Platforms")
    s = sources(env)["records"]["product.zorg-app"]
    check("1.4 append → the line noted", rc == 0 and csrc.line_key("- web-admin") in s, (out[-300:], s))
    body = "- **Jira Project Key:** NEW\n- **Confluence Space:** NEWS\n"
    bf = os.path.join(d, "body.md")
    open(bf, "w", encoding="utf-8").write(body)
    rc, out, res = env.run("add", "product", "Zorg New", "--body-file", bf, "--source", "derived:confluence")
    s = sources(env)["records"].get(res and res.get("id") or "", {})
    check("1.5 add → every field of the new record noted",
          rc == 0 and s.get("field:Jira Project Key", {}).get("kind") == "derived:confluence"
          and "field:Confluence Space" in s, (out[-300:], s))

    rc, out, _ = env.run("show", "product.zorg-app")
    check("2.1 show <id> prints a source beside each field; a field the writes did not touch keeps «migrated», "
          "not the last writer's", "URL ← derived:jira" in out and "Jira Project Key ← migrated" in out
          and "Jira Project Key ← ctx-" not in out and "web-admin ← user" in out, out[-700:])
    rc, out, _ = env.run("show", "product.zorg-lite")
    check("2.1b a record no write touched: its fields fall back to the record's source",
          "Jira Project Key ← migrated (джерело запису)" in out, out[-400:])
    rc, out, res = env.run("show")
    check("2.2 show without ids: how many fields have their own source", "полів із власним джерелом:" in out
          and res["sources"]["own"] >= 4, (out[-400:], res and res.get("sources")))

    # an import of an edit in the file: the entry no longer applies
    env.edit(env.ctx, "- **URL:** https://app.zorg.example", "- **URL:** https://edited.zorg.example")
    rc, out, _ = env.run("sync")
    rc, out, _ = env.run("show", "product.zorg-app")
    check("2.3 a value edited in the file → the editor's (import:home); a field the edit left keeps its own",
          "URL ← import:home · " in out and "Confluence Space ← migrated" in out, out[-700:])
    env.run("set", "product.zorg-lite", "URL", "https://lite.zorg.example", "--source", "derived:tableau")
    rp = os.path.join(env.store, "records", "product.zorg-lite.md")
    text = read(rp)
    open(rp, "w", encoding="utf-8").write(text.replace("https://lite.zorg.example", "https://lite2.zorg.example"))
    env.run("sync")
    rc, out, _ = env.run("show", "product.zorg-lite")
    check("2.4 a value edited in the record's own note (Obsidian) → the old entry no longer applies",
          "URL ← derived:tableau ·" not in out and "URL ← derived:tableau (джерело запису)" in out, out[-500:])

    # undo brings the file back
    before = read(env.store, ".state", "sources.json")
    rc, out, _ = env.run("set", "profile", "Name", "Alex Uno", "--source", "derived:atlassian")
    check("3.1 another write changes sources.json", read(env.store, ".state", "sources.json") != before)
    rc, out, _ = env.run("undo")
    check("3.2 ctx undo → sources.json byte for byte as before the write",
          rc == 0 and read(env.store, ".state", "sources.json") == before, out[-300:])

    # an accepted delta notes its source
    delta = {"op": "UPDATE", "record": "product.zorg-lite", "field": "Confluence Space", "value": "LITE",
             "reason": "seen", "source": {"kind": "derived:confluence", "ref": "LITE space", "at": "2026-10-27"}}
    env.run("propose", "--skill", "product-analysis", "--delta", json.dumps(delta))
    rc, out, res = env.run("inbox", "list")
    rc, out, res = env.run("inbox", "accept", "all", "--code", res["code"])
    e = sources(env)["records"].get("product.zorg-lite", {}).get("field:Confluence Space")
    check("3.3 inbox accept → the field noted with the delta's source and ref",
          rc == 0 and e and e["kind"] == "derived:confluence" and e["ref"] == "LITE space", (out[-300:], e))

    # a file that cannot be read: refused, never reset
    p = os.path.join(env.store, ".state", "sources.json")
    good = read(p)
    open(p, "w", encoding="utf-8").write('{"schema": "context-sources/1", "records": {}, "extra": 1}')
    rc, out, _ = env.run("set", "profile", "Language", "en")
    check("4.1 sources.json of an unknown shape → the write refused (exit 3), the file kept",
          rc == 3 and "sources" in out and '"extra"' in read(p) and "- **Language:** uk" in env.record("profile"),
          (rc, out[-300:]))
    open(p, "w", encoding="utf-8").write(good)

    # review I4: the import never resets a sources file that cannot be read
    bad = '{"schema": "context-sources/1", "records": {}, "extra": 2}'
    open(p, "w", encoding="utf-8").write(bad)
    env.edit(env.ctx, "- **Jira Project Key:** LITE", "- **Jira Project Key:** LIT2")
    rc, out, _ = env.run("sync")
    check("4.2 an import over a sources file that cannot be read: the import done, the file byte for byte",
          rc == 0 and read(p) == bad and "LIT2" in env.record("product.zorg-lite"), (rc, out[-300:]))
    rc, out, res = env.run("show")
    check("4.3 show with a sources file that cannot be read: a warning, exit 0",
          rc == 0 and "джерела полів не читаються" in out, (rc, out[-300:]))
    open(p, "w", encoding="utf-8").write(good)

    # review I1: inbox accept after an import keeps what the import noted
    env2 = Env(os.path.join(d, "two"))
    env2.run("migrate", "--apply")
    env2.run("compile")
    delta = {"op": "UPDATE", "record": "product.zorg-lite", "field": "Confluence Space", "value": "LITE",
             "reason": "seen", "source": {"kind": "derived:confluence", "ref": "LITE", "at": "2026-10-27"}}
    env2.run("propose", "--skill", "product-analysis", "--delta", json.dumps(delta))
    rc, out, res = env2.run("inbox", "list")
    env2.edit(env2.ctx, "- **Confluence Space:** ZAPP", "- **Confluence Space:** ZAP2")
    rc, out, _ = env2.run("inbox", "accept", "all", "--code", res["code"])
    rc, out, _ = env2.run("show", "product.zorg-app")
    check("5.1 accept with an edit waiting: the edited field is the editor's, an untouched one keeps migrated",
          "Confluence Space ← import:home · " in out and "Jira Project Key ← migrated · " in out, out[-500:])
    rc, out, _ = env2.run("show", "product.zorg-lite")
    check("5.2 accept on a record no write touched: its other fields keep migrated (adopted)",
          "Jira Project Key ← migrated · " in out and "Confluence Space ← derived:confluence" in out, out[-500:])

    # review I2: invalidate and a rename keep the fields' sources
    rc, out, _ = env2.run("invalidate", "team.alpha-a", "--reason", "gone")
    rc, out, _ = env2.run("show", "team.alpha-a")
    check("5.3 invalidate: the fields keep migrated, not ctx-invalidate", "Jira Team ID ← migrated · " in out, out[-400:])
    env2.edit(env2.ctx, "### Team: Beta (B)\n\n- **Jira Team ID:** <team-uuid-2>",
              "### Team: Beta Two (B)\n\n- **Jira Team ID:** <team-uuid-3>")
    rc, out, _ = env2.run("sync")
    rc, out, sh = env2.run("show")
    beta = [r["id"] for r in sh["records"] if r["title"].startswith("Team: Beta")]
    rc, out, _ = env2.run("show", beta[0])
    check("5.4 a rename with an edit: the edited field is the editor's", "Jira Team ID ← import:home · " in out, out[-400:])

    # review M7: an appended text of two lines, one of them a field
    rc, out, _ = env2.run("append", "product.zorg-app", "--text", "- **Owner:** Alex One\n- extra line")
    rc, out, _ = env2.run("show", "product.zorg-app")
    check("5.5 append of two lines: the field is noted as a field, the other line as a line",
          "Owner ← user · " in out and "extra line ← user" in out, out[-500:])
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""TC-ctx-3210-inbox — scripts/ctx_inbox.py and `ctx propose` / `ctx inbox` (v3.21.0, plan C1–C6).

The fictional typical context (testing/fixtures/ctx/typical.md) in a temp HOME + vault: deltas a skill proposes —
added, merged from another skill, already so, refused (no record, a value outside its type, a provider's block, a
People skill, a malformed delta), a secret refused without its value anywhere; the urgent ones by the table, not by
the skill; no snapshot per proposal (30 proposals rotate nothing out); the list, its code, two values for one field,
a record that moved; accept and reject with the code, a field changed since, the rejected one remembered; `ctx undo`
of an accept and of a reject back byte for byte, and an undo of any change keeps what was proposed after it.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_inbox_test.py
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


SRC = {"kind": "derived:confluence", "ref": "ZAPP/Dashboards", "at": "2026-10-27"}


def delta(op, record, **kw):
    d = {"op": op, "record": record, "reason": kw.pop("reason", "seen in a run"), "source": dict(SRC)}
    d.update(kw)
    return json.dumps(d, ensure_ascii=False)


def snaps(env):
    p = os.path.join(env.home, ".grow-pm", "snapshots")
    return sorted(os.listdir(p)) if os.path.isdir(p) else []


def inbox(env):
    p = os.path.join(env.store, ".state", "inbox.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def journal(env):
    return [json.loads(l) for l in read(env.store, ".state", "journal.jsonl").splitlines() if l.strip()]


def state_bytes(env):
    out = {}
    for sub in ("records", ".state"):
        base = os.path.join(env.store, sub)
        for f in sorted(os.listdir(base)):
            if f.endswith((".md", ".json")) and f != "journal.jsonl":
                p = os.path.join(base, f)
                if os.path.isfile(p):
                    out[sub + "/" + f] = open(p, "rb").read()
    return out


DASH = "- Zorg funnel — https://tableau.zorg.example/funnel"
d = tempfile.mkdtemp(prefix="ctx-inbox-")
try:
    env = Env(d)
    rc, out, _ = env.run("propose", "--skill", "focus-advisor", "--delta", delta("ADD", "product.zorg-app", text=DASH))
    check("0.1 no store → exit 3, the Enrichment way said", rc == 3 and "Context Enrichment" in out, (rc, out[-300:]))
    env.edit(env.ctx, "- **Jira Team ID:** <team-uuid-2>",
             "<!-- zorg-core:begin id=team v=1 -->\n- **Jira Team ID:** <team-uuid-2>\n<!-- zorg-core:end id=team -->")
    rc, out, _ = env.run("migrate", "--apply")
    check("0.2 a store (with a provider's block in team.beta-b)", rc == 0, out[-400:])
    # ----------------------------------------------------------------------- 1. propose
    print("--- 1. propose")
    env.run("compile")                  # the first run after migrate compiles the mirror (its own snapshot)
    s0 = snaps(env)
    rc, out, res = env.run("propose", "--skill", "product-analysis", "--delta", delta("ADD", "product.zorg-app", text=DASH))
    check("1.1 ADD → added as №1, one line «у скриньці +1 (усього 1)»",
          rc == 0 and res["added"] == [1] and "у скриньці +1 (усього 1)" in out, (rc, out[-400:]))
    check("1.2 no snapshot for a proposal; a journal line op propose with its sig",
          snaps(env) == s0 and journal(env)[-1]["op"] == "propose" and len(journal(env)[-1]["sigs"]) == 1
          and "snapshot" not in journal(env)[-1], (snaps(env), journal(env)[-1]))
    rc, out, res = env.run("propose", "--skill", "cjm-research", "--delta", delta("ADD", "product.zorg-app", text=DASH))
    ib = inbox(env)
    check("1.3 the same delta from another skill → merged: one entry, two skills",
          rc == 0 and res["results"][0]["status"] == "merged" and len(ib["entries"]) == 1
          and ib["entries"][0]["skills"] == ["product-analysis", "cjm-research"], (out[-300:], ib))
    rc, out, res = env.run("propose", "--skill", "focus-advisor", "--delta",
                           delta("ADD", "product.zorg-app", text="- **Jira Project Key:** PROJ"))
    check("1.4 ADD of a line the record already has → already, nothing new",
          rc == 0 and res["results"][0]["status"] == "already" and "нічого нового" in out, out[-300:])
    rc, out, res = env.run("propose", "--skill", "task-creator", "--delta",
                           delta("UPDATE", "product.zorg-app", field="Jira Project Key", value="ZORG"))
    check("1.5 UPDATE of a product's key → urgent by the table, its number and the code said",
          rc == 0 and res["urgent"] == [2] and "термінові №2" in out and res["code"] in out, (out[-400:], res))
    rc, out, res = env.run("propose", "--skill", "product-research", "--delta",
                           delta("UPDATE", "product.zorg-app", field="Competitors", value="Zorg Rival"))
    check("1.6 UPDATE of another field → not urgent", rc == 0 and res["added"] == [3] and res["urgent"] == [], res)
    rc, out, res = env.run("propose", "--skill", "meeting-processor", "--delta",
                           delta("INVALIDATE", "product.zorg-lite", reason="Zorg Lite closed in Q3"),
                           "--delta", delta("NOOP", "product.zorg-app", reason=None))
    check("1.7 INVALIDATE → urgent; NOOP → counted, not kept",
          rc == 0 and res["urgent"] == [4] and res["noop"] == 1 and len(inbox(env)["entries"]) == 4, res)
    rc, out, res = env.run("propose", "--skill", "sprint-planning", "--delta",
                           delta("ADD", "team.alpha-a", text="| Zorg Dev | BE |", under="#### Members"))
    check("1.8 any change to a team → urgent", rc == 0 and res["urgent"] == [5], res)
    before = state_bytes(env)
    rc, out, res = env.run("propose", "--skill", "write-concept",
                           "--delta", delta("UPDATE", "profile", field="Role", value="wizard"),
                           "--delta", delta("ADD", "product.nope", text="- x"),
                           "--delta", json.dumps({"op": "ADD", "record": "profile", "text": "- y", "colour": "red",
                                                  "reason": "r", "source": SRC}),
                           "--delta", delta("UPDATE", "team.beta-b", field="Jira Team ID", value="<t3>"),
                           "--delta", delta("ADD", "setting.focus-focus-advisor", text="- Zorg weekly review"))
    st = [r["status"] for r in res["results"]]
    check("1.9 a value outside its type, no record, an unknown key, a provider's block → refused, each said; "
          "the good one kept; exit 3",
          rc == 3 and st == ["refused"] * 4 + ["added"] and "немає запису product.nope" in out
          and "colour" in out and "блок ядра" in out and "Role" in out, (rc, st, out[-700:]))
    secret = "sk-ant-" + "Zq7x" * 8
    rc, out, res = env.run("propose", "--skill", "requirements-creator", "--delta",
                           delta("ADD", "product.zorg-app", text="- API key " + secret))
    raw = read(env.store, ".state", "inbox.json") + read(env.store, ".state", "journal.jsonl")
    check("1.10 a secret → exit 4, the kind said, the value nowhere (output, inbox, journal)",
          rc == 4 and "секрет" in out and secret not in out and secret not in raw, (rc, out[-300:]))
    rc, out, res = env.run("propose", "--skill", "one-on-one", "--delta", delta("ADD", "profile", text="- likes mornings"))
    check("1.11 a People-contour skill → refused", rc == 3 and "People" in out, (rc, out[-300:]))
    s1 = snaps(env)
    for i in range(30):
        env.run("propose", "--skill", "focus-advisor", "--delta",
                delta("ADD", "setting.focus-focus-advisor", text="- Zorg note %d" % i))
    check("1.12 30 proposals → not one snapshot more (nothing rotated out)", snaps(env) == s1, (len(s1), len(snaps(env))))
    # ----------------------------------------------------------------------- 2. list
    print("--- 2. list")
    env.run("propose", "--skill", "product-reporter", "--delta",
            delta("UPDATE", "product.zorg-app", field="Competitors", value="Zorg Other"))
    rc, out, res = env.run("inbox", "list")
    lines = [l for l in out.splitlines() if l[:1].isdigit()]
    check("2.1 one line an entry, numbered; the code last", rc == 0 and len(lines) == len(res["entries"])
          and ("код: %s" % res["code"]) in out, out[-400:])
    clash = [l for l in lines if l.startswith(("3.", "%d." % res["entries"][-1]["n"]))]
    check("2.2 two values for one field → both marked ⚠", len(clash) == 2 and all("⚠" in l for l in clash), clash)
    check("2.3 urgent entries say so", any(l.startswith("2.") and "терміново" in l for l in lines), lines[:5])
    code = res["code"]
    rc, out, _ = env.run("set", "product.zorg-app", "Confluence Space", "ZAPP2")
    rc, out, res2 = env.run("inbox", "list")
    check("2.4 a record that changed since → «!», and the code moved", "!" in [l for l in out.splitlines()
          if l.startswith("1.")][0] and res2["code"] != code, out[-400:])
    # ----------------------------------------------------------------------- 3. accept / reject
    print("--- 3. accept and reject")
    rc, out, _ = env.run("inbox", "accept", "1", "--code", code)
    check("3.1 accept with the old code → exit 4 «скринька змінилась», nothing taken",
          rc == 4 and "скринька змінилась" in out and DASH not in env.record("product.zorg-app"), (rc, out[-300:]))
    rc, out, _ = env.run("inbox", "accept", "1")
    check("3.2 accept without --code → exit 3", rc == 3, (rc, out[-200:]))
    code = res2["code"]
    rc, out, _ = env.run("inbox", "accept", "99", "--code", code)
    check("3.3 an unknown number → exit 3", rc == 3 and "№99" in out, (rc, out[-200:]))
    before = state_bytes(env)
    n_snap = len(snaps(env))
    rc, out, res = env.run("inbox", "accept", "1", "2", "--code", code)
    rec = env.record("product.zorg-app")
    check("3.4 accept №1 №2 → both lines in the record, one snapshot, one journal line, gone from the inbox",
          rc == 0 and res["accepted"] == [1, 2] and DASH in rec and "**Jira Project Key:** ZORG" in rec
          and len(snaps(env)) == n_snap + 1 and journal(env)[-1]["op"] == "inbox-accept"
          and not [e for e in inbox(env)["entries"] if e["n"] in (1, 2)], (out[-400:], res))
    check("3.5 the record says who wrote it last: inbox:<skill>", "source: \"inbox:task-creator\"" in rec, rec[:400])
    check("3.6 the compiled copy has the line", DASH in read(env.ctx))
    rc, out, res = env.run("undo")
    check("3.7 ctx undo → the records and the inbox byte for byte", rc == 0 and state_bytes(env) == before,
          sorted(k for k in set(before) | set(state_bytes(env)) if before.get(k) != state_bytes(env).get(k)))
    rc, out, res = env.run("inbox", "list")
    env.run("set", "product.zorg-app", "Jira Project Key", "ZX")
    rc, out, res = env.run("inbox", "list")
    rc, out, res = env.run("inbox", "accept", "2", "--code", res["code"])
    check("3.8 a field you changed since → not taken, said, kept",
          rc == 0 and res["held"] == [2] and "поле змінилось" in out and any(e["n"] == 2 for e in inbox(env)["entries"])
          and "ZX" in env.record("product.zorg-app"), (out[-400:], res))
    rc, out, res = env.run("inbox", "list")
    rc, out, res = env.run("inbox", "reject", "3", "--code", res["code"], "--reason", "not a competitor")
    ib = inbox(env)
    check("3.9 reject №3 → gone, remembered", rc == 0 and not any(e["n"] == 3 for e in ib["entries"])
          and len(ib["rejected"]) == 1 and ib["rejected"][0][2] == "not a competitor", (out[-300:], ib["rejected"]))
    rc, out, res = env.run("propose", "--skill", "product-research", "--delta",
                           delta("UPDATE", "product.zorg-app", field="Competitors", value="Zorg Rival"))
    check("3.10 the rejected delta proposed again → «rejected-before», not back",
          rc == 0 and res["results"][0]["status"] == "rejected-before"
          and not any(e["delta"].get("value") == "Zorg Rival" for e in inbox(env)["entries"]), res)
    before = state_bytes(env)
    rc, out, res = env.run("inbox", "list")
    env.run("inbox", "reject", "4", "--code", res["code"])
    rc, out, _ = env.run("undo")
    check("3.11 ctx undo of a reject → the entry back, byte for byte", rc == 0 and state_bytes(env) == before)
    # ----------------------------------------------------------------------- 4. undo keeps later proposals
    print("--- 4. undo keeps what was proposed after the change it takes back")
    env.run("set", "profile", "Language", "uk")
    rc, out, res = env.run("propose", "--skill", "focus-advisor", "--delta",
                           delta("ADD", "setting.planning-planning-suite", text="- Zorg capacity 80%"))
    n_new = res["added"][0]
    rc, out, res = env.run("undo")
    ib = inbox(env)
    check("4.1 undo of a set → the set gone, the later proposal still in the inbox",
          rc == 0 and "**Language:** uk" not in env.record("profile") and any(e["n"] == n_new for e in ib["entries"]),
          (out[-300:], [e["n"] for e in ib["entries"]]))
    rc, out, res = env.run("inbox", "list")
    rc, out, res = env.run("inbox", "accept", str(n_new), "--code", res["code"])
    check("4.2 and it can be taken", rc == 0 and "Zorg capacity 80%" in env.record("setting.planning-planning-suite"),
          out[-300:])
    rc, out, res = env.run("validate")
    check("4.3 validate is happy with the store after all of it", rc == 0 and not res["errors"], res)
    p = os.path.join(env.store, ".state", "inbox.json")
    good = read(p)
    open(p, "w", encoding="utf-8").write(good.replace('"next"', '"later"'))
    rc, out, _ = env.run("propose", "--skill", "focus-advisor", "--delta", delta("ADD", "profile", text="- Zorg"))
    check("4.4 an inbox of another shape → exit 3, the file untouched (never reset)",
          rc == 3 and "inbox" in out and '"later"' in read(p), (rc, out[-300:]))
    open(p, "w", encoding="utf-8").write(good)
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\n%s — %d failure(s)" % ("GREEN" if not fails else "RED", fails))
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""TC-ctx-3220-bootstrap — `ctx bootstrap`: the table of what the connectors say, and its apply (v3.22.0, plan C5, C6).

The fictional observation file (testing/fixtures/bootstrap/observed-zorg.json) against the fictional typical context
in a temp HOME + vault, migrated: the rows (`+`, `~`, `✋ твоє`, a new record), what goes to the inbox, what agrees;
the table reads only; an apply with another code writes nothing; the apply — records, sources, the inbox, one journal
line, the compile — and `ctx undo` byte for byte; a second run with nothing new writes nothing. Then a new user from an
empty HOME: the file from the skeleton, moved into records, every field with its own source, `ctx undo` back to one
file. A local-context.md not yet in records: the table, but no apply. Nothing of a meeting or a mail anywhere.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_bootstrap_test.py
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
from ctx_testenv import CTX, Env, read  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "bootstrap", "observed-zorg.json")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def state_bytes(store, extra=()):
    out = {}
    for sub in ("records", ".state"):
        base = os.path.join(store, sub)
        for f in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            p = os.path.join(base, f)
            if os.path.isfile(p) and f != "journal.jsonl":
                out[sub + "/" + f] = open(p, "rb").read()
    for p in extra:
        out[p] = open(p, "rb").read() if os.path.exists(p) else None
    return out


def all_text(*roots):
    out = []
    for root in roots:
        for dp, _, fs in os.walk(root):
            for f in fs:
                try:
                    out.append(open(os.path.join(dp, f), encoding="utf-8").read())
                except (OSError, UnicodeDecodeError):
                    pass
    return "\n".join(out)


def run_bare(home, *args):
    env = dict(os.environ)
    env.pop("GROW_PM_CONTEXT_PATH", None)
    env.pop("GROW_PM_PROVIDER_PATHS", None)
    p = subprocess.run([sys.executable, CTX] + list(args) + ["--home", home], capture_output=True, text=True, env=env,
                       timeout=120)
    lines = [l for l in p.stdout.splitlines() if l.strip()]
    res = json.loads(lines[-1][len("CTX_RESULT "):]) if lines and lines[-1].startswith("CTX_RESULT ") else None
    return p.returncode, p.stdout + p.stderr, res


d = tempfile.mkdtemp(prefix="ctx-bootstrap-")
try:
    obs = os.path.join(d, "observed.json")
    shutil.copy(FIX, obs)
    # ======================================================================= A. an existing store
    print("--- A. an existing store")
    env = Env(d)
    rc, out, res = env.run("bootstrap", "--observed", obs)
    check("A0 a local-context.md not yet in records: the table is shown", rc == 0 and "код:" in out, out[-400:])
    code0 = res["code"]
    rc, out, _ = env.run("bootstrap", "--observed", obs, "--apply", "--code", code0)
    check("A0b … but the apply waits for the move into records (exit 3, says ctx migrate)",
          rc == 3 and "ctx migrate" in out and not os.path.isdir(env.store), (rc, out[-300:]))
    env.run("migrate", "--apply")
    env.run("compile")
    before = state_bytes(env.store, [env.ctx])
    jbefore = read(env.store, ".state", "journal.jsonl")
    rc, out, res = env.run("bootstrap", "--observed", obs)
    rows = res["rows"]
    by = {(r["type"], r.get("field") or ("new" if r["new"] else r.get("list"))): r for r in rows}
    check("A1 the table reads only: nothing changed, the journal neither",
          state_bytes(env.store, [env.ctx]) == before and read(env.store, ".state", "journal.jsonl") == jbefore)
    check("A2 profile Email: another value, yours (migrated) → ~ ✋ твоє, not taken by default",
          by[("profile", "Email")]["sign"] == "~" and by[("profile", "Email")]["mine"]
          and not by[("profile", "Email")]["default"] and "✋ твоє" in out, rows)
    check("A3 the organisation's Domain and Jira: + high, taken by default",
          by[("org", "Domain")]["sign"] == "+" and by[("org", "Jira")]["default"]
          and by[("org", "Domain")]["confidence"] == "high", rows)
    check("A4 Zorg Pay: a new record row with its key, medium",
          by[("product", "new")]["title"] == "Zorg Pay" and by[("product", "new")]["fields"][0]["value"] == "PAY"
          and "новий запис Product: Zorg Pay" in out, rows)
    check("A5 what agrees is counted, not shown (Name, Role, Zorg App's key and space, the team)",
          res["same"] == 5 and not any(r.get("field") in ("Name", "Role") for r in rows), (res["same"], rows))
    check("A6 the low facts go to the inbox (Tableau dashboard, a co-attendee); two dropped; fireflies did not answer",
          res["inbox"] == 2 and len(res["dropped"]) == 2 and "у скриньку піде: 2" in out
          and "fireflies (error: timeout)" in out, out[-500:])
    check("A7 rows are numbered profile → organisation → product; the defaults named",
          [r["n"] for r in rows] == [1, 2, 3, 4] and res["default"] == [2, 3, 4] and "візьму: 2, 3, 4" in out, rows)

    alt = os.path.join(d, "alt.json")
    o_alt = json.load(open(FIX, encoding="utf-8"))
    o_alt["facts"][4]["value"] = "https://zorg2.atlassian.example"
    o_alt["facts"][4]["title"] = "Zorg2"
    json.dump(o_alt, open(alt, "w", encoding="utf-8"), ensure_ascii=False)
    rc, out, res_alt = env.run("bootstrap", "--observed", alt)
    rc, out, _ = env.run("bootstrap", "--observed", obs, "--apply", "--code", res_alt["code"])
    check("A8a the code of another table → exit 4, nothing written", rc == 4 and res_alt["code"] != res["code"]
          and state_bytes(env.store, [env.ctx]) == before, out[-300:])
    rc, out, _ = env.run("bootstrap", "--observed", obs, "--apply", "--code", "deadbeef")
    check("A8 another code → exit 4, nothing written", rc == 4 and state_bytes(env.store, [env.ctx]) == before,
          out[-300:])
    rc, out, res2 = env.run("bootstrap", "--observed", obs, "--apply", "--code", res["code"], "--take", "9")
    check("A9 a row the table does not have → exit 3, nothing written",
          rc == 3 and state_bytes(env.store, [env.ctx]) == before, out[-300:])

    rc, out, _ = env.run("bootstrap", "--observed", obs, "--apply", "--code", res["code"], "--only", "2", "--take", "3")
    check("A9b --only with --take → exit 3", rc == 3 and "--only" in out, out[-200:])
    ibp = os.path.join(env.store, ".state", "inbox.json")
    open(ibp, "w").write('{"schema": "context-inbox/1", "next": 1, "entries": [], "rejected": [], "x": 1}')
    j1 = read(env.store, ".state", "journal.jsonl")
    rc, out, _ = env.run("bootstrap", "--observed", obs, "--apply", "--code", res["code"])
    check("A9c an inbox that cannot be read → exit 3 before anything is written",
          rc == 3 and state_bytes(env.store, [env.ctx]) == dict(before, **{".state/inbox.json": read(ibp).encode()})
          and read(env.store, ".state", "journal.jsonl") == j1, (rc, out[-300:]))
    os.remove(ibp)
    rc, out, res = env.run("bootstrap", "--observed", obs)
    env.edit(env.ctx, "## Organization: Zorg\n", "## Organization: Zorg\n\n- **Domain:** zorg.edited\n")
    rc, out, _ = env.run("bootstrap", "--observed", obs, "--apply", "--code", res["code"])
    check("A9g an edit waiting in local-context.md changes the table → exit 4 after the import, no row written",
          rc == 4 and "правки з local-context.md" in out and "- **Domain:** zorg.example" not in env.record("org.zorg"),
          (rc, out[-300:]))
    env.edit(env.ctx, "## Organization: Zorg\n\n- **Domain:** zorg.edited\n", "## Organization: Zorg\n")
    env.run("sync")
    rc, out, res = env.run("bootstrap", "--observed", obs)
    env.run("set", "org.zorg", "Domain", "zorg.other")
    rc, out, _ = env.run("bootstrap", "--observed", obs, "--apply", "--code", res["code"])
    check("A9e a record a row touches changed since the table was shown (ctx set) → exit 4, nothing written",
          rc == 4 and "таблиця змінилась" in out, (rc, out[-300:]))
    env.run("undo")
    before = state_bytes(env.store, [env.ctx])
    rc, out, res = env.run("bootstrap", "--observed", obs)
    snaps0 = sorted(os.listdir(os.path.join(env.home, ".grow-pm", "snapshots")))
    rc, out, ap = env.run("bootstrap", "--observed", obs, "--apply", "--code", res["code"])
    org = env.record("org.zorg")
    pay = [f for f in os.listdir(os.path.join(env.store, "records")) if "zorg-pay" in f]
    srcs = json.load(open(os.path.join(env.store, ".state", "sources.json"), encoding="utf-8"))["records"]
    check("A10b an absent organisation field goes right under the heading, not into «#### Tableau»",
          org.index("- **Domain:**") < org.index("#### Tableau"), org)
    check("A10 apply: the organisation's Domain and Jira written, the ✋ email not",
          rc == 0 and "- **Domain:** zorg.example" in org and "- **Jira:** https://zorg.atlassian.example" in org
          and "- **Email:** alex@personal.example" in env.record("profile"), (rc, out[-400:]))
    check("A11 apply: Zorg Pay is a record under the organisation, with its key and an empty Dashboards",
          pay and "- **Jira Project Key:** PAY" in env.record(pay[0][:-3]) and "#### Dashboards" in env.record(pay[0][:-3])
          and read(env.ctx).index("### Product: Zorg Pay") > read(env.ctx).index("## Organization: Zorg"), pay)
    check("A12 sources: Domain derived:mail:domain high; PAY derived:jira:active medium",
          srcs["org.zorg"]["field:Domain"]["kind"] == "derived:mail:domain"
          and srcs["org.zorg"]["field:Domain"]["confidence"] == "high"
          and srcs[pay[0][:-3]]["field:Jira Project Key"]["confidence"] == "medium", srcs)
    ib = json.load(open(os.path.join(env.store, ".state", "inbox.json"), encoding="utf-8"))["entries"]
    texts = sorted(e["delta"].get("text") or "" for e in ib)
    check("A13 the inbox: the dashboard as a line, the co-attendee as a row of the Members table, from ctx-bootstrap",
          len(ib) == 2 and all(e["skills"] == ["ctx-bootstrap"] for e in ib)
          and "| Cid Three | |" in texts and any("Zorg funnel" in x for x in texts)
          and any(e["delta"].get("under") == "#### Members" for e in ib), ib)
    j = [json.loads(l) for l in read(env.store, ".state", "journal.jsonl").splitlines() if l.strip()]
    check("A14 one journal line op bootstrap with the rows taken and a snapshot; one new snapshot",
          j[-1]["op"] == "bootstrap" and j[-1]["rows"] == [2, 3, 4] and j[-1].get("snapshot")
          and len(sorted(os.listdir(os.path.join(env.home, ".grow-pm", "snapshots")))) == len(snaps0) + 1, j[-1])
    text = all_text(env.store, os.path.join(env.home, ".grow-pm"))
    check("A15 nothing of a meeting or a mail anywhere: no 1-1 title, no subject",
          "звільнення" not in text and "bonus" not in text)

    rc, out, again = env.run("bootstrap", "--observed", obs)
    check("A16 a second look: only the ✋ row left", [r["field"] for r in again["rows"]] == ["Email"], again["rows"])
    j0 = read(env.store, ".state", "journal.jsonl")
    s1 = state_bytes(env.store, [env.ctx])
    rc, out, _ = env.run("bootstrap", "--observed", obs, "--apply", "--code", again["code"])
    check("A17 apply with nothing taken and nothing new for the inbox: nothing written, the journal neither",
          rc == 0 and state_bytes(env.store, [env.ctx]) == s1 and "записано: нічого" in out
          and read(env.store, ".state", "journal.jsonl") == j0, out[-300:])

    rc, out, _ = env.run("undo")
    after = state_bytes(env.store, [env.ctx])
    check("A18 ctx undo of the apply → records, sources, inbox and local-context.md byte for byte",
          rc == 0 and after == before, [k for k in set(before) | set(after) if before.get(k) != after.get(k)])
    rc, out, res = env.run("bootstrap", "--observed", obs)
    rc, out, _ = env.run("bootstrap", "--observed", obs, "--apply", "--code", res["code"], "--take", "1", "--skip", "4")
    srcs = json.load(open(os.path.join(env.store, ".state", "sources.json"), encoding="utf-8"))["records"]
    check("A19 --take 1 takes the ✋ row, --skip 4 leaves Zorg Pay",
          rc == 0 and "- **Email:** alex.one@zorg.example" in env.record("profile")
          and srcs["profile"]["field:Email"]["kind"] == "derived:atlassian:user"
          and not any("zorg-pay" in f for f in os.listdir(os.path.join(env.store, "records"))), out[-300:])
    check("A20 the profile's other fields keep migrated (adopted before the write)",
          srcs["profile"]["field:Name"]["kind"] == "migrated", srcs["profile"])

    # ======================================================================= A'. review cases
    print("--- A'. the organisation named otherwise, two values, the lines")
    env3 = Env(os.path.join(d, "three"))
    env3.edit(env3.ctx, "| Bea Two | Eng |\n", "| Bea Two | Eng |\n\nNote: contractors are not listed.\n")
    env3.edit(env3.ctx, "- **Jira Team ID:** <team-uuid-2>\n", "- **Jira Team ID:** <team-uuid-2>\n\n#### Members\n\n- Ann Leeson\n")
    env3.run("migrate", "--apply")
    env3.run("compile")
    o3 = json.load(open(FIX, encoding="utf-8"))
    o3["facts"] = [
        {"type": "org", "title": "acme", "field": "Domain", "value": "acme.example", "from": "mail:domain"},
        {"type": "org", "title": "zorg", "field": "Confluence", "value": "https://zorg.atlassian.example/wiki",
         "from": "atlassian:site"},
        {"type": "org", "title": "zorg-old", "field": "Confluence", "value": "https://zorg-old.atlassian.example/wiki",
         "from": "atlassian:site"},
        {"type": "profile", "field": "Name", "value": "Alexander One", "from": "atlassian:user"},
        {"type": "profile", "field": "Name", "value": "Alex One-Two", "from": "user"},
        {"type": "product", "title": "Zorg Application", "field": "Jira Project Key", "value": "PROJ",
         "from": "jira:active", "count": 9},
        {"type": "product", "title": "Zorg Application", "from": "jira:active", "count": 9},
        {"type": "product", "title": "Zorg Docs", "field": "Confluence Space", "value": "ZDOCS",
         "from": "confluence:active", "count": 9},
        {"type": "profile", "field": "Role", "value": "wizard", "from": "user"},
        {"type": "team", "title": "Alpha (A)", "list": "Members", "value": "Bea Tw", "from": "user"},
        {"type": "team", "title": "Gamma", "list": "Members", "value": "Ann Lee", "from": "user"},
        {"type": "team", "title": "Gamma", "from": "user"},
        {"type": "team", "title": "Beta (B)", "list": "Members", "value": "Ann Lee", "from": "user"}]
    p3 = os.path.join(d, "o3.json")
    json.dump(o3, open(p3, "w", encoding="utf-8"), ensure_ascii=False)
    rc, out, res = env3.run("bootstrap", "--observed", p3)
    shown3 = out
    by3 = {(r["type"], r.get("field") or r.get("list") or "new"): r for r in res["rows"]}
    check("R1 a fact about «acme» attaches to the one organisation but is never taken by default",
          by3[("org", "Domain")]["renamed"] and not by3[("org", "Domain")]["default"] and "≠ назва" in out, res["rows"])
    conf = [r for r in res["rows"] if r.get("field") == "Confluence"]
    name = [r for r in res["rows"] if r.get("field") == "Name"]
    check("R2b your answer outranks Atlassian: one Name row, yours, taken by default",
          len(name) == 1 and name[0]["value"] == "Alex One-Two" and name[0]["from"] == "user" and name[0]["default"], name)
    check("R2c a product named otherwise in Jira but with your key is your product: no new record",
          not any(r["new"] and r["title"] in ("Zorg Application", "Zorg Docs") for r in res["rows"]), res["rows"])
    check("R2d a role its type refuses is no row, said under the table",
          not any(r.get("field") == "Role" for r in res["rows"]) and "не той тип значення: 1" in shown3, shown3[-600:])
    check("R2 two values for Zorg's Confluence (two sites, both high) → ⚠, neither default",
          len(conf) == 2 and all(r["clash"] and not r["default"] for r in conf), conf)
    rc, out, _ = env3.run("bootstrap", "--observed", p3, "--apply", "--code", res["code"], "--take",
                          ",".join(str(r["n"]) for r in conf))
    check("R3 taking both values of one field → exit 3", rc == 3 and "два значення" in out, out[-300:])
    check("R4 «Bea Tw» is not «Bea Two», «Ann Lee» is not «Ann Leeson»: rows, not counted as there",
          sum(1 for r in res["rows"] if r.get("list") == "Members") == 2, res["rows"])
    gamma = by3.get(("team", "new"))
    check("R5 a new team carries its member line, shown in its row", gamma and gamma["lists"][0]["value"] == "Ann Lee"
          and "Members: Ann Lee" in shown3, gamma)
    rc, out, _ = env3.run("bootstrap", "--observed", p3, "--apply", "--code", res["code"])
    team = [f for f in os.listdir(os.path.join(env3.store, "records")) if "gamma" in f]
    check("R6 apply: the new team's Members subsection holds the line; Bea Tw lands inside the Alpha table",
          team and "#### Members\n\n- Ann Lee" in env3.record(team[0][:-3])
          and "| Bea Two | Eng |\n| Bea Tw | |\n\nNote:" in env3.record("team.alpha-a"),
          (out[-300:], env3.record("team.alpha-a")))
    o4 = {"schema": "context-observed/1", "at": "2026-10-27", "connectors": {"tableau": "ok"},
          "facts": [{"type": "product", "title": "Zorg Lite", "list": "Dashboards",
                     "value": "Lite funnel — https://tableau.zorg.example/lite", "from": "tableau:owned"}]}
    p4 = os.path.join(d, "o4.json")
    json.dump(o4, open(p4, "w", encoding="utf-8"), ensure_ascii=False)
    rc, out, res = env3.run("bootstrap", "--observed", p4)
    rc, out, _ = env3.run("bootstrap", "--observed", p4, "--apply", "--code", res["code"])
    j = [json.loads(l) for l in read(env3.store, ".state", "journal.jsonl").splitlines() if l.strip()]
    check("R7 only proposals: one op propose line (skill ctx-bootstrap), no snapshot",
          rc == 0 and j[-1]["op"] == "propose" and j[-1]["skill"] == "ctx-bootstrap" and "snapshot" not in j[-1], j[-1])
    rc, out, _ = env3.run("undo")
    ib = json.load(open(os.path.join(env3.store, ".state", "inbox.json"), encoding="utf-8"))["entries"]
    check("R8 ctx undo of the change before them keeps those proposals", any("Lite funnel" in (e["delta"].get("text") or "")
                                                                            for e in ib), ib)

    o5 = {"schema": "context-observed/1", "at": "2026-10-27", "connectors": {"atlassian": "ok"},
          "facts": [{"type": "org", "title": "zorg", "field": "Jira", "value": "https://zorg.atlassian.example/",
                     "from": "atlassian:site"},
                    {"type": "profile", "field": "Email", "value": "a.one@zorg.example", "from": "atlassian:user"}]}
    p5 = os.path.join(d, "o5.json")
    json.dump(o5, open(p5, "w", encoding="utf-8"), ensure_ascii=False)
    env5 = Env(os.path.join(d, "five"))
    env5.edit(env5.ctx, "## Organization: Zorg\n", "## Organization: Zorg\n\n- **Jira instance:** zorg.atlassian.example\n")
    env5.run("migrate", "--apply")
    rc, out, res = env5.run("bootstrap", "--observed", p5)
    check("R9 a field under its older name (Jira instance, Work Email) with the same value, a link or a bare host → agrees",
          rc == 0 and not res["rows"] and res["same"] == 2, (res["rows"], out[-300:]))

    # ======================================================================= B. a new user
    print("--- B. a new user, an empty HOME")
    home = os.path.join(d, "new")
    os.makedirs(home)
    nobs = os.path.join(d, "new.json")
    o = json.load(open(FIX, encoding="utf-8"))
    o["facts"] = [f for f in o["facts"] if f["type"] != "org" or f["field"] == "Jira"] + [
        {"type": "org", "title": "Zorg", "field": "Domain", "value": "zorg.example", "from": "mail:domain"},
        {"type": "profile", "field": "Language", "value": "uk", "from": "user"}]
    json.dump(o, open(nobs, "w", encoding="utf-8"), ensure_ascii=False)
    rc, out, res = run_bare(home, "bootstrap", "--observed", nobs)
    kinds = sorted((r["type"], r["new"]) for r in res["rows"])
    check("B1 the table from nothing: profile fields, a new organisation, two products, a team — all taken by default",
          rc == 0 and ("org", True) in kinds and kinds.count(("product", True)) == 2 and ("team", True) in kinds
          and all(r["default"] for r in res["rows"]) and not os.path.exists(os.path.join(home, ".grow-pm")),
          (rc, out[-600:]))
    rc, out, ap = run_bare(home, "bootstrap", "--observed", nobs, "--apply", "--code", res["code"])
    ctx = os.path.join(home, ".grow-pm", "local-context.md")
    store = os.path.join(home, ".grow-pm", "_System", "context")
    lc = read(ctx) if os.path.exists(ctx) else ""
    check("B2 apply: local-context.md from the skeleton (Basic, Judgment defaults, teams not deferred)",
          rc == 0 and "- **Mode:** basic" in lc and "- **Hypothesis first:** on" in lc
          and "## Organization: Zorg" in lc and "### Product: Zorg App" in lc and "### Team: Alpha (A)" in lc
          and "- **Language:** uk" in lc and "teams" not in lc.split("Deferred steps:")[1].split("\n")[0],
          (rc, out[-500:], lc[:900]))
    check("B3 … and in records at once, said in one line", os.path.isdir(os.path.join(store, "records"))
          and "контекст у записах" in out, out[-300:])
    rc, out, sh = run_bare(home, "show")
    check("B4 every field has its own source", sh and sh["sources"]["own"] == sh["sources"]["fields"] > 10,
          (sh or {}).get("sources"))
    ib = json.load(open(os.path.join(store, ".state", "inbox.json"), encoding="utf-8"))["entries"]
    check("B5 the co-attendee waits in the inbox for the new team", any("Cid Three" in (e["delta"].get("text") or "")
                                                                       for e in ib), ib)
    rc, out, _ = run_bare(home, "undo")
    check("B6 ctx undo → the store removed, local-context.md one file again",
          rc == 0 and not os.path.isdir(os.path.join(store, "records")) and os.path.exists(ctx), out[-300:])

    home2 = os.path.join(d, "new2")
    os.makedirs(home2)
    o2 = dict(o, facts=[f for f in o["facts"] if f["type"] != "org"])
    json.dump(o2, open(nobs, "w", encoding="utf-8"), ensure_ascii=False)
    rc, out, res = run_bare(home2, "bootstrap", "--observed", nobs)
    orph = [r["n"] for r in res["rows"] if r["orphan"]]
    check("B7 products with no organisation: marked, not taken by default", orph and "немає організації" in out
          and not any(r["default"] for r in res["rows"] if r["orphan"]), res["rows"])
    rc, out, _ = run_bare(home2, "bootstrap", "--observed", nobs, "--apply", "--code", res["code"], "--take", str(orph[0]))
    check("B8 … taken by number → exit 3, nothing written",
          rc == 3 and "організації" in out and not os.path.exists(os.path.join(home2, ".grow-pm", "local-context.md")),
          (rc, out[-300:]))
    home3 = os.path.join(d, "new3")
    os.makedirs(os.path.join(home3, ".grow-pm"))
    open(os.path.join(home3, ".grow-pm", ".ctx-last-store"), "w").write("/somewhere/_System/context\n")
    json.dump(o, open(nobs, "w", encoding="utf-8"), ensure_ascii=False)
    rc, out, res = run_bare(home3, "bootstrap", "--observed", nobs)
    rc, out, _ = run_bare(home3, "bootstrap", "--observed", nobs, "--apply", "--code", res["code"])
    check("B9 no local-context.md but a store was there → a recovery, not a new user: exit 3, nothing written",
          rc == 3 and "RM-1" in out and not os.path.exists(os.path.join(home3, ".grow-pm", "local-context.md")),
          (rc, out[-300:]))

    # ======================================================================= C. the file
    open(nobs, "w").write("{not json")
    rc, out, _ = env.run("bootstrap", "--observed", nobs)
    check("C1 an observation file that is not JSON → exit 3", rc == 3 and "observation file" in out, out[-300:])
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)

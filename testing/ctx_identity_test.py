#!/usr/bin/env python3
"""TC-ctx-3236-identity — «e-mail → team → role» against your own words, both with their source (since v3.23.0).

`provider_bundle.py --propose-only` says where the core's team and role came from (`team_from`, `role_from`).
`ctx identity check REPO --bundle F` puts each of them beside yours — the role in your profile (its source from
`.state/sources.json`), the team your registration names — two lines each, with the source of each side. Your answer is
kept in `.state/identity.json` (context-identity/1): `keep` remembers the core's value aside with the day, and the
question comes back only when the core says something else; `take` of the role writes the core's role into your
profile with the source `repo:<id>`; the team is changed by context-connect, not here. A memory that cannot be read is
never rewritten. On the fictional "Zorg" fixtures. Semantics: references/context-protocol.md §5r.
Stdlib only; run from the repo root.
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_ops as co  # noqa: E402
import ctx_store as cs  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "ctx-repos")
CORE = os.path.join(ROOT, "testing", "fixtures", "context-connect", "zorg-core")
NOW = "2026-10-20T10:00:00+03:00"
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


REG = """schema: provider-registration/2
id: zorg-core
kind: folder
paths:
  - {core}
namespace: zorg-core
blocks_file: Core/_System/context-blocks.md
team: alpha
role: pm
sync: off
"""


def env_of(home):
    env = {k: v for k, v in os.environ.items() if k not in ("GROW_PM_CONTEXT_PATH", "GROW_PM_PROVIDER_PATHS")}
    env["HOME"] = home
    return env


def bundle(home, d, email, *extra):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "provider_bundle.py"), "--core", CORE, "--out",
                        os.path.join(d, "out"), "--email", email, "--propose-only"] + list(extra),
                       capture_output=True, text=True, env=env_of(home))
    body = r.stdout[r.stdout.index("{"):]
    path = os.path.join(d, "bundle-%s.json" % email.split("@")[0])
    open(path, "w", encoding="utf-8").write(body)
    return json.loads(body), path


def setup(d):
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    os.makedirs(os.path.join(home, ".grow-pm", "providers"))
    os.makedirs(os.path.join(vault, "Notes", "_System"))
    text = open(os.path.join(FIX, "context.md"), encoding="utf-8", newline="").read().replace("{{VAULT}}", vault)
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    for p in (ctxp, os.path.join(vault, "Notes", "_System", "local-context.md")):
        open(p, "w", encoding="utf-8", newline="").write(text)
    open(os.path.join(home, ".grow-pm", "providers", "zorg-core.yaml"), "w", encoding="utf-8").write(REG.format(core=CORE))
    copies = co.copies_for(ctxp, text, home=home)
    store = cs.Store(co.store_root_for(text, home=home))
    co.migrate(ctxp, store.root, copies, home, apply=True, now=NOW)
    return home, ctxp, store


def ctx(home, ctxp, *args):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ctx.py")] + list(args) + ["--context", ctxp, "--home", home],
                       capture_output=True, text=True, env=env_of(home))
    out = r.stdout + r.stderr
    res = [l for l in out.splitlines() if l.startswith("CTX_RESULT ")]
    return r.returncode, out, json.loads(res[-1][len("CTX_RESULT "):]) if res else {}


with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = setup(d)
    j, _ = bundle(home, d, "a.one@zorg.example")
    check("propose-only says where the team and the role came from",
          j.get("team_from") == "access-bundles.json: emails" and j.get("role_from") == "People/a-one.md: «Product Manager, Alpha (lead)» → pm"
          and j.get("team_title") == "Alpha — reviews and catalog" and j.get("email") == "a.one@zorg.example", j)
    j2, _ = bundle(home, d, "a.one@zorg.example", "--team", "beta", "--role", "analyst")
    check("…a team or a role you named says so", j2.get("team_from") == "--team" and j2.get("role_from") == "--role", j2)

    jb, fb = bundle(home, d, "b.two@zorg.example")              # the core: team alpha, role analyst; you: pm
    rc, out, res = ctx(home, ctxp, "identity", "check", "zorg-core", "--bundle", fb)
    check("check: the role differs — both values with their source, the commands; the team agrees",
          rc == 0 and res.get("questions") == 1 and "роль: ядро — analyst · People/b-two.md: «Data analyst» → analyst" in out
          and "роль: ти — pm · ← migrated (джерело запису)" in out and "ctx identity keep zorg-core role" in out
          and "команда: збігається (alpha)" in out, out)
    before = open(os.path.join(store.state_dir, "journal.jsonl"), encoding="utf-8").read()
    check("…check writes nothing", not os.path.exists(os.path.join(store.state_dir, "identity.json")), "")

    rc, out, res = ctx(home, ctxp, "identity", "keep", "zorg-core", "role", "--bundle", fb)
    mem = json.load(open(os.path.join(store.state_dir, "identity.json"), encoding="utf-8"))
    check("keep: the answer with the core's value aside and the day, one journal line",
          rc == 0 and mem["schema"] == "context-identity/1" and mem["answers"]["zorg-core"]["role"]["chosen"] == "mine"
          and mem["answers"]["zorg-core"]["role"]["core"] == "analyst" and mem["answers"]["zorg-core"]["role"]["mine"] == "pm"
          and json.loads(open(os.path.join(store.state_dir, "journal.jsonl"), encoding="utf-8").read().splitlines()[-1])["op"] == "identity",
          (out, mem))
    rc, out, res = ctx(home, ctxp, "identity", "check", "zorg-core", "--bundle", fb)
    check("…the next check asks nothing and says what you decided", rc == 0 and res.get("questions") == 0
          and "роль: лишено твоє (pm); ядро каже analyst — відкладено" in out, out)
    jc = dict(jb, role="engineer", role_from="People/b-two.md: «Engineer» → engineer")
    fc = os.path.join(d, "bundle-changed.json")
    json.dump(jc, open(fc, "w", encoding="utf-8"))
    rc, out, res = ctx(home, ctxp, "identity", "check", "zorg-core", "--bundle", fc)
    check("…the core says something else: the question comes back", res.get("questions") == 1 and "ядро — engineer" in out, out)

    rc, out, res = ctx(home, ctxp, "identity", "take", "zorg-core", "role", "--bundle", fb)
    prof = [r for r in store.load() if r["type"] == "profile"][0]
    srcs = json.load(open(os.path.join(store.state_dir, "sources.json"), encoding="utf-8"))
    check("take role: your profile says the core's role, its source repo:zorg-core",
          rc == 0 and "- **Role:** analyst" in prof["body"] and any(e.get("kind") == "repo:zorg-core"
                                                                    for e in srcs["records"][prof["id"]].values()), (out, prof["body"]))
    rc, out, res = ctx(home, ctxp, "identity", "check", "zorg-core", "--bundle", fb)
    check("…then the check agrees", res.get("questions") == 0 and "роль: збігається (analyst)" in out, out)
    rc, out, res = ctx(home, ctxp, "identity", "take", "zorg-core", "team", "--bundle", fb)
    check("take team: not here — context-connect rebuilds the bundle with --team (exit 3)", rc == 3 and "context-connect" in out, out)

    jt = dict(jb, team="beta", team_title="Beta", team_from="access-bundles.json: emails")
    ft = os.path.join(d, "bundle-team.json")
    json.dump(jt, open(ft, "w", encoding="utf-8"))
    rc, out, res = ctx(home, ctxp, "identity", "check", "zorg-core", "--bundle", ft)
    check("a team the core gives your e-mail that is not your registration's: both with their source",
          "команда: ядро — beta (Beta) · access-bundles.json: emails" in out and "команда: ти — alpha · реєстрація zorg-core.yaml" in out, out)

    open(os.path.join(store.state_dir, "identity.json"), "w", encoding="utf-8").write("{broken")
    rc, out, res = ctx(home, ctxp, "identity", "keep", "zorg-core", "role", "--bundle", fb)
    check("a memory that cannot be read: refused, the file untouched", rc == 3
          and open(os.path.join(store.state_dir, "identity.json"), encoding="utf-8").read() == "{broken", out)
    open(os.path.join(store.state_dir, "identity.json"), "w", encoding="utf-8").write('{"schema": "context-identity/2", "answers": {}}')
    rc, out, res = ctx(home, ctxp, "identity", "keep", "zorg-core", "role", "--bundle", fb)
    check("a memory of another schema: refused, never rewritten", rc == 3 and "identity/2" in
          open(os.path.join(store.state_dir, "identity.json"), encoding="utf-8").read(), out)
    rc, out, res = ctx(home, ctxp, "identity", "check", "zorg-core", "--bundle", os.path.join(d, "nope.json"))
    check("a bundle file that is not there: exit 3", rc == 3, out)

import ctx_identity as cid  # noqa: E402
rows = {r["field"]: r["state"] for r in cid.compare({"team": "feedback-x", "role": "pm"},
                                                    {"team": ("team-feedback-x", "реєстрація"), "role": ("Product Manager", "user")},
                                                    cid.empty(), "zorg-core")}
check("the same team with and without team-, «Product Manager» and pm — no question", rows == {"team": "same", "role": "same"}, rows)
rows = {r["field"]: r["state"] for r in cid.compare({"team": "beta", "role": "pm"}, {"team": ("team-alpha", "r"), "role": ("legacy", "u")},
                                                    cid.empty(), "zorg-core")}
check("…another team and a role word no hint knows are asked", rows == {"team": "ask", "role": "ask"}, rows)
rows = {r["field"]: r["state"] for r in cid.compare({"team": "alpha", "role": "analyst"}, {"team": ("alpha", "r"), "role": ("Data analyst", "u")},
                                                    cid.empty(), "zorg-core")}
check("…«Data analyst» is the analyst profile", rows["role"] == "same", rows)

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)

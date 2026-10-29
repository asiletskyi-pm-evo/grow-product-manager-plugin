#!/usr/bin/env python3
"""TC-ctx-3237-provider-kit — the example provider kit and `ctx repo kit-check | add` (since v3.23.0).

The kit the plugin ships, `examples/provider-kit/zorg-core/` (fictional "Zorg"), is checked as a team would check
its own (`ctx repo kit-check`): sound, with no fault; a copy with faults (testing/fixtures/provider-kit-bad) has each
one named. Then «from nothing in one command»: a store with no repository, `ctx repo add <kit> --email E` shows the
team, the role, the registration and the blocks with a code and writes nothing; `--apply --code` writes the
registration and adds every block (`ctx read` shows them with their origin); a second version of the kit (a block
changed, `v` moved) comes in with `ctx provider apply` and no question — with an overlay of yours on it. The kit
folder is never written. Semantics: references/context-provider-protocol.md §9. Stdlib only; run from the repo root.
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_blocks as cb  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_overlay as ov  # noqa: E402
import ctx_store as cs  # noqa: E402

KIT = os.path.join(ROOT, "examples", "provider-kit", "zorg-core")
BAD = os.path.join(ROOT, "testing", "fixtures", "provider-kit-bad")
FIX = os.path.join(ROOT, "testing", "fixtures", "ctx-repos")
NOW = "2026-10-20T10:00:00+03:00"
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def tree(root):
    out = {}
    for base, _, files in os.walk(root):
        for f in files:
            p = os.path.join(base, f)
            out[os.path.relpath(p, root)] = open(p, "rb").read()
    return out


def ctx(home, ctxp, *args):
    env = {k: v for k, v in os.environ.items() if k not in ("GROW_PM_CONTEXT_PATH", "GROW_PM_PROVIDER_PATHS")}
    env["HOME"] = home
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ctx.py")] + list(args) + ["--context", ctxp, "--home", home],
                       capture_output=True, text=True, env=env)
    out = r.stdout + r.stderr
    res = [l for l in out.splitlines() if l.startswith("CTX_RESULT ")]
    return r.returncode, out, json.loads(res[-1][len("CTX_RESULT "):]) if res else {}


MINIMAL = """# Local Context — Grow Product Manager

## User Profile

- **Name:** Pat Moss
- **Role:** pm
- **Work Email:** pat.moss@zorg.example

## Organization: Zorg

### Product: Zorg App

- **Jira Project Key:** PROJ

### Team: Alpha (A)

- **Jira Team ID:** <team-uuid>
"""


def fresh(d):
    """A store of a user who has set the plugin up and connected no repository (no vault: ~/.grow-pm)."""
    home = os.path.join(d, "home")
    os.makedirs(os.path.join(home, ".grow-pm"))
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    open(ctxp, "w", encoding="utf-8").write(MINIMAL)
    copies = co.copies_for(ctxp, MINIMAL, home=home)
    store = cs.Store(co.store_root_for(MINIMAL, home=home))
    co.migrate(ctxp, store.root, copies, home, apply=True, now=NOW)
    return home, ctxp, store


with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = fresh(d)
    rc, out, res = ctx(home, ctxp, "repo", "kit-check", KIT)
    check("kit-check: the shipped example is sound", rc == 0 and res.get("problems") == [] and res.get("id") == "zorg-core", out)
    rc, out, res = ctx(home, ctxp, "repo", "kit-check", BAD)
    probs = "\n".join(res.get("problems") or [])
    check("kit-check: each fault of the faulty kit is named (exit 3)", rc == 3 and "немає roles" in probs
          and "ghost@zorg.example → команда gamma" in probs and "nobody.md" in probs and "блок teams — broken marker" in probs
          and "dev-lane.md: немає email" in probs and "немає картки команди beta" in probs, out)
    check("…the owner's personal layer is a warning, not a fault", any("особистий шар" in w for w in res.get("warnings") or []), res)

    # since v3.24.0: the .md wrappers of the manifest and the role model agree with the files beside them
    sysdir = os.path.join(KIT, "Core", "_System")
    check("the example ships both wrappers", os.path.isfile(os.path.join(sysdir, "provider-manifest.md"))
          and os.path.isfile(os.path.join(sysdir, "access-bundles.md")))
    wk = os.path.join(d, "wrapped")
    shutil.copytree(KIT, wk)
    wsys = os.path.join(wk, "Core", "_System")
    bundles = os.path.join(wsys, "access-bundles.json")
    was = open(bundles, encoding="utf-8").read()
    open(bundles, "w", encoding="utf-8").write(was.replace('"0.1"', '"0.9"', 1))
    rc, out, res = ctx(home, ctxp, "repo", "kit-check", wk)
    check("kit-check: a wrapper that differs from the file beside it is a fault",
          rc == 3 and any("access-bundles.md" in p and "не збігається" in p for p in res.get("problems") or []), out)
    shutil.copy(os.path.join(sysdir, "access-bundles.json"), bundles)
    man = os.path.join(wsys, "provider-manifest.md")
    open(man, "a", encoding="utf-8").write("\n```yaml\nid: other\n```\n")
    rc, out, res = ctx(home, ctxp, "repo", "kit-check", wk)
    check("kit-check: a broken wrapper is a fault with its reason",
          rc == 3 and any("provider-manifest.md" in p and "рівно один" in p for p in res.get("problems") or []), out)
    os.remove(os.path.join(wsys, "access-bundles.json"))
    shutil.copy(os.path.join(sysdir, "provider-manifest.md"), man)
    rc, out, res = ctx(home, ctxp, "repo", "kit-check", wk)
    check("kit-check: a wrapper with no file beside it is a fault", rc == 3
          and any("access-bundles.md" in p and "поруч немає access-bundles.json" in p for p in res.get("problems") or []), out)

    kit_before = tree(KIT)
    store_before = tree(store.root)
    rc, out, res = ctx(home, ctxp, "repo", "add", KIT, "--email", "pat.moss@zorg.example")
    reg = os.path.join(home, ".grow-pm", "providers", "zorg-core.yaml")
    check("repo add (dry run): team, role, registration, blocks, code — and nothing written",
          rc == 0 and "команда: alpha (Alpha — reviews and catalog) · access-bundles.json: emails" in out
          and "роль: pm · People/pat-moss.md: «Product Manager, Alpha (lead)» → pm" in out and reg in out
          and "+ scope" in out and "+ key-metrics" in out and "+ metric-rules" in out and res.get("code")
          and not os.path.exists(reg) and tree(store.root) == store_before, out)
    rc2, out2, _ = ctx(home, ctxp, "repo", "add", KIT, "--email", "pat.moss@zorg.example", "--apply", "--code", "deadbeef")
    check("another code: exit 4, nothing written", rc2 == 4 and not os.path.exists(reg), out2)
    rc, out, res2 = ctx(home, ctxp, "repo", "add", KIT, "--email", "pat.moss@zorg.example", "--apply", "--code", res["code"])
    check("--apply: the registration is written and every block added, one snapshot",
          rc == 0 and os.path.isfile(reg) and sorted(res2.get("blocks") or []) == sorted(res["blocks"]) and res2.get("snapshot"), out)
    regions = cb.find_regions(store.load(), "zorg-core")[0]
    check("the registration asks about Jira writes (jira_write: ask), it grants nothing", "jira_write: ask" in open(reg, encoding="utf-8").read(), "")
    check("…the blocks are in the records, the team block built for alpha", {"scope", "key-metrics", "metric-rules", "teams", "team"}
          <= set(regions) and "Pat Moss" in regions["team"]["text"], sorted(regions))
    rc, out, res = ctx(home, ctxp, "read", "--skill", "product-analysis")
    check("ctx read shows the kit's key metrics with their origin", rc == 0 and "zorg-core · v0.1" in out and "Review rate" in out, out[-800:])
    rc, out, res = ctx(home, ctxp, "repo", "add", KIT, "--email", "pat.moss@zorg.example")
    check("repo add again: already registered (exit 3)", rc == 3 and "уже зареєстровано" in out, out)
    check("the kit folder is never written", tree(KIT) == kit_before, "")

    # a second version of the kit, with an overlay of yours: one apply, no question
    kit2 = os.path.join(d, "kit2")
    shutil.copytree(KIT, kit2)
    bf = os.path.join(kit2, "Core", "_System", "context-blocks.md")
    t = open(bf, encoding="utf-8").read().replace("v=0.1", "v=0.2").replace("the iOS and Android apps.", "the iOS and Android apps, and Zorg Lite.")
    open(bf, "w", encoding="utf-8").write(t)
    rt = open(reg, encoding="utf-8").read().replace(json.dumps(os.path.abspath(KIT)), json.dumps(kit2))
    open(reg, "w", encoding="utf-8").write(rt)
    ctx(home, ctxp, "overlay", "add", "zorg-core", "--block", "teams", "--op", "append", "--value", "- Gamma (mine)", "--reason", "ours")
    rc, out, res = ctx(home, ctxp, "provider", "apply", "zorg-core")
    regions = cb.find_regions(store.load(), "zorg-core")[0]
    check("a second version of the kit: applied with no question, the overlay still on",
          rc == 0 and res.get("pending") == [] and "Zorg Lite" in regions["scope"]["text"] and "- Gamma (mine)" in regions["teams"]["text"]
          and "v=0.2" in regions["scope"]["text"], out[-800:])

with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = fresh(d)
    rc, out, res = ctx(home, ctxp, "repo", "add", KIT, "--email", "nobody@zorg.example")
    check("an e-mail the role model does not know: exit 3, the teams named", rc == 3 and "alpha" in out and "beta" in out, out)
    rc, out, res = ctx(home, ctxp, "repo", "add", BAD, "--email", "pat.moss@zorg.example")
    check("a kit with faults: exit 3, nothing written", rc == 3 and not os.path.exists(os.path.join(home, ".grow-pm", "providers")), out)

for mode in ("auto", "off"):                                    # final review I2: where the registration goes
    with tempfile.TemporaryDirectory() as d:
        home = os.path.join(d, "home"); vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(home, ".grow-pm")); os.makedirs(os.path.join(vault, "Notes", "_System"))
        text = MINIMAL + "\n## Obsidian Vaults (Optional)\n\n| # | Vault Path | Folder Name | Products | Sync Mode | Last Artifact |\n" \
            "|---|---|---|---|---|---|\n| 1 | %s | Notes | all | %s | never |\n" % (vault, mode)
        ctxp = os.path.join(home, ".grow-pm", "local-context.md")
        open(ctxp, "w", encoding="utf-8").write(text)
        copies = co.copies_for(ctxp, text, home=home)
        store = cs.Store(co.store_root_for(text, home=home))
        co.migrate(ctxp, store.root, copies, home, apply=True, now=NOW)
        rc, out, res = ctx(home, ctxp, "repo", "add", KIT, "--email", "pat.moss@zorg.example")
        ctx(home, ctxp, "repo", "add", KIT, "--email", "pat.moss@zorg.example", "--apply", "--code", res.get("code") or "x")
        rc, out, res = ctx(home, ctxp, "repo", "list")
        check("a vault with sync %s: the registration lands where repo list reads it" % mode, rc == 0 and "zorg-core" in out, out[-400:])

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)

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
import json, os, re, shutil, subprocess, sys, tempfile

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

# since v4.2.0: the kit's tools list must read as `tools_scan team` reads it — records with a name
import ctx_kit as ck  # noqa: E402
_d = tempfile.mkdtemp(prefix="kit-tools-")
try:
    _k = os.path.join(_d, "zorg-core")
    shutil.copytree(KIT, _k)
    _m, _model, _probs = ck.check(_k)
    check("the kit's tools list reads", not [p for p in _probs if "tools.yaml" in p], _probs)
    _tf = os.path.join(_k, "Core", "_System", "tools.yaml")
    with open(_tf, "w", encoding="utf-8") as f:
        f.write('tools:\n  - "Zorg Board"\n')
    _md = os.path.join(_k, "Core", "_System", "tools.md")
    with open(_md, encoding="utf-8") as f:
        _wrap = f.read()
    with open(_md, "w", encoding="utf-8") as f:
        f.write(_wrap.split("```yaml")[0] + '```yaml\ntools:\n  - "Zorg Board"\n```\n')
    _m, _model, _probs = ck.check(_k)
    check("a tools list of plain strings is a kit fault, named by its file",
          [p for p in _probs if p.startswith("Core/_System/tools.yaml")], _probs)
    _mf = os.path.join(_k, "Core", "_System", "provider-manifest.yaml")
    with open(_mf, encoding="utf-8") as f:
        _mt = f.read()
    with open(os.path.join(_d, "outside.yaml"), "w", encoding="utf-8") as f:
        f.write('tools:\n  - name: "Outside"\n')
    with open(_mf, "w", encoding="utf-8") as f:
        f.write(_mt.replace("tools_file: Core/_System/tools.yaml", "tools_file: ../../outside.yaml"))
    _m, _model, _probs = ck.check(_k)
    check("a tools_file outside the kit is a fault, said without an absolute path",
          [p for p in _probs if "поза набором" in p] and not [p for p in _probs if _d in p], _probs)
finally:
    shutil.rmtree(_d, ignore_errors=True)

# ===================================================================== v4.4.0: a core that ships no manifest
# `ctx repo add <folder> --infer | --guest | --search-only` (C1): a manifest inferred beside the registration (never in
# the core), a guest whose e-mail the role model does not know, a core folder registered for search only. The core
# is only read; search in it leaves the owner's personal layer out (Review Focus 1).
import ctx_infer as cinf  # noqa: E402


def bare(d, name="zorg-core"):
    """The example kit without its owner's manifest (YAML and wrapper)."""
    k = os.path.join(d, name)
    shutil.copytree(KIT, k)
    for f in ("provider-manifest.yaml", "provider-manifest.md"):
        os.remove(os.path.join(k, "Core", "_System", f))
    return k


with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = fresh(d)
    core = bare(d)
    before = tree(core)
    regs = os.path.join(home, ".grow-pm", "providers")
    reg, man = os.path.join(regs, "zorg-core.yaml"), os.path.join(regs, "manifests", "zorg-core.manifest.yaml")
    rc, out, res = ctx(home, ctxp, "repo", "add", core, "--email", "ana.lyst@zorg.example")
    check("a core with no manifest, no flag: exit 3, and the error offers --infer",
          rc == 3 and "--infer" in out and not os.path.exists(regs), out[-400:])
    store_before = tree(store.root)
    rc, out, res = ctx(home, ctxp, "repo", "add", core, "--email", "ana.lyst@zorg.example", "--infer")
    check("add_infer_dry: a code, «маніфест: виведено → <providers>/manifests/zorg-core.manifest.yaml», nothing written",
          rc == 0 and res.get("code") and "маніфест: виведено → %s" % man in out and res.get("mode") == "inferred"
          and res.get("manifest") == man and not os.path.exists(regs) and tree(store.root) == store_before, out[-900:])
    check("…the team and role from the role model, the blocks of the core, the line for the core's owner (place the manifest)",
          "команда: alpha" in out and "+ scope" in out and "+ key-metrics" in out and "+ team" in out
          and "Власнику ядра" in out and "Core/_System/provider-manifest.yaml" in (res.get("owner_line") or "")
          and "внеси" not in (res.get("owner_line") or ""), out[-900:])
    rc, out, res2 = ctx(home, ctxp, "repo", "add", core, "--email", "ana.lyst@zorg.example", "--infer", "--apply",
                        "--code", res.get("code") or "x")
    text = open(reg, encoding="utf-8").read() if os.path.isfile(reg) else ""
    check("add_infer_apply: the registration (with manifest: and exclude:) and the manifest beside it, in manifests/",
          rc == 0 and os.path.isfile(man) and ("manifest: %s" % json.dumps(man)) in text and "exclude:" in text
          and sorted(os.listdir(regs)) == ["manifests", "zorg-core.yaml"]
          and open(man, encoding="utf-8").read().startswith("# ctx:inferred"), (rc, out[-600:], text))
    regions = cb.find_regions(store.load(), "zorg-core")[0]
    check("…the blocks are added, the team block built for alpha", {"scope", "key-metrics", "metric-rules", "teams", "team"}
          <= set(regions) and "Ana" in regions["team"]["text"], sorted(regions))
    rc, out, res = ctx(home, ctxp, "read", "--skill", "product-analysis")
    check("…ctx read shows them with their origin", rc == 0 and "zorg-core · v0.1" in out and "Review rate" in out, out[-600:])
    rc, out, res = ctx(home, ctxp, "provider", "plan", "zorg-core")
    check("…the next plan reads the core through the manifest beside the registration: nothing to change",
          rc == 0 and res.get("changes") == 0 and not res.get("error"), out[-600:])
    check("…and the core folder is byte for byte the same", tree(core) == before, "")

with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = fresh(d)
    core = bare(d)
    rc, out, res = ctx(home, ctxp, "repo", "add", core, "--email", "new@zorg.example", "--infer")
    check("unknown_email_hint: an e-mail the model does not know → exit 3 naming both --team and --guest",
          rc == 3 and "--team" in out and "--guest" in out, out[-400:])
    rc, out, res = ctx(home, ctxp, "repo", "add", core, "--email", "new@zorg.example", "--infer", "--guest", "--team", "alpha")
    check("…--guest with --team is an error (exit 3)", rc == 3 and "--guest" in out and "--team" in out, out[-300:])
    rc, out, res = ctx(home, ctxp, "repo", "add", core, "--email", "new@zorg.example", "--infer", "--guest")
    check("add_guest: no team, role pm, no team block in the plan, the line for the owner with this e-mail",
          rc == 0 and res.get("mode") == "guest" and res.get("team") == "" and res.get("role") == "pm"
          and not re.search(r"\+ team(?!s)", out) and "+ teams" in out and "гість" in out
          and "new@zorg.example" in (res.get("owner_line") or "")
          and "внеси" in (res.get("owner_line") or "") and "Core/_System/provider-manifest.yaml" in (res.get("owner_line") or ""),
          out[-900:])
    rc, out, res2 = ctx(home, ctxp, "repo", "add", core, "--email", "new@zorg.example", "--infer", "--guest", "--apply",
                        "--code", res.get("code") or "x")
    reg = os.path.join(home, ".grow-pm", "providers", "zorg-core.yaml")
    text = open(reg, encoding="utf-8").read() if os.path.isfile(reg) else ""
    regions = cb.find_regions(store.load(), "zorg-core")[0]
    check("…--apply: `team: \"\"`, the blocks without the team block", rc == 0 and 'team: ""' in text
          and "scope" in regions and "team" not in regions, (rc, out[-500:], sorted(regions)))


with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = fresh(d)
    rc, out, res = ctx(home, ctxp, "repo", "add", KIT, "--email", "new@zorg.example", "--guest")
    check("a guest of a core that ships its manifest: mode guest, no manifest written, the owner asked only to add the e-mail",
          rc == 0 and res.get("mode") == "guest" and res.get("manifest") == "" and "внеси" in (res.get("owner_line") or "")
          and "поклади" not in (res.get("owner_line") or ""), out[-600:])
    rc, out, res = ctx(home, ctxp, "repo", "add", KIT, "--email", "pat.moss@zorg.example", "--id", "zorg-x")
    check("--id without --infer or --search-only: exit 3 (the core's manifest gives the id)", rc == 3 and "--id" in out, out[-300:])

with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = fresh(d)
    core = bare(d)
    os.remove(os.path.join(core, "Core", "_System", "access-bundles.json"))
    os.remove(os.path.join(core, "Core", "_System", "access-bundles.md"))
    write = lambda rel, s: (os.makedirs(os.path.dirname(os.path.join(core, rel)), exist_ok=True),
                            open(os.path.join(core, rel), "w", encoding="utf-8").write(s))
    write("Core/Playbook/02 Zebrafish.md", "# Zebrafish rule\n\nEvery zebrafishword review is read twice.\n")
    write("Core/_personal/note.md", "# Mine\n\nzebrafishword in the owner's personal note.\n")
    write("Core/Meetings/m.md", "# Sync\n\nzebrafishword said in a meeting.\n")
    write("Core/Now.md", "# Now\n\nzebrafishword on the owner's mind.\n")
    write("Core/TODO — owner.md", "# TODO\n\nzebrafishword to do.\n")
    before = tree(core)
    rc, out, res = ctx(home, ctxp, "repo", "add", core, "--infer", "--email", "ana.lyst@zorg.example")
    check("no role model: --infer is refused, and the reason offers --search-only", rc == 3 and "--search-only" in out, out[-400:])
    rc, out, res = ctx(home, ctxp, "repo", "add", core, "--search-only")
    check("add_search_only (dry run): no e-mail needed, «лише пошук», a code, nothing written",
          rc == 0 and res.get("mode") == "search" and res.get("code") and "лише пошук" in out
          and not os.path.exists(os.path.join(home, ".grow-pm", "providers")), out[-600:])
    rc, out, res2 = ctx(home, ctxp, "repo", "add", core, "--search-only", "--apply", "--code", res.get("code") or "x")
    reg = os.path.join(home, ".grow-pm", "providers", "zorg-core.yaml")
    text = open(reg, encoding="utf-8").read() if os.path.isfile(reg) else ""
    check("…--apply: the registration says blocks: none, with exclude:", rc == 0 and "blocks: none" in text
          and "exclude:" in text and "manifest:" not in text, (rc, out[-400:], text))
    rc, out, res = ctx(home, ctxp, "provider", "plan")
    check("…`ctx provider plan` → «лише пошук: zorg-core»", rc == 0 and "лише пошук: zorg-core" in out, out[-400:])
    rc, out, res = ctx(home, ctxp, "search", "--q", "zebrafishword", "--json")
    hits = json.dumps(res, ensure_ascii=False)
    check("…`ctx search` finds the core's note", rc == 0 and "Zebrafish" in hits, out[-600:])
    check("search_skips_personal: _personal/, Meetings/, Now.md and TODO… of the owner are never found",
          "_personal" not in hits and "Meetings" not in hits and "Now.md" not in hits and "TODO" not in hits, hits[:1500])
    rc, out, res = ctx(home, ctxp, "index", "status")
    check("…and the index does not count them", rc == 0 and "_personal" not in out and "Meetings/m.md" not in out, out[-400:])
    check("…the core folder is byte for byte the same", tree(core) == before, "")

with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = fresh(d)
    core = bare(d)
    before = tree(core)
    rc, out, res = ctx(home, ctxp, "repo", "kit-check", core, "--infer")
    check("kit_check_infer: prints the inferred manifest and where each key came from, writes nothing",
          rc == 0 and "# ctx:inferred" in out and "blocks_file: Core/_System/context-blocks.md" in out and "з чого" in out
          and tree(core) == before and not os.path.exists(os.path.join(home, ".grow-pm", "providers")), out[-900:])
    os.makedirs(os.path.join(core, "Second", "_System"))
    open(os.path.join(core, "Second", "_System", "access-bundles.json"), "w").write("{}")
    rc, out, res = ctx(home, ctxp, "repo", "kit-check", core, "--infer")
    check("…an ambiguous layout: exit 3, both folders named", rc == 3 and "Core" in out and "Second" in out, out[-400:])
    rc, out, res = ctx(home, ctxp, "repo", "add", KIT, "--email", "pat.moss@zorg.example", "--infer")
    check("--infer on a core that ships its owner's manifest: exit 3, «без --infer»", rc == 3 and "без --infer" in out, out[-300:])

# ===================================================================== review of tasks 1–4 (v4.4.0)
import ctx_common as ccm  # noqa: E402


def put(core, rel, text):
    os.makedirs(os.path.dirname(os.path.join(core, rel)), exist_ok=True)
    open(os.path.join(core, rel), "w", encoding="utf-8").write(text)


def hits_of(home, ctxp, word):
    rc, out, res = ctx(home, ctxp, "search", "--q", word, "--json")
    return [c.get("path", "") for c in (res.get("candidates") or [])]


with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = fresh(d)
    core = bare(d)
    put(core, "Core/Playbook/02 Zebrafish.md", "# Zebrafish rule\n\nzebrafishword is read twice.\n")
    put(core, "Core/_System/context/records/profile.md", "# Profile\n\nzebrafishword in the owner's own store.\n")  # I1
    for rel in ("Core/Sub/meetings/m.md", "Core/Sub/_Personal/p.md", "Core/Sub/todo.md", "Core/Sub/now.md", "Core/Sub/_Archive/a.md"):
        put(core, rel, "# Note\n\nzebrafishword, another case.\n")                                           # M3
    put(core, "Core/_personal/secret-name.md", "# x\n")                                                          # M10
    rc, out, res = ctx(home, ctxp, "repo", "add", core, "--email", "new@zorg.example", "--infer", "--guest")
    regs = os.path.join(home, ".grow-pm", "providers")
    check("M5: the line for the owner names the manifest's file, never the colleague's local path",
          rc == 0 and "zorg-core.manifest.yaml" in (res.get("owner_line") or "") and home not in (res.get("owner_line") or "")
          and d not in (res.get("owner_line") or ""), res.get("owner_line"))
    check("M10: a guest's dry run counts the owner's personal files, never names them", rc == 0 and "secret-name" not in out, out[-600:])
    check("M1: modes A–C say once that an older plugin on another host or Mac ignores exclude:", "4.4.0" in out, out[-600:])
    ctx(home, ctxp, "repo", "add", core, "--email", "new@zorg.example", "--infer", "--guest", "--apply", "--code", res.get("code") or "x")
    reg = os.path.join(regs, "zorg-core.yaml")
    text = open(reg, encoding="utf-8").read() if os.path.isfile(reg) else ""
    rr = ccm.find_registrations([], extra_dirs=[regs])
    check("I3: an inferred or guest registration writes `writable: []` — the owner's Now.md is no file of yours",
          "writable: []" in text and rr and ccm.boundary_hit(os.path.join(core, "Core", "Now.md"), rr) is not None
          and ccm.boundary_hit(os.path.join(core, "Core", "_personal", "x.md"), rr) is not None, text)
    found = hits_of(home, ctxp, "zebrafishword")
    check("I1: the owner's store in the core (<pf>/_System/context/) is never found", found and not [h for h in found if "_System/context/" in h], found)
    check("M3: meetings/, _Personal/, todo, now.md, _Archive/ in another case are never found either",
          found and not [h for h in found if "/Sub/" in h], found)
    rc2, out2, res2 = ctx(home, ctxp, "repo", "add", core, "--search-only", "--id", "zorg-search")
    check("acceptance: search only on a core that has a role model — the owner is asked for the manifest alone",
          rc2 == 0 and "provider-manifest.yaml" in (res2.get("owner_line") or "")
          and "access-bundles.json" not in (res2.get("owner_line") or ""), res2.get("owner_line"))
    rc, out, res = ctx(home, ctxp, "repo", "add", core, "--search-only")
    check("M4: another mode for a core already registered: exit 3 saying how — remove the registration file, or another --id",
          rc == 3 and "прибери" in out and reg in out and "provider plan" not in out, out[-400:])
    os.remove(reg)
    rc, out, res = ctx(home, ctxp, "repo", "add", core, "--email", "new@zorg.example", "--infer", "--guest")
    check("M4: a manifest left by a removed registration: exit 3 naming it as left over, and what to do",
          rc == 3 and "лишився" in out and "zorg-core.manifest.yaml" in out, out[-400:])

with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = fresh(d)
    core = bare(d)
    os.remove(os.path.join(core, "Core", "_System", "access-bundles.json"))
    os.remove(os.path.join(core, "Core", "_System", "access-bundles.md"))
    put(core, "Core/Playbook/02 Zebrafish.md", "# Zebrafish rule\n\nzebrafishword is read twice.\n")
    rc, out, res = ctx(home, ctxp, "repo", "add", core, "--search-only")
    check("acceptance: search only on a core with no role model — the owner is asked for both files",
          "access-bundles.json" in (res.get("owner_line") or "") and "provider-manifest.yaml" in (res.get("owner_line") or ""), res.get("owner_line"))
    ctx(home, ctxp, "repo", "add", core, "--search-only", "--apply", "--code", res.get("code") or "x")
    rc, out, res = ctx(home, ctxp, "repo", "status")
    check("M9: `repo status` of a search-only core says «лише пошук», no blocks-file error",
          rc == 0 and "лише пошук" in out and "blocks file:" not in out, out[-400:])
    cyr = bare(d, "Ядро")
    rc, out, res = ctx(home, ctxp, "repo", "add", cyr, "--search-only")
    check("M4: a folder name with no Latin letters: exit 3 asking for --id (never the id «core» for every such core)",
          rc == 3 and "--id" in out, out[-300:])

with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = fresh(d)
    kit = os.path.join(d, "kit")
    shutil.copytree(KIT, kit)
    os.remove(os.path.join(kit, "Core", "_System", "provider-manifest.md"))      # the wrapper would differ after the edit
    mpath = os.path.join(kit, "Core", "_System", "provider-manifest.yaml")
    mtext = open(mpath, encoding="utf-8").read()
    assert "  - Core/_personal/\n" in mtext
    open(mpath, "w", encoding="utf-8").write(mtext.replace("  - Core/_personal/\n", "  - Core/_personal/\n  - Core/Journal/\n"))
    put(kit, "Core/Journal/2026-11-05.md", "# Journal\n\nzebrafishword in the owner's journal.\n")                  # I2
    put(kit, "Core/_drafts/d.md", "# Draft\n\nzebrafishword in the owner's draft.\n")
    put(kit, "Core/Playbook/02 Zebrafish.md", "# Zebrafish rule\n\nzebrafishword is read twice.\n")
    rc, out, res = ctx(home, ctxp, "repo", "add", kit, "--email", "new@zorg.example", "--guest")
    ctx(home, ctxp, "repo", "add", kit, "--email", "new@zorg.example", "--guest", "--apply", "--code", res.get("code") or "x")
    found = hits_of(home, ctxp, "zebrafishword")
    check("I2: a guest of a core that ships its manifest: the owner's declared personal layer (Core/Journal/) and exclude never found",
          found and not [h for h in found if "Journal" in h or "_drafts" in h], found)

with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = fresh(d)
    kit = os.path.join(d, "kit")
    shutil.copytree(KIT, kit)
    put(kit, "Core/_drafts/d.md", "# Draft\n\nzebrafishword in the owner's draft.\n")
    put(kit, "Core/Playbook/02 Zebrafish.md", "# Zebrafish rule\n\nzebrafishword is read twice.\n")
    rc, out, res = ctx(home, ctxp, "repo", "add", kit, "--search-only")
    ctx(home, ctxp, "repo", "add", kit, "--search-only", "--apply", "--code", res.get("code") or "x")
    found = hits_of(home, ctxp, "zebrafishword")
    check("I4: search only on a core that ships its manifest keeps the owner's exclude (_drafts/ never found)",
          found and not [h for h in found if "_drafts" in h], found)
    kit2 = os.path.join(d, "kit2")
    shutil.copytree(KIT, kit2)
    sysd = os.path.join(kit2, "Core", "_System")
    os.rename(os.path.join(sysd, "provider-manifest.yaml"), os.path.join(sysd, ".provider-manifest.yaml.icloud"))
    os.remove(os.path.join(sysd, "provider-manifest.md"))
    for args in (("--email", "pat.moss@zorg.example"), ("--email", "pat.moss@zorg.example", "--infer"), ("--search-only", "--id", "zorg-two")):
        rc, out, res = ctx(home, ctxp, "repo", "add", kit2, *args)
        check("I4: the owner's manifest evicted by iCloud (%s): exit 3, «не завантажений», never --infer offered"
              % " ".join(args), rc == 3 and "не завантажений" in out and "підключи з виведеним" not in out, out[-300:])
    rc, out, res = ctx(home, ctxp, "repo", "kit-check", kit2, "--infer")
    check("I4: kit-check --infer on it: exit 3, «не завантажений»", rc == 3 and "не завантажений" in out, out[-300:])

with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = fresh(d)
    core = bare(d)
    put(core, "Core/_System/other-blocks.md", "<!-- zorg-more:begin id=x v=1 -->\nX\n<!-- zorg-more:end id=x -->\n")
    rc, out, res = ctx(home, ctxp, "repo", "kit-check", core, "--infer")
    check("M7: kit-check --infer with a fault never ends saying the owner may place the manifest",
          rc == 3 and "нічого не записано" in out and not [l for l in out.splitlines() if l.startswith("нічого не записано —")], out[-400:])

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)

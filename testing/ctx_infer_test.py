#!/usr/bin/env python3
"""TC-ctx-4400-infer — scripts/ctx_infer.py: a minimal provider manifest inferred from a core's layout (since v4.4.0).

A shared core may come without its owner's `_System/provider-manifest.yaml`. `infer(folder)` reads the layout — the
folder that holds `_System/access-bundles.json`, the one `_System/*.md` with block markers, Teams/, People/,
Playbook/, provider-templates/ — and writes a manifest that only reads: never a command (`people_resolver`), an MCP
address, the owner's filters (`deny_patterns`, `delink_*`) or a write scope; the owner's personal layer and the
conservative `INFERRED_EXCLUDE` are left out of search. An ambiguous layout is named, never guessed. The core is only
read. `ctx_kit.check(folder, manifest_path=…)` checks the manifest from outside the core as it checks the core's own,
with what only the core's owner can fix said as a warning. The fictional «Zorg» kit (examples/provider-kit/zorg-core)
with its manifest removed. Semantics: references/context-provider-protocol.md §9. Stdlib only; run from the repo root.
"""
import hashlib, json, os, re, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_common as cc  # noqa: E402
import ctx_kit as ckit  # noqa: E402
import ctx_infer as ci  # noqa: E402

KIT = os.path.join(ROOT, "examples", "provider-kit", "zorg-core")
TODAY = "2026-11-06"
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def digest(root):
    """One hash of every path and every byte under `root` — the core before and after."""
    h = hashlib.sha256()
    for base, dirs, files in sorted(os.walk(root)):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(base, f)
            h.update(os.path.relpath(p, root).encode() + b"\0" + open(p, "rb").read() + b"\0")
    return h.hexdigest()


def bare_kit(d, name="ZorgCore"):
    """A copy of the example kit without its owner's manifest (the YAML and its `.md` wrapper)."""
    core = os.path.join(d, name)
    shutil.copytree(KIT, core)
    for f in ("provider-manifest.yaml", "provider-manifest.md"):
        os.remove(os.path.join(core, "Core", "_System", f))
    return core


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)


check("INFERRED_EXCLUDE is exactly the eight expressions of the plan (C5)", ci.INFERRED_EXCLUDE == [
    r"(^|/)Meetings/", r"(^|/)Focus/", r"(^|/)_personal/", r"(^|/)TODO", r"\.xlsx$",
    r"local-context\.(existing|proposed)\.md$", r"context-merge-report\.md$", r"(^|/)_archive/"], ci.INFERRED_EXCLUDE)

with tempfile.TemporaryDirectory() as d:
    core = bare_kit(d)
    before = digest(core)
    r = ci.infer(core, today=TODAY)
    m = r.get("manifest") or {}
    check("infers_kit: ok, the plugin folder, the role model and the blocks file of the layout",
          r.get("ok") is True and m.get("plugin_folder") == "Core" and m.get("bundles_file") == "Core/_System/access-bundles.json"
          and m.get("blocks_file") == "Core/_System/context-blocks.md" and m.get("namespace") == "zorg-core"
          and m.get("inferred") is True, r)
    check("…Teams, People and Playbook when they are there; no templates folder when there is none",
          m.get("team_card_dir") == "Core/Teams" and m.get("people_dir") == "Core/People"
          and m.get("playbook") == ["Core/Playbook/01 Rules.md"] and "templates_dir" not in cc.read_yaml_subset(r["text"]), m)
    check("…id is the kebab of the folder's name, title the first heading of its README.md",
          m.get("id") == "zorgcore" and m.get("title") == "Provider kit — example «Zorg»", (m.get("id"), m.get("title")))
    check("…schema, contract, authority, mode", m.get("schema") == "provider-manifest/1" and m.get("contract") == "vault/v1"
          and m.get("authority") == "org" and m.get("mode") == "snapshot", m)
    check("…the owner's personal layer, conservatively, and the eight exclusions",
          m.get("personal_overlay") == ["Core/Now.md", "Core/TODO*", "Core/_personal/"] and m.get("exclude") == ci.INFERRED_EXCLUDE, m)
    parsed = cc.read_yaml_subset(r["text"])
    check("…the text reads back through the YAML subset to the same keys (a round trip)",
          all(parsed.get(k) == m.get(k) for k in parsed) and parsed.get("exclude") == ci.INFERRED_EXCLUDE, parsed)
    check("…every key says where it came from", all(r.get("from", {}).get(k) for k in
                                                     ("plugin_folder", "bundles_file", "blocks_file", "id", "title")), r.get("from"))
    out = os.path.join(d, "outside", "zorgcore.manifest.yaml")
    write(out, r["text"])
    warns = []
    m2, model, problems = ckit.check(core, warns, manifest_path=out)
    check("…ctx_kit.check reads the manifest from outside the core: no fault", m2 is not None and problems == [], problems)
    check("…and the same folder without it is still 'no provider manifest'", ckit.check(core)[2][:1] and
          "no provider manifest" in ckit.check(core)[2][0], ckit.check(core)[2])

    # never_infers_commands
    keys = set(parsed)
    check("never_infers_commands: no command, MCP address, owner filter, write scope or tools list",
          not keys & {"people_resolver", "mcp", "deny_patterns", "delink_targets", "delink_labels", "delink_note",
                      "dashboard_rewrites", "write_scope", "tools_file"}
          and not re.search(r"^(people_resolver|mcp|deny_patterns|tools_file|write_scope)\s*:", r["text"], re.M), sorted(keys))

    # first_line
    first = r["text"].splitlines()[0]
    check("first_line: '# ctx:inferred <date>' and where the owner may put it",
          first.startswith("# ctx:inferred %s" % TODAY) and "Core/_System/provider-manifest.yaml" in first, first)
    check("…and the owner is told to drop `inferred: true` and add their own filters first",
          "inferred: true" in r["text"].splitlines()[1] and "deny_patterns" in r["text"].splitlines()[1], r["text"][:400])

    # --id
    check("--id overrides the folder's name", ci.infer(core, rid="zorg-core", today=TODAY)["manifest"]["id"] == "zorg-core", "")
    bad = ci.infer(core, rid="Not A Kebab", today=TODAY)
    check("…an id that is not kebab-case is refused with the reason", bad["ok"] is False and "kebab" in bad["why"], bad)

    # core_untouched
    check("core_untouched: the core folder is byte for byte as it was", digest(core) == before, "")

with tempfile.TemporaryDirectory() as d:
    core = bare_kit(d, "Zorg_Core")
    check("the kebab of «Zorg_Core» is zorg-core", ci.infer(core, today=TODAY)["manifest"]["id"] == "zorg-core", "")
    os.remove(os.path.join(core, "README.md"))
    write(os.path.join(core, "README — note to Pat.md"), "# A letter, not the core's title\n")
    check("a README with a suffix is a letter, not the title: the folder's name stands in",
          ci.infer(core, today=TODAY)["manifest"]["title"] == "Zorg_Core", ci.infer(core, today=TODAY)["manifest"].get("title"))
    os.makedirs(os.path.join(core, "Core", "_System", "provider-templates"))
    check("templates_dir when <pf>/_System/provider-templates is there",
          ci.infer(core, today=TODAY)["manifest"].get("templates_dir") == "Core/_System/provider-templates", "")

    # files that carry the namespace but are no blocks file: an excluded copy of a context, a generated team block
    sysd = os.path.join(core, "Core", "_System")
    blocks = open(os.path.join(sysd, "context-blocks.md"), encoding="utf-8").read()
    write(os.path.join(sysd, "local-context.proposed.md"), "# Proposed\n\n" + blocks)
    write(os.path.join(sysd, "context-merge-report.md"), blocks)
    write(os.path.join(sysd, "team-context.md"), "<!-- zorg-core:begin id=team v=0.1 -->\n### Team: Alpha\n<!-- zorg-core:end id=team -->\n")
    r = ci.infer(core, today=TODAY)
    check("an excluded copy of a context and a file of the team block alone are no blocks file",
          r["ok"] and r["manifest"].get("blocks_file") == "Core/_System/context-blocks.md", r.get("from"))

    # two_block_files
    write(os.path.join(sysd, "more-blocks.md"), "<!-- zorg-more:begin id=x v=1 -->\nX\n<!-- zorg-more:end id=x -->\n")
    r = ci.infer(core, today=TODAY)
    check("two_block_files: no blocks_file and no namespace, and `from` says why, naming both",
          r["ok"] is True and "blocks_file" not in r["manifest"] and "namespace" not in cc.read_yaml_subset(r["text"])
          and "context-blocks.md" in r["from"].get("blocks_file", "") and "more-blocks.md" in r["from"].get("blocks_file", ""), r)
    os.remove(os.path.join(sysd, "more-blocks.md"))

    # ambiguous_folders
    write(os.path.join(core, "Second", "_System", "access-bundles.json"), "{}")
    r = ci.infer(core, today=TODAY)
    check("ambiguous_folders: two folders with a role model → not ok, both named as candidates and in the reason",
          r["ok"] is False and sorted(r["candidates"]) == ["Core", "Second"] and "Core" in r["why"] and "Second" in r["why"]
          and r["manifest"] is None, r)
    shutil.rmtree(os.path.join(core, "Second"))

    # the role model iCloud has evicted
    os.rename(os.path.join(sysd, "access-bundles.json"), os.path.join(sysd, ".access-bundles.json.icloud"))
    r = ci.infer(core, today=TODAY)
    check("a role model iCloud has evicted: not ok, «not downloaded» — never «no model»",
          r["ok"] is False and "не завантажена" in r["why"], r)
    os.remove(os.path.join(sysd, ".access-bundles.json.icloud"))

    # no_model
    r = ci.infer(core, today=TODAY)
    check("no_model: no role model → not ok, «немає моделі ролей — лише пошук»",
          r["ok"] is False and "немає моделі ролей" in r["why"] and "лише пошук" in r["why"] and r["candidates"] == [], r)

with tempfile.TemporaryDirectory() as d:
    # a core whose role model sits at its root: the plugin folder is the core itself
    core = os.path.join(d, "Flat")
    shutil.copytree(os.path.join(KIT, "Core"), core)
    for f in ("provider-manifest.yaml", "provider-manifest.md"):
        os.remove(os.path.join(core, "_System", f))
    r = ci.infer(core, today=TODAY)
    check("a role model at the root: plugin_folder '.', paths without a prefix",
          r["ok"] and r["manifest"]["plugin_folder"] == "." and r["manifest"]["bundles_file"] == "_System/access-bundles.json"
          and r["manifest"]["personal_overlay"] == ["Now.md", "TODO*", "_personal/"], r.get("manifest"))

with tempfile.TemporaryDirectory() as d:
    # what only the core's owner can fix is a warning under an inferred manifest, a fault under the owner's own
    core = bare_kit(d)
    model_path = os.path.join(core, "Core", "_System", "access-bundles.json")
    model = json.load(open(model_path, encoding="utf-8"))
    model["teams"]["alpha"]["files"].append("Core/Products/Gone page.md")
    json.dump(model, open(model_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    blocks_path = os.path.join(core, "Core", "_System", "context-blocks.md")
    open(blocks_path, "a", encoding="utf-8").write("\n<!-- zorg-core:end -->\n")
    out = os.path.join(d, "zorgcore.manifest.yaml")
    write(out, ci.infer(core, today=TODAY)["text"])
    warns = []
    _, _, problems = ckit.check(core, warns, manifest_path=out)
    check("an inferred manifest: a team's missing file and a stray marker are warnings for the owner, not faults",
          problems == [] and any("Gone page.md" in w for w in warns) and any("broken marker" in w for w in warns), (problems, warns))
    write(os.path.join(core, "Core", "_System", "provider-manifest.yaml"),
          open(os.path.join(KIT, "Core", "_System", "provider-manifest.yaml"), encoding="utf-8").read())
    _, _, problems = ckit.check(core, [])
    check("…the same faults under the owner's own manifest stay faults (kit-check as before)",
          any("Gone page.md" in p for p in problems) and any("broken marker" in p for p in problems), problems)
    os.remove(os.path.join(core, "Core", "_System", "provider-manifest.yaml"))
    open(blocks_path, "w", encoding="utf-8").write("# no blocks here\n")
    _, _, problems = ckit.check(core, [], manifest_path=out)
    check("…a blocks file with no block at all is a fault even so (nothing to connect)",
          any("жодного блоку" in p for p in problems), problems)

# --- review of tasks 1–4 (v4.4.0): each finding reproduced first
import provider_bundle as pbm  # noqa: E402
hit = lambda pats, rel: any(re.search(p, rel, re.I) for p in pats)
ex = ci.registration_exclude()
check("I1: the plugin's own store kept in a core's vault (<pf>/_System/context/) is out of search",
      hit(ex, "Core/_System/context/records/profile.md") and hit(ex, "_System/context/history/2026-11.md")
      and not hit(ex, "Core/Playbook/01 Rules.md") and not hit(ex, "Core/_System/context-blocks.md"), ex)
ex2 = ci.registration_exclude(pbm.Manifest({"exclude": ["(^|/)_drafts/"], "personal_overlay": ["Core/Journal/", "Core/Diary*.md", "Core/Now.md"]}))
check("I2: the core manifest's personal_overlay is out of search too (folder glob, file glob, plain name)",
      hit(ex2, "Core/Journal/2026-11-05.md") and hit(ex2, "Core/Diary 1.md") and hit(ex2, "Core/_drafts/x.md")
      and not hit(ex2, "Core/Journalism.md") and not hit(ex2, "Core/Playbook/Diary.md"), ex2)
is_inf = getattr(pbm, "is_inferred", lambda m: None)
check("M6: «inferred» in any truthy spelling is inferred; false ones are not",
      all(is_inf(pbm.Manifest({"inferred": v})) for v in (True, "true", "True", "yes", "YES", 1, "1", "on"))
      and not any(is_inf(pbm.Manifest(d)) for d in ({"inferred": False}, {"inferred": "no"}, {"inferred": ""}, {})),
      [is_inf(pbm.Manifest({"inferred": v})) for v in (True, "true", "yes", 1)])

with tempfile.TemporaryDirectory() as d:
    core = bare_kit(d)
    sysd = os.path.join(core, "Core", "_System")
    write(os.path.join(core, "Second", "_System", ".access-bundles.json.icloud"), "x")
    r = ci.infer(core, today=TODAY)
    check("M2: a second role model iCloud has evicted is a candidate too — not ok, never a guess",
          r["ok"] is False and "не завантаж" in r["why"] and sorted(r["candidates"]) == ["Core", "Second"], r)
    shutil.rmtree(os.path.join(core, "Second"))
    write(os.path.join(sysd, ".other-blocks.md.icloud"), "x")
    r = ci.infer(core, today=TODAY)
    check("M2: an evicted .md beside the blocks file — no blocks_file, «не завантажено», never the other one",
          r["ok"] and "blocks_file" not in r["manifest"] and "не завантаж" in r["from"].get("blocks_file", ""), r.get("from"))
    os.remove(os.path.join(sysd, ".other-blocks.md.icloud"))
    write(os.path.join(sysd, "other-blocks.md"), "<!-- zorg-more:begin id=x v=1 -->\nX\n<!-- zorg-more:end id=x -->\n")
    r = ci.infer(core, today=TODAY)
    check("M7: two blocks files — the reason says «не вгадую», never «лише командний блок»",
          "не вгадую" in r["from"].get("blocks_file", "") and "командний блок" not in r["from"].get("blocks_file", ""), r.get("from"))
    os.remove(os.path.join(sysd, "other-blocks.md"))
    write(os.path.join(sysd, ".provider-manifest.yaml.icloud"), "x")
    r = ci.infer(core, today=TODAY)
    check("I4: the owner's manifest is there but evicted — not ok, «ще не завантажений», nothing inferred",
          r["ok"] is False and "не завантажений" in r["why"] and r["manifest"] is None, r)

with tempfile.TemporaryDirectory() as d:
    core = bare_kit(d, "Ядро")
    r = ci.infer(core, today=TODAY)
    check("M4: a folder name with no Latin letters gives no id — not ok, «--id»; with --id it is fine",
          r["ok"] is False and "--id" in r["why"] and ci.infer(core, rid="zorg-core", today=TODAY)["ok"], r)

# --- whole-branch review (v4.4.0): each finding reproduced first
import warnings  # noqa: E402
import ctx_index as cidx  # noqa: E402
with warnings.catch_warnings():
    warnings.simplefilter("error")                      # 3.9 warns where 3.11+ raises: a flag not at the start
    try:
        rx = cidx._exclusion(["(^|/)Meetings/", "(?i)(^|/)private/"])
        ok = rx is not None and rx.search("Core/Private/x.md") and rx.search("Core/Meetings/m.md") and not rx.search("Core/Playbook/a.md")
    except Exception as e:  # noqa: BLE001
        ok, rx = False, e
check("I2: an inline-flag expression is compiled on its own — never joined into one that 3.11+ refuses", ok, rx)
bad = cidx._exclusion(["(^|/)Meetings/", "foo(?i)bar"])
check("I2: an expression that does not compile (or warns) hides the whole folder — fail closed, never silently skipped",
      bad is not None and bad.search("Core/Playbook/a.md"), bad)
check("I2: no expressions → nothing hidden", cidx._exclusion([]) is None and cidx._exclusion(None) is None, "")
probs = getattr(ci, "expression_problems", lambda pats: ["missing"])(["(^|/)ok/", "foo(?i)bar", "(unclosed"])
check("I2: repo add names an owner's expression that will not compile everywhere", len(probs) == 2
      and any("foo(?i)bar" in p for p in probs) and any("(unclosed" in p for p in probs), probs)
check("I3: the owner's 1-1 folders are out of search", hit(ci.registration_exclude(), "Core/People/1-1/2026-10-01 x.md")
      and hit(ci.registration_exclude(), "GrowPM/_personal/1-1-Logs/a/b.md") and hit(ci.registration_exclude(), "Core/1-1-Logs/x.md"), "")

with tempfile.TemporaryDirectory() as d:
    core = bare_kit(d)
    sysd = os.path.join(core, "Core", "_System")
    blocks = open(os.path.join(sysd, "context-blocks.md"), encoding="utf-8").read()
    write(os.path.join(sysd, "local-context.md"), "# Local Context\n\n" + blocks)
    r = ci.infer(core, today=TODAY)
    check("M8: the owner's own local-context.md in the core is no second blocks file",
          r["ok"] and r["manifest"].get("blocks_file") == "Core/_System/context-blocks.md", r.get("from"))
    os.remove(os.path.join(sysd, "local-context.md"))
    write(os.path.join(sysd, "provider-manifest.md"), "---\nkind: provider-file\nfile: provider-manifest.yaml\n---\n# m\n\n```yaml\nid: zorg-core\n```\n")
    r = ci.infer(core, today=TODAY)
    check("I1: the owner's manifest only as its .md wrapper — the core ships one: not inferred, «обгортка»",
          r["ok"] is False and "обгортк" in r["why"], r)
    os.remove(os.path.join(sysd, "provider-manifest.md"))
    model_path = os.path.join(sysd, "access-bundles.json")
    model = json.load(open(model_path, encoding="utf-8"))
    model["roles"] = {}
    json.dump(model, open(model_path, "w", encoding="utf-8"))
    write(os.path.join(d, "m.yaml"), ci.infer(core, today=TODAY)["text"])
    _, _, problems = ckit.check(core, [], manifest_path=os.path.join(d, "m.yaml"))
    check("M4: a role model with no roles is a fault, under an inferred manifest too", any("ролей" in p or "roles" in p for p in problems), problems)

# --- validate check 25: the protocol's §9 and the code agree (a mutation of each side is caught)
check("check_protocol: the shipped protocol and ctx_infer agree", getattr(ci, "check_protocol", lambda r: ["missing"])(ROOT) == [],
      getattr(ci, "check_protocol", lambda r: ["missing"])(ROOT))
with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, "references"))
    proto = open(os.path.join(ROOT, "references", "context-provider-protocol.md"), encoding="utf-8").read()
    mutations = [("an exclusion dropped from the protocol", "`(^|/)Focus/`, ", ""),
                 ("a never-inferred key dropped", "`dashboard_rewrites`, ", ""),
                 ("the owner's Now.md dropped from the search paragraph", "`(^|/)Now\\.md$`", "`Now`")]
    for name, old_s, new_s in mutations:
        open(os.path.join(d, "references", "context-provider-protocol.md"), "w", encoding="utf-8").write(proto.replace(old_s, new_s, 1))
        errs = getattr(ci, "check_protocol", lambda r: [])(d)
        check("check_protocol catches %s" % name, old_s in proto and errs, errs)
    # review of tasks 5–7, M3: the check compares both ways and looks at what infer() emits
    open(os.path.join(d, "references", "context-provider-protocol.md"), "w", encoding="utf-8").write(proto.replace(
        "`(^|/)_System/context/` (the owner's own context store", "`(^|/)_System/context/`, `(^|/)Journal/` (the owner's own context store", 1))
    errs = getattr(ci, "check_protocol", lambda r: [])(d)
    check("check_protocol catches a search exclusion the protocol promises and the code lacks", any("Journal" in e for e in errs), errs)
    shutil.copytree(os.path.join(ROOT, "examples"), os.path.join(d, "examples"))
    open(os.path.join(d, "references", "context-provider-protocol.md"), "w", encoding="utf-8").write(proto)
    saved_p = list(ci.PERSONAL_EXCLUDE)
    ci.PERSONAL_EXCLUDE[:] = [x for x in saved_p if "context" not in x]
    errs = ci.check_protocol(d)
    ci.PERSONAL_EXCLUDE[:] = saved_p
    check("check_protocol catches the code dropping an exclusion the protocol promises", any("_System/context/" in e for e in errs), errs)
    real_infer = ci.infer
    ci.infer = lambda *a, **k: dict(real_infer(*a, **k), text=real_infer(*a, **k)["text"] + "tools_file: Core/_System/tools.yaml\n")
    errs = ci.check_protocol(d)
    ci.infer = real_infer
    check("check_protocol catches the code starting to infer a never-inferred key", any("tools_file" in e for e in errs), errs)
    saved = list(ci.INFERRED_EXCLUDE)
    open(os.path.join(d, "references", "context-provider-protocol.md"), "w", encoding="utf-8").write(proto)
    ci.INFERRED_EXCLUDE.append(r"(^|/)Secret/")
    errs = getattr(ci, "check_protocol", lambda r: [])(d)
    ci.INFERRED_EXCLUDE[:] = saved
    check("check_protocol catches an exclusion added to the code alone", any("Secret" in e for e in errs), errs)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""Grow PM — a minimal provider manifest inferred from a shared core's layout (since v4.4.0;
references/context-provider-protocol.md §9 «A core with no manifest»).

A core may reach a colleague without its owner's `_System/provider-manifest.yaml`. `infer(folder)` reads the layout
and writes the manifest the plugin can connect the core with IN PLACE (`ctx repo add --infer`): the folder holding
`_System/access-bundles.json` is the plugin folder, the one `_System/*.md` with block markers of one namespace is the
blocks file, Teams/, People/, Playbook/ and `_System/provider-templates` are named when they are there. It never
infers what would run or reach out — a command (`people_resolver`), an MCP address — nor the owner's filters
(`deny_patterns`, `delink_*`, `dashboard_rewrites`), a write scope or a tools list: the owner's personal layer is left
out conservatively (`personal_overlay` and `INFERRED_EXCLUDE`). The result carries `inferred: true`, which the bundle
builder refuses (a selective copy needs the owner's filters). An ambiguous layout is named, never guessed.

The core is only read; the text goes beside the registration (ctx.py), never into the core. Stdlib only.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import provider_bundle as pb  # noqa: E402

# What search in a shared core leaves out when its owner gave no manifest (C5): an owner's meetings, focus notes,
# personal folder, TODO lists, spreadsheets, archives, and the copies of a context the connect flow leaves behind.
INFERRED_EXCLUDE = [
    r"(^|/)Meetings/", r"(^|/)Focus/", r"(^|/)_personal/", r"(^|/)TODO", r"\.xlsx$",
    r"local-context\.(existing|proposed)\.md$", r"context-merge-report\.md$", r"(^|/)_archive/",
]
# …and, in a registration of a core connected without its owner's manifest (search only, inferred, a guest), the
# owner's current-focus note too: Review Focus 1 of v4.4.0 names it, the eight above do not cover it.
PERSONAL_EXCLUDE = [r"(^|/)Now\.md$"]
# What an inferred manifest never carries: a command the plugin would run, an address it would reach, the owner's
# filters and rewrites, a write scope, a tools list (C4) — named so in context-provider-protocol.md §9.
NEVER_INFERRED = ("people_resolver", "mcp", "deny_patterns", "delink_*", "dashboard_rewrites", "write_scope", "tools_file")
PROTOCOL = os.path.join("references", "context-provider-protocol.md")
MODEL = os.path.join("_System", "access-bundles.json")
KEBAB = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MARKER = re.compile(r"<!--\s*([a-z0-9][a-z0-9-]*):begin\s+id=([A-Za-z0-9_.-]+)")
README_NAMES = ("readme.md", "readme-core.md")


def excluded(rel):
    """Is the core-relative path `rel` (with `/`) one search leaves out under an inferred manifest?"""
    return any(re.search(p, rel) for p in INFERRED_EXCLUDE)


def registration_exclude(manifest=None):
    """The `exclude:` of a registration `ctx repo add --search-only | --infer | --guest` writes: INFERRED_EXCLUDE, the
    owner's Now.md, and the expressions of the core's own manifest when there is one (a guest of a core that ships
    its manifest) — each once, in that order. The index walks the core folder without them (ctx_index.scope)."""
    out = []
    for x in INFERRED_EXCLUDE + PERSONAL_EXCLUDE + [str(v) for v in ((manifest or {}).get("exclude") or []) if str(v).strip()]:
        if x not in out:
            out.append(x)
    return out


def kebab(name):
    """`Zorg_Core` → `zorg-core`: lower case, every run of other characters one '-', at most 64; '' when nothing is left."""
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:64].strip("-")


def _read(path):
    import ctx_store as cs                              # within the time budget: an evicted file never hangs the read
    return cs.read_text(path)


def _join(pf, *parts):
    """A core-relative path with `/`, the plugin folder '.' adding no prefix."""
    return "/".join(([] if pf in ("", ".") else [pf]) + list(parts))


def _subdirs(folder):
    try:
        return sorted(n for n in os.listdir(folder) if not n.startswith(".") and os.path.isdir(os.path.join(folder, n)))
    except OSError:
        return []


def _plugin_folders(folder):
    """([plugin folders holding the role model], [plugin folders whose role model iCloud has evicted]) — the core's
    root ('.') and one level down, where the bundle builder looks for a manifest."""
    found, evicted = [], []
    for pf in ["."] + _subdirs(folder):
        sysd = os.path.join(folder, pf, "_System")
        if os.path.isfile(os.path.join(sysd, "access-bundles.json")):
            found.append(pf)
        elif os.path.exists(os.path.join(sysd, ".access-bundles.json.icloud")):
            evicted.append(pf)
    return found, evicted


def _blocks_file(folder, pf):
    """(the blocks file, its namespace, why) — the one `<pf>/_System/*.md` whose markers are of one namespace and more
    than the team block alone (a generated team block is the bundle builder's output, never the core's blocks file);
    a file search leaves out (a copy of a context, a merge report) is no candidate. None, None, why when there is no
    such file or more than one."""
    sysd = os.path.join(folder, pf, "_System")
    cands = []
    try:
        names = sorted(n for n in os.listdir(sysd) if n.endswith(".md") and not n.startswith("."))
    except OSError:
        names = []
    for n in names:
        rel = _join(pf, "_System", n)
        if excluded(rel):
            continue
        try:
            text = _read(os.path.join(sysd, n))
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        marks = MARKER.findall(text)
        spaces = {ns for ns, _ in marks}
        if len(spaces) != 1 or {bid for _, bid in marks} == {"team"}:
            continue
        cands.append((rel, spaces.pop()))
    if len(cands) == 1:
        return cands[0][0], cands[0][1], "єдиний файл %s/*.md з маркерами блоків (простір імен %s)" % (
            _join(pf, "_System"), cands[0][1])
    if not cands:
        return None, None, ("у %s немає файлу з маркерами блоків одного простору імен — лише командний блок "
                            "і пошук" % _join(pf, "_System"))
    return None, None, "кілька файлів блоків (%s) — не вгадую; лише командний блок і пошук" % ", ".join(r for r, _ in cands)


def title_of(folder):
    """(title, where from): the first `# ` heading of README.md or README-core.md at the core's root, else its name. A
    README with another suffix is a letter to someone, not the core's title."""
    for n in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if n.lower() not in README_NAMES:
            continue
        try:
            for line in _read(os.path.join(folder, n)).splitlines():
                if line.startswith("# ") and line[2:].strip():
                    return line[2:].strip(), n
        except (OSError, UnicodeDecodeError, ValueError):
            pass
    return os.path.basename(os.path.normpath(folder)), "назва теки"


def _fail(why, candidates=()):
    return {"ok": False, "text": "", "manifest": None, "from": {}, "why": why, "candidates": list(candidates)}


def infer(folder, rid="", today=""):
    """{ok, text, manifest, from, why, candidates} for the core `folder`. `text` is the manifest as YAML the plugin's
    reader takes back (first line `# ctx:inferred <today> …`); `manifest` the same as provider_bundle reads it (a
    Manifest, its defaults applied); `from` {key: where it came from}; `why` the reason when not ok — no role model
    (search only), its file not downloaded yet, more than one folder with one (`candidates`: those folders), an id
    that is not kebab-case. Reads only."""
    folder = os.path.abspath(os.path.expanduser(folder))
    if not os.path.isdir(folder):
        return _fail("немає теки ядра: %s" % folder)
    found, evicted = _plugin_folders(folder)
    if len(found) > 1:
        return _fail("кілька тек із _System/access-bundles.json: %s — не вгадую; лише пошук (--search-only) або "
                     "маніфест від власника ядра" % ", ".join(found), found)
    if not found:
        if evicted:
            return _fail("модель ролей (%s/_System/access-bundles.json) ще не завантажена з iCloud — відкрий теку ядра "
                         "у Finder" % evicted[0])
        return _fail("немає моделі ролей (_System/access-bundles.json) — лише пошук (--search-only)")
    pf = found[0]
    origin = {"plugin_folder": "тека з _System/access-bundles.json", "bundles_file": "модель ролей у теці плагіна"}
    name = os.path.basename(folder)
    if rid:
        if not KEBAB.match(rid):
            return _fail("id %r — не kebab-case до 64 символів" % rid)
        mid, origin["id"] = rid, "--id"
    else:
        mid = kebab(name) or "core"
        origin["id"] = "назва теки «%s»" % name
    title, origin["title"] = title_of(folder)
    blocks, ns, origin["blocks_file"] = _blocks_file(folder, pf)
    keys = [("schema", "provider-manifest/1"), ("id", mid), ("title", title)]
    if ns:
        keys.append(("namespace", ns))
    keys += [("plugin_folder", pf), ("contract", "vault/v1"), ("authority", "org"), ("mode", "snapshot"),
             ("inferred", "true"), ("bundles_file", _join(pf, "_System", "access-bundles.json"))]
    if blocks:
        keys.append(("blocks_file", blocks))
    for key, sub in (("team_card_dir", "Teams"), ("people_dir", "People")):
        if os.path.isdir(os.path.join(folder, pf, sub)):
            keys.append((key, _join(pf, sub)))
            origin[key] = "тека %s" % sub
    if os.path.isdir(os.path.join(folder, pf, "_System", "provider-templates")):
        keys.append(("templates_dir", _join(pf, "_System", "provider-templates")))
        origin["templates_dir"] = "тека _System/provider-templates"
    lists = []
    pdir = os.path.join(folder, pf, "Playbook")
    if os.path.isdir(pdir):
        books = sorted(n for n in os.listdir(pdir) if n.endswith(".md") and not n.startswith(("_", ".")))
        if books:
            lists.append(("playbook", [_join(pf, "Playbook", n) for n in books]))
            origin["playbook"] = "тека Playbook"
    lists.append(("personal_overlay", [_join(pf, "Now.md"), _join(pf, "TODO*"), _join(pf, "_personal") + "/"]))
    lists.append(("exclude", list(INFERRED_EXCLUDE)))
    origin["personal_overlay"] = "консервативно: Now.md, TODO*, _personal/"
    origin["exclude"] = "вбудований INFERRED_EXCLUDE"
    target = _join(pf, "_System", "provider-manifest.yaml")
    lines = ["# ctx:inferred %s — виведено плагіном; власник ядра може покласти його в %s" % (today, target),
             "# перед тим — прибрати рядок inferred: true і додати свої exclude, deny_patterns "
             "(references/context-provider-protocol.md §3a)"]
    lines += ["%s: %s" % (k, v if k == "inferred" else pb.yaml_value(v)) for k, v in keys]
    for k, items in lists:
        lines.append("%s:" % k)
        lines += ["  - %s" % pb.yaml_value(x) for x in items]
    text = "\n".join(lines) + "\n"
    manifest = pb.with_defaults(pb.Manifest(cc.read_yaml_subset(text)))
    return {"ok": True, "text": text, "manifest": manifest, "from": origin, "why": "", "candidates": []}


def _paragraph(text, lead):
    """The paragraph of `text` that starts with `lead` (up to the next blank line), or ""."""
    at = text.find(lead)
    if at < 0:
        return ""
    end = text.find("\n\n", at)
    return text[at:end if end >= 0 else len(text)]


def check_protocol(root):
    """[problem] — what context-provider-protocol.md §9 («A core with no manifest», v4.4.0) and this module disagree on:
    every INFERRED_EXCLUDE expression in backticks in its «*The inferred manifest*» paragraph and no other there, every
    NEVER_INFERRED key after «Never inferred», and PERSONAL_EXCLUDE in its «*Search in the core.*» paragraph
    (testing/validate-consistency.sh, check 25). [] when they agree."""
    try:
        text = open(os.path.join(root, PROTOCOL), encoding="utf-8").read()
    except OSError as e:
        return ["%s: %s" % (PROTOCOL, e.strerror or type(e).__name__)]
    out = []
    inferred = _paragraph(text, "*The inferred manifest*")
    if not inferred:
        return ["%s §9: no «*The inferred manifest*» paragraph" % PROTOCOL]
    listed = inferred.split("the built-in list", 1)[1].split(". The file", 1)[0] if "the built-in list" in inferred else ""
    shown = re.findall(r"`([^`]+)`", listed)
    for x in INFERRED_EXCLUDE:
        if x not in shown:
            out.append("%s §9: the exclusion `%s` of ctx_infer.INFERRED_EXCLUDE is not in the built-in list" % (PROTOCOL, x))
    for x in shown:
        if x not in INFERRED_EXCLUDE:
            out.append("%s §9: the built-in list has `%s`, which ctx_infer.INFERRED_EXCLUDE does not" % (PROTOCOL, x))
    never = inferred.split("Never inferred:", 1)[1].split(". ", 1)[0] if "Never inferred:" in inferred else ""
    for k in NEVER_INFERRED:
        if "`%s`" % k not in never:
            out.append("%s §9: «Never inferred» does not name `%s`" % (PROTOCOL, k))
    search = _paragraph(text, "*Search in the core.*")
    for x in PERSONAL_EXCLUDE:
        if "`%s`" % x not in search:
            out.append("%s §9: «Search in the core» does not name `%s`" % (PROTOCOL, x))
    return out

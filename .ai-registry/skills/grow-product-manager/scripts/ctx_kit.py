#!/usr/bin/env python3
"""Grow PM — a provider kit: what a team ships so that its colleagues' plugins share its context (since v3.23.0;
references/context-provider-protocol.md §9). Reads only.

- check(folder)                    the problems of a kit folder ([] — it is sound): the manifest, the role model, the
                                   blocks file, the team cards, the registry cards, no personal layer of the owner
- identity(folder, email, …)       e-mail → team → role as the bundle builder resolves it, with where each came from
- registration(folder, ident, …)   the text of the registration `ctx repo add` writes (provider-registration/2)

The example kit `examples/provider-kit/zorg-core/` passes `check`; `testing/validate-consistency.sh` keeps it so.
Stdlib only.
"""
import fnmatch
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_wrappers as cw  # noqa: E402
import provider_bundle as pb  # noqa: E402

KIT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
REQUIRED = ("id", "plugin_folder", "blocks_file", "bundles_file")
MODEL_KEYS = ("version", "emails", "teams", "roles")
CARD_FIELDS = ("name", "email", "team")


def _read(path):
    import ctx_store as cs                              # within the time budget: an evicted file never hangs the check
    return cs.read_text(path)


def _json(path):
    return json.loads(_read(path))


def _front(path):
    try:
        front, _ = pb.split_fm(_read(path))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return front


def _files(folder):
    return sorted(pb.walk(folder))


def check(folder, warnings=None, manifest_path=None, manifest=None, quiet=False):
    """(manifest or None, model or None, [problem]) of a kit folder. A problem names the file and what is wrong.
    `warnings` (a list) gets what is no fault of the kit but worth knowing when the folder is shared as it is: a
    registry card's private fields and the owner's personal layer — the bundle builder leaves both out of a colleague's
    bundle, but anyone who opens the folder itself sees them.

    `manifest_path` (since v4.4.0) is a manifest from outside the folder — the one `ctx repo add --infer` derives —
    checked as the folder's own would be; `manifest` the same already read (ctx_infer's, before it is written). Under an inferred manifest (`inferred: true`) the person checking is not the
    core's owner and connects it in place: what only the owner can fix and what does not stop the connection (a team
    naming a file that is not there, a missing team card, a person card without its fields, a stray marker beside
    blocks that read, a wrapper) is a warning ending «справа власника ядра»; no role model, no blocks file, no block
    at all stay faults. Under an inferred manifest, and with `quiet` (a guest, `ctx repo add --guest`), the owner's
    personal files and the cards with private fields are counted, never named: the person reading is not the owner."""
    out = []
    warn = warnings if warnings is not None else []
    if not os.path.isdir(folder):
        return None, None, ["немає теки набору: %s" % folder]
    if manifest is not None:
        m = manifest
    else:
        if manifest_path and not os.path.isfile(manifest_path):
            return None, None, ["немає маніфесту: %s" % manifest_path]
        m, why = pb.read_manifest(folder, path=manifest_path or None)
        if m is None:
            return None, None, [why]
    inferred = pb.is_inferred(m)
    quiet = quiet or inferred

    def owner(problem):
        """A fault of the kit — a warning when the manifest is inferred (the owner's to fix, the connection stands)."""
        (warn if inferred else out).append(problem + (" — справа власника ядра" if inferred else ""))
    for k in REQUIRED:
        if not m.s(k):
            out.append("provider-manifest.yaml: немає %s" % k)
    if m.s("id") and not KIT_ID.match(str(m.s("id"))):
        out.append("provider-manifest.yaml: id %r — не kebab-case до 64 символів" % m.s("id"))
    ns = str(m.s("namespace") or m.s("id"))
    if ns and not KIT_ID.match(ns):
        out.append("provider-manifest.yaml: namespace %r — не kebab-case" % ns)
    files = _files(folder)
    model = None
    bp = os.path.join(folder, m.s("bundles_file")) if m.s("bundles_file") else None
    if bp:
        try:
            model = _json(bp)
        except (OSError, ValueError) as e:
            out.append("%s: не читається (%s)" % (m.s("bundles_file"), e))
    if isinstance(model, dict):
        for k in MODEL_KEYS:
            if k not in model:
                out.append("%s: немає %s" % (m.s("bundles_file"), k))
        if "roles" in model and not model.get("roles"):     # since v4.4.0: no role at all — nothing to resolve to
            out.append("%s: немає жодної ролі в roles" % m.s("bundles_file"))
        teams = model.get("teams") if isinstance(model.get("teams"), dict) else {}
        for email, team in (model.get("emails") or {}).items():
            if team not in teams:
                owner("%s: пошта %s → команда %s, якої немає в teams" % (m.s("bundles_file"), email, team))
        for key, tb in teams.items():
            if not isinstance(tb, dict) or not tb.get("title"):
                owner("%s: команда %s без title" % (m.s("bundles_file"), key))
                continue
            for f in tb.get("files") or []:
                if f not in files:
                    owner("%s: команда %s називає файл, якого немає: %s" % (m.s("bundles_file"), key, f))
            if not os.path.isfile(pb.team_card_path(folder, m, key)):
                owner("немає картки команди %s: %s" % (key, os.path.relpath(pb.team_card_path(folder, m, key), folder)))
        for role, layers in (model.get("roles") or {}).items():
            if not isinstance(layers, list) or not layers:
                owner("%s: роль %s без шарів" % (m.s("bundles_file"), role))
    elif model is not None:
        out.append("%s: не об'єкт JSON" % m.s("bundles_file"))
    blocks = os.path.join(folder, m.s("blocks_file")) if m.s("blocks_file") else None
    if blocks:
        try:
            text = _read(blocks)
        except (OSError, UnicodeDecodeError, ValueError) as e:
            out.append("%s: не читається (%s)" % (m.s("blocks_file"), e))
            text = None
        if text is not None:
            import ctx_blocks as cb                     # here: the strict reading of regions lives with the merge
            found, errors = cb.find_regions([{"id": "kit", "body": text}], ns)
            for x in errors:                            # beside blocks that read, a stray marker is the owner's
                (owner if found else out.append)("%s: блок %s — %s" % (m.s("blocks_file"), x["block"] or "?", x["why"]))
            if not found:
                out.append("%s: жодного блоку простору імен %s" % (m.s("blocks_file"), ns))
            for bid, r in found.items():
                if not r["v"]:
                    owner("%s: блок %s без v=" % (m.s("blocks_file"), bid))
    pdir = os.path.join(folder, m.s("people_dir")) if m.s("people_dir") else None
    private_cards = 0
    for name in sorted(os.listdir(pdir)) if pdir and os.path.isdir(pdir) else []:
        if not name.endswith(".md") or name.startswith(("_", ".")):
            continue
        front = _front(os.path.join(pdir, name)) or {}
        missing = [k for k in CARD_FIELDS if not pb.fget(front, k)]
        if missing:
            owner("%s/%s: немає %s" % (m.s("people_dir"), name, ", ".join(missing)))
        private = [k for k in (m.get("people_private_fields") or []) if pb.fget(front, k)]
        if private:
            private_cards += 1
            if not quiet:
                warn.append("%s/%s: приватні поля (%s) — у пакет колеги не підуть, але в спільній теці їх видно"
                            % (m.s("people_dir"), name, ", ".join(private)))
    if quiet and private_cards:
        warn.append("%s: приватні поля в %d картках — у пакет колеги не підуть, але в спільній теці їх видно"
                    % (m.s("people_dir"), private_cards))
    for glob in m.get("personal_overlay") or []:
        hits = [f for f in files if fnmatch.fnmatch(f, glob) or (glob.endswith("/") and f.startswith(glob))]
        if hits:
            warn.append("особистий шар власника в теці (%s): %s — у пакет колеги не піде, але в спільній теці його видно"
                        % (glob, ("%d файл(и) — поза пошуком" % len(hits)) if quiet else ", ".join(hits[:3])))
    if m.s("tools_file"):                           # since v4.2.0: the team's tools list, read as tools_scan team reads it
        tf = str(m.s("tools_file"))
        root, real = os.path.realpath(folder), os.path.realpath(os.path.join(folder, tf))
        if os.path.commonpath([root, real]) != root:
            out.append("provider-manifest.yaml: tools_file %s — поза набором" % tf)
        else:
            try:
                recs = cc.read_yaml_records(_read(real), "tools")
                if not recs or [r for r in recs if not isinstance(r, dict) or not r.get("name")]:
                    out.append("%s: не список інструментів із name (tool-registry.md §5)" % tf)
            except (OSError, UnicodeDecodeError, ValueError) as e:
                out.append("%s: не читається (%s)" % (tf, getattr(e, "strerror", None) or type(e).__name__))
    for problem in _wrapper_problems(folder, files, m, skip_unnamed=inferred):
        owner(problem)
    return m, model, out


def _wrapper_problems(folder, files, m, skip_unnamed=False):
    """Since v3.24.0: every `.md` wrapper of the kit (`kind: provider-file`, ctx_wrappers) is sound and its block is the
    file beside it, byte for byte — a notes server serves the wrapper, a folder the file, and both must say the same.
    `skip_unnamed` (an inferred manifest, since v4.4.0): a wrapper of a file only a manifest key could name (`tools.yaml`
    with no `tools_file`) is no fault — the inferred manifest names none of them, by design."""
    out = []
    for rel in files:
        if not rel.endswith(".md"):
            continue
        try:
            text = _read(os.path.join(folder, rel))
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        front, body = pb.split_fm(text)
        if "provider-file" not in front:
            continue
        try:
            fm = cc.read_yaml_subset(front)
        except ValueError:
            continue
        if not cw.is_wrapper(fm):
            continue
        if skip_unnamed and str(fm.get("file") or "").strip() not in cw.allowed_names(m):
            continue
        name, inner, why = cw.unwrap(fm, body, cw.allowed_names(m), cw.records_names(m))
        if why:
            out.append("%s: обгортка не розгортається — %s" % (rel, why))
            continue
        beside = os.path.join(os.path.dirname(rel), name)
        try:
            real = _read(os.path.join(folder, beside))
        except (OSError, UnicodeDecodeError, ValueError):
            out.append("%s: поруч немає %s" % (rel, name))
            continue
        if real.rstrip("\n") + "\n" != inner:
            out.append("%s: обгортка не збігається з %s поруч — онови обгортку" % (rel, beside))
    return out


def identity(folder, m, model, email, team=None, role=None, guest=False):
    """{email, team, team_title, team_from, role, role_title, role_from, known} as the bundle builder resolves an e-mail
    (`known`: the role model lists it); ValueError when the e-mail has no team and none is named. `guest` (since
    v4.4.0, `ctx repo add --guest`): no team at all — `team` "", `team_title` "гість" — and the role `role` names when
    the model has it, else pm, else the first; with a team named it is a ValueError."""
    email = (email or "").strip().lower()
    known = email in (model.get("emails") or {})
    roles = model.get("roles") or {}
    if guest:
        if team:
            raise ValueError("--guest і --team разом не можна: гість підключається без команди")
        got = role if role in roles else ("pm" if "pm" in roles else (sorted(roles)[0] if roles else ""))
        return {"email": email, "team": "", "team_title": "гість", "team_from": "--guest", "role": got, "role_title": "",
                "role_from": "--role" if role and role in roles else "типово → %s" % got, "known": known}
    named = team
    team = team or (model.get("emails") or {}).get(email)
    if not team or team not in (model.get("teams") or {}):
        raise ValueError("пошти %s немає в моделі ролей набору — назви команду: --team (є: %s) або підключись гостем, "
                         "без команди: --guest" % (email, ", ".join(sorted(model.get("teams") or {}))))
    tb = model["teams"][team]
    people_pre = m.s("people_dir").rstrip("/") + "/"
    local = email.split("@")[0].replace(".", "-")
    pslug = next((os.path.basename(f)[:-3] for f in tb.get("files", []) if f.startswith(people_pre)
                  and os.path.basename(f)[:-3] == local), None)
    title = (model.get("people_role") or {}).get(pslug or "", "")
    inferred = pb.infer_role(title, m)
    got = role or inferred
    if got not in roles:
        got = "pm" if "pm" in roles else sorted(roles)[0]
    word = os.path.basename(people_pre.rstrip("/")) or "People"
    return {"email": email, "team": team, "team_title": tb.get("title", team),
            "team_from": "--team" if named else "access-bundles.json: emails",
            "role": got, "role_title": title,
            "role_from": "--role" if role else ("%s/%s.md: «%s» → %s" % (word, pslug, title, inferred) if pslug and title
                                                else "типово → %s" % got), "known": known}


def _q(s):
    return json.dumps(str(s), ensure_ascii=False)


def registration(folder, m, model, ident, today, manifest_path="", search_only=False, exclude=None, connected_as=""):
    """The text of the registration of this kit (provider-registration/2): a local folder, `sync: off` (the daily sync
    is asked for once by context-connect), the owner's personal layer as `writable`. Since v4.4.0: `manifest_path` —
    the manifest beside the registration (`manifest:`, absolute) for a core that ships none; `exclude` — the
    expressions the index leaves out of the core folder (ctx_infer.registration_exclude), given for modes A–C only,
    which then write `writable: []` (the owner's personal layer is someone else's: the write gate asks for it);
    `connected_as` — `search`, `inferred` or `guest`: the mode, which the index keys the owner's later manifest on;
    `search_only` — a core
    folder registered for search alone (`blocks: none`: no blocks, no team, no role model; `m` gives only the id and
    the title, `model` and `ident` are not read)."""
    folder = os.path.abspath(folder)
    lines = ["schema: provider-registration/2", "id: %s" % m.s("id"), "title: %s" % _q(m.s("title") or m.s("id")),
             "kind: folder", "contract: %s" % (m.s("contract") or "vault/v1"), "authority: %s" % (m.s("authority") or "org"),
             "mode: snapshot", "access: local", "paths:", "  - %s" % _q(folder), "core_root: %s" % _q(folder)]
    if search_only:
        lines += ["blocks: none", "products: []", "writable: []"]
    else:
        lines += ["namespace: %s" % (m.s("namespace") or m.s("id")), "blocks_file: %s" % _q(m.s("blocks_file"))]
        if manifest_path:
            lines.append("manifest: %s" % _q(os.path.abspath(manifest_path)))
        lines.append("products: []")
        ov = [] if exclude else (m.get("personal_overlay") or [])   # modes A–C: the owner's layer is no file of yours
        lines += (["writable:"] + ["  - %s" % _q(g) for g in ov]) if ov else ["writable: []"]
    if connected_as:
        lines.append("connected_as: %s" % connected_as)
    if exclude:
        lines += ["exclude:"] + ["  - %s" % _q(x) for x in exclude]
    if search_only:
        lines += ["sync: off", "status: active", "synced_at: %s" % today]
        return "\n".join(lines) + "\n"
    lines += ["skip_blocks: []", "team: %s" % pb.yaml_value(ident["team"]), "role: %s" % pb.yaml_value(ident["role"]),
              "jira_write: ask", "sync: off", "status: active", "synced_at: %s" % today,
              "source_version: %s" % _q("core %s" % (model.get("version") or "?"))]
    return "\n".join(lines) + "\n"


def registrations_dir(store_root, context_text, home):
    """Where `ctx repo add` puts a registration — where `ctx repo list` reads it (context-provider-protocol.md §3b):
    `{storage_root}/_System/providers/` when the storage root is a vault (its sync mode is not `off`), else
    `~/.grow-pm/providers/`."""
    root = cc.storage_root(context_text, home)
    grow = os.path.join(home, ".grow-pm")
    if os.path.normpath(root) == os.path.normpath(grow):
        return os.path.join(grow, "providers")
    return os.path.join(root, "_System", "providers")

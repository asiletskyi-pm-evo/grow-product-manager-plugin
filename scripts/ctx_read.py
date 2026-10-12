#!/usr/bin/env python3
"""Grow PM — what a skill reads from the context store (since v3.12.0).

references/context-manifest.yaml says, per skill, which records, fields and subsections Step 0c
needs; `read_view` gives the context card plus exactly those parts — read only, no lock, no
writes. Edits not imported yet and records missing on disk are read from the canonical copy,
with a note. Semantics: references/context-protocol.md.

- load_manifest / manifest_for    the manifest
- read_view                       the text of `ctx read --skill <name>` and its result
- check_manifest                  validator check 16: the manifest against the skills and the schema

Stdlib only.
"""
import datetime
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_store as cs  # noqa: E402
import ctx_schema as sc  # noqa: E402
import ctx_ops as co  # noqa: E402

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(PLUGIN_ROOT, "references", "context-manifest.yaml")
_INVALID = re.compile(r"> ⚠ Неактуально з [0-9-]+: (.*)")
# "Which Skills Read What" required context → where the manifest must carry it
REQUIRED_MAP = {"product.name": ("product", None), "jira_project_key": ("product", "Jira Project Key"),
                "platforms": ("product", "Platforms"), "planning": ("required_settings", "Planning"),
                "cjm": ("required_settings", "CJM Configuration"), "user.email": ("profile", "Email")}


def load_manifest(path=None):
    with open(path or MANIFEST_PATH, encoding="utf-8") as f:
        return cc.read_yaml_tree(f.read())


def manifest_for(manifest, skill):
    """The skill's entry merged with `every_skill`; an unknown skill → KeyError."""
    entry = (manifest.get("skills") or {})[skill]
    base = manifest.get("every_skill") or {}
    out = dict(entry or {})
    out["records"] = list(base.get("records") or []) + [r for r in (out.get("records") or []) if r not in (base.get("records") or [])]
    out["settings"] = list(base.get("settings") or []) + list(out.get("settings") or [])
    return out


def tokens_est(text):
    return int(math.ceil(len(text) / 3.2))


def _lines(body):
    return [core for _, core, _ in cs._lines(body)]


def _subsection(body, name):
    """The `#…# name` subsection (heading to the next heading of the same or a higher level), or None."""
    lines = body.splitlines(keepends=True)
    cores = [l.rstrip("\r\n") for l in lines]
    at = next((k for k, c in enumerate(cores) if cs._heading_text(c) == name and cs._level(c) > 0), None)
    if at is None:
        return None
    lvl, end = cs._level(cores[at]), len(lines)
    for k in range(at + 1, len(lines)):
        if 0 < cs._level(cores[k]) <= lvl:
            end = k
            break
    return "".join(lines[at:end]).rstrip("\n") + "\n"


def _field_text(body, name):
    """The field's own line, else its `#### name` subsection."""
    for core in _lines(body):
        m = cs.FIELD_RE.match(core)
        if m and m.group("name").strip() == name:
            return core + "\n"
    return _subsection(body, name)


def _without_heading(body):
    lines = body.splitlines(keepends=True)
    return "".join(lines[1:] if lines and lines[0].startswith("#") else lines).strip("\n") + "\n"


def _head(rec, state, today, note=""):
    seen = sc.verified_of(rec, state)
    marks = ["%s · %s" % (rec["title"], rec["id"])]
    if seen:
        marks.append("перевірено %s" % seen)
    if sc.is_stale(rec, state, today):
        marks.append("⚠ застаріле (TTL %s д)" % sc.ttl_of(rec))
    m = _INVALID.search(rec["body"]) if cs.has_status_region(rec["body"]) else None
    if m:
        marks.append("⚠ неактуально: %s" % m.group(1).strip())
    if note:
        marks.append(note)
    return "## " + " · ".join(marks)


def _live_view(store, copies, now):
    """Records as the canonical copy has them now: imported records, with bodies of edits not imported yet
    and records missing on disk taken from the copy. Returns (records, notes by id, pending count)."""
    recs = {r["id"]: r for r in store.load()}
    plan = co.plan_sync(store, copies)
    notes = {}
    for e in plan["edits"] + plan["renames"]:
        recs[e["id"]] = dict(recs[e["id"]], body=e["text"], title=e.get("title") or recs[e["id"]]["title"])
        notes[e["id"]] = "з файлу, ще не підхоплено — ctx sync"
    for rid in plan["missing"]:
        rec = co._from_copy(store, copies, rid, now)
        if rec:
            prev = store.state().get("order", [])
            rec["order"] = (prev.index(rid) + 1) * 10 if rid in prev else 10 ** 6
            recs[rid] = rec
            notes[rid] = "запису немає на диску — ctx sync"
    for rid in plan["removes"]:
        recs.pop(rid, None)
    pending = sum(co.pending(plan).values()) + len(plan["missing"]) + len(plan["conflicts"])
    return sorted(recs.values(), key=lambda r: r["order"]), notes, pending


def _pick_product(products, wanted):
    """(product or None, needs_choice)."""
    if wanted:
        w = wanted.strip().lower()
        exact = [p for p in products if p["id"] == wanted or p["title"].split(":", 1)[-1].strip().lower() == w]
        if len(exact) == 1:
            return exact[0], False
        part = [p for p in products if w in p["title"].lower()]
        return (part[0], False) if len(part) == 1 else (None, True)
    if len(products) == 1:
        return products[0], False
    return None, len(products) > 1


def read_view(store, copies, skill, product=None, today=None, manifest=None):
    """The text of `ctx read --skill <skill>` and its result (records, missing, chars, tokens_est,
    pending, needs_product). Reads only."""
    spec = manifest_for(manifest or load_manifest(), skill)
    today = (today or datetime.date.today().isoformat())[:10]
    state = store.state()
    card = co._read(store.card_path) if os.path.isfile(store.card_path) else ""
    recs, notes, pending = _live_view(store, copies, today + "T00:00:00")
    blocks, used, missing = [], [], []
    res = {"records": used, "missing": missing, "pending": pending, "needs_product": False}

    def add(rec, text):
        blocks.append(_head(rec, state, today, notes.get(rec["id"], "")) + "\n" + text.rstrip("\n") + "\n")
        used.append(rec["id"])

    absent = []

    def miss(name, required):
        missing.append(name)
        absent.append("%s (обов'язкове)" % name if required else name)

    if spec.get("full"):
        blocks.append("Цей скіл редагує local-context.md і читає його цілком.")
    else:
        prod = None
        if spec.get("product") is not None or spec.get("team") is not None:
            products = [r for r in recs if r["type"] == "product"]
            prod, needs = _pick_product(products, product)
            if needs:
                res["needs_product"] = True
                res["products"] = [p["title"].split(":", 1)[-1].strip() for p in products]
                blocks = ["Продукти: %s — обери продукт (крок 0d) і повтори з --product" % ", ".join(res["products"])]
        if not res["needs_product"]:
            for kind in spec["records"]:
                rec = next((r for r in recs if r["id"] == kind or r["type"] == kind), None)
                if rec:
                    add(rec, _without_heading(rec["body"]))
                    for f in ((spec.get(kind) or {}).get("required") or []):
                        if _field_text(rec["body"], f) is None:
                            miss(f, True)
                else:
                    miss(kind, False)
            want = spec.get("product")
            if want is not None:
                if prod is None:
                    miss("продукт", bool(want.get("required")))
                else:
                    _parts(add, miss, prod, want)
            want = spec.get("team")
            if want is not None:
                teams = [r for r in recs if r["type"] == "team" and (prod is None or r.get("parent") == prod.get("parent"))]
                for t in teams:
                    if want.get("whole"):
                        add(t, _without_heading(t["body"]))
                    else:
                        _parts(add, miss, t, want)
            req = list(spec.get("required_settings") or [])
            for name in req + [n for n in spec["settings"] if n not in req]:
                rec = next((r for r in recs if r["type"] == "setting" and r["title"].lower().startswith(name.lower())), None)
                if rec:
                    add(rec, _without_heading(rec["body"]))
                else:
                    miss("налаштування %s" % name, name in req)
    if absent:
        blocks.append("Відсутнє: %s — для решти діють типові значення" % ", ".join(absent))
    head = "# Контекст для %s · записів %d · %s" % (skill, len(used), "%d правок не підхоплено — ctx sync" % pending if pending else "in sync")
    tail = "Більше з запису: ctx get <id> --section \"…\""
    text = "\n".join([head, "", card.rstrip("\n"), ""] + blocks + ["", tail]) + "\n"
    res.update(chars=len(text), tokens_est=tokens_est(text))
    return text, res


def _parts(add, miss, rec, want):
    parts = []
    for name in (want.get("required") or []) + (want.get("fields") or []):
        t = _field_text(rec["body"], name)
        if t is None:
            miss(name, name in (want.get("required") or []))
        else:
            parts.append(t.rstrip("\n"))
    for name in want.get("sections") or []:
        t = _subsection(rec["body"], name)
        if t is not None:
            parts.append(t.rstrip("\n"))
    add(rec, "\n".join(parts) + "\n")


# ------------------------------------------------------------ manifest check
def _table_rows(root):
    """{skill dir name: [required context tokens]} from "Which Skills Read What"."""
    text = co._read(os.path.join(root, "skills", "plugin-configurator", "references", "context-schema.md"))
    sec = text.split("## Which Skills Read What", 1)[-1].split("\n## ", 1)[0]
    rows = {}
    for m in re.finditer(r"^\| \*\*(.+?)\*\* \| ([^|]*) \|", sec, re.M):
        name = m.group(1).strip()
        if name.lower().startswith("every skill"):
            continue
        toks = [re.split(r"\s*\(", t.strip())[0].strip() for t in m.group(2).split(",")]
        rows[re.sub(r"\s+", "-", name.lower())] = [t for t in toks if t and t != "—"]
    return rows


def check_manifest(root, manifest_path=None):
    """Errors: a skill without an entry or an entry without a skill, a setting name no setting title starts
    with, a required field of "Which Skills Read What" the manifest does not carry."""
    errs = []
    try:
        man = load_manifest(manifest_path or os.path.join(root, "references", "context-manifest.yaml"))
    except (OSError, ValueError) as e:
        return ["context-manifest.yaml: %s" % e]
    entries = man.get("skills") or {}
    skills = sorted(n for n in os.listdir(os.path.join(root, "skills")) if os.path.isdir(os.path.join(root, "skills", n)))
    errs += ["skill %s has no entry in context-manifest.yaml" % s for s in skills if s not in entries]
    errs += ["context-manifest.yaml names %s, which is not a skill" % s for s in entries if s not in skills]
    titles = [t.lower() for t in cs.SETTING_TITLES]
    names = list((man.get("every_skill") or {}).get("settings") or [])
    for e in entries.values():
        names += list((e or {}).get("settings") or []) + list((e or {}).get("required_settings") or [])
    errs += ["setting %r starts no known setting title" % n for n in sorted(set(names)) if n.lower() not in titles]
    for skill, toks in _table_rows(root).items():
        if skill not in skills:
            errs.append("Which Skills Read What row %s is not a skill" % skill)
            continue
        if skill not in entries:
            continue                                    # reported above
        e = entries[skill] or {}
        for tok in toks:
            if tok not in REQUIRED_MAP:
                errs.append("%s: required context %r has no manifest mapping (ctx_read.REQUIRED_MAP)" % (skill, tok))
                continue
            where, field = REQUIRED_MAP[tok]
            if where == "required_settings":
                ok = field in (e.get("required_settings") or [])
            elif field is None:
                ok = e.get(where) is not None or e.get("full")
            else:
                ok = field in ((e.get(where) or {}).get("required") or []) or e.get("full")
            if not ok:
                errs.append("%s: required %s is not under %s in context-manifest.yaml" % (skill, tok, where))
    return errs

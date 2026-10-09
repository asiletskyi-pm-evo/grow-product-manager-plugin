#!/usr/bin/env python3
"""Grow PM — the context store's model (since v3.11.0).

The user's local-context.md is cut into section records that together cover every byte
exactly once, so compiling the records gives the file back byte for byte. Semantics:
references/context-protocol.md. Used by ctx_ops.py and the `ctx` command line.

- split_sections / assign_ids   the split rules and stable record ids
- render_record / parse_record  the record file: frontmatter + the section text as is
- compile_records               the compiled local-context.md

Stdlib only.
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402

# A `##` heading that starts with one of these is a `setting` record; any other is `custom`.
SETTING_TITLES = ("Judgment", "CJM Configuration", "Knowledge Library", "Templates", "Obsidian Vaults", "People",
                  "Planning", "Focus", "Release", "Terminology & Style", "Landscape", "Experiments", "Feedback",
                  "Custom Sections")
RECORD_KEYS = ("ctx", "id", "type", "title", "parent", "order", "owner", "source", "modified", "sha")


def sha_text(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _h2_type(title):
    if title == "User Profile":
        return "profile"
    if title == "Onboarding Status":
        return "onboarding"
    if title.startswith("Organization:"):
        return "org"
    if title.startswith(SETTING_TITLES):
        return "setting"
    return "custom"


def split_sections(text):
    """Fragments {type, title, heading, parent_index, text} in file order; their texts concatenate to `text`.

    A `## ` line starts a fragment; inside `## Organization:` so does `### Product: ` / `### Team: `.
    Lines inside fenced code and inside managed regions never split — except that a region whose
    begin marker is followed, after blank lines only, by a `## ` heading starts a fragment itself."""
    lines = text.splitlines(keepends=True)
    starts, pos = [], 0
    for ln in lines:
        starts.append(pos)
        pos += len(ln)
    spans = cc.managed_spans(text)
    begins = {a for a, _ in spans}

    def inside(off):
        return any(a < off < b for a, b in spans)

    cuts, fence, org_open = [], False, False
    for i, ln in enumerate(lines):
        s = ln.rstrip("\r\n")
        off = starts[i]
        if inside(off):
            continue
        if s.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if s.startswith("## "):
            title = s[3:].strip()
            cuts.append((i, "h2", title, s))
            org_open = title.startswith("Organization:")
        elif org_open and (s.startswith("### Product: ") or s.startswith("### Team: ")):
            cuts.append((i, "h3", s[4:].strip(), s))
        elif off in begins:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].startswith("## "):
                head = lines[j].rstrip("\r\n")
                title = head[3:].strip()
                cuts.append((i, "h2", title, head))
                org_open = title.startswith("Organization:")

    frags = []
    first = cuts[0][0] if cuts else len(lines)
    if first > 0:
        head = next((l.rstrip("\r\n").lstrip("﻿") for l in lines[:first] if l.lstrip("﻿").startswith("# ")), "")
        frags.append(dict(type="header", title=head[2:].strip() if head else "header", heading=head or None,
                          parent_index=None, text="".join(lines[:first])))
    org_index = None
    for k, (i, kind, title, head) in enumerate(cuts):
        end = cuts[k + 1][0] if k + 1 < len(cuts) else len(lines)
        if kind == "h2":
            typ, parent = _h2_type(title), None
            org_index = len(frags) if typ == "org" else None
        else:
            typ, parent = ("product" if title.startswith("Product:") else "team"), org_index
        frags.append(dict(type=typ, title=title, heading=head, parent_index=parent, text="".join(lines[i:end])))
    return frags


def assign_ids(frags, taken=frozenset()):
    """Add `id`, `parent` (id or None) and `order` (10, 20, …) to each fragment."""
    used, out = set(taken), []
    for k, f in enumerate(frags):
        typ = f["type"]
        if typ in ("header", "profile", "onboarding"):
            base = typ
        else:
            name = f["title"]
            for pre in ("Organization:", "Product:", "Team:"):
                if name.startswith(pre):
                    name = name[len(pre):].strip()
                    break
            base = typ + "." + cc.slugify(name)
        rid, n = base, 2
        while rid in used:
            rid, n = "%s-%d" % (base, n), n + 1
        used.add(rid)
        pi = f.get("parent_index")
        out.append(dict(f, id=rid, order=(k + 1) * 10, parent=out[pi]["id"] if pi is not None else None))
    return out


def render_record(rec):
    """Frontmatter in RECORD_KEYS order (strings JSON-quoted, None as ""), then the body as is."""
    out = ["---"]
    for k in RECORD_KEYS:
        v = rec.get(k)
        if isinstance(v, bool) or v is None:
            v = "" if v is None else str(v).lower()
        out.append("%s: %s" % (k, v if isinstance(v, int) else json.dumps(v, ensure_ascii=False)))
    return "\n".join(out) + "\n---\n" + (rec.get("body") or "")


def parse_record(text):
    """Inverse of render_record. Raises ValueError when the frontmatter is missing or unreadable."""
    if not text.startswith("---\n"):
        raise ValueError("no frontmatter")
    end = text.find("\n---\n", 3)
    if end < 0:
        raise ValueError("frontmatter not closed")
    meta = cc.read_yaml_subset(text[4:end])
    rec = {k: meta.get(k) for k in RECORD_KEYS}
    rec["parent"] = rec["parent"] or None
    if not rec.get("id") or not isinstance(rec.get("order"), int):
        raise ValueError("frontmatter lacks id or order")
    rec["body"] = text[end + 5:]
    return rec


def compile_records(records):
    """The compiled local-context.md: record bodies in ascending `order`."""
    return "".join(r["body"] for r in sorted(records, key=lambda r: r["order"]))


# ------------------------------------------------------------------ store I/O
class StoreError(Exception):
    """A record or the store cannot be read (exit 3)."""


class RegionError(Exception):
    """An edit would land inside a provider's managed region (exit 4)."""


def atomic_write(path, text):
    """Write `text` byte for byte through a hidden temp file in the same folder, then replace."""
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    tmp = os.path.join(folder, ".%s.tmp" % os.path.basename(path))
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


ID_RE = re.compile(r"^[a-z0-9][a-z0-9.-]*$")


class Store:
    """`{root}/records/<id>.md`, `{root}/INDEX.md`, `{root}/.state/{compiled.json, journal.jsonl}`."""

    def __init__(self, root):
        self.root = root
        self.records_dir = os.path.join(root, "records")
        self.state_dir = os.path.join(root, ".state")
        self.card_path = os.path.join(root, "INDEX.md")

    def exists(self):
        return os.path.isdir(self.state_dir)

    def _record_files(self):
        if not os.path.isdir(self.records_dir):
            return [], []
        valid, stray = [], []
        for name in sorted(os.listdir(self.records_dir)):
            if name.startswith(".") or not name.endswith(".md"):
                continue
            (valid if ID_RE.match(name[:-3]) else stray).append(name)
        return valid, stray

    def load(self):
        """Records sorted by `order`. A record that cannot be read or parsed → StoreError naming its file."""
        out = []
        valid, _ = self._record_files()
        for name in valid:
            path = os.path.join(self.records_dir, name)
            try:
                with open(path, encoding="utf-8", newline="") as f:
                    text = f.read()
            except (OSError, UnicodeDecodeError) as e:
                raise StoreError("record not readable: %s (%s)" % (name, e))
            try:
                rec = parse_record(text)
            except ValueError as e:
                raise StoreError("record not valid: %s (%s)" % (name, e))
            if rec["id"] != name[:-3]:
                continue                       # a copy under another name (a sync conflict) — stray
            out.append(rec)
        return sorted(out, key=lambda r: r["order"])

    def stray_files(self):
        """Files in records/ that compile ignores: other names, or a record's copy under another name."""
        valid, stray = self._record_files()
        for name in valid:
            try:
                with open(os.path.join(self.records_dir, name), encoding="utf-8", newline="") as f:
                    if parse_record(f.read())["id"] != name[:-3]:
                        stray.append(name)
            except (OSError, UnicodeDecodeError, ValueError):
                pass
        return sorted(stray)

    def write(self, rec):
        rec = dict(rec, sha=sha_text(rec.get("body") or ""))
        atomic_write(os.path.join(self.records_dir, rec["id"] + ".md"), render_record(rec))
        return rec

    def remove(self, rec_id):
        path = os.path.join(self.records_dir, rec_id + ".md")
        if os.path.exists(path):
            os.remove(path)

    def state(self):
        path = os.path.join(self.state_dir, "compiled.json")
        if not os.path.isfile(path):
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def save_state(self, state):
        atomic_write(os.path.join(self.state_dir, "compiled.json"),
                     json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    def journal(self, entry):
        os.makedirs(self.state_dir, exist_ok=True)
        with open(os.path.join(self.state_dir, "journal.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

    def journal_entries(self):
        path = os.path.join(self.state_dir, "journal.jsonl")
        if not os.path.isfile(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]


# --------------------------------------------------------------- field edits
FIELD_RE = re.compile(r"^- \*\*(?P<name>[^*\n]+?):\*\*[ \t]*(?P<value>[^\r\n]*)")


def _lines(body):
    """[(offset, line_without_ending, ending)] for every line of the body."""
    out, pos = [], 0
    for ln in body.splitlines(keepends=True):
        core = ln.rstrip("\r\n")
        out.append((pos, core, ln[len(core):]))
        pos += len(ln)
    return out


def _in_region(off, spans):
    return any(a <= off < b for a, b in spans)


def field_get(body, name):
    """Value of the first `- **<name>:** value` line outside managed regions, or None."""
    spans = cc.managed_spans(body)
    for off, core, _ in _lines(body):
        m = FIELD_RE.match(core)
        if m and m.group("name").strip() == name and not _in_region(off, spans):
            return m.group("value").strip()
    return None


def field_set(body, name, value):
    """Replace the field's line; an absent field goes after the last line of the first bullet list.
    A field present only inside a managed region → RegionError."""
    spans, lines = cc.managed_spans(body), _lines(body)
    new = "- **%s:** %s" % (name, value)
    inside = False
    for off, core, end in lines:
        m = FIELD_RE.match(core)
        if m and m.group("name").strip() == name:
            if _in_region(off, spans):
                inside = True
                continue
            return body[:off] + new + body[off + len(core):]
    if inside:
        raise RegionError("field %r is inside a provider's managed region" % name)
    first = next((k for k, (off, core, _) in enumerate(lines)
                  if core.startswith("- ") and not _in_region(off, spans)), None)
    if first is None:
        off, core, end = lines[0]
        at, end = off + len(core) + len(end), end or "\n"
    else:
        last = first
        while last + 1 < len(lines) and lines[last + 1][1].startswith("- "):
            last += 1
        off, core, end = lines[last]
        at, end = off + len(core) + len(end), end or "\n"
        if not lines[last][2]:
            return body + "\n" + new
    return body[:at] + new + end + body[at:]


def _level(core):
    m = re.match(r"^(#{1,6}) ", core)
    return len(m.group(1)) if m else 0


def append_line(body, text, under=None):
    """Add `text` after the last non-empty line of the body, or of the subsection whose heading line is
    `under` (up to the next heading of the same or a higher level). An identical line there → unchanged."""
    lines = _lines(body)
    lo, hi = 0, len(lines)
    if under is not None:
        lo = next((k for k, (_, core, _) in enumerate(lines) if core.strip() == under.strip()), None)
        if lo is None:
            raise ValueError("subsection not found: %s" % under)
        lvl = _level(lines[lo][1])
        hi = next((k for k in range(lo + 1, len(lines)) if 0 < _level(lines[k][1]) <= lvl), len(lines))
    if any(core.rstrip() == text.rstrip() for _, core, _ in lines[lo:hi]):
        return body
    last = max((k for k in range(lo, hi) if lines[k][1].strip()), default=lo)
    off, core, end = lines[last]
    if not end:
        return body[:off + len(core)] + "\n" + text + body[off + len(core):]
    at = off + len(core) + len(end)
    return body[:at] + text + end + body[at:]


# ------------------------------------------------------------- context card
CARD_MAX = 200
_EMPTY = ("", "_none_", "none", "—", "-", "n/a")


def _heading_text(core):
    m = re.match(r"^#{1,6} (.*)$", core.lstrip("﻿"))
    return m.group(1).strip() if m else None


def _member_count(body):
    """Rows of the first table after a `Members` heading, or None when there is none (names never leave)."""
    lines = [core for _, core, _ in _lines(body)]
    at = next((k for k, c in enumerate(lines) if (_heading_text(c) or "").startswith("Members")), None)
    if at is None:
        return None
    rows = []
    for c in lines[at + 1:]:
        if _heading_text(c) is not None:
            break
        if c.strip().startswith("|"):
            rows.append(c)
        elif rows and c.strip():
            break
    return max(len(rows) - 2, 0) if rows else None


def _bullets_under(body, name):
    lines = [core for _, core, _ in _lines(body)]
    at = next((k for k, c in enumerate(lines) if _heading_text(c) == name), None)
    out = []
    for c in lines[at + 1:] if at is not None else []:
        if _heading_text(c) is not None:
            break
        if c.startswith("- "):
            out.append(c[2:].strip())
    return out


def _cell(s):
    s = s.replace("|", "\\|")
    return s if len(s) <= 80 else s[:79] + "…"


def _summary(rec):
    if rec["type"] == "team":
        n = _member_count(rec["body"])
        return "%d members" % n if n is not None else "—"
    if rec["type"] == "setting" and rec["title"].startswith("People"):
        return "(people settings — open the record)"
    fence = False
    for _, core, _ in _lines(rec["body"]):
        s = core.strip().lstrip("﻿")
        if s.startswith("```"):
            fence = not fence
            continue
        if fence or not s or _heading_text(s) is not None or s.startswith(("|", "<!--")):
            continue
        for mark in ("- ", "> "):
            if s.startswith(mark):
                s = s[len(mark):].strip()
                break
        return _cell(s)
    return "—"


def build_card(records, compiled_text, now):
    """INDEX.md: who, onboarding, products, teams, vaults and providers, then one row per record; ≤ CARD_MAX lines."""
    recs = sorted(records, key=lambda r: r["order"])
    first = lambda t: next((r for r in recs if r["type"] == t), None)
    over = []
    prof = first("profile")
    if prof:
        name, role, lang = (field_get(prof["body"], k) for k in ("Name", "Role", "Language"))
        parts = [name] if name else []
        parts += ["role %s" % role] if role else []
        parts += ["language %s" % lang] if lang else []
        over.append("- **Who:** " + " · ".join(parts))
    onb = first("onboarding")
    if onb:
        mode, deferred = field_get(onb["body"], "Mode"), field_get(onb["body"], "Deferred steps")
        over.append("- **Onboarding:** %s · deferred: %s" % (mode or "—", "—" if (deferred or "").strip() in _EMPTY else deferred))
    for r in recs:
        if r["type"] == "product":
            parts = []
            jira, space = field_get(r["body"], "Jira Project Key"), field_get(r["body"], "Confluence Space")
            parts += ["Jira %s" % jira] if jira else []
            parts += ["Confluence %s" % space] if space else []
            plats = _bullets_under(r["body"], "Platforms")
            parts += ["platforms %s" % ", ".join(plats)] if plats else []
            over.append("- **Product:** %s%s" % (r["title"].split(":", 1)[-1].strip(), " — " + " · ".join(parts) if parts else ""))
    for r in recs:
        if r["type"] == "team":
            n = _member_count(r["body"])
            over.append("- **Team:** %s%s" % (r["title"].split(":", 1)[-1].strip(), " — %d members" % n if n is not None else ""))
    vaults = ", ".join("%s (%s)" % (f or os.path.basename(p), m or "auto") for p, f, m in cc.vault_modes(compiled_text)) or "—"
    provs = ", ".join(b["id"] for b in cc.vault_search_bullets(compiled_text)) or "—"
    over.append("- **Vaults:** %s · **Providers:** %s" % (vaults, provs))
    head = ["# Context card",
            "> Generated by ctx from %d records on %s. Edit local-context.md or the records, not this card." % (len(recs), now),
            ""]
    table = ["| Record | Title | Summary | Modified |", "|---|---|---|---|"]
    rows = ["| %s | %s | %s | %s |" % (r["id"], _cell(r["title"]), _summary(r), (r.get("modified") or "")[:10]) for r in recs]
    fixed = len(head) + len(over) + 1 + len(table)
    if fixed + len(rows) > CARD_MAX:
        keep = max(CARD_MAX - fixed - 1, 0)
        rows = rows[:keep] + ["| … | +%d more — ctx list | | |" % (len(rows) - keep)]
    return "\n".join(head + over + [""] + table + rows) + "\n"

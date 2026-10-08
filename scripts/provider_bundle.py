#!/usr/bin/env python3
"""provider_bundle.py — copy a role-filtered bundle of a shared-context provider's
core and propose its context blocks for the user's local-context.md (since v3.10.0).

  python3 provider_bundle.py --core <core root> --out <target> --email <e-mail>
          [--manifest <path>] [--team <slug>] [--role <profile>] [--name "Name"]
          [--existing-context <copy of local-context.md>] [--jira-write own|none|ask]
          [--dry-run] [--force] [--in-place] [--no-personal-overlay]
  python3 provider_bundle.py --core <core root> --out <target> --core-export

Everything provider-specific — folders, marker namespace, labels, templates, what is
personal, what must never be copied — comes from the provider manifest
(`_System/provider-manifest.yaml`, references/context-provider-protocol.md §3a, §9).

The user's context is never written: the script writes a PROPOSAL into
<out>/<plugin_folder>/_System/ (local-context.proposed.md, context-merge-report.md,
team-context.md, provider-registration.proposed.yaml) and the connect skill applies
it after the user confirms. Last stdout lines: `CONTEXT_REPORT {json}` and
`BUNDLE_RESULT {json}`.

Exit codes: 0 ok · 2 UNKNOWN_TEAM (one JSON line) · 3 core, manifest or role model
missing · 4 a deny pattern or nested markers in the proposal (nothing written).
Stdlib only. Idempotent: existing files are kept unless --force.
"""
import argparse
import datetime
import glob
import json
import os
import re
import shutil
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ctx_common as cc  # noqa: E402

__version__ = "1.0.0"
N = lambda s: unicodedata.normalize("NFC", s or "")
BUILTIN_TEMPLATES = os.path.join(HERE, "provider_templates")
BUILTIN_EXCLUDE = [r"\.zip$", r"\.plugin$", r"\.tgz$", r"\.tar\.gz$", r"(^|/)__pycache__/", r"\.pyc$",
                   r"\.bak(-|\.|$)", r"\.DS_Store$", r"(^|/)_to_delete/", r"(^|/)local-context[^/]*\.md$"]
DEFAULT_ROLE_HINTS = {
    "leadership": r"\bCPO\b|\bCEO\b|head of|director",
    "analyst": r"analyst|data scien",
    "marketer": r"market|brand|communic",
    "support-lead": r"support|customer care|customer service",
    "engineer": r"engineer|developer|tech ?lead|architect|\bqa\b|devops",
}
DEFAULT_ROLE_ENUM = {"pm": "pm", "analyst": "product_analyst", "leadership": "head_of_product"}
# blocks that are reference-only when the user already has the section (Grow PM's own schema)
REFERENCE_BLOCKS = {
    "organization": r"^##\s+Organization", "product": r"^###\s+Product:", "competitors": r"^#{3,5}\s+Competitors",
    "okr": r"^#{3,5}\s+(?:Current\s+)?OKR", "cjm": r"^#{3,5}\s+CJM", "key-metrics": r"^#{3,5}\s+Key Metrics",
}
DEFAULT_JIRA_LABELS = {
    "own": "own project ({KEY}) — tasks and edits only there, through the plugin's write gate; other projects read only",
    "none": "read only — no writes to Jira or Confluence",
    "ask": "_not decided — the connect flow asks whether you have your own project_",
}


def rd(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def wr(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(N(text))


def split_fm(s):
    m = re.match(r"^---\n(.*?)\n---\n?", s, re.S)
    return (m.group(1), s[m.end():]) if m else ("", s)


def fget(front, k):
    m = re.search(r'^%s:\s*"?(.*?)"?\s*$' % re.escape(k), front, re.M)
    return (m.group(1) if m else "").replace('\\"', '"')


def walk(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if not d.startswith(".") and d != "__pycache__"]
        for f in fn:
            yield os.path.relpath(os.path.join(dp, f), root)


# ------------------------------------------------------------------ manifest
class Manifest(dict):
    def s(self, k, default=""):
        v = self.get(k)
        return default if v in (None, "", []) else v


def load_manifest(core, path=None):
    cands = [path] if path else [os.path.join(core, "_System", "provider-manifest.yaml")] + \
        sorted(glob.glob(os.path.join(core, "*", "_System", "provider-manifest.yaml")))
    for p in cands:
        if p and os.path.isfile(p):
            m = Manifest(cc.read_yaml_subset(rd(p)))
            m["_path"] = os.path.relpath(os.path.abspath(p), os.path.abspath(core))
            pf = m.s("plugin_folder", ".")
            m.setdefault("namespace", m.get("id"))
            for k, sub in (("team_card_dir", "Teams"), ("people_dir", "People")):
                if not m.get(k):
                    m[k] = os.path.normpath(os.path.join(pf, sub))
            return m
    sys.stdout.write("no provider manifest under %s (expected _System/provider-manifest.yaml)\n" % core)
    sys.exit(3)


def template(m, core, name, values):
    tdir = m.s("templates_dir")
    p = os.path.join(core, tdir, name) if tdir else ""
    text = rd(p) if p and os.path.isfile(p) else rd(os.path.join(BUILTIN_TEMPLATES, name))
    for k, v in values.items():
        text = text.replace("{{%s}}" % k, str(v))
    return text


def wikilist(items):
    return ", ".join("[[%s]]" % i for i in items) or "—"


# ------------------------------------------------------- personal layer links
def delink_rx(m):
    targets = [t for t in (m.get("delink_targets") or []) if t]
    if not targets:
        return None
    return re.compile(r"\[\[(?:%s)(?:#[^\]|]*)?(?:\\?\|([^\]]*))?\]\]" % "|".join("(?:%s)" % t for t in targets))


def _link_text(mo):
    label = mo.group(1)
    return label if label else mo.group(0)[2:-2].split("|")[0].split("#")[0].split("/")[-1]


def delink(text, m, rx):
    if rx is None or not rx.search(text):
        return text
    labels = set(m.get("delink_labels") or [])
    out = []
    for ln in text.split("\n"):
        if not rx.search(ln):
            out.append(ln); continue
        rest = rx.sub("", ln)
        toks = re.findall(r"\w[\w'’ʼ-]*", rest)
        if labels and toks and all(t in labels for t in toks):
            continue
        out.append(rx.sub(_link_text, ln))
    t2 = "\n".join(out)
    note = m.s("delink_note")
    if t2 != text and note and note not in t2:
        h1 = re.search(r"^# .*\n", t2, re.M)
        t2 = (t2[:h1.end()] + "\n" + note + "\n" + t2[h1.end():]) if h1 else note + "\n\n" + t2
    return t2


def fix_dashboard(text, have, m, rx):
    out = []
    for ln in text.split("\n"):
        for rule in m.get("dashboard_rewrites") or []:
            if " => " in rule:
                old, new = rule.split(" => ", 1)
                ln = ln.replace(old, new)
        if rx is not None and rx.search(ln):
            if ln.lstrip().startswith("- ") and "[[" not in rx.sub("", ln):
                continue
            ln = rx.sub(_link_text, ln)
        if have and ln.lstrip().startswith("- "):
            links = [x.split("|")[0].split("#")[0].strip() for x in re.findall(r"\[\[([^\]]+)\]\]", ln)]
            if links and not any(l in have or l.split("/")[-1] in have for l in links):
                continue
        out.append(ln)
    return "\n".join(out)


def copy_one(src, dst, rel, m):
    """People cards keep registry fields only; everything else is copied as is."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    people = m.s("people_dir").rstrip("/") + "/"
    if rel.startswith(people) and not os.path.basename(rel).startswith("_") and rel.endswith(".md"):
        s = rd(src)
        note = m.s("people_card_note", "> Registry card from the shared core: registry fields only. "
                                       "Notes and history stay with the %s." % m.s("owner_label", "core owner"))
        if note in s:
            shutil.copy2(src, dst); return
        mo = re.match(r"^---\n.*?\n---\n", s, re.S)
        front, body = (mo.group(0), s[mo.end():]) if mo else ("", s)
        for k in m.get("people_private_fields") or []:
            front = re.sub(r"^%s:.*\n" % re.escape(k), "", front, flags=re.M)
        head = body.split("\n## ", 1)[0].strip()
        wr(dst, front + head + "\n\n" + note + "\n")
    else:
        shutil.copy2(src, dst)


# --------------------------------------------------------- identity helpers
TRANSLIT = {"а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie", "ж": "zh", "з": "z",
            "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
            "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
            "щ": "shch", "ю": "iu", "я": "ia", "ь": "", "ʼ": "", "'": "", "’": ""}


def norm_name(s):
    s = "".join(TRANSLIT.get(c, c) for c in N(s).lower().strip())
    s = re.sub(r"^(ye|ie|y)(?=[aeiou]|v)", "i", s)
    s = re.sub(r"[^a-z ]", "", s)
    return " ".join(sorted(t for t in s.split() if len(t) > 1))


def same_person(a, b):
    na, nb = norm_name(a), norm_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = na.split(), nb.split()
    la, lb = max(ta, key=len), max(tb, key=len)
    close = lambda x, y: x == y or (len(x) > 4 and len(y) > 4 and (x.startswith(y[:5]) or y.startswith(x[:5])))
    return (close(la, lb) and any(close(x, y) for x in ta for y in tb if x != la and y != lb)) or \
        (close(la, lb) and len(ta) == 1)


def norm_team(s):
    s = re.sub(r"\(.*?\)", " ", N(s).lower())
    s = re.sub(r"\bteam\b", " ", s)
    s = re.sub(r"[^\w&+ ]", " ", s)
    return " ".join(s.split())


def infer_role(title, m):
    hints = m.get("role_hints") or DEFAULT_ROLE_HINTS
    for prof, rx in hints.items():
        if re.search(rx, title or "", re.I):
            return prof
    return "pm"


# --------------------------------------------------------- managed blocks
def ns_rx(ns):
    e = re.escape(ns)
    return {
        "block": re.compile(r"(<!-- %s:begin id=([a-z0-9-]+) v=[^>]*-->.*?<!-- %s:end id=\2 -->\n?)" % (e, e), re.S),
        "any": re.compile(r"<!-- %s:begin id=[a-z0-9-]+[^>]*-->.*?<!-- %s:end id=[a-z0-9-]+ -->" % (e, e), re.S),
        "section": re.compile(r"<!-- %s:section:begin -->.*?<!-- %s:section:end -->\n?" % (e, e), re.S),
        "depth": re.compile(r"<!-- %s:(begin|end) id=" % e),
    }


def masked(text, R):
    """Blank out managed blocks and reference sections, keeping offsets, so headings inside them never anchor anything."""
    text = R["section"].sub(lambda mo: "\x01" * len(mo.group(0)), text)
    return R["any"].sub(lambda mo: "\x01" * len(mo.group(0)), text)


def replace_block(text, ns, bid, block):
    e = re.escape(ns)
    # the id ends at a space or at "-->": `id=team` must never match `id=teams …` (a prefix of another block id)
    pat = re.compile(r"<!-- %s:begin id=%s(?:\s[^>]*)?-->.*?<!-- %s:end id=%s -->\n?" % (e, re.escape(bid), e, re.escape(bid)), re.S)
    mo = pat.search(text)
    if not mo:
        return text, False, False
    if mo.group(0).rstrip("\n") == block.rstrip("\n"):
        return text, True, False              # same content: leave the text byte-identical
    return text[:mo.start()] + block + text[mo.end():], True, True


def block_version(block):
    mo = re.search(r"\sv=([^\s>]+)", block.split("-->", 1)[0])
    return mo.group(1) if mo else "?"


def find_anchor(text, R, patterns):
    """Position of the first pattern, in PRIORITY order, that matches outside managed regions."""
    mt = masked(text, R)
    for pattern in patterns:
        mo = re.search(pattern, mt, re.M)
        if mo:
            return mo.start()
    return None


# ------------------------------------------------------------- team block
def team_context(core, m, team, tb, J, jira_write):
    card = os.path.join(core, m.s("team_card_dir"), "team-%s.md" % team)
    front, _ = split_fm(rd(card)) if os.path.isfile(card) else ("", "")
    fields = m.get("card_fields") or {}
    title = fget(front, "title") or tb.get("title") or team
    canonical = fget(front, "canonical") or title.split(" — ")[0]
    jira = fget(front, "jira")
    head = fget(front, fields.get("head", "head"))
    node = fget(front, fields.get("node", "node"))
    keys = [k for k in dict.fromkeys(re.findall(r"\b([A-Z][A-Z0-9]{1,9})\b(?=\s*(?:,|·|\(|$))", jira)) if k not in ("QA", "PM", "UI")] \
        or re.findall(r"\b([A-Z]{2,10})\b", jira)[:1]
    tf = re.search(r"Team\s*=\s*([^·]+)", jira)
    members = []
    pdir = os.path.join(core, m.s("people_dir"))
    for p in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
        if not p.endswith(".md") or p.startswith("_"):
            continue
        pf, _ = split_fm(rd(os.path.join(pdir, p)))
        if "team-%s" % team in fget(pf, "team") and fget(pf, "status") != "former":
            members.append(dict(name=fget(pf, "name"), email=fget(pf, "email"), role=fget(pf, "role"),
                                pos=fget(pf, "position"), head=fget(pf, "is_head") == "true", slug=p[:-3],
                                stub=fget(pf, "registry_stub") == "true"))
    pbase = os.path.basename(m.s("people_dir").rstrip("/"))
    rows = []
    for x in sorted(members, key=lambda x: (not x["head"], x["stub"], x["name"])):
        role = x["role"] if x["role"] and x["role"] != x["pos"] else (m.s("head_role_label", "head") if x["head"] else "—")
        rows.append("| %s%s%s | %s | %s | %s | [[%s/%s]] |" % (x["name"], " ⭐" if x["head"] else "", " ◌" if x["stub"] else "",
                                                             role, x["pos"] or "—", x["email"] or "—", pbase, x["slug"]))
    if not rows:
        rows.append("| _the registry has no one for this team yet — ask the %s_ | | | | |" % m.s("owner_label", "core owner"))
    labels = dict(DEFAULT_JIRA_LABELS); labels.update(m.get("jira_write_labels") or {})
    key0 = keys[0] if keys else "?"
    block = template(m, core, "team-block.md", {
        "NAMESPACE": m["namespace"], "BLOCK_VERSION": J.get("version", "?"), "TEAM_CANONICAL": canonical,
        "TEAM_CARD_PATH": os.path.join(m.s("team_card_dir"), "team-%s.md" % team), "NODE": node or "—",
        "HEAD_SUFFIX": (" — %s %s" % (m.s("head_label", "head:"), head)) if head else "", "HEAD": head or "—", "JIRA": jira or "—",
        "JIRA_KEY": keys[0] if keys else "_ask the team_",
        "JIRA_OTHER": (" (%s %s)" % (m.s("jira_other_label", "others:"), ", ".join(keys[1:]))) if len(keys) > 1 else "",
        "JIRA_TEAM_FIELD": tf.group(1).strip() if tf else "_not set_",
        "JIRA_WRITE_SCOPE": labels.get(jira_write, labels["ask"]).replace("{KEY}", key0),
        "MISSIONS": wikilist(tb.get("missions", [])), "MODULES": wikilist(tb.get("modules", [])),
        "METRICS": wikilist(tb.get("metrics", [])), "PEOPLE_DIR": m.s("people_dir"), "MEMBERS_ROWS": "\n".join(rows)})
    return block.rstrip("\n") + "\n", keys, members, title, canonical


# ------------------------------------------------------------ the proposal
def vsm_bullet(m, team):
    access = (m.get("mcp") or {}).get("access") or "local"
    return "- %s: scope = %s (bundle team-%s), mode = %s, access = %s, read-only" % (
        m["id"], m.s("title", m["id"]), team, m.s("mode", "snapshot"), access)


def put_bullet(t, R, bullet, pid):
    line_rx = re.compile(r"^- %s:.*$" % re.escape(pid), re.M)
    vs = re.search(r"^### Vault Search MCP\s*$", masked(t, R), re.M)
    if vs:
        rest = t[vs.end():]
        stop = re.search(r"^#{1,3} ", rest, re.M)
        seg = rest[:stop.start()] if stop else rest
        cur = line_rx.search(seg)
        if cur and cur.group(0) == bullet:
            return t, "unchanged"
        if cur:
            seg2 = line_rx.sub(lambda mo: bullet, seg, count=1); state = "updated"
        else:
            seg2 = seg.rstrip("\n") + "\n" + bullet + "\n\n"; state = "added"
        return t[:vs.end()] + seg2 + (rest[stop.start():] if stop else ""), state
    ov = re.search(r"^## Obsidian Vaults.*$", masked(t, R), re.M)
    if ov:
        rest = t[ov.end():]
        stop = re.search(r"^## ", rest, re.M)
        pos = ov.end() + (stop.start() if stop else len(rest))
        rule = re.search(r"\n-{3,}[ \t]*\n\s*$", t[ov.end():pos])     # the section closes with a horizontal rule
        if rule:
            pos = ov.end() + rule.start() + 1
        return t[:pos].rstrip("\n") + "\n\n### Vault Search MCP\n" + bullet + "\n\n" + t[pos:].lstrip("\n"), "added"
    pos = find_anchor(t, R, [r"^## Custom Sections"])
    sec = "## Obsidian Vaults (Optional)\n\n### Vault Search MCP\n" + bullet + "\n\n"
    return ((t[:pos] + sec + t[pos:]) if pos is not None else t.rstrip("\n") + "\n\n" + sec), "added"


def build_context(core, out, m, J, ident, existing_path, today, jira_write, skip=()):
    ns, pf = m["namespace"], m.s("plugin_folder", ".")
    R = ns_rx(ns)
    sysd = os.path.join(out, pf, "_System")
    cv = J.get("version", "?")
    bpath = os.path.join(core, m.s("blocks_file")) if m.s("blocks_file") else ""
    corectx = rd(bpath) if bpath and os.path.isfile(bpath) else ""
    skip = [s for s in skip if s and s != "team"]
    blocks = [(blk if blk.endswith("\n") else blk + "\n", bid) for blk, bid in R["block"].findall(corectx) if bid not in skip]
    tblock, keys, members, title, canonical = team_context(core, m, ident["team"], ident["tb"], J, jira_write)
    report = dict(mode="merge" if existing_path else "new", added=[], updated=[], unchanged=[], reference_only=[], retired=[], discrepancies=[],
                  provider_entry=None, jira_keys=keys, members=len(members), jira_write=jira_write,
                  existing_context=existing_path, skipped=sorted(skip))
    bullet = vsm_bullet(m, ident["team"])
    if existing_path:
        ex = rd(existing_path); t = ex
        mex = masked(ex, R)
        emails = {e.lower() for e in re.findall(r"[\w.+-]+@[\w.-]+\.\w+", mex[:4000])}
        if emails and ident["email"] not in emails:
            report["discrepancies"].append(dict(field="email", existing=", ".join(sorted(emails)), core=ident["email"],
                                                ask="Your profile has another e-mail (not even under Work Email). Same person?"))
        mn = re.search(r"^- \*\*Name:\*\*\s*(.+)$", mex, re.M)
        if mn and ident["name"] and not same_person(mn.group(1), ident["name"]):
            report["discrepancies"].append(dict(field="name", existing=mn.group(1).strip(), core=ident["name"],
                                                ask="Your name differs from the registry card (not a transliteration). Which one stays?"))
        prods = re.findall(r"^###\s+Product:\s*(.+)$", mex, re.M)
        pname = m.s("product_name")
        if pname and prods and not any(pname.lower() in p.lower() for p in prods):
            report["discrepancies"].append(dict(field="product", existing=prods, core=pname,
                                                ask="Your context names another product. Add this one as another product, or is it a mistake?"))
        ek = re.findall(r"jira[ _]project[ _]key[^:\n]*:\**\s*`?([A-Z][A-Z0-9]+)", mex, re.I)
        if ek and keys and not set(ek) & set(keys):
            report["discrepancies"].append(dict(field="jira_project_key", existing=ek, core=keys,
                                                ask="Your Jira project differs from the team card. Which is right?"))
        et = re.search(r"^###\s+Team:\s*(.+)$", mex, re.M)
        card = os.path.join(core, m.s("team_card_dir"), "team-%s.md" % ident["team"])
        cf, _ = split_fm(rd(card)) if os.path.isfile(card) else ("", "")
        known = {norm_team(x) for x in re.findall(r'"([^"]+)"', fget(cf, "aliases"))} | \
            {norm_team(canonical), norm_team(title.split(" — ")[0]), norm_team(ident["team"].replace("-", " "))}
        known.discard("")
        if et:
            nt = norm_team(et.group(1))
            if nt and nt not in known and not any(k and (k in nt or nt in k) for k in known):
                report["discrepancies"].append(dict(field="team", existing=et.group(1).strip(), core=title,
                                                    ask="Your context has a team under another name. Same team (add an alias) or another one?"))
        # team block: in place when present, else right after the user's own Team section, else before Analytics
        t, done, changed = replace_block(t, ns, "team", tblock)
        if done:
            report["updated" if changed else "unchanged"].append("team")
        else:
            mt = re.search(r"^###\s+Team:.*$", masked(t, R), re.M)
            pos = None
            if mt:
                nxt = re.search(r"^#{1,3} (?!#)", masked(t, R)[mt.end():], re.M)
                pos = mt.end() + (nxt.start() if nxt else len(t) - mt.end())
            if pos is None:
                pos = find_anchor(t, R, [r"^## Analytics", r"^## Knowledge Library", r"^## Custom Sections"])
            t = (t[:pos].rstrip("\n") + "\n\n" + tblock + "\n" + t[pos:]) if pos is not None else t.rstrip("\n") + "\n\n" + tblock
            report["added"].append("team")
        # every other block: in place wherever it already is (the user's own spot or the reference section);
        # new blocks join the reference section, which is created once at the anchor
        rest = []
        for blk, bid in blocks:
            if bid == "team":
                continue
            t, done, changed = replace_block(t, ns, bid, blk)
            if done:
                report["updated" if changed else "unchanged"].append(bid); continue
            rest.append(blk)
            if bid in REFERENCE_BLOCKS and re.search(REFERENCE_BLOCKS[bid], masked(t, R), re.M):
                report["reference_only"].append(bid)
            else:
                report["added"].append(bid)
        # the provider entry first, so a reference section created next can never end up around it
        t, state = put_bullet(t, R, bullet, m["id"])
        report["provider_entry"] = state
        if rest:
            body = "\n".join(b.rstrip("\n") + "\n" for b in rest).rstrip("\n")
            ms = R["section"].search(t)
            if ms:
                end = t.rfind("<!-- %s:section:end -->" % ns, ms.start(), ms.end())
                t = t[:end].rstrip("\n") + "\n\n" + body + "\n" + t[end:]
            else:
                sec = template(m, core, "context-section.md", {"NAMESPACE": ns, "PROVIDER_TITLE": m.s("title", m["id"]),
                                                              "CORE_VERSION": cv, "BLOCKS": body})
                pos = find_anchor(t, R, [r"^## Custom Sections", r"^## Onboarding Status"])
                t = (t[:pos].rstrip("\n") + "\n\n" + sec.rstrip("\n") + "\n\n" + t[pos:].lstrip("\n")) if pos is not None \
                    else t.rstrip("\n") + "\n\n" + sec
        offered = {bid for _, bid in blocks} | {"team"} | set(skip)
        report["retired"] = sorted(set(re.findall(r"<!-- %s:begin id=([a-z0-9-]+)" % re.escape(ns), t)) - offered)
        ver = {bid: block_version(blk) for blk, bid in blocks}
        ver["team"] = block_version(tblock)
        rows = "".join("| %s `%s` | — | added (v%s) |\n" % (ns, b, ver.get(b, "?")) for b in report["added"]) + \
            "".join("| %s `%s` | previous version | updated (v%s) |\n" % (ns, b, ver.get(b, "?")) for b in report["updated"]) + \
            "".join("| %s `%s` | your section | added for reference (v%s); yours stays primary |\n" % (ns, b, ver.get(b, "?")) for b in report["reference_only"]) + \
            ("| Obsidian Vaults → Vault Search MCP | — | provider `%s` %s |\n" % (m["id"], state) if state != "unchanged" else "")
        if not rows:
            proposed = t                          # nothing changed: the proposal is the user's file, byte for byte
        else:
            t = re.sub(r"^(> Generated:[^\n]*?Updated:\s*)[0-9-]+[^\n]*$", lambda mo: "%s%s (%s refresh)." % (mo.group(1), today, ns), t, count=1, flags=re.M)
            proposed = t.rstrip("\n") + "\n\n### Changelog — %s %s\n\n| Section | Was | Became |\n|---|---|---|\n%s" % (ns, today, rows)
            logs = re.findall(r"\n\n### Changelog — %s .*?(?=\n\n### Changelog — %s |\Z)" % (re.escape(ns), re.escape(ns)), proposed, re.S)
            for old in logs[:-3]:
                proposed = proposed.replace(old, "", 1)
    else:
        sec = template(m, core, "context-section.md", {"NAMESPACE": ns, "PROVIDER_TITLE": m.s("title", m["id"]), "CORE_VERSION": cv,
                                                      "BLOCKS": "\n".join(b.rstrip("\n") + "\n" for b, bid in blocks if bid != "team").rstrip("\n")}) if blocks else ""
        enum = (m.get("role_enum_map") or DEFAULT_ROLE_ENUM).get(ident["role"], "other")
        proposed = template(m, core, "context-skeleton.md", {"TODAY": today, "BUNDLE_BUILDER_VERSION": __version__, "NAME": ident["name"],
                                                             "ROLE_ENUM": enum, "ROLE_TITLE": ident["role_title"] or ident["role"],
                                                             "EMAIL": ident["email"], "TEAM_BLOCK": tblock.rstrip("\n"),
                                                             "SECTION": sec.rstrip("\n"), "VSM_BULLET": bullet})
        report["added"] = [b for _, b in blocks if b != "team"] + ["team"]; report["provider_entry"] = "added"
    deny = [p for p in (m.get("deny_patterns") or []) if p and re.search(p, proposed)]
    if deny:
        sys.stdout.write("DENY pattern in the proposed context — nothing written: %s\n" % ", ".join(deny)); sys.exit(4)
    depth = 0
    for kind in R["depth"].findall(proposed):
        depth += 1 if kind == "begin" else -1
        if depth not in (0, 1):
            sys.stdout.write("nested %s markers in the proposed context — nothing written\n" % ns); sys.exit(4)
    wr(os.path.join(sysd, "team-context.md"), "# Team context — %s\n\n> Generated by the connect flow from the team card; block id=team goes next to your own Team section.\n\n%s" % (ident["team"], tblock))
    if bpath and os.path.isfile(bpath):
        dst = os.path.join(out, m.s("blocks_file"))
        if os.path.abspath(dst) != os.path.abspath(bpath):
            os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(bpath, dst)
    wr(os.path.join(sysd, "local-context.proposed.md"), proposed)
    reg = ["schema: provider-registration/1", "id: %s" % m["id"], "title: %s" % json.dumps(m.s("title", m["id"]), ensure_ascii=False),
           "kind: bundle", "contract: %s" % m.s("contract", "vault/v1"), "authority: %s" % m.s("authority", "org"),
           "mode: %s" % m.s("mode", "snapshot"), "access: %s" % ((m.get("mcp") or {}).get("access") or "local"),
           "paths:", "  - %s" % os.path.abspath(out), "writable:"] + ["  - %s" % g for g in (m.get("personal_overlay") or [])] + \
          (["skip_blocks:"] + ["  - %s" % s for s in skip] if skip else ["skip_blocks: []"]) + \
          ["index: \"\"", "synced_at: %s" % today, "source_version: %s" % json.dumps("core %s, provider_bundle %s" % (cv, __version__)),
           "stale_after_days: 30", "team: team-%s" % ident["team"], "role: %s" % ident["role"], "jira_write: %s" % jira_write, "status: active"]
    if (m.get("personal_overlay") or []) == []:
        reg[reg.index("writable:")] = "writable: []"
    wr(os.path.join(sysd, "provider-registration.proposed.yaml"), "\n".join(reg) + "\n")
    rep = ["# Context merge report — %s" % today, "",
           "- Mode: **%s** · core v%s · provider_bundle %s" % ("merge with your context" if existing_path else "new minimal context", cv, __version__),
           "- Proposal: `%s/_System/local-context.proposed.md` → after you confirm it is copied to `~/.grow-pm/local-context.md` (old one backed up)" % pf,
           "- Added: %s · updated: %s · unchanged: %s · reference only (you have your own section): %s · provider entry: %s" % (
               ", ".join(report["added"]) or "—", ", ".join(report["updated"]) or "—", ", ".join(report["unchanged"]) or "—",
               ", ".join(report["reference_only"]) or "—", report["provider_entry"]),
           "- No longer offered by the core (left where they are, yours to remove): %s" % (", ".join(report["retired"]) or "—"),
           "- Team: jira_project_key %s, jira_write_scope `%s`, members in the registry %d" % (keys or "—", jira_write, len(members)),
           "- Skipped on your request (never proposed): %s" % (", ".join(skip) or "—"), ""]
    if report["discrepancies"]:
        rep += ["## Discrepancies to confirm (nothing overwritten)", "", "| Field | Your context | Core | Question |", "|---|---|---|---|"]
        rep += ["| %s | %s | %s | %s |" % (d["field"], d["existing"], d["core"], d["ask"]) for d in report["discrepancies"]]
    else:
        rep += ["## No discrepancies", ""]
    wr(os.path.join(sysd, "context-merge-report.md"), "\n".join(rep) + "\n")
    print("CONTEXT_REPORT " + json.dumps(report, ensure_ascii=False))
    return report


# ------------------------------------------------------------------- main
def select_files(core, J, m, tb, layers, excluded):
    files = set(J.get("shared", []))
    for pre in J.get("always", []):
        p = os.path.join(core, pre)
        if os.path.isdir(p):
            files.update(os.path.join(pre, r) for r in walk(p))
        elif os.path.isfile(p):
            files.add(pre)
        else:
            d = os.path.dirname(pre) or "."
            if os.path.isdir(os.path.join(core, d)):
                files.update(os.path.join(d, f) for f in os.listdir(os.path.join(core, d)) if f.startswith(os.path.basename(pre)))
    if m.get("_path"):
        files.add(m["_path"])
    enabled = [pre for l in layers for pre in J.get("layer_prefixes", {}).get(l, [])]
    if "all-teams" in layers:
        for t2 in J["teams"].values():
            files.update(t2.get("files", []))
    else:
        card_pre = m.s("team_card_dir").rstrip("/") + "/"
        files.update(f for f in tb.get("files", []) if f.startswith(card_pre) or any(f.startswith(p) for p in enabled))
    return sorted(N(f) for f in files if not excluded(f) and os.path.isfile(os.path.join(core, f)))


def main():
    ap = argparse.ArgumentParser(description="Bundle builder for a shared-context provider (references/context-provider-protocol.md)")
    ap.add_argument("--core", required=True); ap.add_argument("--out", required=True); ap.add_argument("--email")
    ap.add_argument("--manifest"); ap.add_argument("--team"); ap.add_argument("--role"); ap.add_argument("--name")
    ap.add_argument("--existing-context"); ap.add_argument("--jira-write", choices=["own", "none", "ask"], default="ask")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--in-place", action="store_true"); ap.add_argument("--no-personal-overlay", action="store_true")
    ap.add_argument("--core-export", action="store_true"); ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("--skip-blocks", default="", help="comma-separated block ids the user declined; never proposed (kept in the registration)")
    a = ap.parse_args()
    core, out = os.path.abspath(a.core), os.path.abspath(a.out)
    if not os.path.isdir(core):
        sys.stdout.write("core folder not found: %s\n" % core); sys.exit(3)
    m = load_manifest(core, a.manifest)
    if not m.get("id"):
        sys.stdout.write("provider manifest has no id\n"); sys.exit(3)
    jp = os.path.join(core, m.s("bundles_file") or os.path.join(m.s("plugin_folder", "."), "_System", "access-bundles.json"))
    if not os.path.isfile(jp):
        sys.stdout.write("role model not found: %s\n" % jp); sys.exit(3)
    J = json.load(open(jp, encoding="utf-8"))
    exc = re.compile("|".join(BUILTIN_EXCLUDE + [x for x in (m.get("exclude") or []) if x]))
    overlay = m.get("personal_overlay") or []
    excluded = lambda f: bool(exc.search(f)) or cc._writable(f, overlay)
    pf = m.s("plugin_folder", ".")
    pages = m.s("pages_dir").rstrip("/") + "/" if m.s("pages_dir") else None
    rx = delink_rx(m)
    today = datetime.date.today().isoformat()

    if a.core_export:
        files = set(J.get("shared", []))
        for pre in J.get("always", []):
            p = os.path.join(core, pre)
            if os.path.isdir(p):
                files.update(os.path.join(pre, r) for r in walk(p))
            elif os.path.isfile(p):
                files.add(pre)
        for t2 in J["teams"].values():
            files.update(t2.get("files", []))
        if pages and os.path.isdir(os.path.join(core, pages)):
            files.update(os.path.join(pages, r) for r in walk(os.path.join(core, pages)))
        if m.get("_path"):
            files.add(m["_path"])
        files = sorted(N(f) for f in files if not excluded(f) and os.path.isfile(os.path.join(core, f)))
        n = 0
        for f in files:
            dst = os.path.join(out, f)
            if os.path.exists(dst) and not a.force:
                continue
            copy_one(os.path.join(core, f), dst, f, m); n += 1
        for f in files:
            if f.startswith(pf.rstrip("/") + "/") and f.endswith(".md") and f != m.s("dashboard_file"):
                fp = os.path.join(out, f); t = rd(fp); t2 = delink(t, m, rx)
                if t2 != t:
                    wr(fp, t2)
        if m.s("dashboard_file") and os.path.isfile(os.path.join(out, m.s("dashboard_file"))):
            dp = os.path.join(out, m.s("dashboard_file")); wr(dp, fix_dashboard(rd(dp), set(), m, rx))
        print("core export: %d files (pages %d), copied %d → %s · provider_bundle %s" % (
            len(files), sum(1 for f in files if pages and f.startswith(pages)), n, out, __version__))
        return

    email = (a.email or "").strip().lower()
    if not email:
        sys.stdout.write("--email is required (except with --core-export)\n"); sys.exit(3)
    team = a.team or J.get("emails", {}).get(email)
    if not team or team not in J.get("teams", {}):
        print("UNKNOWN_TEAM " + json.dumps(dict(email=email, known=bool(J.get("emails", {}).get(email)),
                                                 teams=sorted(J.get("teams", {})), roles=sorted(J.get("roles", {})),
                                                 directory=m.s("directory_label", "directory")), ensure_ascii=False))
        sys.exit(2)
    tb = J["teams"][team]
    people_pre = m.s("people_dir").rstrip("/") + "/"
    local = email.split("@")[0].replace(".", "-")
    pslug = next((os.path.basename(f)[:-3] for f in tb.get("files", []) if f.startswith(people_pre) and os.path.basename(f)[:-3] == local), None)
    role_title = J.get("people_role", {}).get(pslug or "", "")
    role = a.role or infer_role(role_title, m)
    if role not in J.get("roles", {}):
        sys.stdout.write("role profile '%s' is not in the role model (%s)\n" % (role, ", ".join(sorted(J.get("roles", {}))))); sys.exit(3)
    layers = J["roles"][role]
    files = select_files(core, J, m, tb, layers, excluded)
    conf = sum(1 for f in files if pages and f.startswith(pages))
    print("email %s → team %s (%s) · role %s (%s) · layers %d · files %d (pages %d, umbrella %s) · provider_bundle %s" % (
        email, team, tb.get("title", team), role, role_title or "default", len(layers), len(files), conf,
        "yes" if tb.get("umbrella") else "no", __version__))
    name = a.name
    if not name and pslug and os.path.isfile(os.path.join(core, people_pre, pslug + ".md")):
        name = fget(split_fm(rd(os.path.join(core, people_pre, pslug + ".md")))[0], "name")
    name = name or email
    ident = dict(email=email, name=name, team=team, tb=tb, role=role, role_title=role_title)
    existing = a.existing_context or next((c for c in (os.path.join(out, pf, "_System", "local-context.existing.md"),) if os.path.isfile(c)), None)
    in_place = a.in_place or out == core
    skip = [s.strip() for s in a.skip_blocks.split(",") if s.strip()]
    if a.dry_run:
        print(json.dumps(dict(team=team, role=role, role_title=role_title, files=len(files), pages=conf,
                              modules=tb.get("modules", []), missions=tb.get("missions", []), metrics=tb.get("metrics", []),
                              dashboards=tb.get("dashboards", []), union_of=tb.get("union_of", [])), ensure_ascii=False, indent=1))
        if existing or in_place:
            build_context(core, out, m, J, ident, existing, today, a.jira_write, skip)
        return
    n_new = n_skip = 0
    if not in_place:
        for f in files:
            dst = os.path.join(out, f)
            if os.path.exists(dst) and not a.force:
                n_skip += 1; continue
            copy_one(os.path.join(core, f), dst, f, m); n_new += 1
    notes = m.get("personal_notes") or {}
    now_rel = notes.get("now") or os.path.join(pf, "Now.md")
    todo_rel = (notes.get("todo") or os.path.join(pf, "TODO — {{NAME}}.md")).replace("{{NAME}}", name)
    have = set()
    for f in files + [now_rel, todo_rel]:
        if f.endswith(".md"):
            have |= {f[:-3], os.path.basename(f)[:-3], os.path.relpath(f, pf)[:-3]}
    for f in files:
        if f.startswith(pf.rstrip("/") + "/") and f.endswith(".md") and f != m.s("dashboard_file"):
            fp = os.path.join(out, f)
            if os.path.isfile(fp):
                t = rd(fp); t2 = delink(t, m, rx)
                if t2 != t:
                    wr(fp, t2)
    if m.s("dashboard_file") and os.path.isfile(os.path.join(out, m.s("dashboard_file"))):
        dp = os.path.join(out, m.s("dashboard_file")); wr(dp, fix_dashboard(rd(dp), have, m, rx))
    if not in_place:
        for f in (".obsidian/app.json", ".obsidian/appearance.json", ".obsidian/backlink.json", ".obsidian/core-plugins.json", ".obsidian/graph.json"):
            if os.path.isfile(os.path.join(core, f)) and not os.path.exists(os.path.join(out, f)):
                os.makedirs(os.path.join(out, ".obsidian"), exist_ok=True); shutil.copy2(os.path.join(core, f), os.path.join(out, f))
    report = build_context(core, out, m, J, ident, existing, today, a.jira_write, skip)
    pbase = os.path.basename(m.s("people_dir").rstrip("/"))
    own = []
    mdir = os.path.join(core, m.s("missions_dir")) if m.s("missions_dir") else ""
    for mp in sorted(glob.glob(os.path.join(mdir, "*.md"))) if mdir else []:
        if not os.path.basename(mp).startswith("_") and pslug and "%s/%s" % (pbase, pslug) in fget(split_fm(rd(mp))[0], "owner"):
            own.append(os.path.basename(mp)[:-3])
    card_link = os.path.relpath(os.path.join(m.s("team_card_dir"), "team-%s" % team), pf)
    values = {"NAME": name, "EMAIL": email, "TODAY": today, "TEAM_SLUG": team, "TEAM_TITLE": tb.get("title", team),
              "TEAM_CANONICAL": tb.get("title", team).split(" — ")[0], "TEAM_CARD": card_link, "ROLE": role,
              "ROLE_TITLE": role_title or role, "OWN_MISSIONS": wikilist(own),
              "TEAM_MISSIONS": wikilist([x for x in tb.get("missions", []) if x not in own]),
              "OWNER_LABEL": m.s("owner_label", "core owner"), "PLUGIN_FOLDER": pf, "PSLUG": pslug or local}
    if not a.no_personal_overlay:
        for rel, tpl in ((now_rel, "now.md"), (todo_rel, "todo.md")):
            p = os.path.join(out, rel)
            if not os.path.exists(p) or a.force:
                wr(p, template(m, core, tpl, values))
    if not pslug:
        card = os.path.join(out, people_pre, local + ".md")
        if not os.path.exists(card):
            wr(card, template(m, core, "person-card.md", values))
    body = template(m, core, "bundle-manifest.md", dict(values, **{
        "TEAM_SCOPE": ("umbrella: " + ", ".join(tb.get("union_of", []))) if tb.get("umbrella") else "department " + str(tb.get("department", "—")),
        "LAYERS": ", ".join(layers), "FILES": len(files), "PAGES": conf,
        "COPY_SUMMARY": "in-place — the folder already holds the core" if in_place else "copied %d new, kept %d existing" % (n_new, n_skip),
        "MODULES": wikilist(tb.get("modules", [])), "MISSIONS": wikilist(tb.get("missions", [])), "METRICS": wikilist(tb.get("metrics", [])),
        "DASHBOARDS": ", ".join(tb.get("dashboards", [])) or "—", "JIRA_WRITE": a.jira_write, "MODE": report["mode"]}))
    front = "\n".join(['---', 'title: "bundle-manifest"', 'type: bundle-manifest', 'updated: %s' % today, 'email: "%s"' % email,
                       'team: "team-%s"' % team, 'role_profile: %s' % role, 'core_version: "%s"' % J.get("version", "?"),
                       'bundle_builder_version: "%s"' % __version__, 'provider: %s' % m["id"], 'files: %d' % len(files), '---', ''])
    wr(os.path.join(out, pf, "_System", "bundle-manifest.md"), front + body)
    wr(os.path.join(out, pf, "_System", "bundle-files.txt"), "\n".join(files) + "\n")
    print("BUNDLE_RESULT " + json.dumps(dict(team=team, role=role, files=len(files), pages=conf, new=n_new, skipped=n_skip,
                                             in_place=in_place, manifest=os.path.join(pf, "_System", "bundle-manifest.md")), ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Grow PM — the human changelog of the context store (since v3.23.0; references/context-protocol.md §5p).

`ctx history` reads `.state/journal.jsonl` and writes one note per month, `{store}/history/YYYY-MM.md`, to be read in
Obsidian: Keep a Changelog, the newest day first. A core release (a provider pass whose version moved) is a section
`## [<repo> <v>] — <day>` with «Блок | Було | Стало» from the base texts the store keeps (`was` → `taken`); a pass of
the same version is `## <repo> — <day>`; your own changes of a day are `## Твої зміни — <day>` with «Запис | Що | Було
| Стало» from the lines' `changes` and one line for each change that has no values (a line of v3.22, a memory, an
answer). The note is derived: it has no journal line of its own, is not in the snapshots, and is rewritten whole —
only when its text changed — after every writing command (the month of that command) and by `ctx history --write`.

- build(store, month)      the note's text
- write(store, month)      (path, changed) — atomic, through the write allow-list
Stdlib only.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_store as cs  # noqa: E402

MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
PROVIDER_OPS = ("provider-apply", "provider-sync")
BASE_READ_S = 1.0
OWN_ROWS_PER_DAY = 40                                   # a day's table of your changes, then «ще N»
LINE_OPS = ("overlay", "undo", "identity")        # said as one line, never as the block text they rewrote
ROWS_PER_BLOCK = 10
OP_WORDS = {"sync": "імпорт прямих правок", "set": "поле", "append": "рядок", "add": "новий запис", "migrate": "перенесення в записи",
            "invalidate": "неактуальне", "archive": "в архів", "restore": "повернено", "verify": "перевірено", "assign": "хто читає",
            "slot": "слоти", "propose": "у скриньку", "inbox-accept": "прийнято зі скриньки", "inbox-reject": "відхилено зі скриньки",
            "bootstrap": "налаштування з конекторів", "overlay": "поправки до ядра", "provider-adopt": "бази ядра",
            "entity": "сутності", "entity-apply": "мости в нотатках", "undo": "↩ ctx undo", "snapshot": "знімок",
            "compile": "компіляція", "search": "вибір у пошуку", "snapshot-import": "старі бекапи як знімки"}


def _cell(text):
    t = (text or "").replace("|", "\\|").replace("\r", "").strip()
    return t.replace("\n", "<br>") if t else "—"


def _base(store, repo, sha):
    if not sha or not re.fullmatch(r"[0-9a-f]{64}", str(sha)):
        return None
    path = os.path.join(store.state_dir, "blocks", repo, sha + ".md")
    try:
        return cs.read_text(path, timeout=BASE_READ_S)  # an evicted base costs a second, never a hang
    except (OSError, UnicodeDecodeError, cs.StoreError):
        return None


def _inner(region):
    lines = (region or "").replace("\r\n", "\n").split("\n")
    return [ln for ln in lines if not ln.lstrip().startswith("<!--")]


def _block_rows(store, repo, bid, was, now_sha):
    """The «Блок | Було | Стало» rows of one block of a provider pass."""
    if now_sha == "removed":
        return ["| %s | блок | прибрано ядром |" % _cell(bid)]
    old, new = _base(store, repo, was), _base(store, repo, now_sha)
    if not was:
        return ["| %s | — | новий блок |" % _cell(bid)]
    if old is None or new is None:
        return ["| %s | база вже не зберігається | — |" % _cell(bid)]
    import difflib
    rows = []
    a, b = _inner(old), _inner(new)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        olds, news = [x for x in a[i1:i2] if x.strip()], [x for x in b[j1:j2] if x.strip()]
        for k in range(max(len(olds), len(news))):
            rows.append("| %s | %s | %s |" % (_cell(bid), _cell(olds[k] if k < len(olds) else ""),
                                               _cell(news[k] if k < len(news) else "")))
    if not rows:
        return []                                       # the version alone: said once under the table (`build`)
    return rows[:ROWS_PER_BLOCK] + (["| %s | … | ще %d |" % (_cell(bid), len(rows) - ROWS_PER_BLOCK)] if len(rows) > ROWS_PER_BLOCK else [])


def _repo_of(entry):
    src = str(entry.get("source") or "")
    return src[5:] if src.startswith("repo:") else (entry.get("repo") or "?")


def _line(entry):
    """One line for a change with no values: the time, what kind, the records, the reason."""
    op = entry.get("op") or "?"
    bits = ["%s · %s" % ((entry.get("ts") or "")[11:16] or "—", OP_WORDS.get(op, op))]
    if entry.get("action"):
        bits.append(str(entry["action"]))
    if entry.get("what"):
        bits.append(str(entry["what"]))
    if entry.get("repo"):
        bits.append(str(entry["repo"]))
    if entry.get("ids"):
        bits.append(", ".join(str(x) for x in entry["ids"][:6]) + (" …" if len(entry["ids"]) > 6 else ""))
    if entry.get("skill"):
        bits.append(str(entry["skill"]))
    if entry.get("overlay"):
        bits.append("блоки: " + ", ".join(sorted(entry["overlay"])))
    if entry.get("reason"):
        bits.append(os.path.basename(str(entry["reason"])) if op == "undo" else str(entry["reason"]))
    return "- " + " · ".join(b.replace("\n", " ") for b in bits)


def _entries(store):
    """The journal's lines; a line that does not parse (cut by a crash) is passed over, never a reason to stop."""
    path = os.path.join(store.state_dir, "journal.jsonl")
    try:
        text = cs.read_text(path, timeout=5.0)
    except (OSError, UnicodeDecodeError, cs.StoreError):
        return []
    out = []
    for line in text.splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict):
            out.append(e)
    return out


def build(store, month):
    """The note of `month` (YYYY-MM): its frontmatter, title and sections, the newest day first."""
    if not MONTH.match(month or ""):
        raise ValueError("month is YYYY-MM, not %r" % month)
    days = {}
    for e in _entries(store):
        ts = str(e.get("ts") or "")
        if ts[:7] != month:
            continue
        days.setdefault(ts[:10], []).append(e)
    out = ["---", "type: system", "kind: context-history", "month: %s" % month, "---",
           "# Журнал змін контексту — %s" % month, "",
           "> Новіші зверху. «Було | Стало» — для змін від v3.23.0 і для релізів ядра, бази яких ще зберігаються. "
           "Нотатку переписує `ctx` після кожної зміни — правити її немає сенсу.", ""]
    if not days:
        return "\n".join(out + ["За цей місяць змін не було.", ""])
    for day in sorted(days, reverse=True):
        entries = sorted(days[day], key=lambda e: str(e.get("ts")), reverse=True)
        for e in entries:
            if e.get("op") not in PROVIDER_OPS:
                continue
            repo, frm, to = _repo_of(e), e.get("from_v"), e.get("to_v")
            head = "## [%s %s] — %s" % (repo, to, day) if to and to != frm else "## %s — %s" % (repo, day)
            out += [head, "", "%s · %s%s" % ((e.get("ts") or "")[11:16], "синк ядра" if e["op"] == "provider-sync" else "оновлення ядра",
                                             (" · v%s → v%s" % (frm, to)) if frm and to and frm != to else ""), ""]
            taken, was = e.get("taken") or {}, e.get("was") or {}
            per = {bid: _block_rows(store, repo, bid, was.get(bid), taken[bid]) for bid in sorted(taken)}
            rows = [r for bid in sorted(per) for r in per[bid]]
            if rows:
                out += ["| Блок | Було | Стало |", "|---|---|---|"] + rows + [""]
            same = [bid for bid in sorted(per) if not per[bid]]
            if same:
                out.append("- лише версія: %s" % ", ".join(same))
            if e.get("pending"):
                out.append("- чекає рішення: %s" % ", ".join(e["pending"]))
            held = e.get("overlay_held") or {}
            if held:
                out.append("- оверлей чекає рішення: %s" % ", ".join("%s (%s)" % (i, b) for b in sorted(held) for i in held[b]))
            if e.get("proposed"):
                out.append("- пропозицій ядра у твої секції: %d (у скриньці)" % len(e["proposed"]))
            out.append("")
        own = [e for e in entries if e.get("op") not in PROVIDER_OPS]
        if not own:
            continue
        out += ["## Твої зміни — %s" % day, ""]
        rows = [c for e in own if e.get("op") not in LINE_OPS for c in e.get("changes") or []]
        if rows:
            out += ["| Запис | Що | Було | Стало |", "|---|---|---|---|"]
            out += ["| %s | %s | %s | %s |" % (_cell(c.get("id")), _cell(c.get("where")), _cell(c.get("was")), _cell(c.get("became")))
                    for c in rows[:OWN_ROWS_PER_DAY]]
            out += (["| … | ще %d змін | | |" % (len(rows) - OWN_ROWS_PER_DAY)] if len(rows) > OWN_ROWS_PER_DAY else []) + [""]
        lines = [_line(e) for e in own if not e.get("changes") or e.get("op") in LINE_OPS]
        if lines:
            out += lines + [""]
    return "\n".join(out)


def path_of(store, month):
    return os.path.join(store.root, "history", month + ".md")


def write(store, month):
    """Write the note of `month` when its text changed. Returns (path, changed)."""
    text = build(store, month)
    path = path_of(store, month)
    try:
        if cs.read_text(path, timeout=BASE_READ_S) == text:
            return path, False
    except (OSError, UnicodeDecodeError, cs.StoreError):
        pass
    os.makedirs(cs.check_target(os.path.dirname(path)), exist_ok=True)
    cs.atomic_write(path, text)
    return path, True

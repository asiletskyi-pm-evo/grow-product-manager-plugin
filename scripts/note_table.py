#!/usr/bin/env python3
"""note_table.py — what a note-as-source-of-truth script shares (since v4.7.0): reading the note and its frontmatter,
the cells of a markdown table, a page-safe string (links removed, a secret hidden, every text escaped), and the
protocol-table readers a validate check uses. Used by story_map.py (references/story-map-protocol.md) and
journey_map.py (references/journey-protocol.md); a library, no command line. Stdlib only (Python 3.9).
"""
import html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ctx_common as cc  # noqa: E402
import ctx_never as cn  # noqa: E402
import publications as pub  # noqa: E402

LINK = re.compile(r"(?:https?|ftp)://\S+|\bwww\.\S+"                       # a link with a scheme, or www.
                  r"|[\w.+-]+:[^\s@/]+@[\w-]+(?:\.[\w-]+)+\S*"               # user:password@host…
                  r"|\b(?:[a-z0-9-]+\.)+[a-z]{2,}/\S*", re.I)                # host.domain/path, no scheme
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Bad(Exception):
    """A note (or another input) that does not read — the scripts exit 2."""


def read_note(path):
    """(text, frontmatter with LF line ends, body with LF line ends) of a note — raises Bad."""
    try:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    except OSError as e:
        raise Bad("the note does not read: %s" % (e.strerror or type(e).__name__))
    except UnicodeDecodeError:
        raise Bad("the note is not UTF-8 text")
    span = pub._frontmatter(text)
    if not span:
        raise Bad("the note has no frontmatter")
    start, end, _ = span
    return text, text[start:end].replace("\r\n", "\n"), text[end:].replace("\r\n", "\n")


def fm_scalar(fm, name):
    """A top-level scalar of a frontmatter, as a string ("" when absent, a list or unreadable)."""
    m = re.search(r"^%s[ \t]*:[ \t]*(.*?)[ \t]*$" % re.escape(name), fm, re.M)
    if not m:
        return ""
    try:
        v = cc._scalar(cc._strip_comment(m.group(1)), 0)
    except (ValueError, json.JSONDecodeError):
        return ""
    return str(v).strip() if isinstance(v, (str, int, float)) and not isinstance(v, bool) else ""


def cells(line):
    """The cells of one markdown table row; `\\|` is a pipe inside a cell."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", s)]


def row_line(values):
    """One markdown table row from cell values — a pipe inside a cell escaped, a line break flattened, an empty cell
    written `| |` as a person types it."""
    out = []
    for v in values:
        v = re.sub(r"[\r\n]+", " ", str(v or "")).replace("|", "\\|").strip()
        out.append(" %s " % v if v else " ")
    return "|" + "|".join(out) + "|"


def is_separator(cs):
    return all(re.fullmatch(r":?-+:?", c) for c in cs if c)


def tables(body):
    """[(first line number, [lines])] — every run of lines that starts with `|`."""
    out, cur, start = [], [], 0
    for i, line in enumerate(body.split("\n")):
        if line.strip().startswith("|"):
            if not cur:
                start = i
            cur.append(line.rstrip("\r"))
        elif cur:
            out.append((start, cur))
            cur = []
    if cur:
        out.append((start, cur))
    return out


def esc(s):
    return html.escape(str(s), quote=True)


def safe(s):
    """A string fit for a page or a board: links removed, a string holding a secret or an identifier hidden whole (ctx_never)."""
    s = LINK.sub("[link removed]", str(s or ""))
    kinds = cn.scan(s)
    return "[hidden: %s]" % ", ".join(kinds) if kinds else s


def shown(s):
    return esc(safe(s))


# ------------------------------------------------------------------ protocol tables (validate checks)
def section(text, head):
    m = re.search(r"^## %s.*?(?=^## |\Z)" % re.escape(head), text, re.M | re.S)
    return m.group(0) if m else ""


def table_after(sec, header_re):
    m = re.search(header_re + r".*?(?=\n\n|\Z)", sec, re.S)
    if not m:
        return []
    rows = []
    for line in m.group(0).split("\n")[2:]:
        if line.strip().startswith("|"):
            rows.append(cells(line))
    return rows


def tick(cell):
    m = re.match(r"\s*`([^`]+)`", cell or "")
    return m.group(1) if m else None


def cmd_name(cell):
    m = re.match(r"\s*`([a-z-]+)", cell or "")
    return m.group(1) if m else "?"

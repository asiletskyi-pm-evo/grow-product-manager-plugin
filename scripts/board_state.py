#!/usr/bin/env python3
"""board_state.py — a board read back, in one item format (since v4.8.0): a Miro board's SVG, the host board type's
element list saved to a file, and the area to read back. Used by story_map.py (references/story-map-protocol.md §8)
and journey_map.py (references/journey-protocol.md §12); a library, no command line. Stdlib only (Python 3.9).

An item is `{id, kind, text, x, y, rx, ry, w, h, frame, frame_text}`:
- `kind` — `frame` (a Miro frame, a section of the host's board), `sticky` (a Miro sticky note, a person's note on the
  host's board, the plugin's rounded block there), `connector`, or the element's own kind;
- `x`, `y` — absolute, in board coordinates; `rx`, `ry` — relative to the frame it sits in, so a dragged frame moves
  the frame, not every sticky in it;
- `frame`, `frame_text` — the id and the title of that frame (none: `None`, "").
An item of the host's board also keeps the element's own `type` (note, shape, container …). Nothing else of an element
is ever kept — not its author, its author's id, its votes, its colour or its comments: a board state stays free of
names (references/journey-protocol.md §12).

Which frame an element of the host's board sits in is geometry alone — a section there does not record what it holds:
the SMALLEST section whose box holds the element's centre (a point for an element with no size). Miro's SVG nests an
element inside its frame, and the nesting says it.
"""
import html, json, os, re, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import note_table as nt  # noqa: E402

Bad = nt.Bad   # a board read that does not parse — the scripts exit 2
SCOPE_MARGIN = 200
SURFACES = ("miro", "whiteboard")   # the format of a read: a Miro SVG, or the host board type's element list
STICKY_SHAPES = ("rounded",)        # the plugin's sticky on the host's board: a rounded block (the type's own rule)
KINDS = {"container": "frame", "note": "sticky", "arrow": "connector"}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ Miro (moved from story_map.py, v4.6.0, unchanged)
def _translate(tr):
    m = re.search(r"translate\(\s*([-\d.eE]+)(?:[\s,]+([-\d.eE]+))?\s*\)", tr or "")
    if m:
        return float(m.group(1)), float(m.group(2) or 0)
    m = re.search(r"matrix\(([^)]*)\)", tr or "")
    if m:
        parts = [float(x) for x in re.split(r"[\s,]+", m.group(1).strip()) if x]
        if len(parts) == 6:
            return parts[4], parts[5]
    return 0.0, 0.0


def plain(s):
    """A sticky's words without markup: a line break or a paragraph a space, tags dropped, entities read."""
    s = re.sub(r"<br\s*/?>|</p>\s*<p[^>]*>", " ", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def _own_text(el):
    parts = [el.text or ""]
    for ch in el:
        if ch.get("data-miro-id") is None:
            parts.append(_own_text(ch))
        parts.append(ch.tail or "")
    return "".join(parts)


def read_miro_svg(path):
    """{id: item} of the elements of a board SVG that carry a data-miro-id — raises Bad. An item's `x`, `y` are absolute;
    `rx`, `ry` are relative to the frame it sits in (a frame's own translate is relative to its parent frame), so a
    dragged frame moves the frame, not every card in it."""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as e:
        raise Bad("the board does not read: %s" % (getattr(e, "strerror", None) or str(e)[:120]))
    items = {}

    def walk(el, ox, oy, frame, frame_text):
        tag = el.tag.split("}")[-1]
        dx, dy = _translate(el.get("transform")) if tag == "g" else (0.0, 0.0)
        nox, noy = ox + dx, oy + dy
        mid = el.get("data-miro-id")
        if tag == "g" and el.get("data-frame") is not None:
            rect = next((c for c in el if c.get("data-type") == "frame"), None)
            title = el.get("data-frame") or (rect.get("data-title") if rect is not None else "") or ""
            mid = mid or (rect.get("data-miro-id") if rect is not None else None)
            w = _num(rect.get("width")) if rect is not None else None
            h = _num(rect.get("height")) if rect is not None else None
            if mid:
                items[mid] = {"id": mid, "kind": "frame", "text": plain(title), "x": nox, "y": noy, "rx": dx, "ry": dy,
                              "w": w, "h": h, "frame": frame, "frame_text": frame_text}
            for c in el:
                if c is not rect:
                    walk(c, nox, noy, mid or frame, plain(title) if mid else frame_text)
            return
        if mid and el.get("data-type") != "frame":
            x = _num(el.get("x")) if el.get("x") is not None else _num(el.get("cx"))
            y = _num(el.get("y")) if el.get("y") is not None else _num(el.get("cy"))
            body = el.get("data-content")
            if body is None:
                body = el.get("data-title") or _own_text(el)
            items[mid] = {"id": mid, "kind": el.get("data-type") or tag, "text": plain(body),
                          "x": (x or 0.0) + nox, "y": (y or 0.0) + noy, "rx": (x or 0.0) + nox - ox, "ry": (y or 0.0) + noy - oy,
                          "w": _num(el.get("width")), "h": _num(el.get("height")), "frame": frame, "frame_text": frame_text}
        for c in el:
            walk(c, nox, noy, frame, frame_text)

    walk(root, 0.0, 0.0, None, "")
    return items


# ------------------------------------------------------------------ the host's board type (v4.8.0)
def _rows(path):
    """[(id, element)] of a saved `list elements`: a folder of `<id>.json` files (an out_dir read, or its elements/
    subfolder), or one JSON file — a list of `{id, data, …}` rows, or a mapping id → element, alone or under `elements`."""
    if os.path.isdir(path):
        folder = os.path.join(path, "elements") if os.path.isdir(os.path.join(path, "elements")) else path
        out = []
        for n in sorted(os.listdir(folder)):
            if not n.endswith(".json"):
                continue
            try:
                with open(os.path.join(folder, n), encoding="utf-8") as fh:
                    out.append((n[:-5], json.load(fh)))
            except (OSError, ValueError) as e:
                raise Bad("the board's element %s does not read: %s" % (n, getattr(e, "strerror", None) or type(e).__name__))
        return out
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise Bad("the board does not read: %s" % (getattr(e, "strerror", None) or type(e).__name__))
    if isinstance(data, dict) and isinstance(data.get("elements"), (dict, list)):
        data = data["elements"]
    if isinstance(data, dict):
        return [(str(k), v) for k, v in data.items()]
    if isinstance(data, list):
        out = []
        for r in data:
            if isinstance(r, dict) and r.get("id") not in (None, ""):
                out.append((str(r["id"]), r["data"] if "data" in r else {k: v for k, v in r.items() if k != "id"}))
        return out
    raise Bad("the board's element list is neither a list nor a mapping")


def read_whiteboard(path):
    """{id: item} of a saved `list elements` of the host's board type — raises Bad. A section is a frame; an element sits
    in the smallest section that holds its centre; only the item's fields are kept (never an author)."""
    items, placed = {}, set()
    for eid, data in _rows(path):
        if not isinstance(data, dict):
            continue
        typ = str(data.get("type") or "")
        kind = KINDS.get(typ, typ or "other")
        if typ == "shape":
            kind = "sticky" if data.get("kind") in STICKY_SHAPES else "shape"
        text = data.get("label") if typ == "arrow" else data.get("title") if typ == "link" else data.get("text")
        x, y = _num(data.get("x")), _num(data.get("y"))
        if x is not None and y is not None and typ != "arrow":
            placed.add(eid)
        x, y = x or 0.0, y or 0.0
        out = {"id": eid, "kind": kind, "text": re.sub(r"\s+", " ", text).strip() if isinstance(text, str) else "",
               "x": x, "y": y, "rx": x, "ry": y, "w": _num(data.get("w")), "h": _num(data.get("h")),
               "frame": None, "frame_text": "", "type": typ}
        items[eid] = out
    secs = [s for s in items.values() if s["type"] == "container" and s["w"] and s["h"]]
    for it in items.values():
        if it["id"] not in placed:
            continue
        cx, cy = it["x"] + (it["w"] or 0) / 2.0, it["y"] + (it["h"] or 0) / 2.0
        area = (it["w"] or 0) * (it["h"] or 0)
        holders = [s for s in secs if s is not it and s["x"] <= cx <= s["x"] + s["w"] and s["y"] <= cy <= s["y"] + s["h"]
                   and (it["type"] != "container" or s["w"] * s["h"] > area)]
        if holders:
            s = min(holders, key=lambda c: c["w"] * c["h"])
            it["frame"], it["frame_text"] = s["id"], s["text"]
            it["rx"], it["ry"] = it["x"] - s["x"], it["y"] - s["y"]
    return items


# ------------------------------------------------------------------ either
def read_board(path, surface=None):
    """{id: item} of one read — the surface named, else by the file: an .svg is Miro's, a .json or a folder the host's."""
    if surface is None:
        surface = "miro" if str(path).lower().endswith(".svg") else "whiteboard"
    if surface not in SURFACES:
        raise Bad("an unknown board surface %r (%s)" % (surface, ", ".join(SURFACES)))
    return read_miro_svg(path) if surface == "miro" else read_whiteboard(path)


def read_boards(paths, surface=None):
    items = {}
    for path in paths:
        for mid, it in read_board(path, surface).items():
            items.setdefault(mid, it)               # the first read of an element wins (the read by ids comes first)
    return items


def scope(items):
    """The area to read back: the items' box with a margin, or None when there is nothing."""
    xs, ys, xe, ye = [], [], [], []
    for it in items.values():
        xs.append(it["x"]); ys.append(it["y"])
        xe.append(it["x"] + (it["w"] or 0)); ye.append(it["y"] + (it["h"] or 0))
    if not xs:
        return None
    x0, y0 = int(min(xs)) - SCOPE_MARGIN, int(min(ys)) - SCOPE_MARGIN
    return {"x": x0, "y": y0, "width": int(max(xe)) + SCOPE_MARGIN - x0, "height": int(max(ye)) + SCOPE_MARGIN - y0}

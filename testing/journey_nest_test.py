#!/usr/bin/env python3
"""TC-journey-4100-nest — nested journey maps (v4.10.0, references/journey-protocol.md §14).

Fictional «Zorg» maps (testing/fixtures/journey/nest/) are copied into a temp folder: «Перше замовлення» → «Оплата»
(s5, крок «Оплата карткою») → «3-D Secure» (s3, крок «3-D Secure») → «Повтор коду» (a fourth level), «Вибір доставки»
on s4 with no step, a cycle (loop-a ↔ loop-b), another product's child (acme), an orphan (its parent does not exist),
a child whose step the parent's rows do not have, and a map that is its own parent.

- nest (§1): the tree in the parent's stage order, absolute levels (root → child → grandchild), a fourth level only as a
  reference; the roll-up of each child — the pains its page shows by class (a simulated or unsourced pain is none, a
  health-check row is no pain), its anomalies with the critical ones by refresh's own end label, its journey-level
  metric else «⚠️ TBD», its last health point else «немає знімка», its review date; the findings orphan_child,
  nest_cycle, too_deep, other_product_parent, self_parent; nothing written, no row text of a child but its outcome
  metric; a cycle ends; candidates by --map, --dir or the note's own folder; a hand CJM note never nests.
- regression (§9): a map with no children behaves as in v4.9.0 — render-html, board-layout, parse, check and refresh of
  testing/fixtures/journey/journey-first-order.md equal the goldens kept from 332d1a5.
Mutations from the plan — a child's row copied into the parent, a fourth level shown in full, a cycle that loops, the
child's health-check rows counted as pains, a critical anomaly found by a word of its own — each go red. Stdlib only;
run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/journey_nest_test.py
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "journey_map.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "journey")
GOLD = os.path.join(FIX, "nest", "golden")
TODAY = "2026-11-24"

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


SAFE_HOME = tempfile.mkdtemp(prefix="journey-nest-home-")


def run(*args, script=SCRIPT, timeout=60):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GROW_PM_")}
    env["HOME"] = SAFE_HOME
    try:
        p = subprocess.run([sys.executable, script] + list(args), capture_output=True, text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timeout after %ds" % timeout, {}
    res = {}
    for line in p.stdout.splitlines():
        if line.startswith("JOURNEY_RESULT "):
            res = json.loads(line[len("JOURNEY_RESULT "):])
    return p.returncode, p.stdout + p.stderr, res


def read(p):
    with open(p, "rb") as f:
        return f.read()


def write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def text(p):
    return read(p).decode("utf-8")


def digest(folder):
    out = {}
    for n in sorted(os.listdir(folder)):
        p = os.path.join(folder, n)
        if os.path.isfile(p):
            out[n] = hashlib.sha256(read(p)).hexdigest()
    return out


def mutant(d, name, old, new, target="journey_map.py"):
    """A copy of the scripts folder where `old` became `new` in `target`; None when `old` is not there."""
    sdir = os.path.dirname(SCRIPT)
    src = open(os.path.join(sdir, target), encoding="utf-8").read()
    if old not in src:
        return None
    mdir = os.path.join(d, "mut-" + name)
    os.makedirs(mdir)
    for f in os.listdir(sdir):
        if f.endswith(".py"):
            shutil.copy(os.path.join(sdir, f), mdir)
    with open(os.path.join(mdir, target), "w", encoding="utf-8") as f:
        f.write(src.replace(old, new, 1))
    return os.path.join(mdir, "journey_map.py")


def findings_of(res, code):
    return [f for f in res.get("findings", []) if f.get("finding") == code]


def node(tree, note):
    """The node of `note` (its file name without .md) anywhere in a nest tree."""
    if not isinstance(tree, dict):
        return None
    if tree.get("note") == note:
        return tree
    for k in tree.get("children", []):
        n = node(k, note)
        if n is not None:
            return n
    return None


def date_free(s):
    return re.sub(r"(Згенеровано|Generated): \d{4}-\d{2}-\d{2}", r"\1: DATE", s)


def board_items(layout, base=0):
    """A board as the model would build it from a board-layout (one id per element, stable across reads): the title,
    the stage headers, a frame per cell, a sticky per row, and on a tree board each block's title and headers, the
    roll-up and reference stickies in their parents' cells. Each item: id, kind (frame | sticky | text), text, x, y."""
    items, n = [], [base]

    def add(kind, text, x, y, cell=None):
        n[0] += 1
        items.append({"id": str(n[0]), "kind": kind, "text": text, "x": x, "y": y, "cell": cell})
        return items[-1]
    add("text", layout["title"], 0, 0)
    blocks = [(0, layout["stages"], layout["cells"], "")] + [(b["block"], b["stages"], b["cells"], b["title"]) for b in layout.get("blocks", [])]
    for bi, stages, cells, title in blocks:
        y0 = bi * 8000
        if title:
            add("text", title, 0, y0 + 20)
        for si, st in enumerate(stages):
            add("text", st["title"], 220 + si * 420, y0 + 80)
        for c in cells:
            f = add("frame", c["title"], 220 + c["column"] * 420, y0 + 160 + c["line"] * 620)
            for j, r in enumerate(c["rows"]):
                add("sticky", r["text"] + ("\n" + r["second"] if r["second"] else ""), 10, 10 + j * 115, cell=f["id"])
    frames = {it["text"]: it["id"] for it in items if it["kind"] == "frame"}
    for extra in layout.get("rollups", []) + layout.get("references", []):
        add("sticky", extra["text"], 10, 470, cell=frames[extra["cell"]])
    return items


def to_svg(items):
    esc_ = lambda t: t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")  # noqa: E731
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="9000" height="40000">']
    frames = [it for it in items if it["kind"] == "frame"]
    for it in items:
        if it["kind"] == "text":
            out.append('<text data-type="text" data-miro-id="%s" x="%d" y="%d">%s</text>' % (it["id"], it["x"], it["y"], esc_(it["text"])))
    for f in frames:
        out.append('<g data-frame="%s" data-miro-id="%s" transform="translate(%d,%d)"><rect data-type="frame" width="400" height="600" />'
                   % (esc_(f["text"]), f["id"], f["x"], f["y"]))
        for it in items:
            if it["kind"] == "sticky" and it["cell"] == f["id"]:
                out.append('<rect data-type="sticky" data-miro-id="%s" x="%d" y="%d" width="185" height="105" data-content="%s" />'
                           % (it["id"], it["x"], it["y"], esc_(it["text"].replace("\n", "<br>"))))
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def to_wb(items):
    frames = {it["id"]: it for it in items if it["kind"] == "frame"}
    out = []
    for it in items:
        if it["kind"] == "frame":
            out.append({"id": "e" + it["id"], "data": {"type": "container", "x": it["x"], "y": it["y"], "w": 400, "h": 600, "text": it["text"]}})
        elif it["kind"] == "text":
            out.append({"id": "e" + it["id"], "data": {"type": "text", "x": it["x"], "y": it["y"], "text": it["text"]}})
        else:
            f = frames[it["cell"]]
            out.append({"id": "e" + it["id"], "data": {"type": "shape", "kind": "rounded", "x": f["x"] + it["x"], "y": f["y"] + it["y"],
                                                       "w": 185, "h": 105, "color": "yellow", "text": it["text"]}})
    return json.dumps(out, ensure_ascii=False)


def board_read(items, surface, path):
    write(path, to_svg(items) if surface == "miro" else to_wb(items))
    return path


def eid_of(surface, item_id):
    return item_id if surface == "miro" else "e" + item_id


d = tempfile.mkdtemp(prefix="journey-nest-test-")
try:
    shutil.copytree(FIX, os.path.join(d, "fx"))
    fx = os.path.join(d, "fx")
    nest = os.path.join(fx, "nest")
    root = os.path.join(nest, "journey-first-order.md")
    pay = os.path.join(nest, "journey-payment.md")
    tds = os.path.join(nest, "journey-3ds.md")
    retry = os.path.join(nest, "journey-3ds-retry.md")
    loop = os.path.join(nest, "journey-loop-a.md")
    before = digest(nest)

    # 1. nest — the tree, the roll-up, the findings
    rc, out, res = run("nest", "--note", root, "--json")
    check("1.1 nest exits 0 with a JOURNEY_RESULT line", rc == 0 and res.get("ok") is True, out[-600:])
    tree = res.get("tree") or {}
    check("1.2 the root is level 1 and names itself", tree.get("note") == "journey-first-order" and tree.get("level") == 1
          and res.get("level") == 1 and res.get("ancestors") == [], {k: tree.get(k) for k in ("note", "level")})
    kids = [(k.get("note"), k.get("stage"), k.get("step"), k.get("level")) for k in tree.get("children", [])]
    check("1.3 the root's children in its stage order: delivery on s4 (no step), payment on s5 «Оплата карткою»",
          kids == [("journey-shipping", "s4", "", 2), ("journey-payment", "s5", "Оплата карткою", 2)], kids)
    p = node(tree, "journey-payment") or {}
    check("1.4 payment's child: 3-D Secure on s3, step «3-D Secure», level 3 (a wiki-link parent read)",
          [(k.get("note"), k.get("stage"), k.get("step"), k.get("level")) for k in p.get("children", [])]
          == [("journey-3ds", "s3", "3-D Secure", 3)], p.get("children"))
    t = node(tree, "journey-3ds") or {}
    check("1.5 the fourth level is a reference only — no node, no roll-up (R38)",
          t.get("children") == [] and [(x.get("note"), x.get("level")) for x in t.get("deeper", [])] == [("journey-3ds-retry", 4)]
          and "rollup" not in (t.get("deeper") or [{}])[0], t)
    ru = p.get("rollup") or {}
    check("1.6 payment's pains: the ones its page shows by class — a simulated and an unsourced pain are none, a "
          "health-check row is no pain", ru.get("pains") == {"observed": 1, "reported": 2} and ru.get("pains_total") == 3, ru)
    check("1.7 payment's anomalies: 3, the critical one by refresh's end label (a PM's «критично важливо» is unrated)",
          ru.get("anomalies") == {"total": 3, "critical": 1, "warning": 1, "positive": 0, "unrated": 1}, ru.get("anomalies"))
    check("1.8 payment's outcome metric: its journey-level metric row", ru.get("outcome") == "Оплачено з першої спроби: 78% замовлень", ru)
    check("1.9 payment's last health point and review date", ru.get("health") == {"score": 64, "date": "2026-11-02"}
          and ru.get("reviewed") == "2026-11-10", ru)
    rt = t.get("rollup") or {}
    check("1.10 3-D Secure: no journey-level metric → «⚠️ TBD», no health point → «немає знімка»",
          rt.get("outcome") == "⚠️ TBD" and rt.get("health") is None and rt.get("health_label") == "немає знімка"
          and rt.get("pains") == {"observed": 1, "reported": 1}, rt)
    dl = node(tree, "journey-shipping") or {}
    check("1.11 delivery: no health point, an old review date as it is", (dl.get("rollup") or {}).get("health") is None
          and (dl.get("rollup") or {}).get("reviewed") == "2026-08-01", dl.get("rollup"))
    td = findings_of(res, "too_deep")
    check("1.12 too_deep: the fourth level, with its level and the level-3 map it hangs under",
          [(f.get("note"), f.get("level")) for f in td] == [("journey-3ds-retry", 4)] and "journey-3ds" in td[0].get("detail", ""), td)
    cy = findings_of(res, "nest_cycle")
    check("1.13 nest_cycle names the cycle once, both maps", len(cy) == 1 and sorted(cy[0].get("maps", [])) == ["journey-loop-a", "journey-loop-b"], cy)
    orph = sorted((f.get("note"), f.get("why")) for f in findings_of(res, "orphan_child"))
    check("1.14 orphan_child: a parent that does not exist, and a step the parent's rows do not have",
          orph == [("journey-lost", "no_parent"), ("journey-wrong-step", "no_step")], orph)
    check("1.15 other_product_parent: acme's map under zorg's root is never attached",
          [f.get("note") for f in findings_of(res, "other_product_parent")] == ["journey-acme-pay"]
          and node(tree, "journey-acme-pay") is None, findings_of(res, "other_product_parent"))
    check("1.16 self_parent", [f.get("note") for f in findings_of(res, "self_parent")] == ["journey-self"], findings_of(res, "self_parent"))
    check("1.17 no other finding code", {f.get("finding") for f in res.get("findings", [])}
          == {"too_deep", "nest_cycle", "orphan_child", "other_product_parent", "self_parent"}, res.get("findings"))
    check("1.18 the folder's plain markdown is no map (ignored, never named)", res.get("ignored") == 1
          and not any("README" in json.dumps(s, ensure_ascii=False) for s in res.get("skipped", [])), (res.get("ignored"), res.get("skipped")))
    check("1.19 nest writes nothing — every note byte for byte", digest(nest) == before, "a note changed")
    blob = json.dumps(res, ensure_ascii=False)
    check("1.20 no row text of a child in the result — only its outcome metric (R30: rows live in the child's note)",
          "Форма картки скидає" not in blob and "Сторінка банку не відкривається" not in blob
          and "Немає доставки у поштомат" not in blob and "Кнопка «надіслати ще раз»" not in blob, blob[:400])

    rc, out, res2 = run("nest", "--note", root)
    lines = [l for l in out.splitlines() if not l.startswith("JOURNEY_RESULT ")]
    check("1.21 without --json: the tree for the chat, indented by level, then the result line",
          rc == 0 and any("journey-payment" in l and l.startswith("- ") for l in lines)
          and any("journey-3ds" in l and l.startswith("  - ") for l in lines)
          and any("journey-3ds-retry" in l and l.startswith("    ") for l in lines) and res2.get("ok") is True, out[:900])
    check("1.22 the chat tree names each finding", all(c in out for c in ("too_deep", "nest_cycle", "orphan_child",
                                                                         "other_product_parent", "self_parent")), out[:900])
    rc, out, _ = run("nest", "--note", root, "--json")
    check("1.23 with --json: the result line alone", rc == 0 and [l for l in out.splitlines() if l.strip()][0].startswith("JOURNEY_RESULT "), out[:300])

    # a level is absolute (R38): nest on a child cuts where the root's tree cuts
    rc, out, res = run("nest", "--note", pay, "--json")
    tr = res.get("tree") or {}
    check("1.24 nest on a child: level 2, its ancestors, its child at level 3, the fourth level a reference",
          rc == 0 and res.get("level") == 2 and [a.get("note") for a in res.get("ancestors", [])] == ["journey-first-order"]
          and [k.get("note") for k in tr.get("children", [])] == ["journey-3ds"]
          and [x.get("note") for x in (node(tr, "journey-3ds") or {}).get("deeper", [])] == ["journey-3ds-retry"], res)
    rc, out, res = run("nest", "--note", retry, "--json")
    check("1.25 nest on the fourth level: shown as its own subject, too_deep named", rc == 0 and res.get("level") == 4
          and (res.get("tree") or {}).get("note") == "journey-3ds-retry" and findings_of(res, "too_deep"), res)
    rc, out, res = run("nest", "--note", loop, "--json", timeout=20)
    check("1.26 nest on a map in a cycle ends, the cycle named, the map stands alone", rc == 0 and len(findings_of(res, "nest_cycle")) == 1
          and (res.get("tree") or {}).get("children") == [], out[-400:])

    # candidates: --map, --dir, the note's folder
    rc, out, res = run("nest", "--note", root, "--map", pay, tds, "--json")
    tr = res.get("tree") or {}
    check("1.27 --map only: the maps given, the folder not scanned (no delivery)", rc == 0
          and [k.get("note") for k in tr.get("children", [])] == ["journey-payment"]
          and [k.get("note") for k in (node(tr, "journey-payment") or {}).get("children", [])] == ["journey-3ds"]
          and not res.get("findings"), res)
    other = os.path.join(d, "elsewhere")
    os.makedirs(other)
    shutil.copy(pay, other)
    lone = os.path.join(d, "lone", "journey-first-order.md")
    write(lone, read(root))
    rc, out, res = run("nest", "--note", lone, "--dir", other, "--json")
    check("1.28 --dir: a folder's maps", rc == 0 and [k.get("note") for k in (res.get("tree") or {}).get("children", [])] == ["journey-payment"], res)
    write(os.path.join(d, "lone", "notes.md"), "---\ntype: decision\nproduct: zorg\nparent: journey-first-order\nparent_stage: s5\n---\n\n# x\n")
    rc, out, res = run("nest", "--note", os.path.join(d, "lone", "notes.md"), "--json")
    check("1.29 nest on a note that is no journey map: exit 2", rc == 2 and res.get("ok") is False, out[-300:])

    # what never nests or attaches
    c14 = os.path.join(d, "c14")
    shutil.copytree(nest, c14)
    write(os.path.join(c14, "cjm-hand.md"), "---\ntype: cjm\nproduct: zorg\nfunnel: Перше замовлення\nparent: journey-first-order\n"
                                            "parent_stage: s5\n---\n\n## S1 — Вибір\n")
    write(os.path.join(c14, "journey-secret.md"), text(pay).replace("type: cjm-journey\n", "type: cjm-journey\nsensitive: true\n")
          .replace('journey: "Оплата"', 'journey: "Таємна оплата"'))
    write(os.path.join(c14, "journey-nostage.md"), text(pay).replace("parent_stage: s5\n", "").replace('journey: "Оплата"', 'journey: "Без етапу"'))
    write(os.path.join(c14, "journey-badstage.md"), text(pay).replace("parent_stage: s5\n", "parent_stage: s9\n")
          .replace('journey: "Оплата"', 'journey: "Чужий етап"'))
    write(os.path.join(c14, "journey-noproduct.md"), text(pay).replace("product: zorg\n", "").replace('journey: "Оплата"', 'journey: "Без продукту"'))
    rc, out, res = run("nest", "--note", os.path.join(c14, "journey-first-order.md"), "--json")
    tr = res.get("tree") or {}
    names = [k.get("note") for k in tr.get("children", [])]
    check("1.30 a hand CJM note (type: cjm) never nests — no child, no finding (C14)", "cjm-hand" not in names
          and "cjm-hand" not in json.dumps(res.get("findings"), ensure_ascii=False), (names, res.get("findings")))
    check("1.31 a sensitive map is never read into the tree — named as skipped", "journey-secret" not in names
          and any(s.get("reason") == "sensitive" for s in res.get("skipped", [])) and "Таємна" not in json.dumps(res, ensure_ascii=False),
          res.get("skipped"))
    orph = {f.get("note"): f.get("why") for f in findings_of(res, "orphan_child")}
    check("1.32 orphan_child: no parent_stage, and a parent_stage the parent does not declare",
          orph.get("journey-nostage") == "no_stage" and orph.get("journey-badstage") == "no_stage_in_parent", orph)
    check("1.33 a child that names no product hangs on the root (one product: the note says none)", "journey-noproduct" in names, names)
    dup = os.path.join(d, "dup")
    os.makedirs(dup)
    shutil.copy(pay, dup)
    rc, out, res = run("nest", "--note", root, "--dir", nest, dup, "--json")
    check("1.34 two maps of one name: the first kept, the second named (the link is by name)", rc == 0
          and any(s.get("reason") == "duplicate" for s in res.get("skipped", []))
          and [k.get("note") for k in (res.get("tree") or {}).get("children", [])].count("journey-payment") == 1, res.get("skipped"))
    chain = os.path.join(d, "chain")
    os.makedirs(chain)
    write(os.path.join(chain, "journey-c1.md"), text(root))
    for i in range(2, 8):
        write(os.path.join(chain, "journey-c%d.md" % i),
              text(os.path.join(nest, "journey-lost.md")).replace("parent: journey-gone", "parent: journey-c%d" % (i - 1))
              .replace('journey: "journey-lost"', 'journey: "Ланка %d"' % i))
    write(os.path.join(chain, "journey-c1.md"), text(root).replace('journey: "Перше замовлення"', 'journey: "Ланка 1"')
          .replace("| a1 | s1 |", "| a1 | s1 |"))
    rc, out, res = run("nest", "--note", os.path.join(chain, "journey-c1.md"), "--json", timeout=20)
    td = sorted((f.get("note"), f.get("level")) for f in findings_of(res, "too_deep"))
    check("1.35 a chain of seven: levels 1–3 in the tree, too_deep for 4–7, the tree cut at the first reference",
          rc == 0 and td == [("journey-c4", 4), ("journey-c5", 5), ("journey-c6", 6), ("journey-c7", 7)]
          and [x.get("note") for x in (node(res.get("tree") or {}, "journey-c3") or {}).get("deeper", [])] == ["journey-c4"], (td, out[-300:]))

    # 2. the tree page (§9, §14): chips on the parent's steps, a <details> per child, the fourth level a reference
    sys.path.insert(0, os.path.dirname(SCRIPT))
    import journey_map as jm  # noqa: E402 — the page's fixed scripts, to compare bytes
    page = os.path.join(d, "tree-uk.html")
    rc, out, res = run("render-html", "--note", root, "--out", page, "--lang", "uk")
    h = text(page) if os.path.exists(page) else ""
    check("2.1 render-html of the root: exit 0, three child maps shown, the fourth level a reference", rc == 0
          and res.get("children") == 3 and res.get("deeper") == ["journey-3ds-retry"], out[-400:])
    check("2.2 a <details> per child map, the grandchild's inside its parent's", h.count('<details class="child"') == 3
          and re.search(r'<details class="child" id="n\d+">(?:(?!</details>).)*journey-payment(?:(?!</details>).)*'
                        r'<details class="child" id="n\d+">(?:(?!</details>).)*journey-3ds\.md', h, re.S) is not None, h[:300])
    chips = re.findall(r'<div class="item chip" data-open="(n\d+)"', h)
    ids = re.findall(r'<details class="child" id="(n\d+)"', h)
    check("2.3 a chip per child on its parent's step, each opening its own <details>", sorted(chips) == sorted(ids) and len(chips) == 3,
          (chips, ids))

    def grid_of(html, n):
        """The n-th grid of the page — its <div class="wrap"> … </table></div>."""
        parts = re.findall(r'<div class="wrap" tabindex="0">.*?</table></div>', html, re.S)
        return parts[n] if len(parts) > n else ""
    g0 = grid_of(h, 0)
    check("2.4 the root's grid holds no row of a child — only the chips' roll-up (R30)",
          "Форма картки скидає" not in g0 and "Сторінка банку" not in g0 and "Немає доставки у поштомат" not in g0
          and "болі 3 (observed 1 · reported 2)" in g0 and "Оплачено з першої спроби: 78% замовлень" in g0, g0[:400])
    s5 = re.search(r'<th class="lane">дії</th>(.*?)</tr>', g0, re.S)
    cells = re.findall(r"<td>(.*?)</td>", s5.group(1), re.S) if s5 else []
    check("2.5 the chips stand in their stage's first lane (дії): delivery on s4, payment on s5 with its step",
          len(cells) == 5 and "journey-shipping" in cells[3] and "journey-payment" in cells[4] and "Оплата карткою" in cells[4]
          and "journey-payment" not in cells[3], [c[:80] for c in cells])
    check("2.6 each child's rows only in its own grid — in the page's order: delivery (s4), payment (s5), its 3-D Secure",
          "Немає доставки у поштомат" in grid_of(h, 1) and "Форма картки скидає" in grid_of(h, 2)
          and "Сторінка банку не відкривається" in grid_of(h, 3) and "Форма картки скидає" not in grid_of(h, 3),
          [grid_of(h, i)[:60] for i in range(4)])
    check("2.7 the fourth level: named (journey and note) with its level, never its grid or rows",
          "Повтор коду" in h and "journey-3ds-retry.md" in h and "Кнопка «надіслати ще раз»" not in h
          and h.count('<div class="wrap"') == 4, h.count('<div class="wrap"'))
    check("2.8 sticky headers in every grid", len(re.findall(r'<th class="stage">', h)) == 5 + 1 + 3 + 2
          and h.count('<th class="corner">') == 4 and "position:sticky" in h, h.count('<th class="stage">'))
    scripts = re.findall(r"<script>(.*?)</script>", h, re.S)
    check("2.9 one fixed script — no data of a note, no request; every grid pans and a chip opens its child",
          scripts == [jm.PAN_TREE] and not re.search(r"fetch|XMLHttpRequest|import\(|src=|http", jm.PAN_TREE), scripts[:1])
    check("2.10 no link or request anywhere on the page", not re.search(r"<a |href=|src=|https?://|url\(|@import", h),
          re.findall(r".{20}(?:href=|src=|https?://).{20}", h)[:3])
    rc, out, res = run("render-html", "--note", os.path.join(nest, "journey-shipping.md"), "--out", os.path.join(d, "dl.html"), "--lang", "uk")
    dh = text(os.path.join(d, "dl.html")) if os.path.exists(os.path.join(d, "dl.html")) else ""
    check("2.11 a child's own page: the maps above it named, no details when it has no child", rc == 0
          and "Над нею: «Перше замовлення» (journey-first-order)" in dh and "<details" not in dh, out[-300:])
    rc, out, res = run("render-html", "--note", root, "--out", os.path.join(d, "tree-en.html"), "--lang", "en")
    check("2.12 the English page", rc == 0 and "Child maps" in text(os.path.join(d, "tree-en.html"))
          and "pains 3 (observed 1 · reported 2)" in text(os.path.join(d, "tree-en.html")), out[-300:])

    # hostile words in a child: escaped, a link and a contact removed, a secret hidden
    hz = os.path.join(d, "hostile")
    shutil.copytree(nest, hz)
    write(os.path.join(hz, "journey-payment.md"), text(pay)
          .replace('journey: "Оплата"', 'journey: "Оплата <b>x</b> https://evil.example/j bea@zorg.example"')
          .replace("| mj1 | s1 | | metric | Оплачено з першої спроби: 78% замовлень |",
                   "| mj1 | s1 | | metric | Оплачено <script>x</script> 78% https://evil.example/m токен glpat-" + "Qw8" * 7 + " |"))
    rc, out, res = run("render-html", "--note", os.path.join(hz, "journey-first-order.md"), "--out", os.path.join(d, "hz.html"), "--lang", "uk")
    hh = text(os.path.join(d, "hz.html")) if os.path.exists(os.path.join(d, "hz.html")) else ""
    check("2.13 a child's words are page-safe: escaped, no link, no contact, a secret hidden whole", rc == 0
          and "<b>x</b>" not in hh and "&lt;b&gt;x&lt;/b&gt;" in hh and "evil.example" not in hh and "bea@zorg" not in hh
          and "glpat-" not in hh and "<script>x</script>" not in hh, re.findall(r".{30}(?:evil|bea@|glpat|<b>x).{30}", hh)[:3])
    rc, out, res = run("nest", "--note", os.path.join(hz, "journey-first-order.md"), "--json")
    blob = json.dumps(res, ensure_ascii=False)
    check("2.14 the nest result is page-safe too", "evil.example" not in blob and "bea@zorg" not in blob and "glpat-" not in blob, blob[:300])

    # the scheduled refresh of a child re-renders the pages above it, locally, and never touches their notes (C11)
    rf = os.path.join(d, "refresh-tree")
    shutil.copytree(nest, rf)
    snap = os.path.join(d, "snap", "2026-11-23.md")
    write(snap, "---\ntype: cjm-health-check\nproduct: zorg\nmap: journey-payment\ndate: 2026-11-23\nperiod: 2026-11-16..2026-11-22\nhealth_score: 58\n"
                "stages:\n  - id: s2\n    metric: \"card -> confirm\"\n    value: \"55.0%\"\n    baseline: \"66.0%\"\n"
                "    deviation: \"-16.7%\"\n    status: critical\n---\n\n# Health-check\n")
    root_before = read(os.path.join(rf, "journey-first-order.md"))
    rc, out, res = run("refresh", "--note", os.path.join(rf, "journey-payment.md"), "--snapshot", snap, "--lang", "uk")
    rp = os.path.join(rf, "journey-first-order.html")
    rh = text(rp) if os.path.exists(rp) else ""
    check("2.15 a refreshed child re-renders its root's page beside the root, with the new point", rc == 0
          and res.get("pages_above") == [rp] and "здоров&#x27;я 58 (2026-11-23)" in rh and res.get("published") is False, out[-500:])
    check("2.16 the root's note is never written by its child's refresh", read(os.path.join(rf, "journey-first-order.md")) == root_before,
          "the root changed")
    check("2.17 the child's own page is written too", os.path.exists(os.path.join(rf, "journey-payment.html")), os.listdir(rf))

    # mutations: a child's row copied into the parent, the fourth level in full
    for name, old, new, test in (
            ("page-row", "chips.setdefault(k[\"stage\"], []).append(", "chips.setdefault(k[\"stage\"], []).append(\" \".join(r[\"text\"] for r in maps[k[\"note\"]][\"rows\"]) + ",
             lambda html: "Форма картки скидає" in grid_of(html, 0)),
            ("page-deep", "MAX_DEPTH = 3", "MAX_DEPTH = 4", lambda html: "Кнопка «надіслати ще раз»" in html)):
        m = mutant(d, name, old, new)
        if m is None:
            check("M.%s the mutation's pattern is in journey_map.py" % name, False, old)
            continue
        mp = os.path.join(d, "m-%s.html" % name)
        rc, out, res = run("render-html", "--note", root, "--out", mp, "--lang", "uk", script=m)
        check("M.%s a mutant is caught by the page's assertions" % name, rc != 0 or test(text(mp) if os.path.exists(mp) else ""), out[-300:])

    # 3. the tree board (§11–§12, §14, C6–C8): blocks below the root's grid, keys <child>#<id>, two boards, one preview
    rc, out, lay = run("board-layout", "--note", root, "--lang", "uk", "--with-children")
    blocks = lay.get("blocks", [])
    check("3.1 board-layout --with-children: a block per child the page shows, depth first, its cells «<child> · <stage> · <lane>»",
          rc == 0 and [(b["note"], b["level"], len(b["cells"])) for b in blocks]
          == [("journey-shipping", 2, 10), ("journey-payment", 2, 30), ("journey-3ds", 3, 20)]
          and "journey-payment · s2 · болі" in lay.get("titles", []) and len(lay.get("titles", [])) == 50 + 60, out[-400:])
    pb = next((b for b in blocks if b["note"] == "journey-payment"), {})
    pc = {c["title"]: c for c in pb.get("cells", [])}
    check("3.2 a child's rows keyed «<child>#<id>» — only the rows its page shows; the rest named in its block",
          [r["id"] for r in pc.get("journey-payment · s2 · болі", {}).get("rows", [])] == ["journey-payment#pc1", "journey-payment#pc2"]
          and sorted(pb.get("hidden", [])) == ["journey-payment#pc4", "journey-payment#pc5"], pb.get("hidden"))
    ru = [(r["cell"], r["child"]) for r in lay.get("rollups", [])]
    pr = next((r for r in lay.get("rollups", []) if r["child"] == "journey-payment"), {})
    check("3.3 a roll-up sticky per child in its parent's cell «<stage> · дії», with its numbers; on Miro it links to the child's first cell",
          ru == [("s4 · дії", "journey-shipping"), ("s5 · дії", "journey-payment"), ("journey-payment · s3 · дії", "journey-3ds")]
          and "болі 3 (observed 1 · reported 2)" in pr.get("text", "") and pr.get("link_to") == "journey-payment · s1 · дії", lay.get("rollups"))
    check("3.4 the fourth level: one reference sticky, no block, no link",
          [(r["cell"], r["child"]) for r in lay.get("references", [])] == [("journey-3ds · s2 · дії", "journey-3ds-retry")]
          and "link_to" not in (lay.get("references") or [{}])[0] and not any(b["note"] == "journey-3ds-retry" for b in blocks), lay.get("references"))
    rootcells = json.dumps(lay.get("cells", []), ensure_ascii=False)
    blockcells = json.dumps([c for b in blocks for c in b["cells"]], ensure_ascii=False)
    check("3.5 no row of a child in the root's cells; no source, class or date on a child's sticky",
          "Форма картки скидає" not in rootcells and "Форма картки скидає" in blockcells
          and not re.search(r"walkthrough|feedback-triage|observed|reported|2026-10-2", blockcells), re.findall(r".{20}(?:walkthrough|observed).{20}", blockcells)[:2])
    rc, out, lay0 = run("board-layout", "--note", root, "--lang", "uk")
    check("3.6 without --with-children: the map's own grid alone, as before", rc == 0 and "blocks" not in lay0
          and lay0.get("cells") == lay.get("cells") and len(lay0.get("titles", [])) == 50, sorted(lay0))
    check("3.7 the roll-up sticky has its own colour", lay.get("sticky") == {"row": "yellow", "health_check": "blue", "rollup": "purple"}, lay.get("sticky"))

    rc, out, play = run("board-layout", "--note", pay, "--lang", "uk")
    trees = {}
    for sf in ("miro", "whiteboard"):
        E = lambda i, sf=sf: eid_of(sf, i)  # noqa: E731
        items = board_items(lay)
        by_text = {}
        for it in items:
            by_text.setdefault(it["text"].split("\n")[0], it)
        last_r = board_read(items, sf, os.path.join(d, "tree-last-%s.%s" % (sf, "svg" if sf == "miro" else "json")))
        st = os.path.join(d, "journey-first-order.%s.board.json" % sf)
        rc, out, res = run("board-state", "--read", last_r, "--note", root, "--surface", sf, "--out", st, "--with-children")
        check("3.8 [%s] board-state of the tree board: every row's sticky keyed, 110 cells, 3 roll-ups and 1 reference" % sf, rc == 0
              and res.get("rows", {}).get("journey-payment#pc1") == E(by_text["Форма картки скидає введені дані після помилки CVV"]["id"])
              and res.get("rows", {}).get("p5") == E(by_text["Оплата падає без пояснення причини"]["id"])
              and res.get("roles", {}).get("cell") == 110 and res.get("roles", {}).get("rollup") == 4 and res.get("unmapped_rows") == []
              and res.get("tree") == ["journey-shipping", "journey-payment", "journey-3ds"], out[-500:])
        now = [dict(it) for it in items]
        pc1 = next(it for it in now if it["text"].startswith("Форма картки скидає"))
        pc1["text"] = "Форма картки скидає дані після помилки CVV і після оновлення сторінки"
        p5 = next(it for it in now if it["text"] == "Оплата падає без пояснення причини")
        p5["text"] = "Оплата падає без пояснення причини й коду помилки"
        rl = next(it for it in now if it["kind"] == "sticky" and it["text"].startswith("↳ «Оплата» · journey-payment"))
        rl["text"] = rl["text"] + " — перевірити!"
        cell = next(it for it in now if it["kind"] == "frame" and it["text"] == "journey-payment · s2 · болі")
        now.append({"id": "900", "kind": "sticky", "text": "Немає Apple Pay у застосунку", "x": 10, "y": 300, "cell": cell["id"]})
        now_r = board_read(now, sf, os.path.join(d, "tree-now-%s.%s" % (sf, "svg" if sf == "miro" else "json")))
        dfile = os.path.join(d, "tree-diff-%s.json" % sf)
        rc, out, res = run("board-diff", "--last", st, "--now", now_r, "--note", root, "--out", dfile)
        check("3.9 [%s] board-diff of the tree board (the state says tree): a root row and a child row changed, keyed" % sf, rc == 0
              and sorted(c["row"] for c in res.get("changed", [])) == ["journey-payment#pc1", "p5"], res.get("changed"))
        check("3.10 [%s] a team sticky in a child's cell is added with the child's stage; the roll-up's edit is `other`, not counted" % sf,
              [(a["stage"], a["lane"]) for a in res.get("added", [])] == [("journey-payment · s2", "pain")]
              and any(o.get("role") == "rollup" for o in res.get("other", []))
              and res.get("counts") == {"changed": 2, "moved": 0, "added": 1, "removed": 0, "orphaned": 0, "hc_edits": 0}, (res.get("other"), res.get("counts")))
        check("3.11 [%s] the diff names its map and each child's own digest" % sf, res.get("map") == "journey-first-order"
              and sorted(res.get("tree", {})) == ["journey-3ds", "journey-payment", "journey-shipping"], (res.get("map"), res.get("tree")))
        trees[sf] = (dfile, E(pc1["id"]), E(p5["id"]), E("900"))

    # the child's own board (C9): plain ids; pc1 changed there in another way, pc2 changed only there
    sf = "miro"
    own = board_items(play)
    st2 = os.path.join(d, "journey-payment.miro.board.json")
    rc, out, res = run("board-state", "--read", board_read(own, sf, os.path.join(d, "own-last.svg")), "--note", pay, "--surface", sf, "--out", st2)
    check("3.12 the child's own board: plain row ids", rc == 0 and "pc1" in res.get("rows", {}) and "journey-payment#pc1" not in res.get("rows", {}), out[-300:])
    own_now = [dict(it) for it in own]
    o1 = next(it for it in own_now if it["text"].startswith("Форма картки скидає"))
    o1["text"] = "Форма картки скидає CVV після помилки"
    o2 = next(it for it in own_now if it["text"] == "Незрозуміло, чому картку відхилено")
    o2["text"] = "Незрозуміло, чому банк відхилив картку"
    odiff = os.path.join(d, "own-diff.json")
    rc, out, res = run("board-diff", "--last", st2, "--now", board_read(own_now, sf, os.path.join(d, "own-now.svg")), "--note", pay, "--out", odiff)
    check("3.13 the child's own board diff: pc1 and pc2 changed", rc == 0 and sorted(c["row"] for c in res.get("changed", [])) == ["pc1", "pc2"], res.get("changed"))

    tdiff, t_pc1, t_p5, t_new = trees["miro"]
    o_pc1, o_pc2 = o1["id"], o2["id"]
    pay0, root0, tds0 = read(pay), read(root), read(tds)
    rc, out, res = run("board-take", "--note", pay, "--diff", tdiff, odiff, "--take", t_new, o_pc2, "--dry-run", "--date", "2026-11-24")
    conf = res.get("conflicts", [])
    check("3.14 one preview for the child from both boards: pc1 changed differently on the two — both versions shown",
          rc == 0 and len(conf) == 1 and conf[0]["row"] == "pc1" and sorted(v["id"] for v in conf[0]["versions"]) == sorted([t_pc1, o_pc1]), out[-500:])
    check("3.15 the root's own row is elsewhere — named with its map, never in this preview",
          any(e["id"] == t_p5 and e["note"] == "journey-first-order" for e in res.get("elsewhere", []))
          and not any(a.get("row") == "p5" for a in res.get("applied", [])), res.get("elsewhere"))
    check("3.16 the added sticky becomes the child's new row on its own stage; the dry run writes nothing",
          any(a.get("action") == "add" and a.get("cell") == "s2 · болі" for a in res.get("applied", []))
          and res.get("note_written") is False and read(pay) == pay0, res.get("applied"))
    rc, out, res = run("board-take", "--note", pay, "--diff", tdiff, odiff, "--take", t_pc1, o_pc1, "--dry-run", "--date", "2026-11-24")
    check("3.17 both versions taken → both refused `conflict`: the PM takes one or none, never both",
          sorted((r["id"], r["why"]) for r in res.get("refused", [])) == sorted([(t_pc1, "conflict"), (o_pc1, "conflict")])
          and not any(a.get("row") == "pc1" for a in res.get("applied", [])), res.get("refused"))
    rc, out, res = run("board-take", "--note", pay, "--diff", tdiff, odiff, "--take", t_pc1, o_pc2, t_new, t_p5,
                       "--class", "%s=observed" % t_pc1, "--class", "%s=reported" % o_pc2, "--class", "%s=reported" % t_new, "--date", "2026-11-24")
    tp = text(pay)
    check("3.18 the PM picks the root board's version: the child's note alone takes it, with the team's source and date", rc == 0
          and res.get("note_written") is True
          and "| pc1 | s2 | Дані картки | pain | Форма картки скидає дані після помилки CVV і після оновлення сторінки |" in tp
          and "| pc2 | s2 | | pain | Незрозуміло, чому банк відхилив картку |" in tp and "дошка команди 2026-11-24" in tp
          and re.search(r"\| b1 \| s2 \| \| (?:pain|болі) \| Немає Apple Pay у застосунку \|", tp) is not None, out[-600:])
    check("3.19 another map's row is refused `other_note`; the root's and the grandchild's notes untouched",
          any(r["id"] == t_p5 and r["why"] == "other_note" and "journey-first-order" in r["detail"] for r in res.get("refused", []))
          and read(root) == root0 and read(tds) == tds0, res.get("refused"))
    rc, out, res = run("board-take", "--note", pay, "--diff", tdiff, "--take", t_new, "--dry-run")
    check("3.20 a tree board's diff taken into a child that changed since: refused (exit 2) — diff again", rc == 2
          and "changed since" in res.get("error", ""), out[-300:])
    rc, out, res = run("board-take", "--note", root, "--diff", tdiff, "--take", t_p5, t_pc1, "--class", "%s=reported" % t_p5, "--date", "2026-11-24")
    tr_ = text(root)
    check("3.21 the root takes its own row from its tree board; a child's row is refused `other_note`, its note untouched", rc == 0
          and "Оплата падає без пояснення причини й коду помилки" in tr_ and "Форма картки скидає дані після помилки CVV і після" not in tr_
          and any(r["id"] == t_pc1 and r["why"] == "other_note" and "journey-payment" in r["detail"] for r in res.get("refused", [])), out[-500:])
    write(root, root0)
    write(pay, pay0)

    # mutation: two boards' versions taken automatically
    m = mutant(d, "auto-conflict", '            refuse_all = len(hit) > 1 or any(h.startswith("row:") for h in hit)', "            refuse_all = False")
    if m is None:
        check("M.auto-conflict the mutation's pattern is in journey_map.py", False, "refuse_all = len(hit) > 1")
    else:
        rc, out, res = run("board-take", "--note", pay, "--diff", tdiff, odiff, "--take", t_pc1, o_pc1, "--dry-run", "--date", "2026-11-24", script=m)
        check("M.auto-conflict a take of both versions is caught by 3.17", not any(r.get("why") == "conflict" for r in res.get("refused", [])), out[-300:])

    # 12. review 1 (opus, frozen fa5afd4): each finding reproduced first
    import unicodedata
    r1 = os.path.join(d, "r1")
    shutil.copytree(nest, r1)
    lost_t = text(os.path.join(nest, "journey-lost.md"))

    def kid(name, parent_block, stage="s5", step=None, product="zorg", title=None):
        """A small child map of first-order with its `parent` written as given (the YAML lines themselves)."""
        t = lost_t.replace("parent: journey-gone\nparent_stage: s1\n", parent_block + "parent_stage: %s\n" % stage
                           + ('parent_step: "%s"\n' % step if step else "")).replace('journey: "journey-lost"', 'journey: "%s"' % (title or name))
        write(os.path.join(r1, name + ".md"), t.replace("product: zorg", "product: %s" % product))
    kid("journey-k-unquoted", "parent: [[journey-first-order]]\n")
    kid("journey-k-list", 'parent:\n  - "[[journey-first-order]]"\n')
    kid("journey-k-two", 'parent:\n  - "[[journey-first-order]]"\n  - "[[journey-payment]]"\n')
    kid("journey-k-odd", "parent: {a: 1}\n")
    kid("journey-k-null", "parent: null\n")
    kid("journey-k-case", 'parent: "[[Journey-First-Order]]"\n')
    write(os.path.join(r1, "journey-self.md"), text(os.path.join(nest, "journey-self.md")).replace("parent: journey-self", "parent: Journey-Self"))
    nfd = unicodedata.normalize("NFD", "journey-край")
    write(os.path.join(r1, nfd + ".md"), text(os.path.join(nest, "journey-shipping.md")).replace("parent: journey-first-order\nparent_stage: s4\n", "")
          .replace('journey: "Вибір доставки"', 'journey: "Край"'))
    kid("journey-k-nfc", 'parent: "%s"\n' % unicodedata.normalize("NFC", "journey-край"), stage="s1", title="Під краєм")
    kid("journey-bea@zorg.example", "parent: journey-first-order\n", title="Чужий файл")
    kid("journey-k-hostile", 'parent: "bea@zorg.example https://evil.example/p"\n')
    write(os.path.join(r1, "journey-k-tail.md"), lost_t.replace("parent: journey-gone", "parent: journey-loop-a")
          .replace('journey: "journey-lost"', 'journey: "Хвіст кільця"'))
    rc, out, res = run("nest", "--note", os.path.join(r1, "journey-first-order.md"), "--json")
    tr = res.get("tree") or {}
    names = [k.get("note") for k in tr.get("children", [])]
    orph = {f.get("note"): f.get("why") for f in findings_of(res, "orphan_child")}
    check("12.1 #1 a parent written as an unquoted wiki link, or as Obsidian's list property of one, attaches",
          rc == 0 and "journey-k-unquoted" in names and "journey-k-list" in names, (names, orph))
    check("12.2 #1 two parents, or a value that reads as no name: orphan_child `bad_parent` — never silently a root",
          orph.get("journey-k-two") == "bad_parent" and orph.get("journey-k-odd") == "bad_parent", orph)
    check("12.3 #1 `parent: null` is no parent — no finding", "journey-k-null" not in orph and "journey-k-null" not in names, orph)
    check("12.4 #5 a link names a map as Obsidian and the disk resolve it — any case; a map named itself in another case is self_parent",
          "journey-k-case" in names and [f.get("note") for f in findings_of(res, "self_parent")] == ["journey-self"], (names, findings_of(res, "self_parent")))
    rc5, out5, res5 = run("nest", "--note", os.path.join(r1, nfd + ".md"), "--json")
    check("12.5 #5 a name stored decomposed (NFD) on disk is the same name as its link (NFC)", rc5 == 0 and "journey-k-nfc" not in orph
          and [k.get("note") for k in (res5.get("tree") or {}).get("children", [])] == ["journey-k-nfc"], out5[-400:])
    blob = json.dumps(res, ensure_ascii=False)
    check("12.6 #4 a file name that is not page-safe is no map of the tree — named by why, never by itself; a parent value is page-safe in a finding",
          "bea@zorg" not in blob and "evil.example" not in blob and any(sk.get("reason") == "unsafe_name" for sk in res.get("skipped", []))
          and orph.get("journey-k-hostile") == "no_parent", re.findall(r".{30}(?:bea@|evil\.).{20}", blob)[:3])
    rc, out, _ = run("render-html", "--note", os.path.join(r1, "journey-first-order.md"), "--out", os.path.join(d, "r1.html"), "--lang", "uk")
    check("12.7 #4 the page: no unsafe file name", rc == 0 and "bea@zorg" not in text(os.path.join(d, "r1.html")), out[-300:])
    tail = node(res.get("tree") or {}, "journey-k-tail")
    rc, out, res = run("nest", "--note", os.path.join(r1, "journey-loop-a.md"), "--json", timeout=20)
    check("12.8 #6e a chain into a cycle ends: the ring named once, the tail hangs under its ring member",
          rc == 0 and len(findings_of(res, "nest_cycle")) == 1
          and [k.get("note") for k in (res.get("tree") or {}).get("children", [])] == ["journey-k-tail"], out[-400:])

    # #2 (C4c): the chip carries the child's own numbers (R30) and, with children of its own, the whole subtree's (R27)
    rc, out, res = run("nest", "--note", root, "--json")
    pr = (node(res.get("tree") or {}, "journey-payment") or {}).get("rollup", {})
    check("12.9 #2 payment's roll-up: its own pains (3) and, with its 3-D Secure, the subtree's (5); the critical ones too",
          pr.get("pains_total") == 3 and (pr.get("subtree") or {}).get("pains_total") == 5
          and (pr.get("subtree") or {}).get("critical") == 1 and (pr.get("subtree") or {}).get("maps") == 1, pr)
    check("12.10 #2 a child with no child of its own carries no subtree line",
          "subtree" not in ((node(res.get("tree") or {}, "journey-3ds") or {}).get("rollup") or {}), node(res.get("tree") or {}, "journey-3ds"))
    page2 = os.path.join(d, "tree-sub.html")
    run("render-html", "--note", root, "--out", page2, "--lang", "uk")
    check("12.11 #2 the chip says it: «з дочірніми картами (1): болі 5»", "з дочірніми картами (1): болі 5" in grid_of(text(page2), 0), grid_of(text(page2), 0)[:300])

    # #3: a page above that cannot be written never fails the child's refresh; each page in its own map's language
    r3 = os.path.join(d, "r3")
    shutil.copytree(nest, r3)
    os.makedirs(os.path.join(r3, "journey-first-order.html"))          # a folder where the root's page would go
    write(os.path.join(r3, "journey-payment.md"), text(pay).replace("| id | етап | крок | доріжка | текст | рівень | ціль | parent | код | джерело | клас | дата |",
                                                                     "| id | stage | step | lane | text | level | target | parent | code | source | class | date |"))
    snap3 = os.path.join(d, "snap3", "2026-11-23.md")
    write(snap3, "---\ntype: cjm-health-check\nproduct: zorg\nmap: journey-3ds\ndate: 2026-11-23\nhealth_score: 61\nstages:\n  - id: s1\n"
                 "    metric: \"redirect -> code\"\n    value: \"93%\"\n    status: warning\n---\n")
    rc, out, res = run("refresh", "--note", os.path.join(r3, "journey-3ds.md"), "--snapshot", snap3)
    check("12.12 #3/#6c a grandchild's refresh re-renders both pages above it; one that cannot be written is named, the refresh ok",
          rc == 0 and res.get("ok") is True and res.get("pages_above") == [os.path.join(r3, "journey-payment.html")]
          and [f.get("page") for f in res.get("pages_above_failed", [])] == [os.path.join(r3, "journey-first-order.html")], out[-500:])
    ph = text(os.path.join(r3, "journey-payment.html")) if os.path.exists(os.path.join(r3, "journey-payment.html")) else ""
    check("12.13 #3 a page above in its own map's language (payment's headers are English) when --lang is not given",
          'lang="en"' in ph and "Child maps" in ph, ph[:200])

    # #6d: a file iCloud has not downloaded is never opened — counted in a folder, named when given
    wrap = os.path.join(d, "dataless.py")
    write(wrap, "import os, sys\nsys.path.insert(0, %r)\nimport ctx_index\n"
                "ctx_index.is_dataless = lambda p: os.path.basename(p) == 'journey-shipping.md'\n"
                "import journey_map\nsys.exit(journey_map.main(sys.argv[1:]))\n" % os.path.dirname(SCRIPT))
    rc, out, res = run("nest", "--note", root, "--json", script=wrap)
    check("12.14 #6d a dataless file in the folder: counted, never opened or attached", rc == 0 and res.get("undownloaded") == 1
          and node(res.get("tree") or {}, "journey-shipping") is None, out[-300:])
    rc, out, res = run("nest", "--note", root, "--map", os.path.join(nest, "journey-shipping.md"), "--json", script=wrap)
    check("12.15 #6d a dataless file given by its path: named, never opened", rc == 0
          and any(sk.get("reason") == "unreadable" and "iCloud" in sk.get("detail", "") for sk in res.get("skipped", [])), out[-300:])

    # #7 nits: the subject is never `skipped`; render-html names no folder-wide finding count
    sens = os.path.join(d, "sens")
    shutil.copytree(nest, sens)
    write(os.path.join(sens, "journey-payment.md"), text(pay).replace("type: cjm-journey\n", "type: cjm-journey\nsensitive: true\n"))
    rc, out, res = run("nest", "--note", os.path.join(sens, "journey-payment.md"), "--json")
    check("12.16 #7 the subject itself is never listed as skipped", rc == 0 and not any(sk.get("note") == "journey-payment.md" for sk in res.get("skipped", [])),
          res.get("skipped"))
    rc, out, res = run("render-html", "--note", os.path.join(fx, "journey-first-order.md"), "--out", os.path.join(d, "nf.html"))
    check("12.17 #7 render-html carries no folder-wide nest_findings count", rc == 0 and "nest_findings" not in res, sorted(res))

    # #6b/#6f: sharper mutants
    for name, old, new, test in (
            ("hc-only", 'if r["lane"] == "pain":', 'if r["lane"] == "pain" or _is_hc(r):',
             lambda r: (node(r.get("tree") or {}, "journey-payment") or {}).get("rollup", {}).get("pains_total") != 3),
            ("pm-rated", 'st = hc_status(r["text"]) if _is_hc(r) else None', 'st = hc_status(r["text"])',
             lambda r: (node(r.get("tree") or {}, "journey-payment") or {}).get("rollup", {}).get("anomalies", {}).get("critical") != 1),
            ("no-order", "        children[p].sort(key=place)", "        pass",
             lambda r: [k.get("note") for k in (r.get("tree") or {}).get("children", [])] != ["journey-shipping", "journey-payment"])):
        m = mutant(d, name, old, new)
        if m is None:
            check("M.%s the mutation's pattern is in journey_map.py" % name, False, old)
            continue
        rc, out, res = run("nest", "--note", root, "--json", script=m)
        check("M.%s a mutant is caught" % name, rc != 0 or test(res), out[-300:])

    # 5. validate check 28 (C13): §14's findings, why codes and depth, the `nest` command, the skill's Step J naming the
    #    child, artifact-publishing's two places in one question, §15 — no new check
    r28 = os.path.join(d, "root28")
    for rel in ("references/journey-protocol.md", "references/vault-schema.md", "references/artifact-publishing.md",
                "skills/cjm-research/SKILL.md", "references/vault-protocol.md", "skills/cjm-research/references/cjm-reports.md"):
        os.makedirs(os.path.dirname(os.path.join(r28, rel)), exist_ok=True)
        shutil.copy(os.path.join(ROOT, rel), os.path.join(r28, rel))
    e28 = jm.check_protocol(r28)
    check("5.1 check 28 is clean on the tree", e28 == [], e28)
    rc, out, res = run("schema")
    check("5.2 schema prints the nesting's fields, findings, why codes and depth", res.get("nest_findings") == list(jm.NEST_FINDINGS)
          and res.get("orphan_why") == list(jm.ORPHAN_WHY) and res.get("max_depth") == 3
          and res.get("nest_fields") == ["parent", "parent_stage", "parent_step"], out[-300:])

    def drift28(rel, old, new, expect, name, count=1):
        p_ = os.path.join(r28, rel)
        t0 = text(p_)
        if old not in t0:
            check(name, False, "pattern not in %s" % rel)
            return
        write(p_, t0.replace(old, new, count))
        e = jm.check_protocol(r28)
        write(p_, t0)
        check(name, any(expect in x for x in e), e)
    drift28("references/journey-protocol.md", "| `nest_cycle` | maps hang", "| `nest_ring` | maps hang", "§14", "5.3 a finding §14 renames is named")
    drift28("references/journey-protocol.md", "| `no_stage_in_parent` | the parent", "| `stage_missing` | the parent", "§14", "5.4 a why code that drifts is named")
    drift28("references/journey-protocol.md", "three levels at most", "four levels at most", "three levels", "5.5 a depth the protocol changes alone is named")
    drift28("references/journey-protocol.md", "## 14. Nested maps", "## 14. Trees", "§14", "5.6 a protocol without its §14 «Nested maps» is named")
    drift28("references/journey-protocol.md", "## 15. What never happens", "## 15. Never", "§15", "5.7 «What never happens» lost as §15 is named")
    drift28("skills/cjm-research/SKILL.md", "journey_map.py nest", "journey_map.py tree-of", "nest", "5.8 the skill's Step J without `nest` is named", count=-1)
    drift28("references/artifact-publishing.md", "**Two places of two keys in one question**", "**Two keys**", "Two places", "5.9 artifact-publishing without the two places in one question is named")

    # 13. review 2 (opus, frozen 49c226e): each finding reproduced first
    def pair(tag, surface, tree_edit, own_edit, before_tree=None, own_base=5000, mutate=None, align=None):
        """A fresh copy of the tree; the root's tree board and payment's own board built and kept as states, then
        edited and diffed. Miro ids are unique across boards (own_base); a host board's are not (own_base=0)."""
        w = os.path.join(d, "pair-" + tag)
        shutil.copytree(nest, w)
        if mutate:
            mutate(w)
        rw, pw = os.path.join(w, "journey-first-order.md"), os.path.join(w, "journey-payment.md")
        ext = "svg" if surface == "miro" else "json"
        _, _, tl = run("board-layout", "--note", rw, "--lang", "uk", "--with-children")
        _, _, ol = run("board-layout", "--note", pw, "--lang", "uk")
        ti = board_items(tl)
        if align:                                    # two host boards made apart number their elements alike: one row's
            a_t = next(x["id"] for x in ti if x["kind"] == "sticky" and x["text"].startswith(align))     # sticky gets one id
            a_o = next(x["id"] for x in board_items(ol) if x["kind"] == "sticky" and x["text"].startswith(align))
            own_base = int(a_t) - int(a_o)
        oi = board_items(ol, own_base)
        if before_tree:
            before_tree(ti)
        ts, ost = os.path.join(w, "t.state.json"), os.path.join(w, "o.state.json")
        run("board-state", "--read", board_read(ti, surface, os.path.join(w, "t-last." + ext)), "--note", rw, "--surface", surface,
            "--out", ts, "--with-children")
        run("board-state", "--read", board_read(oi, surface, os.path.join(w, "o-last." + ext)), "--note", pw, "--surface", surface, "--out", ost)
        tn, on = [dict(x) for x in ti], [dict(x) for x in oi]
        tree_edit(tn)
        own_edit(on)
        td, od = os.path.join(w, "t.diff.json"), os.path.join(w, "o.diff.json")
        tnow = board_read(tn, surface, os.path.join(w, "t-now." + ext))
        _, _, r1 = run("board-diff", "--last", ts, "--now", tnow, "--note", rw, "--out", td)
        _, _, r2 = run("board-diff", "--last", ost, "--now", board_read(on, surface, os.path.join(w, "o-now." + ext)), "--note", pw, "--out", od)
        E = lambda it: eid_of(surface, it["id"])  # noqa: E731
        return {"w": w, "root": rw, "pay": pw, "td": td, "od": od, "ti": ti, "oi": oi, "tn": tn, "on": on, "E": E, "tdiff": r1,
                "odiff": r2, "ts": ts, "tnow": tnow, "tlast": os.path.join(w, "t-last." + ext)}

    def sticky(items, start):
        return next(it for it in items if it["kind"] == "sticky" and it["text"].startswith(start))

    def frame(items, title):
        return next(it for it in items if it["kind"] == "frame" and it["text"] == title)

    def set_text(start, new):
        def f(items):
            sticky(items, start)["text"] = new
        return f
    keep = lambda items: None  # noqa: E731

    # #1 (high): `row:<id>` never gets past the conflict guard — in either diff order, alone or with an element
    P = pair("row", "miro", set_text("Форма картки скидає", "Версія кореня"), set_text("Форма картки скидає", "Версія своєї дошки"))
    t1, o1 = P["E"](sticky(P["tn"], "Версія кореня")), P["E"](sticky(P["on"], "Версія своєї дошки"))
    for order in ((P["td"], P["od"]), (P["od"], P["td"])):
        rc, out, res = run("board-take", "--note", P["pay"], "--diff", *order, "--take", "row:pc1", "--dry-run")
        check("13.1 #1 `--take row:pc1` of a row changed on two boards is refused `conflict` (diff order %s)" % ("tree, own" if order[0] == P["td"] else "own, tree"),
              rc == 0 and any(r["id"] == "row:pc1" and r["why"] == "conflict" for r in res.get("refused", []))
              and not any(a.get("row") == "pc1" for a in res.get("applied", [])), (res.get("refused"), res.get("applied")))
    rc, out, res = run("board-take", "--note", P["pay"], "--diff", P["td"], P["od"], "--take", "row:pc1", o1, "--dry-run")
    check("13.2 #1 `row:pc1` with one version's element: both refused `conflict`, nothing applied to pc1",
          sorted(r["why"] for r in res.get("refused", []) if r["id"] in ("row:pc1", o1)) == ["conflict", "conflict"]
          and not any(a.get("row") == "pc1" for a in res.get("applied", [])), res.get("refused"))
    rc, out, res = run("board-take", "--note", P["pay"], "--diff", P["td"], P["od"], "--take", t1, "--class", "%s=observed" % t1, "--dry-run")
    check("13.3 #1 one version by its element: taken", any(a.get("row") == "pc1" and a.get("after") == "Версія кореня" for a in res.get("applied", [])),
          res.get("applied"))

    # #3: board-state keeps a tree state a tree, the flag forgotten
    rc, out, res = run("board-state", "--read", P["tnow"], "--note", P["root"], "--surface", "miro", "--last", P["ts"],
                       "--out", os.path.join(P["w"], "t2.state.json"))
    check("13.4 #3 board-state with --last of a tree state and no --with-children: the tree kept, child rows still keyed",
          rc == 0 and res.get("tree") == ["journey-shipping", "journey-payment", "journey-3ds"] and "journey-payment#pc2" in res.get("rows", {})
          and res.get("roles", {}).get("rollup") == 4, out[-400:])

    # #2: a roll-up whose child left the tree never comes back as a team row
    def unlink(w):
        pass
    P2 = pair("stale", "miro", keep, keep)
    sh = os.path.join(P2["w"], "journey-shipping.md")
    write(sh, text(sh).replace("parent: journey-first-order\nparent_stage: s4\n", ""))
    st2 = os.path.join(P2["w"], "t3.state.json")
    rc, out, res = run("board-state", "--read", P2["tlast"], "--note", P2["root"], "--surface", "miro", "--last", P2["ts"], "--out", st2, "--with-children")
    rid = P2["E"](sticky(P2["ti"], "↳ «Вибір доставки» · journey-shipping"))
    stj = json.loads(text(st2)) if os.path.exists(st2) else {}
    check("13.5 #2 the roll-up of a child that left the tree stays `rollup` in the re-kept state",
          rc == 0 and (stj.get("elements", {}).get(rid) or {}).get("role") == "rollup", (stj.get("elements", {}).get(rid), out[-300:]))
    rc, out, res = run("board-diff", "--last", st2, "--now", P2["tlast"], "--note", P2["root"])
    check("13.6 #2 …and is never offered as a team addition", rc == 0 and res.get("added") == [], res.get("added"))

    # #4: a child file name the tree board cannot parse is no map of the tree
    c4 = os.path.join(d, "c4")
    shutil.copytree(nest, c4)
    os.rename(os.path.join(c4, "journey-shipping.md"), os.path.join(c4, "journey shipping.md"))
    write(os.path.join(c4, "journey·x.md"), text(os.path.join(nest, "journey-shipping.md")).replace('journey: "Вибір доставки"', 'journey: "Ікс"'))
    rc, out, res = run("nest", "--note", os.path.join(c4, "journey-first-order.md"), "--json")
    check("13.7 #4 a file name with a space or «·» is skipped unsafe_name, never half-nested",
          rc == 0 and sum(1 for sk in res.get("skipped", []) if sk.get("reason") == "unsafe_name") == 2
          and [k.get("note") for k in (res.get("tree") or {}).get("children", [])] == ["journey-payment"], res.get("skipped"))

    # #5: board-take finds the note by name as the tree does — any case, either Unicode form
    def nfd_child(w):
        n = unicodedata.normalize("NFD", "journey-край-оплати")
        write(os.path.join(w, n + ".md"), text(os.path.join(nest, "journey-shipping.md")).replace("parent_stage: s4", "parent_stage: s3")
              .replace('journey: "Вибір доставки"', 'journey: "Край оплати"'))
    P5 = pair("nfd", "miro", keep, keep, mutate=nfd_child)
    nfdp = os.path.join(P5["w"], unicodedata.normalize("NFD", "journey-край-оплати") + ".md")
    rc, out, res = run("board-take", "--note", nfdp, "--diff", P5["td"], "--dry-run")
    check("13.8 #5 a child stored NFD, passed by its real path: its tree board's diff is its own", rc == 0, out[-300:])
    up = os.path.join(P5["w"], "JOURNEY-PAYMENT.md")
    if os.path.exists(up):                           # a case-insensitive disk (APFS by default)
        rc, out, res = run("board-take", "--note", up, "--diff", P5["td"], "--dry-run")
        check("13.9 #5 a child passed in another letter case: its tree board's diff is its own", rc == 0, out[-300:])

    # #7: a row removed on one board and changed on the other; the same sticky added on both boards
    def drop_pc2(items):
        items.remove(sticky(items, "Незрозуміло, чому картку відхилено"))
    P7 = pair("rm", "miro", set_text("Незрозуміло, чому картку відхилено", "Незрозуміло, чому банк відхилив"), drop_pc2)
    t7 = P7["E"](sticky(P7["tn"], "Незрозуміло, чому банк відхилив"))
    rc, out, res = run("board-take", "--note", P7["pay"], "--diff", P7["td"], P7["od"], "--take", t7, "--drop", "pc2", "--dry-run")
    check("13.10 #7 removed on one board, changed on the other: a conflict — the change and the drop both refused",
          any(c.get("row") == "pc2" and c.get("what") == "removed" for c in res.get("conflicts", []))
          and sorted(r["why"] for r in res.get("refused", []) if r["id"] in (t7, "pc2")) == ["conflict", "conflict"], (res.get("conflicts"), res.get("refused")))

    def add_same(items):
        items.append({"id": "%d" % (len(items) + 7000), "kind": "sticky", "text": "Немає Google Pay", "x": 10, "y": 360,
                      "cell": frame(items, next(t for t in ("journey-payment · s2 · болі", "s2 · болі") if any(i["kind"] == "frame" and i["text"] == t for i in items)))["id"]})
    P8 = pair("dup", "miro", add_same, add_same)
    adds = [a["id"] for a in P8["tdiff"].get("added", [])] + [a["id"] for a in P8["odiff"].get("added", [])]
    rc, out, res = run("board-take", "--note", P8["pay"], "--diff", P8["td"], P8["od"], "--take", *adds,
                       "--class", *["%s=reported" % a for a in adds], "--dry-run")
    check("13.11 #7 the same sticky added on both boards: one row, the second refused `taken`",
          sum(1 for a in res.get("applied", []) if a.get("action") == "add") == 1 and any(r["why"] == "taken" for r in res.get("refused", [])),
          (res.get("applied"), res.get("refused")))

    # #8: two host boards — ids collide; moves; a loose text; a team sticky moved into a child's cell; an older raw --last
    def move_to(start, title):
        def f(items):
            sticky(items, start)["cell"] = frame(items, title)["id"]
        return f
    PW = pair("wb", "whiteboard", set_text("Форма картки скидає", "Версія кореня"), set_text("Форма картки скидає", "Версія своєї дошки"),
              align="Форма картки скидає")
    ids = [c["id"] for c in PW["tdiff"].get("changed", [])] + [c["id"] for c in PW["odiff"].get("changed", [])]
    rc, out, res = run("board-take", "--note", PW["pay"], "--diff", PW["td"], PW["od"], "--take", ids[0], "--dry-run")
    vids = sorted(v["id"] for c in res.get("conflicts", []) for v in c["versions"])
    check("13.12 #8 two host boards whose ids collide: the versions prefixed by their diff, the bare id refused",
          len(set(ids)) == 1 and vids == sorted(["journey-first-order@whiteboard:%s" % ids[0], "journey-payment@whiteboard:%s" % ids[0]])
          and any(r["id"] == ids[0] and r["why"] == "unknown" for r in res.get("refused", [])), (ids, vids, res.get("refused")))
    PM = pair("mv", "miro", move_to("Форма картки скидає", "journey-payment · s3 · болі"), move_to("Форма картки скидає", "s1 · болі"))
    rc, out, res = run("board-take", "--note", PM["pay"], "--diff", PM["td"], PM["od"], "--dry-run")
    check("13.13 #8 one row moved to two different cells on two boards: a conflict of `cell`",
          any(c.get("row") == "pc1" and c.get("what") == "cell" for c in res.get("conflicts", [])), res.get("conflicts"))

    def loose(items):
        items.append({"id": "8800", "kind": "text", "text": "↳ «Оплата» · journey-payment — примітка команди", "x": 4000, "y": 40})
    PL = pair("loose", "miro", loose, keep)
    check("13.14 #8 a loose text that starts like a roll-up is `other`, never the plugin's",
          any(o.get("id") == "8800" and o.get("change") == "added" for o in PL["tdiff"].get("other", []))
          and not any(u.get("id") == "8800" for u in PL["tdiff"].get("unrecorded", [])), (PL["tdiff"].get("other"), PL["tdiff"].get("unrecorded")))

    def team_note(items):
        items.append({"id": "8900", "kind": "sticky", "text": "Командна нотатка про оплату", "x": 10, "y": 360, "cell": frame(items, "s5 · болі")["id"]})
    PT = pair("tm", "miro", move_to("Командна нотатка про оплату", "journey-payment · s2 · болі"), keep, before_tree=team_note)
    rc, out, res = run("board-take", "--note", PT["pay"], "--diff", PT["td"], "--take", "8900", "--class", "8900=reported", "--dry-run")
    check("13.15 #8 a team sticky moved from a root cell into a child's cell is the child's — by where it is now",
          rc == 0 and any(a.get("action") == "add" and a.get("cell") == "s2 · болі" for a in res.get("applied", [])), (res.get("applied"), res.get("refused")))
    rc, out, res = run("board-diff", "--last", P["tlast"], "--now", P["tnow"], "--note", P["root"], "--with-children")
    check("13.16 #8 an older raw read as --last of a tree board: its roles by the tree",
          rc == 0 and any(c.get("row") == "journey-payment#pc1" for c in res.get("changed", [])), res.get("changed"))

    # #9 nit: a map without children keeps its result lines; the root's own name page-safe in the chat fields
    plain_ = os.path.join(d, "plain")
    os.makedirs(plain_)
    shutil.copy(os.path.join(fx, "journey-first-order.md"), plain_)
    pn = os.path.join(plain_, "journey-first-order.md")
    rc, out, res = run("render-html", "--note", pn, "--out", os.path.join(plain_, "p.html"))
    check("13.17 #9 render-html of a map without children: no nesting keys", rc == 0 and not ({"children", "deeper", "above"} & set(res)), sorted(res))

    # mutants that stayed green in review 2
    for name, old, new, cmd, test in (
            ("no-prefix", '                    e["id"] = "%s:%s" % (d["_tag"], e["id"])', '                    pass  #',
             lambda m: run("board-take", "--note", PW["pay"], "--diff", PW["td"], PW["od"], "--take", ids[0], "--dry-run", script=m),
             lambda r: not any(rr["why"] == "unknown" for rr in r.get("refused", []))),
            ("no-move-conflict", '    for cat, what in (("changed", "text"), ("moved", "cell")):', '    for cat, what in (("changed", "text"),):',
             lambda m: run("board-take", "--note", PM["pay"], "--diff", PM["td"], PM["od"], "--dry-run", script=m),
             lambda r: not any(c.get("what") == "cell" for c in r.get("conflicts", []))),
            ("no-rerole", "        last, _, _ = load_board_state(args.last, note, args.surface)   # an older read: its roles by the tree", "        pass",
             lambda m: run("board-diff", "--last", P["tlast"], "--now", P["tnow"], "--note", P["root"], "--with-children", script=m),
             lambda r: not any(c.get("row") == "journey-payment#pc1" for c in r.get("changed", []))),
            ("rollup-any-kind", 'if marks and it["kind"] == "sticky" and t.lower() not in heads else None', 'if marks and t.lower() not in heads else None',
             lambda m: run("board-diff", "--last", os.path.join(PL["w"], "t.state.json"), "--now", os.path.join(PL["w"], "t-now.svg"), "--note", PL["root"], script=m),
             lambda r: not any(o.get("id") == "8800" for o in r.get("other", [])))):
        m = mutant(d, name, old, new)
        if m is None:
            check("M.%s the mutation's pattern is in journey_map.py" % name, False, old)
            continue
        rc, out, res = cmd(m)
        check("M.%s a mutant is caught" % name, test(res), out[-300:])

    # 14. review 3 (opus, whole branch, frozen b2dfbb7): each finding reproduced first
    r4 = os.path.join(d, "r4")
    shutil.copytree(nest, r4)
    funnel = os.path.join(fx, "snapshot-2026-11-16.md")
    p4, root4 = os.path.join(r4, "journey-payment.md"), os.path.join(r4, "journey-first-order.md")
    p40, root40 = read(p4), read(root4)
    rc, out, res = run("refresh", "--note", p4, "--snapshot", funnel, "--lang", "uk")
    check("14.1 #1 the funnel's snapshot never refreshes a child map (its stages are its own) — refused, the note byte for byte",
          rc == 2 and "map" in res.get("error", "") and read(p4) == p40, out[-300:])
    own4 = os.path.join(d, "snap4", "2026-11-23.md")
    write(own4, "---\ntype: cjm-health-check\nproduct: zorg\nmap: journey-payment\ndate: 2026-11-23\nhealth_score: 60\nstages:\n"
                "  - id: s2\n    metric: \"card -> confirm\"\n    value: \"57%\"\n    status: critical\n---\n")
    rc, out, res = run("refresh", "--note", p4, "--snapshot", own4, "--lang", "uk")
    check("14.2 #1 a snapshot that names the child (`map: journey-payment`) refreshes it", rc == 0 and res.get("health", {}).get("score") == 60, out[-300:])
    rc, out, res = run("refresh", "--note", root4, "--snapshot", own4, "--lang", "uk")
    check("14.3 #1 a snapshot of another map never refreshes the root — refused, the root byte for byte",
          rc == 2 and "map" in res.get("error", "") and read(root4) == root40, out[-300:])
    rep_ = text(os.path.join(ROOT, "skills", "cjm-research", "references", "cjm-reports.md"))
    check("14.4 #1 the scheduled health-check refreshes only maps without a `parent`; a child by its own snapshot",
          re.search(r"^(?=.*journey_map\.py refresh)(?=.*without a `parent`).*$", rep_, re.M) is not None, "cjm-reports.md")

    # #2: the roll-ups and references are mapped to their element ids, so a new version updates them by id
    rc, out, res = run("board-state", "--read", P["tlast"], "--note", P["root"], "--surface", "miro", "--out", os.path.join(P["w"], "t4.state.json"),
                       "--with-children")
    want = {"journey-shipping": P["E"](sticky(P["ti"], "↳ «Вибір доставки» · journey-shipping")),
            "journey-payment": P["E"](sticky(P["ti"], "↳ «Оплата» · journey-payment")),
            "journey-3ds": P["E"](sticky(P["ti"], "↳ «3-D Secure» · journey-3ds"))}
    check("14.5 #2 board-state names each child's roll-up sticky and each reference by its element id",
          rc == 0 and res.get("rollups") == want and res.get("references") == {"journey-3ds-retry": P["E"](sticky(P["ti"], "↳ «Повтор коду» · journey-3ds-retry"))},
          (res.get("rollups"), res.get("references")))
    rc, out, res = run("board-diff", "--last", os.path.join(P["w"], "t4.state.json"), "--note", P["root"])
    check("14.6 #2 board-diff gives them too (the ids to update)", res.get("rollups") == want, res.get("rollups"))
    shp = os.path.join(P["w"], "journey-shipping.md")
    write(shp, text(shp).replace('journey: "Вибір доставки"', 'journey: "Доставка й самовивіз"'))
    rc, out, res = run("board-state", "--read", P["tlast"], "--note", P["root"], "--surface", "miro", "--last", os.path.join(P["w"], "t4.state.json"),
                       "--out", os.path.join(P["w"], "t5.state.json"))
    check("14.7 #2 a child renamed since: its old roll-up keeps its child by its element id", rc == 0
          and (res.get("rollups") or {}).get("journey-shipping") == want["journey-shipping"], res.get("rollups"))

    # #5: the take does not depend on the order of --diff
    outs = []
    for order in ((PW["td"], PW["od"]), (PW["od"], PW["td"])):
        rc, out, res = run("board-take", "--note", PW["pay"], "--diff", *order, "--dry-run")
        outs.append(sorted(v["id"] for c in res.get("conflicts", []) for v in c["versions"]))
    check("14.8 #5 a version's id names its board, whatever the order of --diff", outs[0] == outs[1] and outs[0]
          and all("@whiteboard:" in i for i in outs[0]), outs)
    rows_ = []
    for order in ((P8["td"], P8["od"]), (P8["od"], P8["td"])):
        rc, out, res = run("board-take", "--note", P8["pay"], "--diff", *order, "--take", *adds, "--class", *["%s=reported" % a for a in adds], "--dry-run")
        rows_.append(sorted((a.get("element"), a.get("row")) for a in res.get("applied", []) if a.get("action") == "add"))
    check("14.9 #5 a new row's id is the same in either order", rows_[0] == rows_[1] and rows_[0], rows_)

    # #7 nits: a skipped parent named as such; an unreadable map named; parent as a mapping; parent_step as a list
    c7 = os.path.join(d, "c7")
    shutil.copytree(nest, c7)
    write(os.path.join(c7, "journey-shipping.md"), text(os.path.join(nest, "journey-shipping.md")).replace("type: cjm-journey\n", "type: cjm-journey\nsensitive: true\n"))
    write(os.path.join(c7, "journey-k-sub.md"), lost_t.replace("parent: journey-gone", "parent: journey-shipping").replace('journey: "journey-lost"', 'journey: "Під доставкою"'))
    write(os.path.join(c7, "journey-k-map.md"), lost_t.replace("parent: journey-gone\n", "parent:\n  name: journey-first-order\n").replace('journey: "journey-lost"', 'journey: "Мапа"'))
    write(os.path.join(c7, "journey-k-steps.md"), lost_t.replace("parent: journey-gone\nparent_stage: s1\n", "parent: journey-first-order\nparent_stage: s5\nparent_step: [Оплата карткою, Інше]\n")
          .replace('journey: "journey-lost"', 'journey: "Два кроки"'))
    locked = os.path.join(c7, "journey-locked.md")
    write(locked, text(os.path.join(nest, "journey-self.md")))
    os.chmod(locked, 0)
    rc, out, res = run("nest", "--note", os.path.join(c7, "journey-first-order.md"), "--json")
    os.chmod(locked, 0o644)
    orph = {f.get("note"): f for f in findings_of(res, "orphan_child")}
    check("14.10 #7 a child whose parent was skipped: named so, not «renamed, deleted or not given»",
          "skipped" in (orph.get("journey-k-sub") or {}).get("detail", ""), orph.get("journey-k-sub"))
    check("14.11 #7 `parent:` written as a mapping is `bad_parent`, never silently a root", (orph.get("journey-k-map") or {}).get("why") == "bad_parent",
          orph.get("journey-k-map"))
    check("14.12 #7 `parent_step` written as a list is named (`no_step`), never read as no step",
          (orph.get("journey-k-steps") or {}).get("why") == "no_step", orph.get("journey-k-steps"))
    if os.getuid() != 0:
        check("14.13 #7 a map the folder holds but cannot read is named unreadable, never counted as plain markdown",
              any(sk.get("note") == "journey-locked.md" and sk.get("reason") == "unreadable" for sk in res.get("skipped", [])), res.get("skipped"))

    # #3: check 28 guards the unsafe-name marks, the subtree wording and the skill's tree board and two-diff take
    for name, rel, old, new, expect in (
            ("unsafe marks", "references/journey-protocol.md", "«:», «#»", "«#»", "unsafe"),
            ("subtree words", "references/journey-protocol.md", "«з дочірніми картами (N)", "«з підкартами (N)", "з дочірніми картами"),
            ("tree board in J8", "skills/cjm-research/SKILL.md", "board-layout --with-children", "board-layout --tree", "--with-children"),
            ("two-diff take in J8", "skills/cjm-research/SKILL.md", "board-take --note <child> --diff", "board-take --note <child> --from", "board-take")):
        drift28(rel, old, new, expect, "14.x #3 check 28 names a drift of %s" % name)

    # 15. the user's rule (2026-11-24, during acceptance): the whole process works on the host's own tools — a board
    #     tool's paid account is never needed, so the host's own board is the first board offered, a registry record's
    #     (Miro) after it; check 29 keeps the order in §11, artifact-publishing §3 and the skill's J4
    r29 = os.path.join(d, "root29n")
    for rel in ("references/journey-protocol.md", "references/artifact-publishing.md", "references/tools-seed.yaml",
                "scripts/story_map.py", "scripts/journey_map.py", "skills/cjm-research/SKILL.md"):
        os.makedirs(os.path.dirname(os.path.join(r29, rel)), exist_ok=True)
        shutil.copy(os.path.join(ROOT, rel), os.path.join(r29, rel))
    e29 = jm.check_board_protocol(r29)
    check("15.1 check 29 is clean: the host's own board comes first", e29 == [], e29)
    for name, rel, old, new in (
            ("§11", "references/journey-protocol.md", "then the host's own board, then a registry record's board", "then a registry record's board, then the host's own board"),
            ("artifact-publishing §3", "references/artifact-publishing.md", "the host's own first, then a registry record's", "a registry record's first, then the host's own"),
            ("J4", "skills/cjm-research/SKILL.md", "the host's own before a registry record's", "a registry record's before the host's own")):
        p_ = os.path.join(r29, rel)
        t0 = text(p_)
        if old not in t0:
            check("15.x the order's site is in %s" % rel, False, old)
            continue
        write(p_, t0.replace(old, new, 1))
        e = jm.check_board_protocol(r29)
        write(p_, t0)
        check("15.x check 29 names a board tool put before the host's own board in %s" % name, any("host's own board" in x for x in e), e)

    # 9. regression — a map without children behaves as in v4.9.0 (the goldens of 332d1a5)
    main = os.path.join(fx, "journey-first-order.md")
    rc, out, res = run("render-html", "--note", main, "--out", os.path.join(d, "p-uk.html"), "--lang", "uk")
    check("9.1 render-html (uk) of a map without children = v4.9.0", rc == 0
          and date_free(text(os.path.join(d, "p-uk.html"))) == text(os.path.join(GOLD, "page-uk-first-order.html")), out[-300:])
    rc, out, res = run("render-html", "--note", main, "--out", os.path.join(d, "p-en.html"), "--lang", "en")
    check("9.2 render-html (en) = v4.9.0", rc == 0
          and date_free(text(os.path.join(d, "p-en.html"))) == text(os.path.join(GOLD, "page-en-first-order.html")), out[-300:])
    rc, out, res = run("board-layout", "--note", main, "--lang", "uk")
    check("9.3 board-layout of a map without children = v4.9.0", rc == 0
          and res == json.loads(text(os.path.join(GOLD, "board-layout-first-order.json"))), out[-300:])
    rc, out, res = run("parse", "--note", main)
    gp = json.loads(text(os.path.join(GOLD, "parse-first-order.json")))
    check("9.4 parse = v4.9.0 plus the three nesting fields, empty", rc == 0
          and {k: v for k, v in res.items() if k not in ("parent", "parent_stage", "parent_step")} == gp
          and (res.get("parent"), res.get("parent_stage"), res.get("parent_step")) == ("", "", ""), out[-300:])
    rc, out, res = run("check", "--note", main, "--snapshots", os.path.join(fx, "health-checks"))
    check("9.5 check = v4.9.0", rc == 0 and res == json.loads(text(os.path.join(GOLD, "check-first-order.json"))), out[-300:])
    rmain = os.path.join(d, "refresh", "journey-first-order.md")
    write(rmain, read(main))
    rc, out, res = run("refresh", "--note", rmain, "--snapshot", os.path.join(fx, "snapshot-2026-11-16.md"),
                       "--out", os.path.join(d, "refresh", "r.html"), "--lang", "uk")
    gr = json.loads(text(os.path.join(GOLD, "refresh-first-order.json")))
    check("9.6 refresh of a map without children: the note, the result and the page = v4.9.0", rc == 0
          and text(rmain) == text(os.path.join(GOLD, "refresh-first-order.md"))
          and {k: v for k, v in res.items() if k != "out"} == gr
          and date_free(text(os.path.join(d, "refresh", "r.html"))) == text(os.path.join(GOLD, "refresh-first-order.html")),
          (out[-300:], {k: v for k, v in res.items() if k != "out"}))

    # mutations from the plan
    for name, old, new, test in (
            ("copied-row", '"outcome": outcome or OUTCOME_TBD,', '"outcome": outcome or OUTCOME_TBD, "rows": [r["text"] for r in shown],',
             lambda r: "Форма картки скидає" in json.dumps(r, ensure_ascii=False)),
            ("deep-grid", "MAX_DEPTH = 3", "MAX_DEPTH = 4",
             lambda r: node(r.get("tree") or {}, "journey-3ds-retry") is not None),
            ("hc-pains", 'if r["lane"] == "pain":', 'if r["lane"] in ("pain", "metric", "anomaly"):',
             lambda r: (node(r.get("tree") or {}, "journey-payment") or {}).get("rollup", {}).get("pains_total") != 3),
            ("own-word", 'st = hc_status(r["text"]) if _is_hc(r) else None', 'st = "critical" if "критично" in r["text"] else None',
             lambda r: (node(r.get("tree") or {}, "journey-payment") or {}).get("rollup", {}).get("anomalies", {}).get("critical") != 1)):
        m = mutant(d, name, old, new)
        if m is None:
            check("M.%s the mutation's pattern is in journey_map.py" % name, False, old)
            continue
        rc, out, res = run("nest", "--note", root, "--json", script=m)
        check("M.%s a mutant is caught by the same assertions" % name, rc != 0 or test(res), out[-300:])
    m = mutant(d, "loop", "if cur in seen:", "if False:")
    if m is None:
        check("M.loop the mutation's pattern is in journey_map.py", False, "if cur in seen:")
    else:
        rc, out, res = run("nest", "--note", root, "--json", script=m, timeout=10)
        check("M.loop a cycle that loops is caught (the run times out)", rc is None, out[-300:])
finally:
    shutil.rmtree(d, ignore_errors=True)
    shutil.rmtree(SAFE_HOME, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)

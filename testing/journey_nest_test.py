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
          kids == [("journey-delivery", "s4", "", 2), ("journey-payment", "s5", "Оплата карткою", 2)], kids)
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
    dl = node(tree, "journey-delivery") or {}
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

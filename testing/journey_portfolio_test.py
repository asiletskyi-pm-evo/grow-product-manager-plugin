#!/usr/bin/env python3
"""TC-portfolio-4900 — scripts/journey_portfolio.py, the journey portfolio (v4.9.0, references/journey-protocol.md §13).

Fictional «Zorg» notes (testing/fixtures/journey/portfolio/) are copied into a temp folder: three journey maps of the
product (a health drop of 14 points with a critical anomaly; a review older than 90 days, no owner and a stage without
evidence; a fresh published one), a map of another product, a hand CJM note (`type: cjm` with `funnel` and stage
headings `## <ID> — <name>`), a cjm-research report (`type: cjm` without them) and a CJM index note.
- list: the maps that need attention first (by the number of reasons, then by name), the rest by name, the hand CJMs in
  their own block; each map's owner, stages, health with its delta and date, review, pains by class, anomalies with
  the critical ones read by journey_map's labels, gaps, findings, publication places; the hand CJM's funnel, stages,
  metric rows per stage and snapshot only, with stage_count / no_snapshot; the report skipped and named; another
  product's note counted, never listed; a folder read gives the same; nothing is written to any note;
- render-html: one self-contained page — no link, no request, no row text, numbers only; sparklines; light theme;
  sticky headers and journey_map's fixed pan script; every text escaped; a page that cannot be written: exit 1;
- schema: the columns, attention reasons, hand-CJM fields and skip reasons.
Mutations (ledger): a `type: cjm` report taken as a hand CJM, a health drop that does not raise a map, a hand CJM's
link in the output, another product's note in the portfolio, criticality by a word of its own instead of the label —
each caught. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/journey_portfolio_test.py
"""
import hashlib, html, json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "journey_portfolio.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "journey", "portfolio")
TODAY = "2026-11-20"
sys.path.insert(0, os.path.join(ROOT, "scripts"))

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


SAFE_HOME = tempfile.mkdtemp(prefix="portfolio-home-")


def run(*args, script=SCRIPT):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GROW_PM_")}
    env["HOME"] = SAFE_HOME
    p = subprocess.run([sys.executable, script] + list(args), capture_output=True, text=True, env=env)
    res = {}
    for line in p.stdout.splitlines():
        if line.startswith("PORTFOLIO_RESULT "):
            res = json.loads(line[len("PORTFOLIO_RESULT "):])
    return p.returncode, p.stdout + p.stderr, res


def text(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def digest(top):
    out = {}
    for dp, _, names in os.walk(top):
        for n in names:
            p = os.path.join(dp, n)
            out[os.path.relpath(p, top)] = hashlib.sha1(open(p, "rb").read()).hexdigest()
    return out


def mutant(d, name, old, new, target="journey_portfolio.py"):
    """A copy of the scripts folder where `old` became `new` in `target`; None when `old` is not there."""
    sdir = os.path.dirname(SCRIPT)
    if not os.path.exists(os.path.join(sdir, target)):
        return None
    src = open(os.path.join(sdir, target), encoding="utf-8").read()
    if old not in src:
        return None
    mdir = os.path.join(d, "mut-" + name)
    os.makedirs(mdir)
    for f in os.listdir(sdir):
        if f.endswith(".py"):
            shutil.copy(os.path.join(sdir, f), mdir)
    write(os.path.join(mdir, target), src.replace(old, new))
    return os.path.join(mdir, os.path.basename(SCRIPT))


# What a portfolio never carries: row texts, sources, the hand CJM's links, dashboards, modules, owners, missions,
# meetings and text, a person's name or contact, an epic code from a note's text.
NEVER = ("http", "example.com", "Bea", "bea.two", "+380", "Модулі", "Місії", "PROJ-1234", "Команда пошуку", "Мітинг",
         "Загальний текст", "Дашборд", "Друга таблиця", "Пошукові сесії", "Додавання в кошик", "Команда кошика",
         "Головна довго вантажиться", "Не видно вартості", "Не знаходить минуле", "Форма заяви", "buyer@zorg",
         "walkthrough", "feedback-triage", "зі слів PM", "product-research", "persona run", "Довга форма", "Quux",
         "Повтор кошика", "zorg-first-order-page")

if not os.path.exists(SCRIPT):
    check("0.0 scripts/journey_portfolio.py exists", False, SCRIPT)
    print("\nRESULT: RED ❌ (%d failed)" % fails)
    sys.exit(1)

with tempfile.TemporaryDirectory() as d:
    fx = os.path.join(d, "fx")
    shutil.copytree(FIX, fx)
    J = os.path.join(fx, "journeys", "zorg")
    H = os.path.join(fx, "hand")
    notes = [os.path.join(J, n) for n in ("journey-first-order.md", "journey-repeat-order.md", "journey-returns.md")]
    quux = os.path.join(fx, "journeys", "quux", "journey-signup.md")
    buyer, report, index = (os.path.join(H, n) for n in ("cjm-zorg-buyer.md", "cjm-report-zorg-2026-10.md", "cjm-index.md"))
    before = digest(fx)

    # 1. list over the notes ctx search would give
    args = ["list", "--product", "zorg", "--today", TODAY, "--lang", "uk"]
    for n in notes + [quux, buyer, report]:
        args += ["--note", n]
    rc, out, res = run(*args)
    check("1.1 list: exit 0 and one PORTFOLIO_RESULT line", rc == 0 and res.get("ok") is True
          and out.count("PORTFOLIO_RESULT ") == 1, out[-800:])
    maps = res.get("maps") or []
    names = [m.get("journey") for m in maps]
    check("1.2 the maps that need attention first — by the number of reasons, then by name; the fresh one below",
          names == ["Повернення товару", "Повторне замовлення", "Перше замовлення"], names)
    by = {m.get("journey"): m for m in maps}
    rt, rp, fo = by.get("Повернення товару", {}), by.get("Повторне замовлення", {}), by.get("Перше замовлення", {})
    reasons = lambda m: [a.get("reason") for a in m.get("attention", [])]  # noqa: E731
    check("1.3 the returns map: stale review, no owner, a stage without evidence", reasons(rt) == ["stale_review", "no_owner", "empty_stage"],
          rt.get("attention"))
    check("1.4 the repeat-order map: a health drop of more than 10 points and a critical anomaly",
          reasons(rp) == ["health_drop", "critical_anomaly"], rp.get("attention"))
    check("1.5 the fresh map needs nothing", reasons(fo) == [], fo.get("attention"))
    check("1.6 health: the last score, the delta to the previous point, the point's date, every point for the sparkline",
          (rp.get("health") or {}).get("score") == 64 and rp["health"].get("delta") == -14 and rp["health"].get("date") == "2026-11-09"
          and rp["health"].get("points") == [{"date": "2026-11-02", "score": 78}, {"date": "2026-11-09", "score": 64}]
          and (fo.get("health") or {}).get("delta") == 3, (rp.get("health"), fo.get("health")))
    check("1.7 one point: no delta; no point: no score", (rt.get("health") or {}).get("score") == 66 and rt["health"].get("delta") is None,
          rt.get("health"))
    check("1.8 review: its date and «застаріло» past 90 days", rt.get("reviewed") == "2026-07-01" and rt.get("stale_review") is True
          and fo.get("stale_review") is False, (rt.get("reviewed"), rt.get("stale_review")))
    check("1.9 owner (a role or a team), stage count", fo.get("owner") == "Команда оформлення Zorg" and fo.get("stages") == 2
          and rt.get("owner") == "", (fo.get("owner"), fo.get("stages"), rt.get("owner")))
    check("1.10 pains by class — a gap row is no pain, a simulated one counted as written",
          rp.get("pains") == {"observed": 1, "reported": 2, "simulated": 1} and rt.get("pains") == {"observed": 1, "reported": 1},
          (rp.get("pains"), rt.get("pains")))
    check("1.11 anomalies: critical apart, the status read from the health-check row by journey_map's labels — a row "
          "the PM wrote counted without a level, a word inside the text is no status",
          rp.get("anomalies") == {"total": 3, "critical": 1, "warning": 0, "positive": 1, "unrated": 1}, rp.get("anomalies"))
    check("1.12 gaps: empty_stage and no_outcome by stage", rt.get("gaps") == {"empty_stage": ["s2"], "no_outcome": ["s2"]}
          and fo.get("gaps") == {"empty_stage": [], "no_outcome": []}, rt.get("gaps"))
    check("1.13 findings: journey_map's own findings, counted", (rt.get("findings") or {}).get("total") == 6
          and rt["findings"].get("by") == {"no_owner": 1, "stale_review": 1, "no_outcome": 1, "empty_stage": 1, "link": 1,
                                           "contact": 1}
          and (fo.get("findings") or {}).get("total") == 0, (rt.get("findings"), fo.get("findings")))
    check("1.14 where it is published: places and versions from the `published` mirror — never its link or id",
          fo.get("published") == [{"surface": "artifact", "kind": "dashboard", "level": "page", "version": 2, "audience": "private"}]
          and rp.get("published") == [], fo.get("published"))
    check("1.15 each map row: only the portfolio's fields — no row of the map", set(fo) == {
        "journey", "note", "path", "product", "owner", "stages", "health", "reviewed", "stale_review", "pains", "anomalies",
        "gaps", "findings", "published", "attention", "product_missing"}, sorted(fo))
    cj = res.get("cjm") or []
    check("1.16 the hand CJM: its own block, partly — funnel, stages from the headings with the metric rows of the first "
          "metric table under each, the snapshot, the mark",
          len(cj) == 1 and cj[0].get("title") == "CJM покупця Zorg" and cj[0].get("funnel") == "buyer"
          and cj[0].get("stages_declared") == 4
          and cj[0].get("stages") == [{"id": "B1", "name": "Пошук", "metrics": 2}, {"id": "B2", "name": "Кошик", "metrics": 1},
                                      {"id": "B3", "name": "Оплата", "metrics": 0}]
          and cj[0].get("snapshot") == "2026-10-01" and cj[0].get("mark") == "ручна CJM — частково: без джерел, класів і здоров'я",
          cj)
    check("1.17 …its findings: stage_count (4 declared, 3 headings); no product → «продукт не вказано», it stays",
          cj and [f["finding"] for f in cj[0].get("findings", [])] == ["stage_count"] and cj[0].get("product_missing") is True,
          cj and cj[0])
    check("1.18 …only its fields", cj and set(cj[0]) == {"title", "note", "path", "funnel", "stages_declared", "stages", "snapshot",
                                                          "product", "product_missing", "findings", "mark"}, cj and sorted(cj[0]))
    sk = res.get("skipped") or []
    check("1.19 the cjm-research report (type: cjm, no funnel, no stage headings) is skipped and named",
          sk == [{"note": "cjm-report-zorg-2026-10.md", "reason": "not_cjm_map", "detail": "не CJM-карта — немає воронки чи стадій"}], sk)
    check("1.20 another product's note: counted, never listed", res.get("other_products") == 1
          and all("signup" not in json.dumps(x, ensure_ascii=False) for x in maps + cj + sk), res.get("other_products"))
    leaked = [w for w in NEVER if w in out]
    check("1.21 the output never carries a row text, a source, a link, a dashboard, a module, an owner, a mission, a "
          "meeting, a name or a contact of a note", not leaked, leaked)
    check("1.22 the chat table: a header of the portfolio's columns and a row per map, the hand CJM block after",
          "| шлях | власник | етапи | здоров'я | зміна | дата точки | рев'ю | болі | аномалії | розриви | знахідки | опубліковано | увага |" in out
          and out.index("Повернення товару") < out.index("Перше замовлення") < out.index("CJM покупця Zorg"), out[:1500])
    check("1.23 the counts", res.get("counts") == {"maps": 3, "attention": 2, "cjm": 1, "skipped": 1, "other_products": 1},
          res.get("counts"))
    check("1.24 list writes nothing — every note byte for byte", digest(fx) == before)

    # 2. the folders (no context index): the maps' folder and the hand-CJM folder give the same portfolio
    rc, out2, res2 = run("list", "--product", "zorg", "--today", TODAY, "--lang", "uk", "--dir", J, "--dir", H)
    check("2.1 --dir: the same maps, hand CJMs and skipped report; a note of another type in a folder is counted "
          "(ignored), never named", rc == 0 and [m["journey"] for m in res2.get("maps", [])] == names
          and res2.get("cjm") == cj and res2.get("skipped") == sk and res2.get("ignored") == 1, (out2[-600:]))
    rc, out3, res3 = run("list", "--product", "zorg", "--today", TODAY, "--note", index, "--note", notes[0], "--note", notes[0])
    check("2.2 --note of another type: skipped as wrong_type; a note given twice is read once", rc == 0
          and res3.get("skipped") == [{"note": "cjm-index.md", "reason": "wrong_type", "detail": "type: cjm-index"}]
          and len(res3.get("maps", [])) == 1, res3)
    rc, out4, res4 = run("list", "--product", "zorg", "--today", TODAY, "--dir", os.path.join(fx, "journeys", "nope"))
    check("2.3 a folder that does not exist yet: named, an empty portfolio, exit 0", rc == 0 and res4.get("maps") == []
          and res4.get("missing_dirs") == [os.path.join(fx, "journeys", "nope")], res4)
    rc, out5, res5 = run("list", "--product", "zorg", "--today", TODAY, "--note", os.path.join(fx, "nope.md"))
    check("2.4 a note that does not read: skipped as unreadable, exit 0", rc == 0
          and [s["reason"] for s in res5.get("skipped", [])] == ["unreadable"], res5)
    rc, out6, res6 = run("list", "--today", TODAY, "--note", notes[0])
    check("2.5 --product is required: exit 2 and the result line", rc == 2 and res6.get("ok") is False, out6[-300:])
    rc, out7, res7 = run("list", "--product", "zorg", "--today", "20.11.2026", "--note", notes[0])
    check("2.6 a bad --today: exit 2", rc == 2 and res7.get("ok") is False, out7[-300:])

    # 3. variants of the notes in a scratch copy
    v = os.path.join(d, "v")
    os.makedirs(v)
    rep2 = os.path.join(v, "journey-repeat-order.md")
    write(rep2, text(notes[1]).replace(
        "| a-s1-return-browse | s1 | | anomaly | return -> browse: -20.0% від бази — критично | | | | | health-check 2026-11-09, "
        "2026-11-02..2026-11-08 | measured | 2026-11-09 |\n", ""))
    rc, _, r3 = run("list", "--product", "zorg", "--today", TODAY, "--note", notes[0], "--note", rep2)
    check("3.1 a health drop alone raises a map above a fresh one that sorts before it by name",
          [m["journey"] for m in r3.get("maps", [])] == ["Повторне замовлення", "Перше замовлення"]
          and [a["reason"] for a in r3["maps"][0]["attention"]] == ["health_drop"], r3.get("maps"))
    for drop, raised in ((10, False), (11, True)):
        p = os.path.join(v, "journey-drop-%d.md" % drop)
        write(p, text(rep2).replace("score: 78", "score: %d" % (64 + drop)))
        rc, _, r = run("list", "--product", "zorg", "--today", TODAY, "--note", p)
        got = [a["reason"] for a in (r.get("maps") or [{}])[0].get("attention", [])]
        check("3.2 a drop of %d points %s (the health-check escalates a drop of more than 10)" % (drop, "raises" if raised else "does not raise"),
              ("health_drop" in got) == raised, got)
    nof = os.path.join(v, "cjm-no-funnel.md")
    write(nof, text(buyer).replace("funnel: buyer\n", ""))
    noh = os.path.join(v, "cjm-no-headings.md")
    write(noh, re.sub(r"^## (B\d) — ", r"## Етап \1: ", text(buyer), flags=re.M))
    nos = os.path.join(v, "cjm-no-snapshot.md")
    write(nos, text(buyer).replace("snapshot: 2026-10-01\n", "").replace("stages: 4\n", "stages: 3\n")
          .replace('title: "CJM покупця Zorg"', 'name: "CJM продавця Zorg"'))
    other = os.path.join(v, "cjm-other.md")
    write(other, text(buyer).replace("type: cjm\n", "type: cjm\nproduct: quux\n"))
    rc, _, r = run("list", "--product", "zorg", "--today", TODAY, "--note", nof, "--note", noh, "--note", nos, "--note", other)
    check("3.3 a type: cjm without its funnel, or without a stage heading, is no CJM map — skipped and named",
          [(s["note"], s["reason"]) for s in r.get("skipped", [])] == [("cjm-no-funnel.md", "not_cjm_map"), ("cjm-no-headings.md", "not_cjm_map")],
          r.get("skipped"))
    c2 = (r.get("cjm") or [{}])[0]
    check("3.4 `name` when there is no `title`; no snapshot → no_snapshot; declared = headings → no stage_count",
          c2.get("title") == "CJM продавця Zorg" and [f["finding"] for f in c2.get("findings", [])] == ["no_snapshot"]
          and c2.get("snapshot") == "", c2)
    check("3.5 a hand CJM of another product is counted, never listed", r.get("other_products") == 1 and len(r.get("cjm", [])) == 1, r)
    sec = os.path.join(v, "cjm-secret.md")
    write(sec, text(buyer).replace("## B2 — Кошик https://example.com/d/cart", "## B2 — Кошик " + "ghp_" + "Zx9Q" * 9)
          .replace("## B1 — Пошук", "## B1 — Пошук <script>alert(1)</script>"))
    rc, outs, r = run("list", "--product", "zorg", "--today", TODAY, "--note", sec)
    st = [s["name"] for s in (r.get("cjm") or [{}])[0].get("stages", [])]
    check("3.6 a stage name holding a secret is hidden whole", st[1:2] and st[1].startswith("[hidden") and "ghp_" not in outs, st)
    # own review: a folder's plain markdown (no frontmatter) is no note of the portfolio — ignored, never «не читається»;
    # a fenced block never joins two tables into one metric table
    fd = os.path.join(d, "folder")
    os.makedirs(fd)
    write(os.path.join(fd, "README.md"), "# Як ми ведемо CJM\n\nТекст без frontmatter.\n")
    shutil.copy(buyer, os.path.join(fd, "cjm-zorg-buyer.md"))
    rc, _, r = run("list", "--product", "zorg", "--today", TODAY, "--dir", fd)
    check("3.7 a folder's markdown without frontmatter is ignored, never named as unreadable",
          rc == 0 and r.get("skipped") == [] and r.get("ignored") == 1 and len(r.get("cjm", [])) == 1, r)
    fen = os.path.join(v, "cjm-fence.md")
    write(fen, text(buyer).replace("| CTR видачі | Команда пошуку | 12% |\n",
                                   "| CTR видачі | Команда пошуку | 12% |\n```\nкод\n```\n| ще | рядок | x |\n| і ще | рядок | y |\n"))
    rc, _, r = run("list", "--product", "zorg", "--today", TODAY, "--note", fen)
    st = (r.get("cjm") or [{}])[0].get("stages") or [{}]
    check("3.8 a fenced block ends a table: B1 keeps the 2 rows of its own metric table", st[0].get("metrics") == 2, st)
    xs = os.path.join(v, "journey-xss.md")
    write(xs, text(notes[0]).replace('journey: "Перше замовлення"', 'journey: "Перше <script>alert(1)</script> замовлення"'))

    # 4. render-html
    page = os.path.join(d, "portfolio.html")
    pargs = ["render-html", "--product", "zorg", "--today", TODAY, "--out", page, "--lang", "uk"]
    for n in notes + [quux, buyer, report, xs]:
        pargs += ["--note", n]
    rc, outp, rp_ = run(*pargs)
    hraw = text(page) if os.path.exists(page) else ""
    h = html.unescape(hraw)
    check("4.1 render-html: exit 0, the page written, the result names it", rc == 0 and rp_.get("ok") is True and h
          and rp_.get("out") == page and rp_.get("maps") == 4 and rp_.get("cjm") == 1, outp[-600:])
    check("4.2 no link, no request: no http, href, src, url(, fetch, XMLHttpRequest, import",
          not any(w in hraw for w in ("http", "href", "src=", "url(", "fetch(", "XMLHttpRequest", "import(", "<a ", "<link", "<img", "<iframe")),
          [w for w in ("http", "href", "src=", "url(", "fetch(") if w in hraw])
    leaked = [w for w in NEVER if w in h]
    check("4.3 no row text, source, link, owner of a hand CJM, name or contact — numbers only", not leaked, leaked)
    check("4.4 a sparkline per map with a point (each point's date and score)", hraw.count('<svg class="spark"') == 4
          and "<title>2026-11-09: 64</title>" in hraw, hraw.count('<svg class="spark"'))
    check("4.5 light theme; sticky headers; journey_map's fixed pan script — the page's only script",
          "color-scheme:light" in hraw and "position:sticky" in hraw and hraw.count("<script>") == 1
          and "<script>%s</script>" % __import__("journey_map").PAN in hraw, "")
    check("4.6 every text escaped", "<script>alert(1)</script>" not in hraw and "&lt;script&gt;alert(1)&lt;/script&gt;" in hraw, "")
    check("4.7 the hand CJM block with its mark and its metric rows per stage", "ручна CJM — частково: без джерел, класів і здоров'я" in h
          and "CJM покупця Zorg" in h and "Оплата" in h, "")
    check("4.8 the attention reasons, the review «застаріло», the page's date",
          "рев'ю застаріло" in h and "застаріло" in h and "критична аномалія" in h and TODAY in h, "")
    check("4.9 the skipped report counted on the page, another product counted", "не CJM-карта" in h and "Іншого продукту" in h, "")
    check("4.10 the order on the page is the list's", h.index("Повернення товару") < h.index("Повторне замовлення") < h.index("Перше"), "")
    rc, oute, _ = run("render-html", "--product", "zorg", "--today", TODAY, "--note", notes[0], "--out", page, "--lang", "en")
    he = html.unescape(text(page))
    check("4.11 English labels", rc == 0 and "Journey portfolio" in he and "Journey maps" in he and "review" in he, oute[-300:])
    rc, outx, rx = run("render-html", "--product", "zorg", "--note", notes[0], "--out", os.path.join(d, "no-such-dir", "p.html"))
    check("4.12 a page that cannot be written: exit 1", rc == 1 and rx.get("ok") is False, outx[-300:])
    check("4.13 render-html writes nothing but the page — every note byte for byte", digest(fx) == before)
    check("4.14 each map and each hand CJM names its note — the source of its numbers (artifact-publishing.md §9)",
          all('<div class="m">%s</div>' % n in hraw for n in ("journey-first-order.md", "journey-returns.md", "journey-xss.md"))
          and '<span class="m">cjm-zorg-buyer.md</span>' in hraw, "")

    # 5. schema
    rc, outs5, sc = run("schema")
    check("5.1 schema: the commands, columns, attention reasons, hand-CJM fields and findings, skip reasons",
          rc == 0 and sc.get("commands") == ["list", "render-html", "schema"]
          and [c[0] for c in sc.get("columns", [])] == ["journey", "owner", "stages", "health", "delta", "health_date", "reviewed",
                                                       "pains", "anomalies", "gaps", "findings", "published", "attention"]
          and [a[0] for a in sc.get("attention", [])] == ["health_drop", "stale_review", "no_owner", "critical_anomaly", "empty_stage"]
          and sc.get("cjm_fields") == ["title", "funnel", "stages", "stage_headings", "metrics", "snapshot"]
          and sc.get("cjm_findings") == ["stage_count", "no_snapshot"]
          and [s[0] for s in sc.get("skips", [])] == ["not_cjm_map", "other_product", "wrong_type", "unreadable"]
          and sc.get("drop") == 10, outs5[-800:])

    # 6. mutations (ledger): each caught by the assertions above
    def caught(tag, old, new, judge, why):
        m = mutant(d, tag, old, new)
        if m is None:
            check("6.%s mutation site present — %s" % (tag, why), False, "pattern not in the script: %r" % old)
            return
        rc, o, r = run(*args, script=m)
        check("6.%s M: %s — caught" % (tag, why), not judge(r, o), "")

    caught("report", "if not funnel or not stages:", "if False:",
           lambda r, o: [s["reason"] for s in r.get("skipped", [])] == ["not_cjm_map"] and len(r.get("cjm", [])) == 1,
           "a `type: cjm` report taken as a hand CJM")
    caught("drop", 'prev["score"] - last["score"] > DROP', 'prev["score"] - last["score"] > 100',
           lambda r, o: [a["reason"] for a in [m for m in r.get("maps", []) if m["journey"] == "Повторне замовлення"][0]["attention"]]
           == ["health_drop", "critical_anomaly"], "a health drop that does not raise the map")
    caught("link", "s = nt.safe(s)", "s = str(s)",
           lambda r, o: "http" not in o and "example.com" not in o, "a hand CJM's link in the output")
    m = mutant(d, "link2", '"name": plain(m.group(2))', '"name": m.group(2) + " https://example.com/d"')
    if m is None:
        check("6.link2 mutation site present", False, "")
    else:
        rc, o, r = run(*args, script=m)
        check("6.link2 M: a stage heading's link kept — caught by 1.21", "http" in o, "")
    caught("product", "if not _same_product(nt.fm_scalar(fm, \"product\"), product):", "if False:",
           lambda r, o: r.get("other_products") == 1 and "Реєстрація" not in o, "another product's note in the portfolio")
    caught("word", 'if t.endswith("— " + label):', "if label in t:",
           lambda r, o: [m for m in r.get("maps", []) if m["journey"] == "Повторне замовлення"][0]["anomalies"]
           == {"total": 3, "critical": 1, "warning": 0, "positive": 1, "unrated": 1}, "criticality by a word of its own")
    caught("hc", "st = status_of(r[\"text\"]) if jm._is_hc(r) else None", "st = status_of(r[\"text\"])",
           lambda r, o: [m for m in r.get("maps", []) if m["journey"] == "Повторне замовлення"][0]["anomalies"]["critical"] == 1,
           "a hand-written anomaly rated by its own words")

# 8. review 1 (frozen 0af13de): each finding reproduced first
HOSTILE = ("evil.example", "bea@zorg", "token=abc", "+380 50", "Bea Two", "<b>x", "&lt;b&gt;x")
with tempfile.TemporaryDirectory() as d:
    first = os.path.join(FIX, "journeys", "zorg", "journey-first-order.md")
    buyer0 = os.path.join(FIX, "hand", "cjm-zorg-buyer.md")
    hm = os.path.join(d, "journey-hostile.md")
    write(hm, text(first)
          .replace('journey: "Перше замовлення"', 'journey: "Перше замовлення https://evil.example/j bea@zorg.example"')
          .replace('owner: "Команда оформлення Zorg"', 'owner: "Команда https://evil.example/o +380 50 123 45 67"')
          .replace("reviewed: 2026-11-10", 'reviewed: "see https://evil.example/review bea@zorg.example"')
          .replace("  - id: s2\n", '  - id: "https://evil.example/s2"\n')
          .replace("    surface: artifact\n    kind: dashboard\n    level: page\n",
                   '    surface: "https://evil.example/leak?token=abc"\n    kind: "bea@zorg.example"\n    level: "<b>x</b>"\n')
          .replace("| p1 | s1 | | pain | Головна довго вантажиться на мобільному | | | | | feedback-triage 2026-10-30, тема «швидкість», pain 6.0 | reported |",
                   "| p1 | s1 | | pain | Головна довго вантажиться на мобільному | | | | | feedback-triage 2026-10-30, тема «швидкість», pain 6.0 | bea@zorg.example https://evil.example/c |"))
    hb = os.path.join(d, "cjm-hostile.md")
    write(hb, text(buyer0).replace('title: "CJM покупця Zorg"', 'title: "CJM [покупця](https://evil.example/t) bea@zorg.example"')
          .replace("funnel: buyer", "funnel: https://evil.example/f")
          .replace("## B3 — [[Оплата|Оплата]]", "````\n```\n## Z9 — inside nested fence\n```\n````\n<!-- comment\n## C7 — inside comment Bea Two\n-->\n%% ## C8 — inside an Obsidian comment %%\n## B3 — [[Оплата|Оплата]]"))
    rc, out8, r8 = run("list", "--product", "zorg", "--today", TODAY, "--lang", "uk", "--note", hm, "--note", hb)
    page8 = os.path.join(d, "p8.html")
    run("render-html", "--product", "zorg", "--today", TODAY, "--lang", "uk", "--note", hm, "--note", hb, "--out", page8)
    h8 = text(page8) if os.path.exists(page8) else ""
    leak = [w for w in HOSTILE if w in out8 or w in h8]
    check("8.1 I-1/I-2/M-1/M-6 no link, contact or token of a note's class cell, stage id, publication value, review, journey, "
          "owner or a hand CJM's title and funnel reaches the chat, the result or the page", rc == 0 and not leak, leak)
    m8 = (r8.get("maps") or [{}])[0]
    check("8.2 I-1 a class that is no class is counted as «?», never its words", m8.get("pains") == {"observed": 1, "?": 1}, m8.get("pains"))
    check("8.3 I-2 a review that is no date: «застаріло» with an empty date, never its words", m8.get("reviewed") == ""
          and all(a.get("detail") == "" for a in m8.get("attention", []) if a.get("reason") == "stale_review"), m8.get("attention"))
    c8 = (r8.get("cjm") or [{}])[0]
    check("8.4 M-4 a fenced heading (a longer fence around a shorter one) and a commented one are no stages; B3 after them kept",
          [x["id"] for x in c8.get("stages", [])] == ["B1", "B2", "B3"], c8.get("stages"))
    check("8.5 M-1 the first table whose first header cell is «Metric» counts — the module table before it (2 rows) never",
          [x["metrics"] for x in c8.get("stages", [])] == [2, 1, 0], c8.get("stages"))
    sup = os.path.join(d, "cjm-sup.md")
    write(sup, text(buyer0).replace("stages: 4", "stages: ²"))
    rc, outs, rs = run("list", "--product", "zorg", "--today", TODAY, "--note", sup)
    check("8.6 M-3 `stages: ²` is no number: no crash, the result line, no stage_count", rc == 0 and rs.get("ok") is True
          and (rs.get("cjm") or [{}])[0].get("stages_declared") is None, outs[-300:])
    nop = os.path.join(d, "journey-noproduct.md")
    write(nop, text(first).replace("product: zorg\n", ""))
    rc, outn, rn = run("list", "--product", "zorg", "--today", TODAY, "--lang", "uk", "--note", nop)
    pn = os.path.join(d, "pn.html")
    run("render-html", "--product", "zorg", "--today", TODAY, "--lang", "uk", "--note", nop, "--out", pn)
    check("8.7 M-5 a journey map with no product is marked «продукт не вказано» in the chat and on the page",
          "Перше замовлення (продукт не вказано)" in outn and "продукт не вказано" in html.unescape(text(pn)), outn[:600])
    wt = os.path.join(d, "wt.md")
    write(wt, '---\ntype: "Bea bea@zorg.example https://evil.example/t"\nproduct: zorg\n---\n# x\n')
    wq = os.path.join(d, "wq.md")
    write(wq, "---\ntype: meeting\nproduct: quux\n---\n# Quux sync\n")
    rc, outw, rw = run("list", "--product", "zorg", "--today", TODAY, "--note", wt, "--note", wq)
    check("8.8 M-6 a wrong type is named page-safe; another product's note of another type is counted, never named",
          [s_["note"] for s_ in rw.get("skipped", [])] == ["wt.md"] and "evil.example" not in outw and "bea@" not in outw
          and rw.get("other_products") == 1, rw)
    up = os.path.join(os.path.dirname(first), "JOURNEY-FIRST-ORDER.md")
    if os.path.exists(up):                       # a case-insensitive disk (macOS): the same file by two spellings
        rc, _, ru = run("list", "--product", "zorg", "--today", TODAY, "--note", first, "--note", up)
        check("8.9 M-7 the same file by two spellings is read once", len(ru.get("maps", [])) == 1, ru.get("maps"))
    tgt = os.path.join(d, "journey-target.md")
    write(tgt, text(first))
    before8 = text(tgt)
    for out_ in (tgt, os.path.join(d, "x.md")):
        rc, outo, ro = run("render-html", "--product", "zorg", "--note", tgt, "--out", out_)
        check("8.10 M-8 --out that is a note given or any .md is refused (exit 2), the note untouched: %s" % os.path.basename(out_),
              rc == 2 and ro.get("ok") is False and text(tgt) == before8 and not os.path.exists(os.path.join(d, "x.md")), outo[-300:])
    rc, outh, rh = run()
    check("8.11 M-11 no command: exit 2 and the result line", rc == 2 and rh.get("ok") is False, outh[-300:])
    empty = os.path.join(d, "empty.html")
    run("render-html", "--product", "zorg", "--note", buyer0, "--out", empty)
    check("8.12 a page with no map carries no script", os.path.exists(empty) and "<script" not in text(empty), "")
    import journey_portfolio as jp8  # noqa: E402
    real_dl, real_read = jp8.ci.is_dataless, jp8.nt.read_note
    opened = []
    jp8.ci.is_dataless = lambda p_: True
    jp8.nt.read_note = lambda p_: opened.append(p_) or real_read(p_)
    try:
        got8 = jp8.collect([first], [os.path.dirname(first)], "zorg", __import__("datetime").date(2026, 11, 20), None, "uk")
    finally:
        jp8.ci.is_dataless, jp8.nt.read_note = real_dl, real_read
    check("8.13 M-9 a file iCloud has not downloaded is never opened: named as unreadable with the iCloud line",
          not opened and got8["maps"] == [] and got8["skipped"] and all(s_["reason"] == "unreadable" and "iCloud" in s_["detail"]
                                                                        for s_ in got8["skipped"]), (opened, got8["skipped"][:2]))
    check("8.14 M-2 a product is one product: «Quux: App» is not «Zorg: App», «日本» is not «中国», «Zorg App» is «zorg app»",
          jp8._same_product("Zorg: App", "Quux: App") is False and jp8._same_product("日本", "中国") is False
          and jp8._same_product("Zorg App", "zorg app") is True and jp8._same_product("", "zorg") is True, "")

# 7. validate-consistency.sh check 30 — §13 of the protocol and the script agree, and so do the places that name the
# portfolio (the publication key, the surfaces row, the scheduled re-render, `ctx search --type`)
import journey_portfolio as jp  # noqa: E402

cp_ = getattr(jp, "check_protocol", None)
check("7.0 journey_portfolio.check_protocol exists (validate check 30)", callable(cp_))
if callable(cp_):
    errs0 = cp_(ROOT)
    check("7.1 check 30 is clean on the tree", errs0 == [], errs0)
    FILES30 = ("references/journey-protocol.md", "references/artifact-publishing.md", "references/native-surfaces.md",
               "references/context-protocol.md", "skills/cjm-research/references/cjm-reports.md",
               "skills/cjm-research/SKILL.md", "scripts/journey_portfolio.py")
    DRIFTS = [
        ("columns", "references/journey-protocol.md", "| `delta` | `зміна` |", "| `delta` | `різниця` |"),
        ("attention reasons", "references/journey-protocol.md", "| `health_drop` | `здоров'я впало` |", "| `health_fall` | `здоров'я впало` |"),
        ("the drop threshold", "references/journey-protocol.md", "more than 10 points below", "10 points or more below"),
        ("hand-CJM fields", "references/journey-protocol.md", "| `stage_headings` |", "| `headings` |"),
        ("hand-CJM findings", "references/journey-protocol.md", "| `no_snapshot` |", "| `no_snap` |"),
        ("skips", "references/journey-protocol.md", "| `wrong_type` | `не карта шляху й не CJM-нотатка` |", "| `wrong_type` | `інший тип` |"),
        ("commands", "references/journey-protocol.md", "| `schema` | the commands", "| `dump` | the commands"),
        ("the hand-CJM mark", "references/journey-protocol.md", "«ручна CJM — частково: без джерел, класів і здоров'я»", "«ручна CJM»"),
        ("finding the notes", "references/journey-protocol.md", "ctx.py search --type cjm-journey --type cjm", "ctx.py search --q journeys"),
        ("the publication key", "references/artifact-publishing.md", "`cjm-research/<product>/portfolio`", "`cjm-research/<product>/journeys`"),
        ("the surfaces row", "references/native-surfaces.md", "| The journey portfolio (`cjm-research` Step J7", "| The journey list (`cjm-research` Step J9"),
        ("the scheduled re-render", "skills/cjm-research/references/cjm-reports.md", "journey_portfolio.py render-html", "journey_portfolio.py list"),
        ("the ctx row", "references/context-protocol.md", "| `search --type TYPE", "| `search --kind TYPE"),
        ("the skill's step J7", "skills/cjm-research/SKILL.md", "- **J7 ", "- **J9 "),
        ("journey_map imported", "scripts/journey_portfolio.py", "import journey_map as jm", "import note_table as jm"),
        ("no copy of journey_map", "scripts/journey_portfolio.py", "# ------------------------------------------------------------------ a journey map's row",
         "def findings(note, today, newest=None):\n    return []\n\n\n# ------------------------------------------------------------------ a journey map's row"),
    ]
    with tempfile.TemporaryDirectory() as d:
        for name, rel, old, new in DRIFTS:
            r2 = os.path.join(d, re.sub(r"\W+", "-", name))
            for f in FILES30:
                os.makedirs(os.path.dirname(os.path.join(r2, f)), exist_ok=True)
                shutil.copy(os.path.join(ROOT, f), os.path.join(r2, f))
            src = text(os.path.join(r2, rel))
            if old not in src:
                check("7.x drift site present — %s" % name, False, old)
                continue
            write(os.path.join(r2, rel), src.replace(old, new, 1))
            errs = cp_(r2)
            check("7.x check 30 names a drift of %s" % name, errs and any(os.path.basename(rel) in e for e in errs), errs)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)

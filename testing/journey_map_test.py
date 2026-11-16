#!/usr/bin/env python3
"""TC-journey-4700 — scripts/journey_map.py, the journey map (v4.7.0, references/journey-protocol.md).

Fictional «Zorg» notes and health-check snapshots (testing/fixtures/journey/) are copied into a temp folder:
- parse: the stages in the frontmatter's order, the rows by stage and lane, the gap rows, each stage's tree; English
  headers too; a CRLF note; a note without the table or without a required column, and a short row, are named;
- check: the built map raises only its gap (empty_stage, no_outcome on s5); the findings note raises each structural
  finding of the protocol; a row holding a secret is named; findings never make the command fail;
- render-html: one self-contained page (no request, no link), every text escaped, a secret hidden, the stages and
  lanes, each row's source and class, the health sparkline; Ukrainian and English labels;
- health: the trend from the snapshots' frontmatter only — a snapshot without health_score named and skipped, another
  product's ignored — and only the `health` field changes (LF and CRLF), a second run byte-identical;
- refresh: only the health-check rows are replaced by id (the PM's cells kept), a new anomaly after its stage's last
  row, a resolved one removed, a PM row with a health-check id kept and named, every other line byte for byte, the
  health point appended and the page written;
- tree: Mermaid for a stage, the target marked, few_solutions under three solutions, an unknown stage refused;
- schema: check 28's check_protocol is clean on a sound tree and names each drift.
Mutations: a `health` that rewrites another field, a `refresh` that touches another row, and a render without escaping
are each caught by the same assertions. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/journey_map_test.py
"""
import json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "journey_map.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "journey")
TODAY = "2026-11-16"

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


SAFE_HOME = tempfile.mkdtemp(prefix="journey-home-")


def run(*args, script=SCRIPT):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GROW_PM_")}
    env["HOME"] = SAFE_HOME
    p = subprocess.run([sys.executable, script] + list(args), capture_output=True, text=True, env=env)
    res = {}
    for line in p.stdout.splitlines():
        if line.startswith("JOURNEY_RESULT "):
            res = json.loads(line[len("JOURNEY_RESULT "):])
    return p.returncode, p.stdout + p.stderr, res


def read(p):
    with open(p, "rb") as f:
        return f.read()


def write(p, data):
    with open(p, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def text(p):
    return read(p).decode("utf-8")


def mutant(d, name, old, new, target="journey_map.py"):
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
    with open(os.path.join(mdir, target), "w", encoding="utf-8") as f:
        f.write(src.replace(old, new, 1))
    return os.path.join(mdir, "journey_map.py")


def strip_field(t, name):
    """The note without its top-level frontmatter field `name` (its key line and the lines under it)."""
    out, skip = [], False
    for line in t.splitlines(True):
        if re.match(r"^%s\s*:" % re.escape(name), line):
            skip = True
            continue
        if skip and (line.startswith((" ", "\t", "-")) and not line.startswith("---")):
            continue
        skip = False
        out.append(line)
    return "".join(out)


def finding_set(res):
    return {f["finding"] for f in res.get("findings", [])}


def has(res, code, **kw):
    return any(f["finding"] == code and all(f.get(k) == v for k, v in kw.items()) for f in res.get("findings", []))


d = tempfile.mkdtemp(prefix="journey-test-")
try:
    shutil.copytree(FIX, os.path.join(d, "fx"))
    fx = os.path.join(d, "fx")
    note = os.path.join(fx, "journey-first-order.md")
    bad = os.path.join(fx, "journey-findings.md")
    snaps = os.path.join(fx, "health-checks")
    new_snap = os.path.join(fx, "snapshot-2026-11-16.md")

    # 1. parse
    rc, out, res = run("parse", "--note", note)
    check("1.1 parse exits 0 with a JOURNEY_RESULT line", rc == 0 and res.get("ok") is True, out)
    check("1.2 the stages in the frontmatter's order", [s["id"] for s in res.get("stages", [])] == ["s1", "s2", "s3", "s4", "s5"],
          res.get("stages"))
    check("1.3 the stage names and outcomes", (res.get("stages") or [{}])[0].get("name") == "Візит"
          and (res.get("stages") or [{}] * 5)[4].get("outcome") == "⚠️ TBD", res.get("stages"))
    check("1.4 the product, journey, owner and review date", res.get("product") == "zorg" and res.get("journey") == "Перше замовлення"
          and res.get("owner") == "Команда оформлення Zorg" and res.get("reviewed") == "2026-11-02", res)
    check("1.5 the ten lanes in the protocol's order", res.get("lanes") == ["action", "touchpoint", "experience", "pain", "metric",
                                                                           "anomaly", "opportunity", "solution", "initiative", "experiment"],
          res.get("lanes"))
    rows = res.get("rows", [])
    check("1.6 every row with its id, stage, lane, source and class", len(rows) == 19
          and {"id", "stage", "step", "lane", "text", "level", "target", "parent", "code", "source", "class", "date"} <= set(rows[0]),
          (len(rows), rows[:1]))
    grid = res.get("grid", {})
    check("1.7 the grid: rows by stage and lane", grid.get("s3", {}).get("solution") == ["h1", "h2", "h3"]
          and grid.get("s2", {}).get("anomaly") == ["a-s2-search-cart"], grid.get("s3"))
    check("1.8 the gap row of s5", [g["stage"] for g in res.get("gaps", [])] == ["s5"], res.get("gaps"))
    tr = res.get("trees", {}).get("s3", {})
    check("1.9 the tree of s3: the target with its solutions and tests", tr.get("target") == "o2"
          and [o["id"] for o in tr.get("opportunities", [])] == ["o2"]
          and sorted(s["id"] for s in tr["opportunities"][0].get("solutions", [])) == ["h1", "h2", "h3"], tr)
    check("1.10 no structural errors on the built note", res.get("errors") == [], res.get("errors"))

    en = os.path.join(fx, "journey-en.md")
    write(en, text(note).replace("| id | етап | крок | доріжка | текст | рівень | ціль | parent | код | джерело | клас | дата |",
                                 "| id | stage | step | lane | text | level | target | parent | code | source | class | date |"))
    rc, out, res = run("parse", "--note", en)
    check("1.11 English headers parse the same", rc == 0 and len(res.get("rows", [])) == 19, out)
    crlf = os.path.join(fx, "journey-crlf.md")
    write(crlf, text(note).replace("\n", "\r\n"))
    rc, out, res = run("parse", "--note", crlf)
    check("1.12 a CRLF note parses the same", rc == 0 and len(res.get("rows", [])) == 19 and res.get("errors") == [], out)
    nt_ = os.path.join(fx, "journey-notable.md")
    write(nt_, re.sub(r"## Карта.*?(?=## Здоров)", "", text(note), flags=re.S))
    rc, out, res = run("parse", "--note", nt_)
    check("1.13 a note without the table is named (exit 2), never a crash", rc == 2 and res.get("ok") is False and "table" in res.get("error", ""), out)
    nc = os.path.join(fx, "journey-nocol.md")
    write(nc, text(note).replace("| доріжка |", "| смуга |", 1))
    rc, out, res = run("parse", "--note", nc)
    check("1.14 a table without the lane column is refused (exit 2)", rc == 2 and "lane" in res.get("error", ""), out)
    sr = os.path.join(fx, "journey-short.md")
    write(sr, text(note).replace("| t1 | s1 | | touchpoint | Головна сторінка, мобільний веб | | | | | walkthrough 2026-10-12, крок 1 | observed | 2026-10-12 |",
                                 "| t1 | s1 | | touchpoint | Головна сторінка, мобільний веб |"))
    rc, out, res = run("parse", "--note", sr)
    check("1.15 a short row is padded and named", rc == 0 and any("t1" in e and "padded" in e for e in res.get("errors", [])), res.get("errors"))
    nofm = os.path.join(fx, "journey-nofm.md")
    write(nofm, "# no frontmatter\n")
    rc, out, res = run("parse", "--note", nofm)
    check("1.16 a note without frontmatter is refused (exit 2)", rc == 2 and res.get("ok") is False, out)

    # 2. check
    rc, out, res = run("check", "--note", note, "--snapshots", snaps, "--today", TODAY)
    check("2.1 the built map: only its gap — empty_stage and no_outcome on s5", rc == 0 and finding_set(res) == {"empty_stage", "no_outcome"}
          and has(res, "empty_stage", stage="s5") and has(res, "no_outcome", stage="s5"), res.get("findings"))
    rc, out, res = run("check", "--note", bad, "--today", TODAY)
    check("2.2 findings never fail the command", rc == 0 and res.get("ok") is True, out)
    expect = [("no_owner", {}), ("stale_review", {}), ("no_outcome", {"stage": "s2"}), ("empty_stage", {"stage": "s4"}),
              ("undeclared_stage", {"row": "g1"}), ("unknown_lane", {"row": "g1"}), ("no_source", {"row": "p3"}),
              ("no_class", {"row": "p4"}), ("wrong_class", {"row": "m1"}), ("simulated_pain", {"row": "p2"}),
              ("bad_level", {"row": "a1"}), ("bad_level", {"row": "m1"}), ("bad_target", {"row": "h2"}),
              ("bad_target", {"row": "o2"}), ("bad_date", {"row": "m2"}), ("bad_code", {"row": "i1"}),
              ("orphan", {"row": "h3"}), ("orphan", {"row": "x1"}), ("orphan", {"row": "h4"}),
              ("pain_no_action", {"row": "p1"}), ("few_solutions", {"row": "o1"}), ("stale_metric", {"row": "m3"}),
              ("duplicate_id", {"row": "p5"}), ("link", {"row": "k1"})]
    for i, (code, kw) in enumerate(expect, 3):
        check("2.%d %s %s" % (i, code, kw or ""), has(res, code, **kw), [f for f in res.get("findings", []) if f["finding"] == code])
    check("2.27 a bad date and a word that is not a class on the first p5", has(res, "bad_date", row="p5") and has(res, "wrong_class", row="p5"),
          res.get("findings"))
    check("2.28 a recent pain is not pain_no_action", not has(res, "pain_no_action", row="p3") and not has(res, "pain_no_action", row="p4"),
          res.get("findings"))
    check("2.29 the simulated pain is not also wrong_class", not has(res, "wrong_class", row="p2"), res.get("findings"))
    check("2.35 a PM metric from another source is never stale_metric — no snapshot refreshes it", not has(res, "stale_metric", row="m1"),
          res.get("findings"))
    check("2.30 the model's findings are never the script's", not ({"opportunity_no_story", "two_pains"} & finding_set(res)), finding_set(res))
    sec = os.path.join(fx, "journey-secret.md")
    write(sec, text(note).replace("Головна сторінка, мобільний веб", "Головна сторінка, токен " + "glpat-" + "Qw8" * 7))
    rc, out, res = run("check", "--note", sec, "--today", TODAY)
    check("2.31 a row holding a secret is named", has(res, "secret", row="t1"), res.get("findings"))
    acted = os.path.join(fx, "journey-acted.md")
    write(acted, text(bad).replace("| p1 | s1 | | pain | Не пам'ятає, що замовляв минулого разу | | | | |",
                                   "| p1 | s1 | | pain | Не пам'ятає, що замовляв минулого разу | | | o9 | |")
          + "| x9 | s1 | | solution | Історія замовлень на головній | | | o9 | | зі слів PM | | |\n"
          + "| x10 | s1 | | experiment | A/B історії на головній | | | x9 | exp-home-history-20261105 | experiment-tracker registry | | |\n")
    rc, out, res = run("check", "--note", acted, "--today", TODAY)
    check("2.32 a pain whose chain reaches an experiment is acted on", not has(res, "pain_no_action", row="p1"), res.get("findings"))
    rc, out, res = run("check", "--note", note, "--snapshots", snaps, "--today", "2027-05-20")
    check("2.33 a review older than 90 days is stale_review; a pain older than 182 days with no action is named",
          has(res, "stale_review") and has(res, "pain_no_action", row="p1") and not has(res, "pain_no_action", row="p2"), res.get("findings"))
    rc, out, res = run("check", "--note", note, "--today", "16.11.2026")
    check("2.34 a --today that is not a date is refused (exit 2)", rc == 2, out)

    # 3. render-html
    page = os.path.join(fx, "first-order.html")
    rc, out, res = run("render-html", "--note", note, "--out", page, "--lang", "uk")
    h = text(page) if os.path.exists(page) else ""
    check("3.1 render-html writes one page", rc == 0 and res.get("ok") is True and h.startswith("<!doctype html>"), out)
    check("3.2 self-contained: no request, no link", "http" not in h and "<script" not in h and "<link" not in h
          and "src=" not in h and "@import" not in h, re.findall(r"http\S{0,40}|<script|<link|src=", h)[:5])
    check("3.3 the stages and their outcomes", all(s in h for s in ("Візит", "Пошук", "Кошик", "Оформлення", "Оплата", "search -&gt; cart &gt;= 35%")), "")
    check("3.4 the lanes in Ukrainian", all(s in h for s in ("дії", "болі", "метрики", "можливості", "рішення", "експерименти")), "")
    check("3.5 each row's source and class", "walkthrough 2026-10-12, крок 4" in h and "observed" in h and "measured" in h, "")
    check("3.6 the note's name, owner and review date", "journey-first-order.md" in h and "Команда оформлення Zorg" in h and "2026-11-02" in h, "")
    check("3.7 a stage without evidence shows its gap", "немає доказів" in h, "")
    check("3.8 no trend yet: the page says so", "health_score" in h or "тренду" in h.lower(), "")
    xss = os.path.join(fx, "journey-xss.md")
    write(xss, text(note).replace("Багато зусиль, щоб звузити видачу", "<script>alert(1)</script> & \"лапки\"")
          .replace("Головна сторінка, мобільний веб", "Головна, деталі https://user:pw@zorg.example.com/x?token=abc, токен " + "glpat-" + "Zx9" * 7))
    page2 = os.path.join(fx, "xss.html")
    run("render-html", "--note", xss, "--out", page2)
    h2 = text(page2) if os.path.exists(page2) else "<script>alert(1)</script>"
    check("3.9 row text is escaped", "<script>alert(1)</script>" not in h2 and "&lt;script&gt;" in h2, "")
    check("3.10 a link never reaches the page; a secret is hidden", "zorg.example.com" not in h2 and "http" not in h2 and "glpat-" not in h2, "")
    check("3.11 English labels by default", "Journey map" in h2 and "lanes" in h2.lower() or "Pains" in h2, "")
    m = mutant(d, "escape", "esc, shown = nt.esc, nt.shown", "esc, shown = str, lambda s: str(s)")
    if m is None:
        check("3.12 M3 the escaping mutation applies", False, "pattern not in the script")
    else:
        page3 = os.path.join(fx, "xss-m.html")
        run("render-html", "--note", xss, "--out", page3, script=m)
        h3 = text(page3) if os.path.exists(page3) else ""
        check("3.12 M3 a render without escaping is caught", "<script>alert(1)</script>" in h3, "")
    rc, out, res = run("render-html", "--note", note, "--out", os.path.join(fx, "no-such-dir", "x.html"))
    check("3.13 a page that cannot be written: exit 1", rc == 1 and res.get("ok") is False, out)

    # 4. health
    before = text(note)
    rc, out, res = run("health", "--note", note, "--snapshots", snaps)
    after = text(note)
    pts = res.get("points", [])
    check("4.1 health exits 0", rc == 0 and res.get("ok") is True, out)
    check("4.2 the trend from three scored snapshots, oldest first", [(p["date"], p["score"]) for p in pts]
          == [("2026-09-07", 68), ("2026-10-05", 74), ("2026-11-02", 71)], pts)
    check("4.3 the snapshot without health_score is named and skipped", [s.get("snapshot") for s in res.get("skipped", [])] == ["2026-08-10.md"],
          res.get("skipped"))
    check("4.4 another product's snapshot is ignored", all("acme" not in p.get("snapshot", "") for p in pts)
          and all("acme" not in s.get("snapshot", "") for s in res.get("skipped", [])), res)
    check("4.5 only the `health` field changed", strip_field(before, "health") == strip_field(after, "health") and before != after,
          "the note changed outside its health field")
    check("4.6 the field holds the points", 'score: 74' in after and 'snapshot: "2026-11-02.md"' in after, after[:900])
    rc, out, res = run("parse", "--note", note)
    check("4.7 parse reads the health points back", [(p["date"], p["score"]) for p in res.get("health", [])]
          == [("2026-09-07", 68), ("2026-10-05", 74), ("2026-11-02", 71)], res.get("health"))
    run("health", "--note", note, "--snapshots", snaps)
    check("4.8 a second run is byte-identical", text(note) == after, "")
    crlf2 = os.path.join(fx, "journey-crlf2.md")
    write(crlf2, before.replace("\n", "\r\n"))
    run("health", "--note", crlf2, "--snapshots", snaps)
    c2 = read(crlf2).decode("utf-8")
    check("4.9 a CRLF note keeps CRLF and every other byte", strip_field(c2.replace("\r\n", "\n"), "health") == strip_field(before, "health")
          and "\r\n" in c2 and "\n" not in c2.replace("\r\n", ""), "")
    page4 = os.path.join(fx, "health.html")
    run("render-html", "--note", note, "--out", page4, "--lang", "uk")
    h4 = text(page4) if os.path.exists(page4) else ""
    check("4.10 the page carries the sparkline with the three points", "<svg" in h4 and "<polyline" in h4 and "71" in h4, "")
    m = mutant(d, "health", "pub.write_field(path, note[\"text\"], False, \"health\"",
               "pub.write_field(path, note[\"text\"].replace(\"reviewed: 2026-11-02\", \"reviewed: 2026-11-03\"), False, \"health\"")
    if m is None:
        check("4.11 M1 the health mutation applies", False, "pattern not in the script")
    else:
        mn = os.path.join(fx, "journey-m1.md")
        write(mn, before)
        run("health", "--note", mn, "--snapshots", snaps, script=m)
        check("4.11 M1 a health that rewrites another field is caught", strip_field(text(mn), "health") != strip_field(before, "health"), "")
    rc, out, res = run("health", "--note", note, "--snapshots", os.path.join(fx, "no-such"))
    check("4.12 a snapshots folder that does not exist is refused (exit 2)", rc == 2, out)

    # 5. refresh
    rn = os.path.join(fx, "journey-refresh.md")
    write(rn, before)
    html5 = os.path.join(fx, "journey-refresh.html")
    rc, out, res = run("refresh", "--note", rn, "--snapshot", new_snap, "--lang", "uk")
    r5 = text(rn)
    check("5.1 refresh exits 0", rc == 0 and res.get("ok") is True, out)
    check("5.2 the health-check rows replaced by id", sorted(res.get("replaced", [])) == sorted(
        ["m-s1-visit-search", "m-s2-search-cart", "m-s3-cart-checkout", "m-s4-checkout-payment", "a-s2-search-cart"]), res.get("replaced"))
    check("5.3 the new anomaly of s3 added", res.get("added") == ["a-s3-cart-checkout"], res.get("added"))
    check("5.4 the new values in the note", "search -> cart: 29.0% (база 35.0%, -17.1%)" in r5
          and "cart -> checkout: -26.0% від бази — критично" in r5 and "health-check 2026-11-16, 2026-11-09..2026-11-15" in r5, "")
    check("5.5 the PM's level on a replaced row kept", re.search(r"^\| m-s2-search-cart \| s2 \| \| metric \| [^|]+ \| transition \|", r5, re.M) is not None, "")
    bl = [l for l in before.split("\n") if l.startswith("| ") and not re.match(r"^\| (m-|a-)", l)]
    al = [l for l in r5.split("\n") if l.startswith("| ") and not re.match(r"^\| (m-|a-)", l)]
    check("5.6 every other row byte for byte, in order", bl == al, [x for x in bl if x not in al][:3])
    lines = r5.split("\n")
    ia = next((i for i, l in enumerate(lines) if l.startswith("| a-s3-cart-checkout |")), -1)
    check("5.7 the new row after its stage's last row", ia > 0 and lines[ia - 1].startswith("| m-s3-cart-checkout |")
          and lines[ia + 1].startswith("| e2 |"), lines[ia - 1:ia + 2] if ia > 0 else "no row")
    body_b = before.split("## Карта")[1].split("| id |")[0] + before.split("## Здоров'я")[1]
    body_a = r5.split("## Карта")[1].split("| id |")[0] + r5.split("## Здоров'я")[1]
    check("5.8 the sections around the table byte for byte", body_b == body_a, "")
    check("5.9 the health point appended", (res.get("health") or {}).get("score") == 64 and 'snapshot: "snapshot-2026-11-16.md"' in r5, res.get("health"))
    check("5.10 the page rendered next to the note", res.get("out") == html5 and os.path.exists(html5), res.get("out"))
    check("5.11 the summary line says local, not published", "локально" in res.get("line", "") and res.get("published") is False, res)
    rc, out, res = run("parse", "--note", rn)
    check("5.12 the refreshed note parses clean", rc == 0 and res.get("errors") == [] and len(res.get("rows", [])) == 20, (res.get("errors"), len(res.get("rows", []))))
    same = os.path.join(fx, "journey-same.md")
    write(same, before)
    rc, out, res = run("refresh", "--note", same, "--snapshot", os.path.join(snaps, "2026-11-02.md"), "--lang", "uk")
    check("5.13 a refresh from the snapshot the rows came from changes no row", strip_field(text(same), "health") == strip_field(before, "health")
          and res.get("added") == [] and res.get("removed") == [], (res.get("added"), res.get("removed")))
    res_snap = os.path.join(fx, "snapshot-resolved.md")
    write(res_snap, text(new_snap).replace("status: warning", "status: info"))
    rs = os.path.join(fx, "journey-resolved.md")
    write(rs, before)
    rc, out, res = run("refresh", "--note", rs, "--snapshot", res_snap)
    check("5.14 an anomaly the new snapshot no longer has is removed", res.get("removed") == ["a-s2-search-cart"] and "| a-s2-search-cart |" not in text(rs), res.get("removed"))
    pm = os.path.join(fx, "journey-pm.md")
    write(pm, before.replace("| transition | | | | health-check 2026-11-02, 2026-10-26..2026-11-01 | measured | 2026-11-02 |\n| e2 |",
                             "| transition | | | | дашборд PM, тиждень 45 | measured | 2026-11-02 |\n| e2 |", 1))
    pml = [l for l in text(pm).split("\n") if l.startswith("| m-s3-cart-checkout |")]
    rc, out, res = run("refresh", "--note", pm, "--snapshot", new_snap)
    check("5.15 a PM row with a health-check id but another source is kept and named", res.get("kept") == ["m-s3-cart-checkout"]
          and [l for l in text(pm).split("\n") if l.startswith("| m-s3-cart-checkout |")] == pml, (res.get("kept"), pml))
    m = mutant(d, "refresh", 'r["source"].startswith(HC_SOURCE)', "True")
    if m is None:
        check("5.16 M2 the refresh mutation applies", False, "pattern not in the script")
    else:
        mp = os.path.join(fx, "journey-m2.md")
        write(mp, text(pm).replace("| m-s3-cart-checkout |", "| m-s3-cart-checkout |"))
        run("refresh", "--note", mp, "--snapshot", new_snap, script=m)
        check("5.16 M2 a refresh that touches another row is caught",
              [l for l in text(mp).split("\n") if l.startswith("| m-s3-cart-checkout |")] != pml, "")
    other = os.path.join(fx, "snapshot-acme.md")
    write(other, text(new_snap).replace("product: zorg", "product: acme"))
    ro = os.path.join(fx, "journey-other.md")
    write(ro, before)
    rc, out, res = run("refresh", "--note", ro, "--snapshot", other)
    check("5.17 a snapshot of another product is refused, the note untouched", rc == 2 and text(ro) == before, out)
    noscore = os.path.join(fx, "snapshot-noscore.md")
    write(noscore, re.sub(r"^health_score: .*\n", "", text(new_snap), flags=re.M))
    rn2 = os.path.join(fx, "journey-noscore.md")
    write(rn2, before)
    rc, out, res = run("refresh", "--note", rn2, "--snapshot", noscore)
    check("5.18 a snapshot without health_score refreshes the rows and names the missing score",
          rc == 0 and res.get("health") is None and res.get("skipped") and "health:\n  - " not in text(rn2), (res.get("health"), res.get("skipped")))

    extra = os.path.join(fx, "snapshot-extra.md")
    write(extra, text(new_snap).replace("stages:\n", "stages:\n  - id: s6\n    metric: \"order -> repeat\"\n    value: \"12.0%\"\n    baseline: \"15.0%\"\n    deviation: \"-20.0%\"\n    status: warning\n", 1))
    rx = os.path.join(fx, "journey-extra.md")
    write(rx, before)
    rc, out, res = run("refresh", "--note", rx, "--snapshot", extra)
    check("5.19 a snapshot stage the note does not declare gets no row and is named", rc == 0 and res.get("skipped_stages") == ["s6"]
          and "| m-s6-" not in text(rx) and "| a-s6-" not in text(rx), (res.get("skipped_stages"), res.get("added")))

    # 6. tree
    rc, out, res = run("tree", "--stage", "s3", "--note", note)
    mm = res.get("mermaid", "")
    check("6.1 tree prints Mermaid", rc == 0 and mm.startswith("flowchart TD"), out)
    check("6.2 the outcome, the target and its solutions and tests", all(s in mm for s in ("cart -> checkout >= 55%", "o2", "h1", "h2", "h3", "x1"))
          and res.get("target") == "o2" and res.get("solutions") == 3, mm)
    check("6.3 three solutions: no few_solutions", res.get("findings") == [], res.get("findings"))
    check("6.4 the initiative hangs under its pain", "p2" in mm and "i1" in mm, mm)
    rc, out, res = run("tree", "--stage", "s3", "--note", bad)
    check("6.5 two solutions on the target: few_solutions", any(f["finding"] == "few_solutions" and f.get("row") == "o1" for f in res.get("findings", [])),
          res.get("findings"))
    rc, out, res = run("tree", "--stage", "s7", "--note", note)
    check("6.6 an unknown stage is refused (exit 2)", rc == 2 and res.get("ok") is False, out)
    qt = os.path.join(fx, "journey-quote.md")
    write(qt, text(note).replace("Калькулятор доставки в кошику", 'Калькулятор "доставки" [у кошику]'))
    rc, out, res = run("tree", "--stage", "s3", "--note", qt)
    check("6.7 a quote or a bracket cannot break the Mermaid text", '"доставки"' not in res.get("mermaid", "") and "#quot;" in res.get("mermaid", ""),
          res.get("mermaid", "")[:300])

    # 8. review 1 (frozen 371e81f)
    # I-1 a row the protocol bans never reaches the page and never hides a stage's gap
    i1 = os.path.join(fx, "journey-i1.md")
    write(i1, text(note).replace("| g1 | s5 | | pain | ⚠️ немає доказів | | | | | | | |",
                                 "| g1 | s5 | | pain | Персона: «хочу оплату частинами» | | | | | persona interview | simulated | 2026-10-20 |\n"
                                 "| m9 | s5 | | metric | payment success 91% | transition | | | | | | 2026-11-02 |"))
    rc, out, res = run("check", "--note", i1, "--today", TODAY)
    check("8.1 I-1 a stage with only a simulated pain and an unsourced metric is still empty_stage", has(res, "empty_stage", stage="s5"), res.get("findings"))
    pi1 = os.path.join(fx, "i1.html")
    rc, out, res = run("render-html", "--note", i1, "--out", pi1, "--lang", "uk")
    hi1 = text(pi1) if os.path.exists(pi1) else ""
    check("8.2 I-1 the simulated pain and the unsourced number are not on the page; the gap is", "хочу оплату частинами" not in hi1
          and "payment success 91%" not in hi1 and "немає доказів" in hi1 and res.get("not_shown") == 2, (res.get("not_shown"), "gap" in hi1))
    # I-2 refresh never removes a PM's anomaly row, whatever its source says
    i2 = os.path.join(fx, "journey-i2.md")
    pm_row = "| an-outage | s3 | Оплата | anomaly | Сплеск відмов 14.10 — збій шлюзу, відомо | | | | | health-check 2026-10-19, 2026-10-12..2026-10-18 | measured | 2026-10-19 |"
    write(i2, before.replace("| e2 | s4 |", pm_row + "\n| e2 | s4 |", 1))
    rc, out, res = run("refresh", "--note", i2, "--snapshot", new_snap, "--lang", "uk")
    check("8.3 I-2 a PM anomaly row with a health-check source is kept", "an-outage" not in res.get("removed", []) and pm_row in text(i2), res.get("removed"))
    # I-3 refresh keeps a column the protocol does not know
    i3 = os.path.join(fx, "journey-i3.md")
    t3 = before.replace("| id | етап | крок | доріжка | текст | рівень | ціль | parent | код | джерело | клас | дата |",
                        "| id | етап | крок | доріжка | текст | рівень | ціль | parent | код | джерело | клас | дата | нотатка |")
    t3 = t3.replace("|---|---|---|---|---|---|---|---|---|---|---|---|", "|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    t3 = re.sub(r"^(\| [^\n]*\|)$", lambda m: m.group(1) + (" перевірити з аналітиком |" if m.group(1).startswith("| m-s2-search-cart ") else " |")
                if m.group(1).startswith("| ") and not m.group(1).startswith("| id ") else m.group(1), t3, flags=re.M)
    write(i3, t3)
    rc, out, res = run("refresh", "--note", i3, "--snapshot", new_snap, "--lang", "uk")
    l3 = [l for l in text(i3).split("\n") if l.startswith("| m-s2-search-cart |")]
    check("8.4 I-3 a PM's extra column on a replaced row is kept", l3 and l3[0].rstrip().endswith("| перевірити з аналітиком |") and "29.0%" in l3[0], l3)
    rc, out, res = run("parse", "--note", i3)
    check("8.5 I-3 the refreshed note with an extra column parses clean", res.get("errors") == [], res.get("errors"))
    # I-4 health never erases the trend the note keeps
    i4 = os.path.join(fx, "journey-i4.md")
    write(i4, text(bad))
    empty = os.path.join(fx, "empty-snapshots")
    os.makedirs(empty)
    rc, out, res = run("health", "--note", i4, "--snapshots", empty)
    rc, out, res = run("parse", "--note", i4)
    check("8.6 I-4 an empty snapshots folder keeps the note's points", [p["snapshot"] for p in res.get("health", [])] == ["2026-10-05.md", "2026-11-02.md"], res.get("health"))
    rc, out, res = run("health", "--note", i4, "--snapshots", snaps)
    rc, out, res = run("parse", "--note", i4)
    check("8.7 I-4 the folder's points join the note's", [p["snapshot"] for p in res.get("health", [])] == ["2026-09-07.md", "2026-10-05.md", "2026-11-02.md"], res.get("health"))
    # I-5 a person's contact never on the map or the page
    i5 = os.path.join(fx, "journey-i5.md")
    write(i5, text(note).replace('owner: "Команда оформлення Zorg"', 'owner: "ivan.petrenko@zorg.example"')
          .replace("Головна сторінка, мобільний веб", "Головна сторінка, дзвінок +380 67 123 45 67"))
    rc, out, res = run("check", "--note", i5, "--today", TODAY)
    check("8.8 I-5 an e-mail as the owner and a phone in a row are `contact`", has(res, "contact") and has(res, "contact", row="t1")
          and any(f["finding"] == "contact" and "row" not in f for f in res.get("findings", [])), [f for f in res.get("findings", []) if f["finding"] == "contact"])
    pi5 = os.path.join(fx, "i5.html")
    run("render-html", "--note", i5, "--out", pi5)
    hi5 = text(pi5) if os.path.exists(pi5) else "@"
    check("8.9 I-5 no e-mail and no phone on the page", "ivan.petrenko" not in hi5 and "123 45 67" not in hi5, "")
    # I-6 every file in the folder that is not a usable snapshot of the product is named
    i6 = os.path.join(fx, "snapshots-i6")
    shutil.copytree(snaps, i6)
    write(os.path.join(i6, "2026-07-06.md"), "# Zorg — health-check 2026-07-06\n\nFunnel Health Score: 66 / 100\n")
    write(os.path.join(i6, "2026-07-20.md"), "---\nhealth_score: 69\ndate: 2026-07-20\n---\n\nbody\n")
    i6n = os.path.join(fx, "journey-i6.md")
    write(i6n, before)
    rc, out, res = run("health", "--note", i6n, "--snapshots", i6)
    sk = {s["snapshot"]: s["why"] for s in res.get("skipped", [])}
    check("8.10 I-6 a snapshot without frontmatter and one without type and product are named", "2026-07-06.md" in sk and "2026-07-20.md" in sk
          and "2026-08-10.md" in sk and "acme-2026-10-05.md" not in sk, sk)
    # m-1 is session_start_test 4700.14–4700.15; m-2 anomaly ids by metric
    two = os.path.join(fx, "snapshot-two.md")
    write(two, text(new_snap).replace("  - id: s3\n", "  - id: s2\n    metric: \"search -> filters\"\n    value: \"20.0%\"\n    baseline: \"25.0%\"\n    deviation: \"-20.0%\"\n    status: warning\n  - id: s3\n", 1))
    i7 = os.path.join(fx, "journey-i7.md")
    write(i7, before)
    run("refresh", "--note", i7, "--snapshot", two, "--lang", "uk")
    t7 = text(i7).replace("| a-s2-search-filters | s2 | |", "| a-s2-search-filters | s2 | Фільтри |")
    write(i7, t7)
    nxt = os.path.join(fx, "snapshot-next.md")
    write(nxt, text(two).replace("date: 2026-11-16", "date: 2026-11-23").replace("status: warning\n  - id: s2", "status: info\n  - id: s2", 1))
    rc, out, res = run("refresh", "--note", i7, "--snapshot", nxt, "--lang", "uk")
    check("8.11 m-2 an anomaly keeps its id (and the PM's step) when another one on the stage resolves",
          "a-s2-search-cart" in res.get("removed", []) and any(l.startswith("| a-s2-search-filters | s2 | Фільтри |") for l in text(i7).split("\n")), (res.get("removed"), res.get("replaced")))
    # m-3 the note's language when --lang is not given
    i8 = os.path.join(fx, "journey-i8.md")
    write(i8, before)
    rc, out, res = run("refresh", "--note", i8, "--snapshot", new_snap)
    check("8.12 m-3 a Ukrainian note is refreshed in Ukrainian without --lang", "(база 35.0%, -17.1%)" in text(i8) and "локально" in res.get("line", ""), res.get("line"))
    # m-5 a new health-check metric is a transition
    check("8.13 m-5 a new metric row from the snapshot is `transition`", any(l.startswith("| m-s2-search-filters | s2 | | metric |") and "| transition |" in l for l in text(i7).split("\n")), "")
    # m-7 a row without an id is named, never a duplicate_id of ""
    i9 = os.path.join(fx, "journey-i9.md")
    write(i9, text(note).replace("| t1 | s1 |", "|  | s1 |").replace("| e2 | s4 |", "|  | s4 |"))
    rc, out, res = run("check", "--note", i9, "--today", TODAY)
    check("8.14 m-7 rows without an id are named, not duplicate_id", any("without an id" in e for e in res.get("errors", []))
          and not has(res, "duplicate_id"), (res.get("errors"), res.get("findings")))
    # m-8 a snapshot entry without its metric is named
    nom = os.path.join(fx, "snapshot-nometric.md")
    write(nom, text(new_snap).replace('    metric: "cart -> checkout"\n', "", 1))
    i10 = os.path.join(fx, "journey-i10.md")
    write(i10, before)
    rc, out, res = run("refresh", "--note", i10, "--snapshot", nom)
    check("8.15 m-8 a snapshot entry without its metric is named", any(e.get("stage") == "s3" for e in res.get("skipped_entries", [])), res.get("skipped_entries"))
    # m-9 an older snapshot never rolls the rows back
    old = os.path.join(fx, "snapshot-old.md")
    write(old, text(new_snap).replace("date: 2026-11-16", "date: 2026-10-01"))
    i11 = os.path.join(fx, "journey-i11.md")
    write(i11, before)
    rc, out, res = run("refresh", "--note", i11, "--snapshot", old)
    check("8.16 m-9 a snapshot older than the map's health-check rows is refused, the note untouched", rc == 2 and text(i11) == before, out)
    # m-12 the Ukrainian lane names of §2 are the lanes
    i12 = os.path.join(fx, "journey-i12.md")
    write(i12, text(note).replace("| p1 | s2 | Фільтри | pain |", "| p1 | s2 | Фільтри | болі |").replace("| t1 | s1 | | touchpoint |", "| t1 | s1 | | точки контакту |"))
    rc, out, res = run("parse", "--note", i12)
    g12 = res.get("grid", {})
    check("8.17 m-12 «болі» and «точки контакту» are the pain and touchpoint lanes", "p1" in g12.get("s2", {}).get("pain", [])
          and "t1" in g12.get("s1", {}).get("touchpoint", []), (g12.get("s2", {}).get("pain"), g12.get("s1", {}).get("touchpoint")))
    # m-16 a health point on the page names its snapshot
    check("8.18 m-16 the page names each point's snapshot", "2026-11-02.md" in h4, "")
    # m-17 a wrong argument still ends with a JOURNEY_RESULT line
    rc, out, res = run("tree", "--note", note)
    check("8.19 m-17 a missing argument: exit 2 with a JOURNEY_RESULT line", rc == 2 and res.get("ok") is False, out[-300:])

    # 7. schema — check 28
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    try:
        import journey_map as jm  # noqa: E402
    except ImportError as e:
        jm = None
        check("7.0 journey_map imports", False, e)
    if jm is not None:
        r2 = os.path.join(d, "root")
        for rel in ("references/journey-protocol.md", "references/vault-schema.md", "references/artifact-publishing.md",
                    "skills/cjm-research/SKILL.md", "references/vault-protocol.md", "skills/cjm-research/references/cjm-reports.md"):
            os.makedirs(os.path.dirname(os.path.join(r2, rel)), exist_ok=True)
            shutil.copy(os.path.join(ROOT, rel), os.path.join(r2, rel))
        sk = os.path.join(r2, "skills", "cjm-research", "SKILL.md")
        skt = text(sk)
        if "journey-protocol.md" not in skt:                       # before task 5 the skill does not cite it yet
            write(sk, skt + "\n`references/journey-protocol.md`\n")
        errs = jm.check_protocol(r2)
        check("7.1 check_protocol is clean on a sound tree", errs == [], errs)
        rc, out, res = run("schema")
        check("7.2 schema prints the fields, columns, lanes, levels, findings and commands",
              rc == 0 and res.get("fields") == list(jm.FIELDS) and len(res.get("columns", [])) == 12
              and [l[0] for l in res.get("lanes", [])] == res.get("lanes_order") and res.get("levels") == ["stage", "transition", "journey"]
              and res.get("findings") == list(jm.FINDINGS) and "refresh" in res.get("commands", []), out)

        def drift(rel, old, new, expect, name, count=1):
            p = os.path.join(r2, rel)
            t0 = text(p)
            if old not in t0:
                check(name, False, "pattern not in %s" % rel)
                return
            write(p, t0.replace(old, new, count))
            e = jm.check_protocol(r2)
            write(p, t0)
            check(name, any(expect in x for x in e), e)

        drift("references/journey-protocol.md", "| `health` | written only", "| `trend` | written only", "health", "7.3 a frontmatter field the protocol renames is named")
        drift("references/journey-protocol.md", "| `source` | `джерело` |", "| `source` | `звідки` |", "джерело", "7.4 a Ukrainian header that drifts is named")
        drift("references/journey-protocol.md", "| `stale_metric` | script |", "| `stale_metric` | model |", "stale_metric", "7.5 a script finding the protocol hands to the model is named")
        drift("references/journey-protocol.md", "| `touchpoint` | `точки контакту` |", "| `channel` | `канали` |", "touchpoint", "7.6 a lane that drifts is named")
        drift("references/journey-protocol.md", "| `transition` | the result", "| `step` | the result", "transition", "7.7 a level that drifts is named")
        drift("references/journey-protocol.md", "| `refresh --note", "| `update --note", "refresh", "7.8 a command the protocol stops naming is named")
        drift("references/vault-schema.md", "| cjm-journey | cjm-research |", "| cjm-map | cjm-research |", "cjm-journey", "7.9 vault-schema without the cjm-journey type is named")
        drift("references/vault-schema.md", "period: string (the analysed period", "span: string (the analysed period", "period", "7.10 a snapshot field vault-schema drops is named")
        drift("references/artifact-publishing.md", "`cjm-research/<product>/journey-<slug>`", "`cjm-research/<product>/map-<slug>`", "journey-", "7.11 artifact-publishing without the journey key is named")
        drift("skills/cjm-research/SKILL.md", "journey-protocol.md", "journey.md", "cite", "7.12 a skill that stops citing the protocol is named", count=-1)
        # review 2: the lanes' classes, the parents, the thresholds, the vault-protocol rule, the scheduled hook, Step J
        drift("references/journey-protocol.md", "| `metric` | `метрики` | `measured` |", "| `metric` | `метрики` | `measured`, `reported` |", "metric", "7.14 a lane's classes that drift from LANE_CLASSES are named")
        drift("references/journey-protocol.md", "| `experiment` | a `solution` (required) |", "| `experiment` | an `opportunity` (required) |", "experiment", "7.15 a parent rule that drifts from PARENTS is named")
        drift("references/journey-protocol.md", "older than 90 days", "older than 60 days", "90", "7.16 a threshold the protocol changes alone is named")
        drift("references/vault-protocol.md", 'IF artifact.type == "cjm-journey":', 'IF artifact.type == "cjm-map":', "vault-protocol", "7.17 vault-protocol without the journey's save-by-name rule is named")
        drift("skills/cjm-research/references/cjm-reports.md", "journey_map.py refresh", "journey_map.py update", "refresh", "7.18 the scheduled health-check without its refresh step is named", count=-1)
        drift("skills/cjm-research/SKILL.md", "### Step J — Journey map", "### Step K — Journey map", "Step J", "7.19 the skill without its Step J is named")
        os.remove(os.path.join(r2, "references", "journey-protocol.md"))
        check("7.13 a missing protocol is an error, not silence", jm.check_protocol(r2) != [], jm.check_protocol(r2))
finally:
    shutil.rmtree(d, ignore_errors=True)
    shutil.rmtree(SAFE_HOME, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)

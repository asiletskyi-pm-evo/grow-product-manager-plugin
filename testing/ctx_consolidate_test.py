#!/usr/bin/env python3
"""TC-ctx-3220-consolidate — `ctx consolidate`: tidying as proposals (v3.22.0, plan C13, R4).

The fictional typical context with a line written twice, a relative date, a passed deadline and a past quarter — and
the same kinds inside fenced code and a provider's block, which are never touched. consolidate proposes REPLACE deltas
(ctx-consolidate), writes no record; a second run proposes nothing new; health counts what it would find; the deltas
accepted change exactly those lines and `ctx undo` puts them back; a record no longer current for 90+ days is named
with `ctx archive`. Unit checks of the relative dates.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_consolidate_test.py
"""
import datetime, json, os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
import ctx_consolidate as ccn  # noqa: E402
from ctx_testenv import Env, read  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


base = datetime.date(2026, 10, 27)                       # a Tuesday
check("0.1 «вчора» → the day before", ccn.absolute("- рев'ю вчора", base) == "- рев'ю 2026-10-26")
check("0.2 «next week» → week of its Monday", ccn.absolute("- review next week", base) == "- review week of 2026-11-02")
check("0.3 «минулого місяця» → the month", ccn.absolute("- запуск минулого місяця", base) == "- запуск 2026-09")
check("0.4 a word that only contains one is not one: «todayish», «завтрашній»",
      ccn.absolute("- todayish, завтрашній", base) is None)
check("0.5 a passed deadline and a passed quarter after до / by / until", ccn.passed("- launch by 2026-09-30", base)
      == "2026-09-30" and ccn.passed("- ship by Q3 2026", base) == "Q3 2026" and ccn.passed("- ship by Q4 2026", base) is None
      and ccn.passed("- до 2026-12-01", base) is None)
check("0.6 never a deadline: a result «у Q3 2026», a baseline, a field line, a table row, a deadline moved ahead",
      ccn.passed("- Baseline: CR 2.1% у Q1 2026", base) is None and ccn.passed("- Результат в Q3 2026: +12% GMV", base) is None
      and ccn.passed("- **Строк:** до 2026-09-30", base) is None
      and ccn.passed("| Checkout redesign | до 2026-09-30 | done |", base) is None
      and ccn.passed("- до 2026-09-30, продовжено до 2027-03-31", base) is None)
check("0.7 never a relative date: in a link, a name, a possessive, Tomorrow.io",
      ccn.absolute("- https://x.example/today/report", base) is None and ccn.absolute("- екран «Сьогодні»", base) is None
      and ccn.absolute("- today's numbers", base) is None and ccn.absolute("- Tomorrow.io weather", base) is None)

EXTRA = """
#### Notes

- Weekly sync with Bea
- weekly sync with  Bea
- Next review next week
- Launch by 2026-09-30
- Pricing test by Q3 2026
- Baseline 2.1% у Q1 2026

#### Owners

- Weekly sync with Bea

```
- same
- same
```
"""
d = tempfile.mkdtemp(prefix="ctx-consolidate-")
try:
    env = Env(d)
    env.edit(env.ctx, "- web\n- iOS\n", "- web\n- iOS\n" + EXTRA)
    env.edit(env.ctx, "- **Jira Team ID:** <team-uuid-2>",
             "<!-- zorg-core:begin id=team v=1 -->\n- **Jira Team ID:** <team-uuid-2>\n- dup\n- dup\n- due 2020-01-01\n"
             "<!-- zorg-core:end id=team -->")
    env.run("migrate", "--apply")
    env.run("compile")
    r0 = {f: read(env.store, "records", f) for f in os.listdir(os.path.join(env.store, "records"))}
    rc, out, res = env.run("health")
    check("1.0 health counts what consolidate would find", "consolidate знайде 4" in out, out[-900:])
    rc, out, res = env.run("consolidate")
    ib = json.load(open(os.path.join(env.store, ".state", "inbox.json"), encoding="utf-8"))["entries"]
    got = sorted((e["delta"]["text"], e["delta"]["value"]) for e in ib)
    monday = (datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
              + datetime.timedelta(weeks=1)).isoformat()
    check("1.1 four REPLACE deltas: the second of a line written twice, the passed deadline, the past quarter, the "
          "relative date", rc == 0 and got == sorted([("- weekly sync with  Bea", ""), ("- Launch by 2026-09-30", ""),
                                                     ("- Pricing test by Q3 2026", ""),
                                                     ("- Next review next week", "- Next review week of %s" % monday)])
          and all(e["skills"] == ["ctx-consolidate"] for e in ib), (out[-400:], got))
    check("1.2 fenced code and a provider's block are never touched; no record written",
          not any("same" in t or "dup" in t or "2020" in t for t, _ in got)
          and {f: read(env.store, "records", f) for f in os.listdir(os.path.join(env.store, "records"))} == r0, got)
    check("1.2b … not even tried: no proposal refused as a provider's block",
          not any(r["status"] == "provider-block" for r in res["results"]), res["results"])
    j = [json.loads(l) for l in read(env.store, ".state", "journal.jsonl").splitlines() if l.strip()]
    check("1.3 one journal line op propose (skill ctx-consolidate), no snapshot",
          j[-1]["op"] == "propose" and j[-1]["skill"] == "ctx-consolidate" and "snapshot" not in j[-1], j[-1])
    jl = len(j)
    rc, out, res = env.run("consolidate")
    check("1.4 a second run proposes nothing new and writes no journal line",
          rc == 0 and not res["added"] and "нічого нового" in out
          and len(read(env.store, ".state", "journal.jsonl").splitlines()) == jl, out[-300:])
    rc, out, _ = env.run("health")
    check("1.5 health: nothing more for consolidate once it is in the inbox", "consolidate знайде" not in out, out[-600:])

    rc, out, res = env.run("inbox", "list")
    rc, out, res = env.run("inbox", "accept", "all", "--code", res["code"])
    app = env.record("product.zorg-app")
    check("2.1 accept: the duplicate, the deadline and the quarter gone, the date absolute",
          rc == 0 and "weekly sync with  Bea" not in app and "Weekly sync with Bea" in app and "2026-09-30" not in app
          and "Q3 2026" not in app and "- Next review week of %s" % monday in app
          and app.count("Weekly sync with Bea") == 2 and "Baseline 2.1% у Q1 2026" in app, app)
    rc, out, _ = env.run("undo")
    check("2.2 ctx undo → the records byte for byte",
          {f: read(env.store, "records", f) for f in os.listdir(os.path.join(env.store, "records"))} == r0, out[-300:])

    # review I5: a duplicate fixed by hand before the accept — the copy left stays
    env.run("consolidate")
    env.edit(env.ctx, "- weekly sync with  Bea\n", "")
    env.run("sync")
    rc, out, res = env.run("inbox", "list")
    rc, out, res = env.run("inbox", "accept", "all", "--code", res["code"])
    check("2.3 the duplicate removed by hand first: accept keeps the one copy left",
          env.record("product.zorg-app").count("Weekly sync with Bea") == 2, env.record("product.zorg-app"))
    rc, out, res = env.run("consolidate", "--now", "garbage")
    check("2.4 consolidate --now garbage → exit 3", rc == 3, out[-200:])
    env.run("invalidate", "product.zorg-lite", "--reason", "closed")
    rc, out, res = env.run("consolidate")
    check("3.0 no longer current since today → not named yet", "ctx archive" not in out, out[-300:])
    later = (datetime.date.today() + datetime.timedelta(days=120)).isoformat()
    rc, out, res = env.run("consolidate", "--now", later)
    check("3.1 a record no longer current for 90+ days → named with ctx archive, no delta",
          "ctx archive product.zorg-lite" in out and "product.zorg-lite" in res["archive"]
          and not any(r.get("record") == "product.zorg-lite" for r in res["results"]), out[-400:])
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)

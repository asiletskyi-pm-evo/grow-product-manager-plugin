#!/usr/bin/env python3
"""The model level of the search's acceptance (v3.16.0, spec §11 «рівень моделі»): criteria 1–3 of the spec.

Not shipped to the plugin's users — a tool of the acceptance run in a Claude Code session, as the imitation of
2026-10-20 was (not a headless `claude -p`). It holds no data of any organisation: every question, variant and path
comes from the golden set named by --golden, every candidate from `ctx search --json` on the home and context named.

  prepare --golden G --out DIR --home H --context C [--batch 24]
      For each row of the golden set (the empty ones too): `ctx search --q <q> --q <variant> … [--product P] [--skill S]
      --json` on H and C; the batches DIR/batch-001.json, … — each a JSON list of {q, variants, product, skill,
      candidates, notes} (an error of the search: {…, error}). Never the answers: no good, ok or bad in a batch. A
      subagent per batch reads the candidates (`ctx search --get ID` for the ones it rates «прямо» — the own index keeps
      every section's id; a note only a local index or MCP knows is in last.json for the latest 1000 ids, so run a batch's
      agents soon after its prepare), follows references/search-protocol.md and writes its answers to a JSON file.

  score --golden G --answers DIR
      Reads every *.json of DIR: {q: {"taken": [path], "variants": [path], "nothing": bool}} — what the skill took
      silently, what its block of options offered, and whether it said «У базі нічого прямо про це». A path may carry
      `#heading` or ` › section`: the note counts. Prints and ends with `SCORE {json}`:
        precision_taken  criterion 1 — of everything taken (in every row answered), the share the set marks right
                         (`good` or `ok` of its row; in an empty row nothing is right); None when nothing was taken
        empty_clean      criterion 2 — the share of the empty rows answered with nothing taken
        hit              criterion 3 — the share of the rows with an answer whose right note was taken or offered
        bad_taken        how many taken notes the set marks `bad`
        missing          the rows of the set with no answer (left out of the three shares)

Stdlib only; run from the repo root.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_hints as ch  # noqa: E402

CTX = os.path.join(ROOT, "scripts", "ctx.py")
BATCH = 24


def _search(row, home, context):
    """`ctx search --json` of a row: its CTX_RESULT, or {"error": …}."""
    args = [sys.executable, CTX, "search"]
    for q in [row["q"]] + list(row.get("variants") or []):
        args += ["--q", q]
    if row.get("product"):
        args += ["--product", row["product"]]
    if row.get("skill"):
        args += ["--skill", row["skill"]]
    args += ["--json", "--home", home, "--context", context]
    p = subprocess.run(args, capture_output=True, text=True, timeout=180)
    last = (p.stdout.strip().splitlines() or [""])[-1]
    try:
        res = json.loads(last[len("CTX_RESULT "):]) if last.startswith("CTX_RESULT ") else None
    except ValueError:
        res = None
    if res is None:
        return {"error": "ctx search gave no CTX_RESULT (exit %d): %s" % (p.returncode, (p.stdout + p.stderr)[-300:])}
    if p.returncode not in (0, 5):
        return {"error": res.get("error") or "exit %d" % p.returncode}
    return res


def prepare(golden, out, home, context, batch=BATCH):
    rows = ch.load_golden(golden)
    os.makedirs(out, exist_ok=True)
    batch = max(1, int(batch))
    files = []
    for k in range(0, len(rows), batch):
        items = []
        for row in rows[k:k + batch]:
            res = _search(row, home, context)
            item = {"q": row["q"], "variants": list(row.get("variants") or []), "product": row.get("product") or "",
                    "skill": row.get("skill") or "", "candidates": res.get("candidates") or [], "notes": res.get("notes") or []}
            if res.get("error"):
                item["error"] = res["error"]
            items.append(item)
        name = os.path.join(out, "batch-%03d.json" % (k // batch + 1))
        with open(name, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)
            f.write("\n")
        files.append(name)
        print("%s · %d" % (name, len(items)))
    return files


def _note(path):
    """The note a taken or offered path names: without `#heading` and without ` › section`."""
    return ch.note_of(str(path or "").split(" › ", 1)[0].strip())


def _in(path, entries):
    note = _note(path)
    return any(ch.note_of(e) == note for e in entries)


def _answers(folder):
    out = {}
    for name in sorted(glob.glob(os.path.join(folder, "*.json"))):
        with open(name, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("%s: not an object {q: answer}" % name)
        for q, a in data.items():
            if not isinstance(a, dict):
                raise ValueError("%s: the answer for %r is not an object" % (name, q))
            out[ch.N(q).strip()] = a
    return out


def _share(k, n):
    return k / n if n else None


def score(golden, folder):
    rows = ch.load_golden(golden)
    answers = _answers(folder)
    taken = right = bad_taken = 0
    empty = clean = full = hit = 0
    missing = []
    for row in rows:
        a = answers.get(row["q"])
        if a is None:
            missing.append(row["q"])
            continue
        took = [p for p in a.get("taken") or [] if isinstance(p, str) and p.strip()]
        offered = [p for p in a.get("variants") or [] if isinstance(p, str) and p.strip()]
        good = list(row["good"]) + list(row.get("ok") or [])
        taken += len(took)
        right += sum(1 for p in took if _in(p, good))
        bad_taken += sum(1 for p in took if _in(p, row.get("bad") or []))
        if not row["good"]:
            empty += 1
            clean += not took
        else:
            full += 1
            hit += any(_in(p, good) for p in took + offered)
    return {"precision_taken": _share(right, taken), "empty_clean": _share(clean, empty), "hit": _share(hit, full),
            "taken": taken, "taken_right": right, "bad_taken": bad_taken, "empty": empty, "empty_clean_n": clean,
            "rows": full, "hits": hit, "missing": len(missing), "missing_q": missing}


def _shown(x):
    return "—" if x is None else "%.3f" % x


def main(argv=None):
    p = argparse.ArgumentParser(prog="search_agent_eval", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("prepare")
    sp.add_argument("--golden", required=True); sp.add_argument("--out", required=True)
    sp.add_argument("--home", required=True); sp.add_argument("--context", required=True)
    sp.add_argument("--batch", type=int, default=BATCH)
    sp = sub.add_parser("score")
    sp.add_argument("--golden", required=True); sp.add_argument("--answers", required=True)
    a = p.parse_args(argv)
    try:
        if a.cmd == "prepare":
            prepare(a.golden, a.out, a.home, a.context, a.batch)
            return 0
        s = score(a.golden, a.answers)
    except (OSError, ValueError) as e:
        print("search_agent_eval: %s" % e)
        return 3
    print("precision_taken %s (%d of %d taken are right; bad taken: %d)" % (_shown(s["precision_taken"]), s["taken_right"],
                                                                          s["taken"], s["bad_taken"]))
    print("empty_clean %s (%d of %d empty rows with nothing taken)" % (_shown(s["empty_clean"]), s["empty_clean_n"], s["empty"]))
    print("hit %s (%d of %d rows: the right note taken or offered)" % (_shown(s["hit"]), s["hits"], s["rows"]))
    if s["missing"]:
        print("без відповіді: %d" % s["missing"])
    print("SCORE " + json.dumps(s, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""TC-ctx-3235-history — the journal with values and the human changelog `ctx history` (since v3.23.0).

Every journal line of a write that changed records carries `changes` [{id, where, was, became}] — read from the
snapshot the write took and the records after it: a field as its label and values, any other lines under their heading
— each value at most 300 characters, a secret or an identifier hidden («[приховано: …]»); a provider pass carries `was`
{block: the old base's hash} beside `taken`. A journal line of v3.22 (no values) is still read. `ctx history` builds one
note per month, `history/YYYY-MM.md` (Keep a Changelog, newest first): `## [<repo> <v>] — <day>` for a core release with
«Блок | Було | Стало» from the bases, `## Твої зміни — <day>` with «Запис | Що | Було | Стало», a line for what has no
values. `--write` writes it only when its text changed; every writing command refreshes the note of its month.
On the fictional "Zorg" fixture. Semantics: references/context-protocol.md §5p. Stdlib only; run from the repo root.
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_blocks as cb  # noqa: E402
import ctx_history as ch  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_store as cs  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "ctx-repos")
NOW = "2026-10-20T10:00:00+03:00"
NS = "zorg-core"
REPO = crp.normalise({"id": "zorg-core", "kind": "bundle", "paths": ["/zorg/core"], "team": "team-alpha"})
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def migrated(d):
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    os.makedirs(os.path.join(home, ".grow-pm"))
    os.makedirs(os.path.join(vault, "Notes", "_System"))
    text = open(os.path.join(FIX, "context.md"), encoding="utf-8", newline="").read().replace("{{VAULT}}", vault)
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    for p in (ctxp, os.path.join(vault, "Notes", "_System", "local-context.md")):
        open(p, "w", encoding="utf-8", newline="").write(text)
    copies = co.copies_for(ctxp, text, home=home)
    store = cs.Store(co.store_root_for(text, home=home))
    co.migrate(ctxp, store.root, copies, home, apply=True, now=NOW)
    return home, text, copies, store, ctxp


def ctx(home, ctxp, *args):
    env = {k: v for k, v in os.environ.items() if k not in ("GROW_PM_CONTEXT_PATH", "GROW_PM_PROVIDER_PATHS")}
    env["HOME"] = home
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ctx.py")] + list(args) + ["--context", ctxp, "--home", home],
                       capture_output=True, text=True, env=env)
    out = r.stdout + r.stderr
    res = [l for l in out.splitlines() if l.startswith("CTX_RESULT ")]
    return r.returncode, out, json.loads(res[-1][len("CTX_RESULT "):]) if res else {}


def journal(store):
    p = os.path.join(store.state_dir, "journal.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.isfile(p) else []


def region(bid, v, body):
    return "<!-- %s:begin id=%s v=%s -->\n%s\n<!-- %s:end id=%s -->" % (NS, bid, v, body, NS, bid)


with tempfile.TemporaryDirectory() as d:
    home, text, copies, store, ctxp = migrated(d)
    rc, out, res = ctx(home, ctxp, "set", "product.zorg-app", "Jira Project Key", "ZORG")
    j = journal(store)[-1]
    check("set: the journal line carries the field's change", rc == 0 and j.get("changes") ==
          [{"id": "product.zorg-app", "where": "Jira Project Key", "was": "PROJ", "became": "ZORG"}], j)
    rc, out, res = ctx(home, ctxp, "append", "product.zorg-app", "--text", "- a new line about Zorg")
    j = journal(store)[-1]
    check("append: the added line under its heading, was empty", rc == 0 and j.get("changes") ==
          [{"id": "product.zorg-app", "where": "Product: Zorg App", "was": "", "became": "- a new line about Zorg"}], j)
    month = journal(store)[-1]["ts"][:7]
    note = os.path.join(store.root, "history", month + ".md")
    check("every writing command refreshes the note of its month", os.path.isfile(note)
          and "| product.zorg-app | Jira Project Key | PROJ | ZORG |" in open(note, encoding="utf-8").read(), note)

    lc = open(ctxp, encoding="utf-8").read()
    open(ctxp, "w", encoding="utf-8").write(lc.replace("- a new line about Zorg\n", "- a new line about Zorg\n- card 4111 1111 1111 1111\n", 1))
    rc, out, res = ctx(home, ctxp, "sync")
    j = journal(store)[-1]
    became = [c["became"] for c in j.get("changes") or []]
    check("an import whose line holds a card number: the value is hidden, its kind named",
          j["op"] == "sync" and became and all("4111" not in b for b in became) and any(b.startswith("[приховано:") for b in became), j)
    lc = open(ctxp, encoding="utf-8").read()
    open(ctxp, "w", encoding="utf-8").write(lc.replace("- a new line about Zorg\n", "- a new line about Zorg\n- **API key:** abcd1234efgh5678\n", 1))
    rc, out, res = ctx(home, ctxp, "sync")
    j = journal(store)[-1]
    check("a labelled secret (API key: …) is hidden in the journal too", "abcd1234efgh5678" not in json.dumps(j, ensure_ascii=False)
          and any(c["became"].startswith("[приховано:") for c in j.get("changes") or []), j)
    os.remove(note)
    rc, out, res = ctx(home, ctxp, "set", "product.zorg-app", "Jira Project Key", "ZORG")
    check("a write that added no journal line writes no changelog", "unchanged" in out and not os.path.exists(note), out[-200:])
    ctx(home, ctxp, "history", "--write", "--month", month)
    long = "x" * 400
    rc, out, res = ctx(home, ctxp, "set", "product.zorg-app", "Notes", long)
    j = journal(store)[-1]
    check("a value longer than 300 characters is cut with …", len(j["changes"][0]["became"]) == 300
          and j["changes"][0]["became"].endswith("…"), j["changes"])

    rc, out, res = ctx(home, ctxp, "undo")
    check("undo is in the history as a line", rc == 0 and "↩" in ch.build(store, month), out[-300:])
    with open(os.path.join(store.state_dir, "journal.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": month + "-01T09:00:00+03:00", "op": "sync", "ids": ["org.zorg"], "source": "import",
                            "reason": "a line of v3.22", "snapshot": "/nowhere"}) + "\n")
    with open(os.path.join(store.state_dir, "journal.jsonl"), "a", encoding="utf-8") as f:
        f.write('{"ts": "%s-02T09:00:00+03:00", "op": "sy' % month + "\n")
    text_m = ch.build(store, month)
    check("history: a torn journal line is passed over, the rest still read", "a line of v3.22" in text_m, "")
    check("history: a v3.22 line is listed with what changed and no values", "a line of v3.22" in text_m and "org.zorg" in text_m, text_m)
    check("history: the note's form — frontmatter, title, newest day first, own changes as a table",
          text_m.startswith("---\ntype: system\nkind: context-history\nmonth: %s\n---\n" % month)
          and "# Журнал змін контексту — %s" % month in text_m and "## Твої зміни — " in text_m
          and "| Запис | Що | Було | Стало |" in text_m
          and text_m.index("## Твої зміни — %s" % j["ts"][:10]) < text_m.index("## Твої зміни — %s-01" % month), text_m)
    rc, out, res = ctx(home, ctxp, "history", "--write", "--month", month)
    rc2, out2, res2 = ctx(home, ctxp, "history", "--write", "--month", month)
    check("history --write: a second run changes nothing", rc == 0 and rc2 == 0 and res2.get("changed") is False, (res, res2))
    rc, out, res = ctx(home, ctxp, "history", "--month", month)
    check("history (no --write) prints the note", rc == 0 and "# Журнал змін контексту — %s" % month in out, out[:300])
    rc, out, res = ctx(home, ctxp, "history", "--month", "2026-13")
    check("history: a month that is no month → exit 3", rc == 3, out)

# ------------------------------------------------------------------ a core release: Було | Стало from the bases
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store, ctxp = migrated(d)
    regions = {k: v["text"] for k, v in cb.find_regions(store.load(), NS)[0].items()}
    f = {"source": "folder", "version": "0.4", "blocks": {k: v for k, v in regions.items() if k != "team"}, "team": regions["team"],
         "team_source": "folder", "team_error": None, "error": None, "checked": NOW}
    with cs.guard_roots(co.allowed_roots(home, text)):
        cb.adopt(store, copies, home, REPO, f, NOW, True)
        old_sha = cb.load_state(store, "zorg-core")["blocks"]["scope"]["base_sha"]
        S5 = region("scope", "0.5", "### Scope of work\nThe user works on Zorg App and Zorg Lite.")
        res = cb.apply(store, copies, home, REPO, dict(f, version="0.5", blocks=dict(f["blocks"], scope=S5)), {}, [], NOW)
    j = journal(store)[-1]
    check("provider-apply: was holds the old base's hash beside taken", j.get("was") == {"scope": old_sha}
          and j["taken"]["scope"] == cb.offered(S5), j)
    t = ch.build(store, "2026-10")
    check("history: a core release as its own section with the block's lines before and after",
          "## [zorg-core 0.5] — 2026-10-20" in t and "| Блок | Було | Стало |" in t
          and "| scope | The user works on Zorg App only. | The user works on Zorg App and Zorg Lite. |" in t, t)
    os.remove(os.path.join(store.state_dir, "blocks", "zorg-core", old_sha + ".md"))
    t = ch.build(store, "2026-10")
    check("…a base no longer kept: the release is listed, its lines say so", "## [zorg-core 0.5] — 2026-10-20" in t
          and "база вже не зберігається" in t, t)
    check("history of a month with no line: the note says so", "змін не було" in ch.build(store, "2026-01"), "")

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)

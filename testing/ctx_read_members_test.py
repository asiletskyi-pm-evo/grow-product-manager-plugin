#!/usr/bin/env python3
"""TC-ctx-3181-read — `ctx read`: team.members one line per person (since v3.19.0, plan R1, C8, C8a).

The fictional Zorg vault of testing/fixtures/entity/ is copied to a temp dir with a store migrated from its
local-context.md, where the team «Zorg Pay» lists its members by hand: the record's items, the core card's «Склад
команди» and the members derived from each person's winning team are joined by entity — one line per person with
every source —, a name exactly one card carries joins, a namesake or a name no card carries stays text; a record no team
card matches, a busy index and a core rule are shown as before, with one line that says why. `ctx read` writes nothing.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_read_members_test.py
"""
import io, contextlib, json, os, shutil, sqlite3, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx as ctx_cli  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_resolve as rv  # noqa: E402
import ctx_search as cs_  # noqa: E402

CTX = os.path.join(ROOT, "scripts", "ctx.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "entity")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:1200]))


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8", newline="").write(text)


TEAM = """### Team: Zorg Pay (ZP)

- **Jira Team ID:** <team-uuid-2>

#### Members

- [[Notes/People/rhea|Rhea One]] — PM
- Dee — QA
- Ann Other — QA

"""


class Env:
    def __init__(self, d, team=TEAM):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        shutil.copytree(os.path.join(FIX, "vault"), self.vault)
        for dirpath, _, names in os.walk(self.vault):
            for n in names:
                p = os.path.join(dirpath, n)
                if n.endswith(".yaml") and "{{VAULT}}" in read(p):
                    write(p, read(p).replace("{{VAULT}}", self.vault))
        text = read(FIX, "context.md").replace("{{VAULT}}", self.vault).replace("{{HOME}}", self.home)
        text = text.replace("## Obsidian Vaults (Optional)", team + "## Obsidian Vaults (Optional)")
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        write(self.ctx, text)
        rc, out, _ = self.cli("migrate", "--apply")
        assert rc == 0, out[-500:]
        self.text = read(self.ctx)
        sctx = cs_.context_for(self.home, self.text, store_root=os.path.join(self.vault, "Notes", "_System", "context"))
        ci.Index(self.home).refresh(sctx["roots"], sctx["store_rel"], sctx["blocks_rels"])

    def cli(self, *args):
        env = dict(os.environ)
        env.pop("GROW_PM_CONTEXT_PATH", None)
        p = subprocess.run([sys.executable, CTX] + list(args) + ["--home", self.home, "--context", self.ctx],
                           capture_output=True, text=True, env=env, timeout=120)
        lines = [l for l in p.stdout.splitlines() if l.startswith("CTX_RESULT ")]
        return p.returncode, p.stdout + p.stderr, json.loads(lines[-1][len("CTX_RESULT "):]) if lines else None

    def inproc(self, *args):
        saved = os.environ.pop("GROW_PM_CONTEXT_PATH", None)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                try:
                    rc = ctx_cli.main(list(args) + ["--home", self.home, "--context", self.ctx])
                except SystemExit as e:
                    rc = e.code
        finally:
            if saved is not None:
                os.environ["GROW_PM_CONTEXT_PATH"] = saved
        return rc, buf.getvalue()


def team_part(out, title):
    """The part of a read view from the record `title`'s heading to the next record's."""
    at = out.find("## Team: " + title)
    if at < 0:
        return ""
    nxt = out.find("\n## ", at + 1)
    return out[at:nxt if nxt > 0 else len(out)]


def tree(*tops):
    out = {}
    for top in tops:
        for dirpath, _, names in os.walk(top):
            for n in names:
                p = os.path.join(dirpath, n)
                st = os.stat(p)
                out[p] = (st.st_size, st.st_mtime)
    return out


with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    before = tree(env.vault, os.path.join(env.home, ".grow-pm"))
    rc, out, res = env.cli("read", "--skill", "task-creator")
    after = tree(env.vault, os.path.join(env.home, ".grow-pm"))
    zp = team_part(out, "Zorg Pay")
    lines = [l for l in zp.splitlines() if l.startswith("- ")]
    rhea = [l for l in lines if "Rhea One" in l]
    check("v3.18.1 C8: ctx read team.members — Rhea is ONE line: your record's row, the core card's «Склад команди» and "
          "her winning team (derived) as its sources", rc == 0 and len(rhea) == 1 and "твоє" in rhea[0]
          and "zorg-core" in rhea[0] and "виведене" in rhea[0], zp[-1500:])
    check("…the line keeps your row (`— PM`)", rhea and "PM" in rhea[0], rhea)
    check("…Fay, derived alone, is a line of her own, marked", any("Fay Four" in l and "лише виведене" in l for l in lines), lines)
    check("…Dee joins by the name exactly one card carries (`за назвою`); Ann Other, whom no card names, stays your text",
          any(l.startswith("- Dee") and "за назвою" in l for l in lines) and any("Ann Other" in l and "твоє" in l for l in lines),
          lines)
    check("…the list says it is joined by entity, and where its sources are", rv.WHY_JOINED.split(" — ")[1] in zp
          or "склеєно за сутністю" in zp, zp[-1200:])
    check("v3.18.1 `ctx read` writes nothing — not the store, not the index", before == after,
          sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))[:5])

with tempfile.TemporaryDirectory() as d:
    env = Env(d, team=TEAM.replace("- Dee — QA\n", "- Cy Namesake — QA\n"))
    rc, out, _ = env.cli("read", "--skill", "task-creator")
    lines = [l for l in team_part(out, "Zorg Pay").splitlines() if l.startswith("- ")]
    check("v3.18.1 Review Focus: «Cy Namesake», a name two cards of the core carry, stays text, joined with nobody",
          any(l.startswith("- Cy Namesake — QA") and "за назвою" not in l for l in lines), lines)

with tempfile.TemporaryDirectory() as d:
    env = Env(d, team=TEAM.replace("### Team: Zorg Pay (ZP)", "### Team: Beta (B)"))
    rc, out, _ = env.cli("read", "--skill", "task-creator")
    beta = team_part(out, "Beta")
    check("v3.18.1 C8: a team record no team card matches — its own items joined among themselves, and one line "
          "«команду «…» не зіставлено з карткою: …»", "не зіставлено з карткою" in beta and "Rhea One" in beta
          and "Fay Four" not in beta, beta[-900:])

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    real = ci.Index.cards

    def busy(self):
        self.problem = ci.BUSY_NOTE
        return []
    ci.Index.cards = busy
    t0 = time.monotonic()
    try:
        rc, out = env.inproc("read", "--skill", "task-creator")
    finally:
        ci.Index.cards = real
    zp = team_part(out, "Zorg Pay")
    check("v3.18.1 Review Focus: the index busy — the members as v3.18.0 printed them, and «пункти не склеєно: …», "
          "with no wait", rc == 0 and "пункти не склеєно" in zp and "Ann Other — QA" in zp and "Fay Four" not in zp
          and time.monotonic() - t0 < cs_.OPEN_S + 10, (rc, zp[-800:]))

import ctx_entity as ce  # noqa: E402
import ctx_eslots as es  # noqa: E402
import ctx_slots as sl  # noqa: E402


class FakeOrigin:
    def line(self, ns, block, version, marks, slots=()):
        return "> [%s · v%s%s]" % (ns, version, "".join(" · " + m for m in marks))

    def clip(self, x):
        return x


with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    sctx = cs_.context_for(env.home, env.text, store_root=os.path.join(env.vault, "Notes", "_System", "context"))
    idx = ci.Index(env.home)
    reg, _ = ce.load(sctx, idx, ce.empty_memory())
    rule = {"level": "rule", "source": "zorg-core", "ns": "zorg-core", "block": "team", "version": "0.2", "rank": 500,
            "text": "#### Members\n\n- Core Person — PM\n", "record": "team.zorg-pay-zp", "how": "marker", "placed": True}
    result = {"slot": "team.members", "kind": "list", "shown": [rule], "note": None, "also": [], "diverges": [],
              "why": rv.WHY_RULE, "decision": None, "prefer": "mine"}
    text = es.read_members(result, {"id": "team.zorg-pay-zp", "title": "Team: Zorg Pay (ZP)"}, FakeOrigin(),
                           lambda: ((reg, idx, sctx), None), sl.load_catalogue())
    check("v3.18.1 C8a: a core rule for team.members — its list alone, as before, and «з карток ще N — ctx entity …»",
          "Core Person — PM" in text and "Rhea One" not in text and "з карток ще 2" in text
          and 'ctx entity "Zorg Pay" --slot team.members' in text, text)
    result["why"], result["prefer"] = "перевага: repo:zorg-core", "repo:zorg-core"
    text = es.read_members(result, {"id": "team.zorg-pay-zp", "title": "Team: Zorg Pay (ZP)"}, FakeOrigin(),
                           lambda: ((reg, idx, sctx), None), sl.load_catalogue())
    check("…and so does your `prefer repo:` for it", "Rhea One" not in text and "з карток ще 2" in text, text)

# --- v3.18.1 acceptance findings (the user's data, 2026-10-26)
def local_team_index(env):
    """A local index of the user's that holds another team's card under the same team's name (as Growth's does)."""
    con = sqlite3.connect(os.path.join(env.home, "zorg-brain.sqlite"))
    con.execute("CREATE TABLE meta(k TEXT, v TEXT)")
    con.execute("INSERT INTO meta VALUES ('vault_root', ?)", (env.vault,))
    con.execute("CREATE TABLE notes(path TEXT PRIMARY KEY, title TEXT, type TEXT, fm_json TEXT)")
    con.execute("CREATE VIRTUAL TABLE notes_fts USING fts5(path, title, body)")
    con.execute("INSERT INTO notes VALUES (?, ?, ?, ?)", ("Partner/Team/Zorg Pay Team.md", "Zorg Pay Team", "team",
                                                         json.dumps({"type": "team", "name": "Zorg Pay Team"})))
    con.commit()
    con.close()


with tempfile.TemporaryDirectory() as d:
    env = Env(d, team=TEAM.replace("- [[Notes/People/rhea|Rhea One]] — PM\n", "- One Rhea ◌ — PM\n"))
    local_team_index(env)
    rc, out, _ = env.cli("read", "--skill", "task-creator")
    zp = team_part(out, "Zorg Pay")
    lines = [l for l in zp.splitlines() if l.startswith("- ")]
    check("v3.18.1 acceptance: another team's card of a like name in a local index does not keep the record from its "
          "core card — the exact name wins", "не зіставлено" not in zp and any("Fay Four" in l for l in lines), zp[-900:])
    rhea = [l for l in lines if "Rhea" in l]
    check("v3.18.1 acceptance: your row that names a person the list's other sources name, in another spelling («One "
          "Rhea ◌»), is ONE line with them — `схоже ім'я` —, never a second line", len(rhea) == 1 and "схоже ім'я" in rhea[0]
          and "zorg-core" in rhea[0] and "твоє" in rhea[0], rhea)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    rc, out, _ = env.cli("read", "--skill", "task-creator")
    read_items = sorted(l[2:].split(" · ")[0].split(" — ")[0] for l in team_part(out, "Zorg Pay").splitlines()
                        if l.startswith("- ") and "Jira Team ID" not in l)
    rc2, out2, res2 = env.cli("entity", "Zorg Pay", "--slot", "team.members")
    m = (((res2 or {}).get("entities") or [{}])[0].get("slots") or {}).get("team.members") or {}
    ent_items = sorted(i["label"].split(" — ")[0] for i in m.get("items", []))
    check("v3.18.1 C8: `ctx entity <team> --slot team.members` and `ctx read`'s team.members are one composition — "
          "your record's items too (Ann Other), one line per person", rc2 == 0 and len(ent_items) == len(read_items)
          and any("Ann Other" in x for x in ent_items), (read_items, ent_items))

# --- v3.18.1 Task 4–5 review fixes
PROSE = TEAM.replace("#### Members\n\n", "#### Members\n\nCore squad of five; contractors listed separately.\n\n##### Backend\n\n"
                     ).replace("- Ann Other — QA\n", "##### Contractors\n\n- Ann Other — QA\n\n_Dee on leave until Nov._\n")
with tempfile.TemporaryDirectory() as d:
    env = Env(d, team=PROSE)
    rc, out, _ = env.cli("read", "--skill", "task-creator")
    zp = team_part(out, "Zorg Pay")
    check("v3.18.1 Task 4 review I1: no line of the section is lost — its prose, sub-headings and notes stay, after the "
          "joined list", all(x in zp for x in ("Core squad of five; contractors listed separately.", "##### Backend",
                                               "##### Contractors", "_Dee on leave until Nov._")) and "Rhea One" in zp, zp[-1200:])
with tempfile.TemporaryDirectory() as d:
    env = Env(d, team=TEAM.replace("### Team: Zorg Pay (ZP)", "### Team: Checkout (Zorg Pay)"))
    rc, out, _ = env.cli("read", "--skill", "task-creator")
    co = team_part(out, "Checkout")
    check("v3.18.1 Task 4 review I2: a team named in brackets («Checkout (Zorg Pay)») is not this record's card — "
          "«не зіставлено»", "не зіставлено" in co and "Fay Four" not in co, co[-700:])
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(os.path.join(env.vault, "Notes", "Teams", "Zorg Pay.md"), "---\ntype: team\n---\n# Zorg Pay\n")
    sctx = cs_.context_for(env.home, env.text, store_root=os.path.join(env.vault, "Notes", "_System", "context"))
    ci.Index(env.home).refresh(sctx["roots"], sctx["store_rel"], sctx["blocks_rels"])
    rc, out, _ = env.cli("read", "--skill", "task-creator")
    zp = team_part(out, "Zorg Pay")
    check("v3.18.1 Task 4 review M8: two cards of one team name — «кілька карток» says what to do: `ctx entity same`",
          "кілька карток" in zp and "ctx entity same" in zp, zp[-600:])
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    text = read(env.ctx)
    write(env.ctx, text.split("## Obsidian Vaults (Optional)")[0])      # no vault: nothing to index
    rc, out, _ = env.cli("read", "--skill", "task-creator", "--store", os.path.join(env.vault, "Notes", "_System", "context"))
    check("v3.18.1 Task 4 review M1: no vault and no index — the members as before, no «ctx index rebuild» line",
          rc == 0 and "ctx index rebuild" not in out and "Ann Other — QA" in out, out[-500:])
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    real = es.read_members
    es.read_members = lambda *a_, **k_: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        rc, out = env.inproc("read", "--skill", "task-creator")
    finally:
        es.read_members = real
    check("v3.18.1 Task 4 review M3: a failure of the join never fails the read — the members as before and «пункти не "
          "склеєно»", rc == 0 and "Ann Other — QA" in out and "пункти не склеєно" in out, (rc, out[-500:]))
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    sctx = cs_.context_for(env.home, env.text, store_root=os.path.join(env.vault, "Notes", "_System", "context"))
    idx = ci.Index(env.home)
    reg, _ = ce.load(sctx, idx, ce.empty_memory())
    rule = {"level": "rule", "source": "zorg-core", "ns": "zorg-core", "block": "team", "version": "0.2", "rank": 500,
            "text": "#### Members\n\n- [[Notes/People/rhea|Rhea One]] — PM\n", "record": "team.zorg-pay-zp", "how": "marker",
            "placed": True}
    result = {"slot": "team.members", "kind": "list", "shown": [rule], "note": None, "also": [], "diverges": [],
              "why": rv.WHY_RULE, "decision": None, "prefer": "mine"}
    text = es.read_members(result, {"id": "team.zorg-pay-zp", "title": "Team: Zorg Pay (ZP)"}, FakeOrigin(),
                           lambda: ((reg, idx, sctx), None), sl.load_catalogue())
    check("v3.18.1 Task 4 review M4: «з карток ще N» counts only the people the rule does not list (Rhea is in it)",
          "з карток ще 1" in text, text)
    result["why"], result["prefer"] = "перевага: all", "all"
    text = es.read_members(result, {"id": "team.zorg-pay-zp", "title": "Team: Zorg Pay (ZP)"}, FakeOrigin(),
                           lambda: ((reg, idx, sctx), None), sl.load_catalogue())
    check("v3.18.1 Task 4 review M5: `prefer all` shows every candidate in full, as before — no join",
          "склеєно за сутністю" not in text and "Rhea One" in text, text)

# --- v3.18.1 final review fixes
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    sctx = cs_.context_for(env.home, env.text, store_root=os.path.join(env.vault, "Notes", "_System", "context"))
    idx = ci.Index(env.home)
    reg, _ = ce.load(sctx, idx, ce.empty_memory())
    rule = {"level": "rule", "source": "zorg-core", "ns": "zorg-core", "block": "team", "version": "0.2", "rank": 500,
            "text": "#### Members\n\n- [[Notes/People/rhea|Rhea One]] — PM\n", "record": "team.zorg-pay-zp", "how": "marker",
            "placed": True}
    ent = reg.of("ZorgCore/Teams/zorg-pay.md")
    ans = es.slots_of(reg, idx, ent, sl.load_catalogue(), sctx, only=["team.members"],
                      records=lambda e: {"cands": es.record_candidates([rule]), "exclusive": True})["team.members"]
    check("v3.18.1 final review I2: under a core rule `ctx entity --slot team.members` is the rule's list, as `ctx read` "
          "prints it, with how many more the cards name", [i["label"] for i in ans["items"]] == ["Rhea One"]
          and ans.get("from_cards") == 1, ans)
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    rc, out, res = env.cli("read", "--skill", "one-on-one")
    rc, out, res = env.cli("read", "--skill", "task-creator", "--json")
    sl_ = (res or {}).get("slots", {}).get("team.members", {})
    check("v3.18.1 final review M10: CTX_RESULT's `shown` holds source ids alone — the cards say so in their own key",
          "картки" not in sl_.get("shown", []), sl_)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌")
sys.exit(1 if fails else 0)

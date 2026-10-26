#!/usr/bin/env python3
"""TC-ctx-3181-read — `ctx read`: team.members one line per person (since v3.18.1, plan R1, C8, C8a).

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

print("RESULT:", "GREEN ✅" if not fails else "RED ❌")
sys.exit(1 if fails else 0)

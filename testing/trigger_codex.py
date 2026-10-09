#!/usr/bin/env python3
"""Live trigger evals on Codex CLI (since v3.10.1; the v3.0.0 pilot runner, kept in the repository).

Installs the working tree (tracked files, via `git stash create`, which leaves the stash list alone) as a
uniquely named temporary marketplace, disables the user's installed Grow PM copies for these processes
only (`-c plugins.<id>.enabled=false`; config.toml keeps its entries), checks that the listing shows the
branch alone, then asks one `codex exec -s read-only` per phrase which skill it would load. Cleans up
the temporary marketplace, plugin and cache on any exit. Codex has no hooks, so no context digest runs.

  python3 testing/trigger_codex.py <out.json> [--groups T] [--ids T1,T4] [--repeat N] [--workers N]
          [--also-disable plugin@marketplace,...]

Expected-column grammar as in trigger_claude.py; "Claude: n/a" rows run here (migrated commands are
skills on Codex). A single-line prompt only — a multi-line argument hangs `codex exec`.
"""
import argparse, atexit, collections, fnmatch, json, os, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--ids", default=""); ap.add_argument("--groups", default="T")
ap.add_argument("--repeat", type=int, default=1); ap.add_argument("--workers", type=int, default=3)
ap.add_argument("--also-disable", default="", help="comma-separated plugin@marketplace keys to disable for these runs only")
a = ap.parse_args()
a.repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CODEX_DIR = os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex")
STAGE = tempfile.mkdtemp(prefix="cx-stage-"); NEUTRAL = tempfile.mkdtemp(prefix="cx-neutral-")
MKT = "grow-pm-trig-%d" % os.getpid()
OLD = ["grow-product-manager@grow-product-manager-plugins", "grow-product-manager@claude-cowork"]
EXTRA = [k for k in a.also_disable.split(",") if k]

def cx(args, **kw):
    return subprocess.run(["codex"] + args, cwd=NEUTRAL, stdin=subprocess.DEVNULL, capture_output=True, text=True, **kw)

def cleanup():
    cx(["plugin", "remove", "grow-product-manager@" + MKT]); cx(["plugin", "marketplace", "remove", MKT])
    for p in (os.path.join(CODEX_DIR, "plugins", "cache", MKT), STAGE, NEUTRAL):
        shutil.rmtree(p, ignore_errors=True)
atexit.register(cleanup)

# stage HEAD as a uniquely named marketplace (same as testing/host-smoke.sh)
ref = subprocess.run(["git", "-C", a.repo, "stash", "create"], capture_output=True, text=True).stdout.strip() or "HEAD"
print("staging", "working tree (stash create)" if ref != "HEAD" else "HEAD", flush=True)
arc = subprocess.run(["git", "-C", a.repo, "archive", ref], capture_output=True, check=True).stdout
subprocess.run(["tar", "-x", "-C", STAGE], input=arc, check=True)
mp = os.path.join(STAGE, ".claude-plugin", "marketplace.json")
d = json.load(open(mp, encoding="utf-8"), object_pairs_hook=collections.OrderedDict); d["name"] = MKT
json.dump(d, open(mp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
if cx(["plugin", "marketplace", "add", STAGE]).returncode or cx(["plugin", "add", "grow-product-manager@" + MKT]).returncode:
    sys.exit("install of the branch marketplace failed")

def listing(overrides):
    p = cx(overrides + ["debug", "prompt-input"], timeout=180)
    try:
        t = "".join(c.get("text", "") for m in json.loads(p.stdout) for c in m.get("content", []))
    except Exception:
        return None
    roots = {m.group(1): m.group(2) for m in re.finditer(r"- `(r\d+)` = `([^`]+)`", t)}
    new = old = 0
    for l in t.splitlines():
        m = re.match(r"- grow-product-manager:[a-z0-9-]+: .* \(file: (r\d+)/", l.strip())
        if m:
            if "/%s/" % MKT in roots.get(m.group(1), ""): new += 1
            else: old += 1
    return new, old

variants = [sum((["-c", "plugins.%s.enabled=false" % k] for k in OLD + EXTRA), []),
            sum((["-c", 'plugins."%s".enabled=false' % k] for k in OLD + EXTRA), [])]
OFF = None
for v in variants:
    r = listing(v)
    print("listing with", v[1], "→ new/old entries:", r, flush=True)
    if r and r[0] > 0 and r[1] == 0:
        OFF = v; break
if OFF is None:
    sys.exit("could not list the branch alone — not running (the user's installed copies would skew routing)")
if os.environ.get("DUMP_LISTING"):
    p = cx(OFF + ["debug", "prompt-input"], timeout=180)
    t = "".join(c.get("text", "") for m in json.loads(p.stdout) for c in m.get("content", []))
    lines = [l.strip() for l in t.splitlines() if re.match(r"- [a-z0-9-]+:[a-z0-9-]+: ", l.strip())]
    open(a.out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("listed skills:", len(lines)); sys.exit(0)

text = open(os.path.join(a.repo, "testing", "trigger-evals.md"), encoding="utf-8").read().split("## Results log")[0]
rows, group = [], None
for line in text.splitlines():
    m = re.match(r"### Group ([A-Z]+)\b", line)
    if m: group = m.group(1); continue
    m = re.match(r"\|\s*([A-Z]+\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", line)
    if m and group: rows.append(dict(group=group, id=m.group(1), phrase=m.group(2), expected=m.group(3)))
gs = set(filter(None, a.groups.split(","))); ids = set(filter(None, a.ids.split(",")))
rows = [r for r in rows if (r["id"] in ids) if ids] or [r for r in rows if r["group"] in gs]
for r in rows:
    raw = r["expected"].replace("`", "")
    r["alts"] = re.findall(r"accepted alternative:\s*([A-Za-z0-9*:_-]+)", raw)
    s = re.sub(r"\([^)]*\)", " ", re.split(r"\s+—\s+|;", raw)[0])
    r["allowed"] = sorted({re.findall(r"[a-z][a-z0-9-]+", part)[0] for part in re.split(r"\s+or\s+|/", s) if re.findall(r"[a-z][a-z0-9-]+", part)})

def one(r):
    prompt = ("Routing diagnostic only: do not run any command or tool and do not start the task. "
              "Which single skill from your available skills would you load for this user message: "
              "«%s» Reply with nothing but that skill's full name exactly as listed, or none if no skill fits." % r["phrase"])
    lm = tempfile.mktemp(prefix="cx-last-", dir=NEUTRAL)
    p = cx(["exec"] + OFF + ["-s", "read-only", "--skip-git-repo-check", "--ephemeral", "--color", "never", "-o", lm, prompt], timeout=300)
    reply = open(lm, encoding="utf-8").read().strip() if os.path.exists(lm) else "ERROR rc=%s %s" % (p.returncode, p.stderr[-200:])
    m = re.search(r"([a-z0-9-]+):([a-z0-9-]+)", reply)
    got = m.group(2) if m else ("none" if re.fullmatch(r"\W*none\W*", reply, re.I) else (re.findall(r"[a-z][a-z0-9]+(?:-[a-z0-9]+)+", reply) or [reply[:60]])[0])
    ns = m.group(1) if m else ""
    ok = got in r["allowed"] and (ns in ("", "grow-product-manager") or got == "none")
    ok = ok or any(fnmatch.fnmatch((ns + ":" + got) if ns else got, pat) for pat in r["alts"])
    err = reply.startswith("ERROR")          # usage limit, auth, timeout — not a routing answer
    return dict(id=r["id"], phrase=r["phrase"], allowed=r["allowed"], reply=reply[:200], got=got, ns=ns, ok=ok and not err, error=err)

res = []
with ThreadPoolExecutor(max_workers=a.workers) as ex:
    for x in ex.map(one, [r for r in rows for _ in range(a.repeat)]):
        res.append(x); print("⚠️" if x["error"] else ("✅" if x["ok"] else "❌"), x["id"], "→",
                             x["reply"][:120] if x["error"] else (x["ns"] + ":" if x["ns"] else "") + x["got"], flush=True)
json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("SUMMARY %d/%d | errors %d (not scored)" % (sum(x["ok"] for x in res), len(res) - sum(x["error"] for x in res), sum(x["error"] for x in res)))

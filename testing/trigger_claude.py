#!/usr/bin/env python3
"""Live trigger evals on Claude Code, isolated from the user's own context (since v3.10.1).

Stages the plugin — the working tree (default) or a git ref — into a temp folder, patches the staged
`scripts/session_start.py` with a test-only override (GROW_PM_TEST_CONTEXT; never shipped) so the
digest reads a fictional context instead of ~/.grow-pm, checks that it does, then asks one headless
`claude -p --plugin-dir <stage>` per phrase which skill it would load. No MCP servers load, write tools
are disallowed, HOME and CLAUDE_CONFIG_DIR are untouched.

  python3 testing/trigger_claude.py <out.json> [--ref WT|<git ref>] [--mode real|visible]
          [--groups A,B] [--ids T1,T4] [--repeat N] [--workers N]

Modes (references/host-profiles.md §7): `real` — the skill listing as this machine builds it (its
listing budget and usage history); `visible` — SLASH_COMMAND_TOOL_CHAR_BUDGET raised for these
processes only, so every description is shown. Run both: a miss only in `real` is a visibility problem,
a miss in both is a description problem.

Expected-column grammar (testing/trigger-evals.md): the skill(s) before ";" or " — " ("a or b", "a / b");
"accepted alternative: <glob>" matches the full reply (ns:name or bare name); "Claude: n/a" skips the
row here. Prints one line per call and a SUMMARY; writes every reply to <out.json>.
"""
import argparse, atexit, collections, fnmatch, json, os, re, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--ref", default="WT", help="WT = the working tree as it is on disk; else a git ref")
ap.add_argument("--mode", choices=["real", "visible"], default="real")
ap.add_argument("--groups", default=""); ap.add_argument("--ids", default="")
ap.add_argument("--repeat", type=int, default=1); ap.add_argument("--workers", type=int, default=4)
a = ap.parse_args()

# ---------------------------------------------------------------- rows
text = open(os.path.join(ROOT, "testing", "trigger-evals.md"), encoding="utf-8").read().split("## Results log")[0]
rows, group = [], None
for line in text.splitlines():
    m = re.match(r"### Group ([A-Z]+)\b", line)
    if m:
        group = m.group(1); continue
    m = re.match(r"\|\s*([A-Z]+\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", line)
    if m and group:
        rows.append(dict(group=group, id=m.group(1), phrase=m.group(2), expected=m.group(3)))
sel_g = set(filter(None, a.groups.split(","))); sel_i = set(filter(None, a.ids.split(",")))
rows = [r for r in rows if (not sel_g or r["group"] in sel_g) and (not sel_i or r["id"] in sel_i)]
for r in rows:
    s = r["expected"].replace("`", "")
    r["alts"] = re.findall(r"accepted alternative:\s*([A-Za-z0-9*:_-]+)", s)
    r["na"] = "Claude: n/a" in s
    head = re.sub(r"\([^)]*\)", " ", re.split(r"\s+—\s+|;", s)[0])
    r["allowed"] = sorted({re.findall(r"[a-z][a-z0-9-]+", p)[0] for p in re.split(r"\s+or\s+|/", head)
                           if re.findall(r"[a-z][a-z0-9-]+", p)})
skipped = [r["id"] for r in rows if r["na"]]
rows = [r for r in rows if not r["na"]]

# ---------------------------------------------------------------- stage
STAGE = tempfile.mkdtemp(prefix="gpm-stage-"); CTXD = tempfile.mkdtemp(prefix="gpm-ctx-"); NEUTRAL = tempfile.mkdtemp(prefix="gpm-run-")
atexit.register(lambda: [shutil.rmtree(p, ignore_errors=True) for p in (STAGE, CTXD, NEUTRAL)])
if a.ref == "WT":
    subprocess.run(["rsync", "-a", "--exclude", ".git", "--exclude", "__pycache__", "--exclude", "org-tokens.local",
                    "--exclude", ".claude", ROOT + "/", STAGE + "/"], check=True)
else:
    arc = subprocess.run(["git", "-C", ROOT, "archive", a.ref], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", STAGE], input=arc, check=True)
p = os.path.join(STAGE, "scripts", "session_start.py")
t = open(p, encoding="utf-8").read()
for old, new in [("    fixed = [\n", '    fixed = ([os.environ["GROW_PM_TEST_CONTEXT"]] if os.environ.get("GROW_PM_TEST_CONTEXT") else []) + [\n'),
                 ("        low = p.lower()\n", '        low = p.lower()\n        if os.environ.get("GROW_PM_TEST_CONTEXT") == p: return -1\n'),
                 ("if len(existing) > 1:", 'if len(existing) > 1 and not os.environ.get("GROW_PM_TEST_CONTEXT"):')]:
    if t.count(old) != 1:
        sys.exit("trigger_claude: the digest changed shape (%r) — update the test-only override" % old.strip())
    t = t.replace(old, new)
open(p, "w", encoding="utf-8").write(t)
CTX = os.path.join(CTXD, "local-context.md")
fx = open(os.path.join(ROOT, "testing", "fixtures", "context-connect", "existing-context.md"), encoding="utf-8").read()
open(CTX, "w", encoding="utf-8").write(fx.replace("| 1 | /Users/name/Vault |", "| 1 | %s/vault |" % CTXD))
ENV = dict(os.environ, GROW_PM_TEST_CONTEXT=CTX, GROW_PM_CONTEXT_PATH=CTX)
ENV.pop("CLAUDE_ENV_FILE", None); ENV.pop("SLASH_COMMAND_TOOL_CHAR_BUDGET", None)
probe = subprocess.run([sys.executable, p], input=json.dumps({"cwd": NEUTRAL}), capture_output=True, text=True, env=ENV).stdout
if ("FOUND at " + CTX) not in probe or os.path.join(os.path.expanduser("~"), ".grow-pm") in probe:
    sys.exit("trigger_claude: the staged digest does not read only the test context — not running")
if a.mode == "visible":
    ENV["SLASH_COMMAND_TOOL_CHAR_BUDGET"] = "400000"
CMD = ["claude", "-p", "--plugin-dir", STAGE, "--no-session-persistence", "--max-turns", "1", "--output-format", "json",
       "--mcp-config", '{"mcpServers":{}}', "--strict-mcp-config",
       "--disallowedTools", "Bash", "Write", "Edit", "MultiEdit", "NotebookEdit", "--"]

# ---------------------------------------------------------------- run
def ask(phrase):
    prompt = ("Routing diagnostic only: do not call any tool and do not start the task. "
              "Which single skill from your available skills would you load for this user message: "
              "«%s» Reply with nothing but that skill's full name exactly as listed, or none if no skill fits." % phrase)
    err = ""
    for attempt in range(3):
        try:
            r = subprocess.run(CMD + [prompt], cwd=NEUTRAL, env=ENV, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=300)
            d = json.loads(r.stdout)
            if d.get("is_error"):
                raise RuntimeError(str(d.get("result", ""))[:200])
            return d.get("result", "").strip(), sorted((d.get("modelUsage") or {}).keys())
        except Exception as e:
            err = str(e); time.sleep(15 * (attempt + 1))
    return "ERROR: " + err[:200], []

def one(r):
    reply, models = ask(r["phrase"])
    m = re.search(r"([a-z0-9-]+):([a-z0-9-]+)", reply)
    if m:
        ns, name = m.group(1), m.group(2)
    elif re.fullmatch(r"\W*none\W*", reply, re.I):
        ns, name = "", "none"
    else:   # a hyphenated skill name inside the reply, else a reply that is one bare word
        m = re.search(r"\b([a-z][a-z0-9]+(?:-[a-z0-9]+)+)\b", reply) or re.fullmatch(r"\W*([a-z][a-z0-9-]*)\W*", reply.strip())
        ns, name = "", (m.group(1) if m else reply[:60] or "?")
    full = ns + ":" + name if ns else name
    ok = name in r["allowed"] and (ns in ("", "grow-product-manager") or name == "none")
    alt = not ok and any(fnmatch.fnmatch(full, pat) for pat in r["alts"])
    return dict(id=r["id"], group=r["group"], phrase=r["phrase"], allowed=r["allowed"], alts=r["alts"], reply=reply[:200],
                got=full, ok=ok or alt, via_alt=alt, error=reply.startswith("ERROR"), models=models)

results = []
with ThreadPoolExecutor(max_workers=a.workers) as ex:
    for res in ex.map(one, [r for r in rows for _ in range(a.repeat)]):
        results.append(res)
        print("⚠️" if res["error"] else ("✅" if res["ok"] else "❌"), res["id"], "→", res["got"], "(alt)" if res["via_alt"] else "", flush=True)
json.dump(dict(mode=a.mode, ref=a.ref, skipped=skipped, results=results), open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
by = collections.OrderedDict()
for res in results:
    by.setdefault(res["group"], []).append(res["ok"])
print("SUMMARY", a.mode, " · ".join("%s %d/%d" % (g, sum(v), len(v)) for g, v in by.items()),
      "| total %d/%d | errors %d | skipped %s" % (sum(r["ok"] for r in results), len(results), sum(r["error"] for r in results), skipped))
print("MODELS", sorted({m for res in results for m in res["models"]}))

#!/usr/bin/env python3
"""TC-hook-350-role — the SessionStart digest prints the role layer line.

Builds three variants of local-context.example.md in a temp dir (enum role,
legacy free-text role, no role) and asserts the digest line
`user.role: <enum | legacy | absent> | level_home: <Lx | derived at Step 0i>`.
The free-text label must never reach the digest. Stdlib only; run from the repo root.
"""
import importlib.util, os, re, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("session_start", os.path.join(ROOT, "scripts", "session_start.py"))
ss = importlib.util.module_from_spec(spec); spec.loader.exec_module(ss)
example = open(os.path.join(ROOT, "local-context.example.md"), encoding="utf-8").read()

def variant(role_line, level_line):
    t = re.sub(r"^- \*\*Role:\*\*.*$", role_line, example, count=1, flags=re.M)
    return re.sub(r"^- \*\*Level home:\*\*.*$\n?", level_line, t, count=1, flags=re.M)

cases = [
    ("enum role", variant("- **Role:** head_of_product", "- **Level home:** L3\n"), "user.role: head_of_product | level_home: L3"),
    ("enum role + trailing comment", variant("- **Role:** cpo <!-- set by Step 4a -->", "- **Level home:** L4\n"), "user.role: cpo | level_home: L4"),
    ("legacy free text", variant("- **Role:** Senior PM, Area 1", ""), "user.role: legacy | level_home: derived at Step 0i"),
    ("no role", variant("", ""), "user.role: absent | level_home: derived at Step 0i"),
]
fails = 0
for name, text, expected in cases:
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text); path = f.name
    out = ss.digest(path, ss.parse(path), [], "test")
    os.unlink(path)
    ok = expected in out and "Area 1" not in out
    fails += not ok
    print(("✅" if ok else "❌"), name, "->", next((l.strip() for l in out.splitlines() if "user.role" in l), "(no role line)"))
print("RESULT:", "GREEN ✅" if not fails else "RED ❌")
sys.exit(1 if fails else 0)

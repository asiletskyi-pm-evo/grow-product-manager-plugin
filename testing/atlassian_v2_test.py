#!/usr/bin/env python3
"""TC-atl-4120 — the plugin speaks Atlassian MCP v2 (issue #96, since v4.12.0).

Atlassian switches v1 (https://mcp.atlassian.com/v1/mcp) off on 2027-03-01. This test
keeps the migration from drifting back:

1. `.mcp.json` declares the v2 endpoint for `atlassian`.
2. No skill, agent or skill reference names a tool that exists only on v1. The v1
   names live in one place, references/integration-strategy.md §1c (the v1 column),
   and in the write gate, which keeps them until v1 is switched off.
3. Every Confluence page read a skill names carries `detail: "full"` in the same
   line — on v2 the default is an excerpt of a few hundred characters.
4. The write gate still covers both the v2 and the v1 Confluence write names.

Stdlib only; run from the repo root.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V1_ONLY = ("getConfluencePage", "createConfluencePage", "updateConfluencePage",
           "searchConfluenceUsingCql", "getConfluenceSpaces", "getVisibleJiraProjects",
           "getJiraProjectIssueTypesMetadata", "createIssueLink", "getIssueLinkTypes")
SCOPES = ("skills", "agents", os.path.join(".codex", "agents"))

fails = 0
def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + repr(detail)[:400]))

mcp = json.load(open(os.path.join(ROOT, ".mcp.json")))["mcpServers"]
check("1 .mcp.json declares Atlassian MCP v2", mcp["atlassian"]["url"] == "https://mcp.atlassian.com/v2/mcp",
      mcp["atlassian"]["url"])

hits, reads = [], []
word = re.compile(r"\b(%s)\b" % "|".join(V1_ONLY))
for scope in SCOPES:
    for dirpath, _, files in os.walk(os.path.join(ROOT, scope)):
        for f in files:
            if not f.endswith((".md", ".toml", ".yaml", ".yml", ".json")):
                continue
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, ROOT)
            for n, line in enumerate(open(path, encoding="utf-8"), 1):
                if word.search(line):
                    hits.append("%s:%d %s" % (rel, n, word.search(line).group(1)))
                if "getConfluenceContent" in line and "detail" not in line and "snapshotToken" not in line:
                    reads.append("%s:%d" % (rel, n))
check("2 no skill, agent or skill reference names a v1-only Atlassian tool", not hits, hits)
check("3 every getConfluenceContent a skill names asks for detail: \"full\"", not reads, reads)

gate = open(os.path.join(ROOT, "scripts", "write_gate.py")).read()
hooks = json.load(open(os.path.join(ROOT, "hooks", "hooks.json")))["hooks"]["PreToolUse"]
matcher = [h["matcher"] for h in hooks if "Jira" in h["matcher"]][0]
for op in ("createConfluenceContent", "updateConfluenceContent", "createConfluencePage", "updateConfluencePage"):
    check("4 the write gate covers " + op, op in gate and re.search(matcher, "mcp__Atlassian_MCP__" + op) is not None)

strategy = open(os.path.join(ROOT, "references", "integration-strategy.md")).read()
check("5 integration-strategy.md §1c describes v2 as the declared server",
      "**1c. Atlassian MCP v2" in strategy and "2027-03-01" in strategy)

print("\n%s — %d failure(s)" % ("GREEN" if not fails else "RED", fails))
sys.exit(1 if fails else 0)

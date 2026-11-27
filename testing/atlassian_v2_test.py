#!/usr/bin/env python3
"""TC-atl-4110 — the plugin speaks Atlassian MCP v2 (issue #96, since v4.11.0).

Atlassian switches v1 (https://mcp.atlassian.com/v1/mcp) off on 2027-03-01. This test
keeps the migration from drifting back:

1. `.mcp.json` declares the v2 endpoint for `atlassian`.
2. No skill, agent, command or protocol names a tool that exists only on v1 (since
   v4.15.0 the plugin speaks v2 only). The v1 names live in two places: §1c of
   references/integration-strategy.md names `getConfluencePage` as the sign of a v1-only
   session, and the write gate keeps the v1 Confluence write names for a v1 server
   another plugin may bring.
3. Every Confluence page read a skill names carries `detail: "full"` in the same
   line — on v2 the default is an excerpt of a few hundred characters.
4. The write gate still covers both the v2 and the v1 Confluence write names.
6. (since v4.15.0) The write rows measured live on 2026-11-27 stay in §1c: the link direction,
   the replaced multi-value list, the reporter shape, the Team id, the upload operations;
   no protocol still says the MCP has no upload; a Blocks link in task-creator names the
   blocker as `inwardIssue`; scripts/jira_rows.py refuses a v1 response.

Stdlib only; run from the repo root.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V1_ONLY = ("getConfluencePage", "createConfluencePage", "updateConfluencePage",
           "searchConfluenceUsingCql", "getConfluenceSpaces", "getVisibleJiraProjects",
           "getJiraProjectIssueTypesMetadata", "createIssueLink", "getIssueLinkTypes")
SCOPES = ("skills", "agents", "commands", "references", os.path.join(".codex", "agents"))
ALLOWED = {os.path.join("references", "integration-strategy.md"): ("getConfluencePage",),   # the sign of a v1-only session
           os.path.join("commands", "setup.md"): ("createConfluencePage", "updateConfluencePage"),  # the gate's v1 names
           os.path.join("references", "artifact-style-gate.md"): ("createConfluencePage", "updateConfluencePage")}
GUIDE = re.compile(r'toolName\W{1,4}(createConfluencePage|updateConfluencePage)')  # the format guide's own key, not a tool
GATE_LINE = "The write gate covers"

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
                scan = GUIDE.sub("toolName", line)
                if rel.endswith("integration-strategy.md") and scan.startswith(GATE_LINE):
                    scan = ""
                for m in word.finditer(scan):
                    if m.group(1) not in ALLOWED.get(rel, ()):
                        hits.append("%s:%d %s" % (rel, n, m.group(1)))
                if (scope in ("skills", "agents") and "getConfluenceContent" in line and "detail" not in line
                        and "snapshotToken" not in line):
                    reads.append("%s:%d" % (rel, n))
check("2 no skill, agent, command or protocol names a v1-only Atlassian tool", not hits, hits)
check("3 every getConfluenceContent a skill names asks for detail: \"full\"", not reads, reads)

gate = open(os.path.join(ROOT, "scripts", "write_gate.py")).read()
hooks = json.load(open(os.path.join(ROOT, "hooks", "hooks.json")))["hooks"]["PreToolUse"]
matcher = [h["matcher"] for h in hooks if "Jira" in h["matcher"]][0]
for op in ("createConfluenceContent", "updateConfluenceContent", "createConfluencePage", "updateConfluencePage"):
    check("4 the write gate covers " + op, op in gate and re.search(matcher, "mcp__Atlassian_MCP__" + op) is not None)

strategy = open(os.path.join(ROOT, "references", "integration-strategy.md")).read()
check("5 integration-strategy.md §1c describes v2 as the declared server",
      "**1c. Atlassian MCP v2" in strategy and "2027-03-01" in strategy)

# 6. the writes, as measured on 2026-11-27
s1c = strategy.split("**1c.", 1)[1].split("\n### ", 1)[0] if "**1c." in strategy else ""
for needle, what in (("`inwardIssue` block `outwardIssue`", "the link direction"),
                     ("A multi-value field is replaced, not appended", "the replaced list"),
                     ('`fields.reporter` is `{\"accountId\": \"…\"}`', "the reporter shape"),
                     ("the Team field takes the team's id", "the Team field by id"),
                     ("`uploadAttachmentToJiraIssue`", "the Jira upload"),
                     ("`createConfluenceAttachment`", "the Confluence upload"),
                     ("`addLabelsToConfluenceContent`", "the page labels"),
                     ("appendNodeToEnd", "the append edit"),
                     ("never call a v1 tool", "v1 is never called")):
    check("6 §1c keeps " + what, needle in s1c, needle)
check("6 §1c has no v1 column any more", "v1 name (until" not in s1c, "")
vap = open(os.path.join(ROOT, "references", "visual-annotation-protocol.md"), encoding="utf-8").read()
check("6 Step V-6 no longer says the MCP has no upload, and never runs an uploadCommand as returned",
      "NO attachment-upload tools" not in vap and "never run as returned" in vap and "--config -" in vap, "")
tc = open(os.path.join(ROOT, "skills", "task-creator", "SKILL.md"), encoding="utf-8").read()
check("6 task-creator: a Blocks link names the blocker as inwardIssue", "`inwardIssue` = **the blocker**" in tc, "")
jr = open(os.path.join(ROOT, "scripts", "jira_rows.py"), encoding="utf-8").read()
check("6 jira_rows.py refuses a v1 response", "reads v2 only" in jr and 'shape = "v1"' not in jr, "")

print("\n%s — %d failure(s)" % ("GREEN" if not fails else "RED", fails))
sys.exit(1 if fails else 0)

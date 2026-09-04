#!/usr/bin/env bash
# validate-consistency.sh — repo consistency checks (run locally or in CI).
# Usage: bash testing/validate-consistency.sh
set -uo pipefail
cd "$(dirname "$0")/.."

FAIL=0
err() { echo "FAIL: $*"; FAIL=1; }
ok()  { echo "ok:   $*"; }

# --- 1. Plugin version consistency -------------------------------------------
PLUGIN_VER=$(sed -n 's/.*"version": "\([0-9.]*\)".*/\1/p' .claude-plugin/plugin.json | head -1)
MARKET_VER=$(sed -n 's/.*"version": "\([0-9.]*\)".*/\1/p' .claude-plugin/marketplace.json | head -1)
README_VER=$(sed -n 's/^\*\*Version:\*\* \([0-9.]*\).*/\1/p' README.md | head -1)
CHANGELOG_VER=$(sed -n 's/^## v\([0-9.]*\) .*/\1/p' CHANGELOG.md | head -1)

[ -n "$PLUGIN_VER" ] || err "plugin.json: no structured \"version\" field"
if [ -n "$PLUGIN_VER" ]; then
  [ "$PLUGIN_VER" = "$MARKET_VER" ]    || err "version mismatch: plugin.json=$PLUGIN_VER marketplace.json=$MARKET_VER"
  [ "$PLUGIN_VER" = "$README_VER" ]    || err "version mismatch: plugin.json=$PLUGIN_VER README header=$README_VER"
  [ "$PLUGIN_VER" = "$CHANGELOG_VER" ] || err "version mismatch: plugin.json=$PLUGIN_VER CHANGELOG top entry=$CHANGELOG_VER"
  [ $FAIL -eq 0 ] && ok "plugin version consistent everywhere: $PLUGIN_VER"
fi

# README footer must match header
FOOTER_COUNT=$(grep -cF "**Version:** $README_VER" README.md || true)
[ "$FOOTER_COUNT" -ge 2 ] || err "README footer version differs from header ($README_VER found $FOOTER_COUNT time(s), expected 2)"

# Version must be mentioned in manifest descriptions too (human-readable tail).
# -F matters: without it the dots are regex wildcards, so "v2x1x0" (or v2.10.0)
# satisfies a "v2.1.0" check and a desynced tail passes green.
grep -qF "v$PLUGIN_VER" .claude-plugin/plugin.json      || err "plugin.json description tail does not mention v$PLUGIN_VER"
grep -qF "v$PLUGIN_VER" .claude-plugin/marketplace.json || err "marketplace.json description tail does not mention v$PLUGIN_VER"

# --- 2. SKILL.md frontmatter --------------------------------------------------
for f in skills/*/SKILL.md; do
  head -6 "$f" | grep -q '^name: '        || err "$f: missing 'name:' in frontmatter"
  head -6 "$f" | grep -Eq '^version: [0-9]+\.[0-9]+\.[0-9]+$' || err "$f: missing or malformed 'version:' in frontmatter"
  head -6 "$f" | grep -q '^description: ' || err "$f: missing 'description:' in frontmatter"
done
ok "SKILL.md frontmatter: $(ls -d skills/*/ | wc -l | tr -d ' ') skills checked"

# --- 3. No leftover editorial artifacts ---------------------------------------
# Match artifacts at line start only (historical CHANGELOG entries may mention the pattern in prose).
if grep -qn '^<!-- Препенди' CHANGELOG.md; then err "CHANGELOG.md contains leftover editorial prepend-instructions"; fi
# v2.0.1: the example file shipped an author-directed note ("Додай цю секцію у ...").
# Editorial artifacts are a repo-wide class, not a CHANGELOG-only one.
for f in local-context.example.md README.md; do
  if grep -qnE '^<!--[[:space:]]*(Додай|Препенди|TODO|FIXME|Встав)' "$f"; then
    err "$f contains a leftover editorial note addressed to the author"
  fi
done

# --- 4. Reference paths mentioned in skills must exist ------------------------
# Convention: in a SKILL.md, `references/X.md` may mean the root references/ dir
# OR the skill's own references/ subfolder. Accept either.
MISSING=0
for f in skills/*/SKILL.md; do
  skill_dir=$(dirname "$f")
  while IFS= read -r ref; do
    [ -f "$ref" ] || [ -f "$skill_dir/$ref" ] || { err "broken reference path in $f: $ref"; MISSING=1; }
  done < <(grep -hoE '\breferences/[a-z0-9-]+\.md' "$f" | sort -u)
done
[ $MISSING -eq 0 ] && ok "all reference paths in SKILL.md files resolve (root or skill-local)"

# --- 5. Old jira-data-protocol location must not reappear ---------------------
if grep -rqn 'skills/team-ops-reporter/references/jira-data-protocol' skills/ references/ README.md 2>/dev/null; then
  err "stale path to skills/team-ops-reporter/references/jira-data-protocol.md found (moved to references/ in v1.26.1)"
fi

# --- 6. CI gate parity --------------------------------------------------------
# validate.yml promises in a comment that its gate matches release.yml's "exactly".
# A comment cannot enforce that: if they drift, a PR goes green, merges, and the
# auto-release fails on main with no earlier signal. Check it instead of promising it.
gate_of() {  # extract the validator commands each workflow actually runs
  grep -hoE '(bash testing/validate-consistency\.sh|python3 testing/skill_lint\.py|python3 testing/seeded_leak_test\.py)' "$1" | sort -u
}
V_GATE=$(gate_of .github/workflows/validate.yml)
R_GATE=$(gate_of .github/workflows/release.yml)
if [ "$V_GATE" != "$R_GATE" ]; then
  err "CI gate drift: validate.yml and release.yml do not run the same validators
  validate.yml: $(echo "$V_GATE" | tr '\n' ' ')
  release.yml:  $(echo "$R_GATE" | tr '\n' ' ')"
else
  ok "CI gate parity: validate.yml == release.yml ($(echo "$V_GATE" | wc -l | tr -d ' ') validators)"
fi
# The strict-YAML env flag must be set in both, or one of them silently degrades.
V_YAML=$(grep -c 'GROW_LINT_REQUIRE_YAML' .github/workflows/validate.yml || true)
R_YAML=$(grep -c 'GROW_LINT_REQUIRE_YAML' .github/workflows/release.yml || true)
if [ "$V_YAML" -eq 0 ] || [ "$R_YAML" -eq 0 ]; then
  err "GROW_LINT_REQUIRE_YAML must be set in BOTH workflows (validate=$V_YAML, release=$R_YAML) — otherwise the strict frontmatter parse degrades to a warning that gates nothing"
fi

# --- 7. Plugin agents (agents/*.md) ------------------------------------------
# v2.5.0: the plugin ships named subagents. Their frontmatter is what the host
# parses — a typo there means the agent silently never loads, and the skill
# that chains to it falls back to inline mode without anyone noticing.
if [ -d agents ]; then
  for f in agents/*.md; do
    base=$(basename "$f" .md)
    head -12 "$f" | grep -q "^name: $base$"       || err "$f: frontmatter 'name:' must equal the file name ($base)"
    head -12 "$f" | grep -q '^description: '      || err "$f: missing 'description:' in frontmatter"
    head -12 "$f" | grep -Eq '^(tools|disallowedTools): ' || err "$f: an agent must declare 'tools:' or 'disallowedTools:' — an unrestricted agent is a general-purpose one and does not belong here"
    head -12 "$f" | grep -Eq '^model: (sonnet|opus|haiku|inherit)$' || err "$f: 'model:' must be one of sonnet|opus|haiku|inherit"
  done
  ok "agents frontmatter: $(ls agents/*.md | wc -l | tr -d ' ') agents checked"
fi

# --- 8. Plugin commands (commands/*.md) --------------------------------------
# Every command is user-only by policy: they are service entry points, and the
# reason they exist is to stay OUT of the model's auto-routing (trigger-evals L).
if [ -d commands ]; then
  for f in commands/*.md; do
    head -8 "$f" | grep -q '^description: '                    || err "$f: missing 'description:' in frontmatter"
    head -8 "$f" | grep -q '^argument-hint: '                  || err "$f: missing 'argument-hint:' in frontmatter"
    head -8 "$f" | grep -q '^disable-model-invocation: true$'  || err "$f: commands are user-only — set 'disable-model-invocation: true'"
  done
  ok "commands frontmatter: $(ls commands/*.md | wc -l | tr -d ' ') commands checked"
fi

# --- 9. Declared connectors (.mcp.json) <-> integration-strategy table --------
# The host reads .mcp.json; the skills read the table in integration-strategy.md.
# If they drift, a skill looks for a namespace no connector provides (or a
# connector is declared that no skill knows how to call).
if [ -f .mcp.json ]; then
  MCP_KEYS=$(python3 -c 'import json,sys; d=json.load(open(".mcp.json")); print("\n".join(sorted(d.get("mcpServers", d).keys())))' 2>/dev/null) \
    || err ".mcp.json is not valid JSON"
  DOC_KEYS=$(sed -n '/^\*\*1a\. Declared connectors/,/^\*\*1b\./p' references/integration-strategy.md \
             | grep -v '^| `.mcp.json` key' | grep -oE '^\| `[^`]+`' | sed 's/^| `//; s/`$//' | sort)
  if [ "$MCP_KEYS" != "$DOC_KEYS" ]; then
    err "declared connectors drift: .mcp.json keys != integration-strategy.md 'Declared connectors' table
  .mcp.json: $(echo "$MCP_KEYS" | tr '\n' ' ')
  table:     $(echo "$DOC_KEYS" | tr '\n' ' ')"
  else
    ok "declared connectors: .mcp.json == integration-strategy.md ($(echo "$MCP_KEYS" | wc -l | tr -d ' ') servers)"
  fi
fi

# --- 11. Host hooks (hooks/hooks.json + scripts/) -----------------------------
# A hook that points at a missing or non-executable script fails silently at the
# host — the session simply never gets its digest. Check the wiring, not the prose.
N_HOOKS=0
if [ -f hooks/hooks.json ]; then
  HOOK_EVENTS=$(python3 -c '
import json,sys
d=json.load(open("hooks/hooks.json"))
ok={"SessionStart","SessionEnd","Stop","StopFailure","UserPromptSubmit","PreToolUse","PostToolUse","PostToolUseFailure","PermissionRequest","Notification","SubagentStart","SubagentStop","PreCompact","Setup"}
bad=[e for e in d.get("hooks",{}) if e not in ok]
if bad: print("BAD:"+",".join(bad)); sys.exit(0)
n=0
for e,groups in d["hooks"].items():
    for g in groups:
        for h in g.get("hooks",[]):
            n+=1
            if "timeout" not in h: print("NOTIMEOUT:"+e); sys.exit(0)
            if h.get("type")=="command":
                cmd=h["command"].replace("${CLAUDE_PLUGIN_ROOT}/","").strip("\"")
                import os
                if not os.path.isfile(cmd): print("MISSING:"+cmd); sys.exit(0)
                if not os.access(cmd, os.X_OK): print("NOEXEC:"+cmd); sys.exit(0)
print(n)') || err "hooks/hooks.json is not valid JSON"
  case "$HOOK_EVENTS" in
    BAD:*)       err "hooks/hooks.json: unknown event(s) ${HOOK_EVENTS#BAD:}" ;;
    NOTIMEOUT:*) err "hooks/hooks.json: hook without 'timeout' under ${HOOK_EVENTS#NOTIMEOUT:} — a hung hook blocks the session" ;;
    MISSING:*)   err "hooks/hooks.json: command script not found: ${HOOK_EVENTS#MISSING:}" ;;
    NOEXEC:*)    err "hooks/hooks.json: command script not executable (chmod +x): ${HOOK_EVENTS#NOEXEC:}" ;;
    *)           N_HOOKS=$HOOK_EVENTS; ok "hooks: $N_HOOKS hook(s) wired to existing executable scripts" ;;
  esac
  for f in scripts/*.py; do python3 -m py_compile "$f" 2>/dev/null || err "$f does not compile"; done
fi

# --- 10. Component counts in the three public descriptions -------------------
# "29 skills across five contours" lives in plugin.json, marketplace.json and
# README. With agents/commands/connectors the counts multiply; grep them all.
N_SKILLS=$(ls -d skills/*/ | wc -l | tr -d ' ')
N_AGENTS=$([ -d agents ] && ls agents/*.md 2>/dev/null | wc -l | tr -d ' ' || echo 0)
N_COMMANDS=$([ -d commands ] && ls commands/*.md 2>/dev/null | wc -l | tr -d ' ' || echo 0)
N_CONNECTORS=$([ -f .mcp.json ] && echo "$MCP_KEYS" | grep -c . || echo 0)
for f in .claude-plugin/plugin.json .claude-plugin/marketplace.json README.md; do
  grep -qF "$N_SKILLS skills"        "$f" || err "$f: does not state '$N_SKILLS skills' (actual count)"
  grep -qF "$N_AGENTS agents"        "$f" || err "$f: does not state '$N_AGENTS agents' (actual count)"
  grep -qF "$N_COMMANDS commands"    "$f" || err "$f: does not state '$N_COMMANDS commands' (actual count)"
  grep -qF "$N_CONNECTORS connectors" "$f" || err "$f: does not state '$N_CONNECTORS connectors' (actual count)"
  grep -qF "$N_HOOKS hooks"          "$f" || err "$f: does not state '$N_HOOKS hooks' (actual count)"
done
ok "component counts: $N_SKILLS skills, $N_AGENTS agents, $N_COMMANDS commands, $N_CONNECTORS connectors, $N_HOOKS hooks"

echo
if [ $FAIL -eq 0 ]; then echo "✅ All consistency checks passed (v$PLUGIN_VER)"; else echo "❌ Consistency checks failed"; exit 1; fi

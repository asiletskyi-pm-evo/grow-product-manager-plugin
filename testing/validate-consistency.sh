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

echo
if [ $FAIL -eq 0 ]; then echo "✅ All consistency checks passed (v$PLUGIN_VER)"; else echo "❌ Consistency checks failed"; exit 1; fi

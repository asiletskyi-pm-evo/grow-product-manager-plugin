#!/usr/bin/env bash
# host-smoke.sh — prove a plugin version still loads on BOTH hosts before it ships.
# Static validators are necessary but not sufficient: a manifest can be valid and
# still make Claude drop a component or Codex list zero plugins (v3.0.0 pilot).
# Runs locally (needs `claude` logged in and `codex` installed); CI cannot run it —
# release-manager Step 4 requires the summary line in the release PR body.
#
# Usage: bash testing/host-smoke.sh            (from the repo root)
#        SKIP_CLAUDE=1 / SKIP_CODEX=1 to skip a host that is not installed here.
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd); cd "$ROOT"
FAIL=0; err() { echo "FAIL: $*"; FAIL=1; }; ok() { echo "ok:   $*"; }
CLAUDE=${CLAUDE_BIN:-$(command -v claude || echo "$HOME/.local/bin/claude")}
N_SKILLS=$(ls -d skills/*/ | wc -l | tr -d ' '); N_CMDS=$(ls commands/*.md 2>/dev/null | wc -l | tr -d ' ')
VER=$(python3 -c 'import json;print(json.load(open(".claude-plugin/plugin.json"))["version"])')

echo "== static =="
bash testing/validate-consistency.sh >/dev/null 2>&1 && ok "validate-consistency.sh" || err "validate-consistency.sh is red — run it for details"
python3 testing/skill_lint.py 2>&1 | grep -q "RESULT: GREEN" && ok "skill_lint.py" || err "skill_lint.py is red — run it for details"

if [ "${SKIP_CLAUDE:-0}" != "1" ]; then
  echo "== Claude Code =="
  "$CLAUDE" plugin validate . 2>&1 | grep -q "Validation passed" && ok "claude plugin validate ." || err "claude plugin validate . failed"
  if "$CLAUDE" auth status 2>/dev/null | grep -q '"loggedIn": true'; then
    TMP=$(mktemp -d); OUT=$(cd "$TMP" && "$CLAUDE" -p --plugin-dir "$ROOT" --no-session-persistence --max-turns 1 --output-format json \
      "Diagnostic only, reply with exactly three lines and nothing else: SKILLS=<exact count of skills whose name starts with grow-product-manager:>; DIGEST=<yes|no — did a GROW_PM_SESSION block appear in your context>; VERSION=<the plugin version the digest states, or none>" </dev/null 2>/dev/null)
    RES=$(printf '%s' "$OUT" | python3 -c 'import sys,json
try: d=json.load(sys.stdin); print(d.get("result","").replace("\n"," ")); print("ERR="+str(d.get("is_error")))
except Exception: print("ERR=parse")')
    echo "      $RES" | head -1
    printf '%s' "$RES" | grep -q "ERR=False" || err "claude -p reported an error"
    S=$(printf '%s' "$RES" | grep -oE "SKILLS=[0-9]+" | grep -oE "[0-9]+" | head -1)
    [ -n "$S" ] && [ "$S" -ge "$N_SKILLS" ] && ok "Claude loads the plugin: $S skills reported (≥ $N_SKILLS on disk)" || err "Claude reported '$S' skills, expected ≥ $N_SKILLS"
    printf '%s' "$RES" | grep -q "DIGEST=yes" && ok "SessionStart hook ran (GROW_PM_SESSION digest present)" || err "no GROW_PM_SESSION digest — hooks did not run"
    printf '%s' "$RES" | grep -q "VERSION=$VER" && ok "digest states v$VER" || err "digest version differs from plugin.json ($VER)"
    rm -rf "$TMP"
  else
    err "claude is not logged in — run: $CLAUDE auth login (or SKIP_CLAUDE=1)"
  fi
fi

if [ "${SKIP_CODEX:-0}" != "1" ]; then
  echo "== Codex CLI =="
  if command -v codex >/dev/null; then
    STAGE=$(mktemp -d); MKT="grow-pm-smoke-$$"
    git archive HEAD | tar -x -C "$STAGE"
    python3 - "$STAGE" "$MKT" <<'PY'
import json,collections,pathlib,sys
p=pathlib.Path(sys.argv[1])/".claude-plugin/marketplace.json"; d=json.loads(p.read_text(),object_pairs_hook=collections.OrderedDict); d["name"]=sys.argv[2]; p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n")
PY
    codex plugin marketplace add "$STAGE" >/dev/null 2>&1 || err "codex plugin marketplace add failed"
    codex plugin add "grow-product-manager@$MKT" >/dev/null 2>&1 || err "codex plugin add failed (marketplace source form?)"
    ENTRIES=$(codex debug prompt-input 2>/dev/null | python3 -c "
import sys,json,re
d=json.load(sys.stdin); t=''.join(c.get('text','') for m in d for c in m.get('content',[]))
roots={m.group(1):m.group(2) for m in re.finditer(r'- \`(r\d+)\` = \`([^\`]+)\`', t)}
n=0
for l in t.splitlines():
    m=re.match(r'- grow-product-manager:[a-z0-9-]+: .* \(file: (r\d+)/', l.strip())
    if m and '/$MKT/' in roots.get(m.group(1),''): n+=1
print(n)")
    EXP=$((N_SKILLS + N_CMDS))
    [ "${ENTRIES:-0}" = "$EXP" ] && ok "Codex lists $ENTRIES entries ($N_SKILLS skills + $N_CMDS migrated commands)" || err "Codex lists ${ENTRIES:-0} entries, expected $EXP"
    C=$(ls -d "$HOME/.codex/plugins/cache/$MKT/grow-product-manager/"*/ 2>/dev/null | head -1)
    [ -n "$C" ] && [ -d "$C/references" ] && ok "Codex cache carries references/ (shared protocols reachable)" || err "Codex cache lacks references/"
    [ -n "$C" ] && [ -f "$C/.codex-plugin/plugin.json" ] && ok "Codex manifest present in cache" || err ".codex-plugin/plugin.json missing in the Codex cache"
    codex plugin remove "grow-product-manager@$MKT" >/dev/null 2>&1; codex plugin marketplace remove "$MKT" >/dev/null 2>&1; rm -rf "$HOME/.codex/plugins/cache/$MKT" "$STAGE"
  else
    err "codex is not installed here (SKIP_CODEX=1 to skip)"
  fi
fi

echo
if [ $FAIL -eq 0 ]; then echo "✅ host-smoke passed (v$VER: Claude + Codex)"; else echo "❌ host-smoke failed"; exit 1; fi

#!/bin/sh
# Grow PM — SessionStart hook wrapper. Fail-open by design: whatever goes wrong,
# exit 0 with no output, so a broken hook can never block a session.
# Delegates to session_start.py when python3 exists; otherwise emits a static note.
DIR="$(cd "$(dirname "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  python3 "$DIR/session_start.py" 2>/dev/null || exit 0
else
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"GROW_PM_SESSION: python3 not available in this environment — no context digest; skills follow references/local-context-protocol.md Step 0 unchanged."}}'
fi
exit 0

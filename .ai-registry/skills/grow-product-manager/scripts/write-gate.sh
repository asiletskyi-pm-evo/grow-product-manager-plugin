#!/bin/sh
# Grow PM — PreToolUse write gate wrapper. Fail-open: any error → exit 0, no output (= allow).
DIR="$(cd "$(dirname "$0")" && pwd)"
command -v python3 >/dev/null 2>&1 || exit 0
python3 "$DIR/write_gate.py" 2>/dev/null || exit 0
exit 0

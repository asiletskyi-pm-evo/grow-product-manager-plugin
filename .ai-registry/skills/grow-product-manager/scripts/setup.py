#!/usr/bin/env python3
"""Grow PM — /grow-product-manager:setup backend (since v2.6.0).

Usage: setup.py --show | --write-gate on|off | --write-gate pause <minutes>
Stores host-level toggles in the plugin data dir ($CLAUDE_PLUGIN_DATA/config.json,
falling back to ~/.grow-pm/plugin-data/config.json). Never touches local-context.md.
Prints one JSON object with the resulting state.

`--write-gate pause <minutes>` (1–240) writes `write_gate_pause_until`, a UTC time
that many minutes ahead: until then the write gate skips its Jira / Confluence
question, and asks again on its own afterwards (scripts/write_gate.py). It also sets
`write_gate: on`, so a gate that was off comes back when the pause ends.
`--write-gate on` and `--write-gate off` drop the pause.
"""
import json
import math
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from write_gate import MAX_PAUSE_MINUTES, PAUSE_KEY, pause_state  # noqa: E402 — one reading of the pause for both


def config_path():
    d = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(os.path.expanduser("~"), ".grow-pm", "plugin-data")
    return os.path.join(d, "config.json")


def load(p):
    try:
        with open(p, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def main(argv):
    p = config_path()
    cfg = load(p)
    changed = False
    if "--write-gate" in argv:
        i = argv.index("--write-gate")
        val = argv[i + 1].lower() if i + 1 < len(argv) else ""
        if val == "pause":
            try:
                minutes = int(argv[i + 2])
            except (IndexError, ValueError):
                minutes = 0
            if not 1 <= minutes <= MAX_PAUSE_MINUTES:
                print(json.dumps({"error": "--write-gate pause expects whole minutes, 1-%d" % MAX_PAUSE_MINUTES}))
                return 2
            until = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=minutes)
            cfg["write_gate"] = "on"
            cfg[PAUSE_KEY] = until.strftime("%Y-%m-%dT%H:%M:%SZ")
        elif val in ("on", "off"):
            cfg["write_gate"] = val
            cfg.pop(PAUSE_KEY, None)
        else:
            print(json.dumps({"error": "--write-gate expects on|off|pause <minutes>"})); return 2
        changed = True
    if changed:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    gate = cfg.get("write_gate", "on")
    pstate, until = pause_state(cfg)
    paused = pstate == "active" and str(gate).lower() not in ("off", "false", "0")
    left = math.ceil((until - datetime.now(timezone.utc)).total_seconds() / 60) if paused else None
    state = {
        "config_path": p,
        "write_gate": gate,
        "write_gate_pause_until": cfg.get(PAUSE_KEY),
        "write_gate_pause_state": pstate,          # none | active | expired | invalid (ignored: the gate asks)
        "write_gate_paused": paused,
        "write_gate_pause_minutes_left": left,
        "python3": shutil.which("python3") is not None,
        "hooks_env": {"CLAUDE_PLUGIN_DATA": bool(os.environ.get("CLAUDE_PLUGIN_DATA")),
                      "CLAUDE_ENV_FILE": bool(os.environ.get("CLAUDE_ENV_FILE")),
                      "GROW_PM_CONTEXT_PATH": os.environ.get("GROW_PM_CONTEXT_PATH", "")},
        "changed": changed,
    }
    print(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

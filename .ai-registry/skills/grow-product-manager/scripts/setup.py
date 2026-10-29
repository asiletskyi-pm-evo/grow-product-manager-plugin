#!/usr/bin/env python3
"""Grow PM — /grow-product-manager:setup backend (since v2.6.0).

Usage: setup.py --show | --write-gate on|off
Stores host-level toggles in the plugin data dir ($CLAUDE_PLUGIN_DATA/config.json,
falling back to ~/.grow-pm/plugin-data/config.json). Never touches local-context.md.
Prints one JSON object with the resulting state.
"""
import json
import os
import shutil
import sys


def config_path():
    d = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(os.path.expanduser("~"), ".grow-pm", "plugin-data")
    return os.path.join(d, "config.json")


def load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def main(argv):
    p = config_path()
    cfg = load(p)
    changed = False
    if "--write-gate" in argv:
        i = argv.index("--write-gate")
        val = argv[i + 1].lower() if i + 1 < len(argv) else ""
        if val not in ("on", "off"):
            print(json.dumps({"error": "--write-gate expects on|off"})); return 2
        cfg["write_gate"] = val
        changed = True
    if changed:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    state = {
        "config_path": p,
        "write_gate": cfg.get("write_gate", "on"),
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

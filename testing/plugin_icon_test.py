#!/usr/bin/env python3
"""TC-icon-4123 — validate-consistency.sh check 1, the Claude listing icon (since v4.12.3).

`.claude-plugin/plugin.json` `icon` names the picture Claude shows beside the plugin's name.
The documented rules: a square PNG or JPEG inside the plugin, 512 to 2048 px on a side,
under 2 MB. This test copies the tree, seeds one bad icon at a time, and asserts the
validator's icon line goes from `ok` to `FAIL`; two good icons (the repo's own PNG and a
square JPEG) must stay `ok`. Synthetic images only — nothing real enters the repository.

Usage: python3 testing/plugin_icon_test.py
"""
import json, os, shutil, struct, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FAIL_LINE = "FAIL: plugin.json icon"
OK_LINE = "ok:   plugin icon:"


def png(w, h, pad=0):
    """The PNG signature and an IHDR with this size — all the check reads — plus padding."""
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", w, h) + b"\x08\x06\x00\x00\x00" + b"\0" * (4 + pad)


def jpeg(w, h):
    """SOI, an APP0 segment to skip, then SOF0 with this size."""
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\0" + b"\x01\x01\0\0\x01\0\x01\0\0"
    sof0 = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, h, w, 1) + b"\x01\x11\0"
    return b"\xff\xd8" + app0 + sof0 + b"\xff\xd9"


# (name, icon path in plugin.json, file to write at that path or None, expected: "ok" | "fail")
CASES = [
    ("the repo's own logo", "./assets/logo.png", None, "ok"),
    ("a square JPEG of 1024", "./assets/seed-icon.jpg", jpeg(1024, 1024), "ok"),
    ("too small: 128 px", "./assets/seed-icon.png", png(128, 128), "fail"),
    ("too large: 4096 px", "./assets/seed-icon.png", png(4096, 4096), "fail"),
    ("not square: 1024×512", "./assets/seed-icon.png", png(1024, 512), "fail"),
    ("a JPEG not square", "./assets/seed-icon.jpg", jpeg(800, 600), "fail"),
    ("2 MB or more", "./assets/seed-icon.png", png(512, 512, pad=2 * 1024 * 1024), "fail"),
    ("not an image", "./README.md", None, "fail"),
    ("an SVG (not accepted)", "./assets/seed-icon.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>", "fail"),
    ("a missing file", "./assets/no-such-icon.png", None, "fail"),
    ("a path out of the plugin", "../outside.png", None, "fail"),
]


def run(tree):
    p = subprocess.run(["bash", "testing/validate-consistency.sh"], cwd=tree, capture_output=True, text=True)
    return p.stdout + p.stderr


def main():
    tree = tempfile.mkdtemp(prefix="grow-icon-")
    failures = 0
    try:
        shutil.copytree(ROOT, tree, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        manifest = os.path.join(tree, ".claude-plugin", "plugin.json")
        original = open(manifest, encoding="utf-8").read()
        # a file just outside the plugin, so the path case fails for leaving it, not for being missing
        open(os.path.join(os.path.dirname(tree), "outside.png"), "wb").write(png(512, 512))
        for name, icon, data, want in CASES:
            written = None
            try:
                m = json.loads(original)
                m["icon"] = icon
                open(manifest, "w", encoding="utf-8").write(json.dumps(m, indent=2, ensure_ascii=False) + "\n")
                if data is not None:
                    written = os.path.join(tree, os.path.normpath(icon))
                    open(written, "wb").write(data)
                out = run(tree)
                got = "fail" if FAIL_LINE in out else "ok" if OK_LINE in out else "silent"
                good = got == want
                failures += not good
                print(f"  {'✅' if good else '❌'} {name}: expected {want}, got {got}")
            finally:
                open(manifest, "w", encoding="utf-8").write(original)
                if written and os.path.isfile(written):
                    os.remove(written)
        # no icon at all: the check says nothing and fails nothing (the field is optional)
        m = json.loads(original); m.pop("icon", None)
        open(manifest, "w", encoding="utf-8").write(json.dumps(m, indent=2, ensure_ascii=False) + "\n")
        out = run(tree)
        good = FAIL_LINE not in out and OK_LINE not in out
        failures += not good
        print(f"  {'✅' if good else '❌'} no icon field: the check stays silent")
    finally:
        shutil.rmtree(tree, ignore_errors=True)
        outside = os.path.join(os.path.dirname(tree), "outside.png")
        if os.path.isfile(outside):
            os.remove(outside)
    print("RESULT:", "GREEN ✅" if not failures else f"RED ❌ ({failures} case(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Registry copy — the plugin as a subfolder a registry can sync.

Some internal registries sync a plugin from a folder `.ai-registry/skills/<name>/` of
the source repository, never from its root, and refuse it unless a Claude, a Codex and a
Cursor manifest sit there with the same name. The root of this repository IS the plugin,
so that folder is a generated copy: every file of the plugin as git has it staged, minus
the maintainer's own (EXCLUDE), plus a `.cursor-plugin/plugin.json` derived from
`.claude-plugin/plugin.json`.

  python3 testing/registry_copy.py               # rebuild the copy from the index
  python3 testing/registry_copy.py --check       # exit 1 if the copy differs from a rebuild
  python3 testing/registry_copy.py --manifests   # exit 1 if its manifests lag plugin.json

Built from the index, not the working tree: unstaged work in progress never reaches the
copy, and a file the release adds counts once it is staged. Rebuilt at release
(release-manager Step 3), never edited by hand — between releases the copy lags main on
purpose, so a registry sees releases only; validator check 22 runs --manifests. Real
files, never symlinks (a registry downloads an archive of the folder), and never
`export-ignore` it in .gitattributes (that archive would come back empty). Stdlib + git.
"""
import argparse, json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_ROOT = ".ai-registry/skills"
# The maintainer's tooling and history: tests, design notes, CI, local settings, the
# GitHub marketplace catalogue (a registry writes its own) and the copy itself.
EXCLUDE = ("testing/", "docs/", ".github/", ".claude/", ".ai-registry/",
           ".claude-plugin/marketplace.json", ".gitignore", ".gitattributes")
MANIFESTS = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json")


class CopyError(Exception):
    pass


def git(*args, binary=False):
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if p.returncode:
        raise CopyError("git %s: %s" % (" ".join(args), p.stderr.decode(errors="replace").strip()))
    return p.stdout if binary else p.stdout.decode()


def staged_files():
    """{path: (mode, sha)} of every staged file, from `git ls-files --stage`."""
    out = {}
    for rec in git("ls-files", "--stage", "-z").split("\0"):
        if not rec:
            continue
        meta, path = rec.split("\t", 1)
        mode, sha, _stage = meta.split()
        out[path] = (mode, sha)
    return out


def blob(sha):
    return git("cat-file", "blob", sha, binary=True)


def expected():
    """{relative path in the copy: (bytes, executable)} and the copy's folder."""
    files = staged_files()
    if ".claude-plugin/plugin.json" not in files:
        raise CopyError(".claude-plugin/plugin.json is not staged")
    claude = json.loads(blob(files[".claude-plugin/plugin.json"][1]))
    name = claude.get("name")
    if not name:
        raise CopyError(".claude-plugin/plugin.json has no name")
    if ".codex-plugin/plugin.json" not in files:
        raise CopyError(".codex-plugin/plugin.json is not staged — a registry refuses a copy without it")
    codex_name = json.loads(blob(files[".codex-plugin/plugin.json"][1])).get("name")
    if codex_name != name:
        raise CopyError(".codex-plugin/plugin.json names '%s', plugin.json '%s'" % (codex_name, name))
    tree = {}
    for path, (mode, sha) in sorted(files.items()):
        if path.startswith(EXCLUDE) or path in EXCLUDE:
            continue
        if mode == "120000":
            raise CopyError("%s is a symlink — a registry archive does not resolve it; commit a real file" % path)
        if mode == "160000":
            raise CopyError("%s is a submodule — a registry archive does not carry it" % path)
        tree[path] = (blob(sha), mode == "100755")
    if ".cursor-plugin/plugin.json" not in tree:
        cursor = {k: claude[k] for k in ("name", "version", "description", "author") if k in claude}
        cursor["skills"] = "./skills/"
        tree[".cursor-plugin/plugin.json"] = ((json.dumps(cursor, indent=2, ensure_ascii=False) + "\n").encode(), False)
    return os.path.join(REGISTRY_ROOT, name), tree


def on_disk(dest):
    """{relative path: (bytes, executable)} of the copy as it is."""
    found, base = {}, os.path.join(ROOT, dest)
    for dp, _, fs in os.walk(base):
        for f in fs:
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, base).replace(os.sep, "/")
            with open(full, "rb") as fh:
                found[rel] = (fh.read(), os.access(full, os.X_OK))
    return found


def build():
    dest, tree = expected()
    base = os.path.join(ROOT, dest)
    if os.path.isdir(base):
        shutil.rmtree(base)
    for rel, (data, exe) in tree.items():
        full = os.path.join(base, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(data)
        os.chmod(full, 0o755 if exe else 0o644)
    print("registry-copy: %s rebuilt from the index (%d files) — stage it: git add %s" % (dest, len(tree), dest))
    return 0


def check():
    dest, tree = expected()
    have = on_disk(dest)
    if not have:
        print("registry-copy: %s is missing — run python3 testing/registry_copy.py" % dest)
        return 1
    diffs = ["missing: %s" % p for p in sorted(set(tree) - set(have))] + \
            ["extra: %s" % p for p in sorted(set(have) - set(tree))] + \
            ["differs: %s" % p for p in sorted(set(tree) & set(have)) if tree[p] != have[p]]
    for d in diffs[:20]:
        print("  " + d)
    if len(diffs) > 20:
        print("  … and %d more" % (len(diffs) - 20))
    print("registry-copy: %s" % ("in sync with the index (%d files)" % len(tree) if not diffs else
          "%d difference(s) — rebuild it: python3 testing/registry_copy.py" % len(diffs)))
    return 1 if diffs else 0


def manifests():
    """The copy exists and its three manifests carry plugin.json's name and version (working tree)."""
    with open(os.path.join(ROOT, ".claude-plugin/plugin.json"), encoding="utf-8") as fh:
        root = json.load(fh)
    dest = os.path.join(REGISTRY_ROOT, root.get("name", ""))
    problems = []
    for m in MANIFESTS:
        path = os.path.join(ROOT, dest, m)
        if not os.path.isfile(path):
            problems.append("%s/%s is missing" % (dest, m))
            continue
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for key in ("name", "version"):
            if data.get(key) != root.get(key):
                problems.append("%s/%s: %s '%s', plugin.json '%s'" % (dest, m, key, data.get(key), root.get(key)))
    for p in problems:
        print(p)
    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="compare the copy with a rebuild from the index")
    mode.add_argument("--manifests", action="store_true", help="compare the copy's manifests with plugin.json")
    a = ap.parse_args()
    try:
        return check() if a.check else manifests() if a.manifests else build()
    except CopyError as e:
        print("registry-copy: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())

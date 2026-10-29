#!/usr/bin/env python3
"""TC-ctx-3240-copy-wrap — the `.md` wrappers of the manifest and the role model, unpacked in the copy (since v3.24.0).

The example kit `examples/provider-kit/zorg-core/` (fictional "Zorg") served as a notes server serves it — its `.md`
notes only, the frontmatter apart from the text (testing/mcp_fake.py, 127.0.0.1) — is copied by ctx_copy: the two
wrappers (`Core/_System/provider-manifest.md`, `access-bundles.md`) are unpacked beside them into the files they wrap,
byte for byte the kit's own; a rerun writes neither again; each fault of a wrapper (two blocks, an unknown name, a
wrong language tag, JSON that does not read) leaves its file out — one unpacked before is moved into `.removed/`, never
left stale — and the state says why (`wrapper_problem`); a wrapper gone from the server takes its file with it; the
kit folder itself is never written. Semantics: references/context-provider-protocol.md §9, §12.12. Stdlib only.
"""
import datetime, os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"
import ctx_common as cc  # noqa: E402
import ctx_copy as cp  # noqa: E402
import ctx_mcp as cm  # noqa: E402
import provider_bundle as pb  # noqa: E402
from mcp_fake import FakeMcp  # noqa: E402

cm.McpClient.BACKOFF = 0.0
KIT = os.path.join(ROOT, "examples", "provider-kit", "zorg-core")
NOW = datetime.datetime(2026, 10, 29, 9, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=2)))
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


def read(p):
    return open(p, encoding="utf-8", newline="").read()


def served(kit):
    """The kit as a notes server serves it: {"Zorg/<path>": {frontmatter, content}} for every `.md` note."""
    out = {}
    for rel in sorted(pb.walk(kit)):
        if not rel.endswith(".md"):
            continue
        text = read(os.path.join(kit, rel))
        front, body = pb.split_fm(text)
        try:
            fm = cc.read_yaml_subset(front) if front else {}
        except ValueError:
            fm, body = {}, text
        out["Zorg/" + rel.replace(os.sep, "/")] = {"frontmatter": fm, "content": body}
    return out


def snapshot(folder):
    out = {}
    for dp, dn, fn in os.walk(folder):
        for f in fn:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, folder)] = (os.stat(p).st_mtime_ns, open(p, "rb").read())
    return out


MAN, MODEL = "Core/_System/provider-manifest.md", "Core/_System/access-bundles.md"
kit_before = snapshot(KIT)
tmp = tempfile.mkdtemp(prefix="ctx-copy-wrap-")
try:
    home = os.path.join(tmp, "home")
    os.makedirs(os.path.join(home, ".grow-pm"))
    tree = served(KIT)
    check("the server serves the wrappers and no .yaml/.json", "Zorg/" + MAN in tree and "Zorg/" + MODEL in tree
          and not any(p.endswith((".yaml", ".json")) for p in tree))
    with FakeMcp(tree=tree) as fake:
        repo = {"id": "zorg-core", "endpoint": {"url": fake.url, "root": "Zorg/", "headers_env": ""}, "writable": []}
        res = cp.run(home, repo, NOW)
        folder = cp.copy_dir(home, "zorg-core")
        sysd = os.path.join(folder, "Core", "_System")
        check("complete", res["outcome"] == "complete", res)
        for name in ("provider-manifest.yaml", "access-bundles.json"):
            check("unpacked %s, byte for byte the kit's" % name,
                  os.path.isfile(os.path.join(sysd, name)) and read(os.path.join(sysd, name)) == read(os.path.join(KIT, "Core", "_System", name)))
        st = cp.load_state(folder)
        check("the state records what each wrapper unpacked", st.get("unpacked") == {
            "Core/_System/provider-manifest.yaml": MAN, "Core/_System/access-bundles.json": MODEL}, st.get("unpacked"))
        check("no wrapper problem", cp.wrapper_problem(st) == "", cp.wrapper_problem(st))
        m, why = pb.read_manifest(folder)
        check("the bundle builder reads the manifest from the copy", m is not None and m.s("id") == "zorg-core", why)
        before = snapshot(folder)
        cp.run(home, repo, NOW + datetime.timedelta(hours=2))
        after = snapshot(folder)
        check("a rerun writes no unpacked file again",
              all(after[k][0] == before[k][0] for k in ("Core/_System/provider-manifest.yaml", "Core/_System/access-bundles.json")))

        print("— the faults of a wrapper")
        good = dict(tree["Zorg/" + MODEL])
        faults = [
            ("two blocks", dict(good, content=good["content"] + "\n```json\n{}\n```\n"), "рівно один"),
            ("an unknown name", dict(good, frontmatter=dict(good["frontmatter"], file="secrets.json")), "невідоме ім'я"),
            ("a wrong language tag", dict(good, content=good["content"].replace("```json", "```yaml", 1)), "мовний тег"),
            ("JSON that does not read", dict(good, content=good["content"].replace('"version"', 'version', 1)), "JSON не читається"),
            ("a block never closed", dict(good, content=good["content"].rstrip().rstrip("`") + "\n"), "не закритий"),
        ]
        t = NOW + datetime.timedelta(days=1)
        for label, note, word in faults:
            fake.tree["Zorg/" + MODEL] = note
            t += datetime.timedelta(hours=1)
            cp.run(home, repo, t)
            st = cp.load_state(folder)
            check("%s: not unpacked, the reason kept" % label,
                  not os.path.exists(os.path.join(sysd, "access-bundles.json")) and word in cp.wrapper_problem(st)
                  and "access-bundles" in cp.wrapper_problem(st), cp.wrapper_problem(st))
            fake.tree["Zorg/" + MODEL] = good
            t += datetime.timedelta(hours=1)
            cp.run(home, repo, t)
        check("the stale file went to .removed/, never deleted",
              any(f == "access-bundles.json" for dp, dn, fn in os.walk(os.path.join(folder, ".removed")) for f in fn))
        check("a sound wrapper again: unpacked again, no problem",
              os.path.isfile(os.path.join(sysd, "access-bundles.json")) and cp.wrapper_problem(cp.load_state(folder)) == "")

        print("— a wrapper elsewhere, a wrapper that is no wrapper any more")
        fake.tree["Zorg/Archive/old-manifest.md"] = {"frontmatter": {"kind": "provider-file", "file": "provider-manifest.yaml"},
                                                    "content": "no block here\n"}
        t += datetime.timedelta(hours=1)
        cp.run(home, repo, t)
        st = cp.load_state(folder)
        m, _ = pb.read_manifest(folder)
        check("a broken wrapper outside the manifest's folder is no reason for the team block",
              cp.wrapper_problem(st) == "" and cp.wrapper_problem(st, m) == "" and "Archive/old-manifest.md" in st["wrappers"], st["wrappers"])
        del fake.tree["Zorg/Archive/old-manifest.md"]
        was = fake.tree["Zorg/" + MODEL]
        fake.tree["Zorg/" + MODEL] = dict(was, frontmatter=dict(was["frontmatter"], kind="note"))
        t += datetime.timedelta(hours=1)
        cp.run(home, repo, t)
        check("a wrapper whose note is no wrapper any more takes its file with it",
              not os.path.exists(os.path.join(sysd, "access-bundles.json"))
              and "Core/_System/access-bundles.json" not in cp.load_state(folder)["unpacked"])
        fake.tree["Zorg/" + MODEL] = was
        t += datetime.timedelta(hours=1)
        cp.run(home, repo, t)

        print("— a wrapper gone from the server")
        fake.hidden = {"Zorg/" + MAN}
        t += datetime.timedelta(days=1)
        cp.run(home, repo, t)
        t += datetime.timedelta(days=1)
        cp.run(home, repo, t)
        check("its file goes with it into .removed/", not os.path.exists(os.path.join(sysd, "provider-manifest.yaml"))
              and not os.path.exists(os.path.join(sysd, "provider-manifest.md")), os.listdir(sysd))
        st = cp.load_state(folder)
        check("a wrapper that is gone is no fault of a wrapper (the team block gives the advice)",
              cp.wrapper_problem(st) == "" and not st.get("unpacked", {}).get("Core/_System/provider-manifest.yaml"), st.get("unpacked"))
    check("the kit folder itself is never written", snapshot(KIT) == kit_before)

    print("— a server with no wrappers at all")
    plain = {k: v for k, v in served(KIT).items() if k not in ("Zorg/" + MAN, "Zorg/" + MODEL)}
    with FakeMcp(tree=plain) as fake:
        repo = {"id": "zorg-bare", "endpoint": {"url": fake.url, "root": "Zorg/", "headers_env": ""}, "writable": []}
        cp.run(home, repo, NOW)
        st = cp.load_state(cp.copy_dir(home, "zorg-bare"))
        check("nothing unpacked, no problem recorded (the reason is the absence)", not st.get("unpacked")
              and cp.wrapper_problem(st) == "", st.get("unpacked"))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)

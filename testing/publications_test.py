#!/usr/bin/env python3
"""TC-pub-4300 — scripts/publications.py, the record of where a result was published (v4.3.0,
references/artifact-publishing.md §5–§6).

Fictional «Zorg» notes (testing/fixtures/publications/) are copied into a temp folder and recorded into:
the first version, the next version of the same id, a second place, a place created anew (the old id to
`replaced`), a note without a frontmatter, a CRLF note, a YAML state file (the Focus Board), a note whose
own `published` property is something else, a `published` field that does not read, and the older
`published_to` / `confluence_page_id`. Everything outside the `published` field stays byte for byte. A link
with a user, a token, a signature or a pre-signed query is refused and never echoed — and a mutated script
that skips the link check is caught by the same check. `digest` equals `openssl dgst -sha256 -binary | base64`;
check 24's `check_schema` is clean on the repo and red on a copy whose vault-schema drifted. Secret-looking
values are assembled at run time. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/publications_test.py
"""
import base64, hashlib, json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "publications.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "publications")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def run(*args, script=SCRIPT):
    p = subprocess.run([sys.executable, script] + list(args), capture_output=True, text=True,
                       env={k: v for k, v in os.environ.items() if not k.startswith("GROW_PM_")})
    res = {}
    for line in p.stdout.splitlines():
        if line.startswith("PUB_RESULT "):
            res = json.loads(line[len("PUB_RESULT "):])
    return p.returncode, p.stdout + p.stderr, res


def read(p):
    with open(p, "rb") as f:
        return f.read()


def fm_end(b):
    """The offset of the closing `---` line of the first frontmatter of bytes `b`."""
    m = re.match(rb"---\r?\n", b)
    if not m:
        return None
    m2 = re.compile(rb"^---\r?$", re.M).search(b, m.end())
    return m2.start() if m2 else None


def rec(p, *extra, script=SCRIPT, surface="atlassian", kind="deck", id_="zorg-art-0001",
        url="https://your-org.atlassian.net/artifacts/zorg-art-0001", audience="private", at="2026-11-02T10:00"):
    return run("record", "--note", p, "--surface", surface, "--kind", kind, "--id", id_, "--url", url,
               "--audience", audience, "--at", at, *extra, script=script)


def find(p, *extra):
    rc, out, res = run("find", "--note", p, *extra)
    return rc, out, res, res.get("found") or []


TOKEN = "tok" + "en=" + "Zorg9" * 5                       # a query a never-store filter must refuse
SIG = "X-Amz-" + "Signature=" + "a1b2" * 16
USERINFO = "https://zorg-user:" + "Zorg-pass-" + "77" + "@zorg.example/deck"

d = tempfile.mkdtemp(prefix="publications-")
try:
    for f in os.listdir(FIX):
        shutil.copy(os.path.join(FIX, f), os.path.join(d, f))
    deck = os.path.join(d, "zorg-deck.md")
    orig = read(deck)

    # 1. nothing recorded yet
    rc, out, res, found = find(deck)
    check("1.1 a note without the field has no record", rc == 0 and found == [], out)

    # 2. the first version
    rc, out, res = rec(deck)
    after = read(deck)
    end0 = fm_end(orig)
    check("2.1 the first record is version 1", rc == 0 and res.get("recorded", {}).get("version") == 1, out)
    check("2.2 the record is inserted at the end of the frontmatter, everything else byte for byte",
          end0 is not None and after.startswith(orig[:end0]) and after.endswith(orig[end0:]), after[:600])
    rc, out, res, found = find(deck)
    check("2.3 find gives it back with every field",
          len(found) == 1 and found[0].get("surface") == "atlassian" and found[0].get("kind") == "deck" and
          found[0].get("id") == "zorg-art-0001" and found[0].get("version") == 1 and
          found[0].get("published") == "2026-11-02T10:00" and found[0].get("audience") == "private" and
          found[0].get("url") == "https://your-org.atlassian.net/artifacts/zorg-art-0001", found)
    check("2.4 the body's own fence and its «published:» line are untouched",
          after.count(b"published:\n  - surface: atlassian\n---") == 1, after[-200:])

    # 3. the next version of the same id
    one = read(deck)
    rc, out, res = rec(deck, at="2026-11-03T09:30")
    two = read(deck)
    rc2, out2, res2, found = find(deck, "--surface", "atlassian", "--kind", "deck")
    check("3.1 the same id again is version 2 of the same entry, at the new time",
          rc == 0 and res.get("recorded", {}).get("version") == 2 and len(found) == 1 and
          found[0]["version"] == 2 and found[0]["published"] == "2026-11-03T09:30", (out, found))
    s1, s2 = one.index(b"published:"), two.index(b"published:")
    check("3.2 only the block changes between versions", one[:s1] == two[:s2] and
          one[fm_end(one):] == two[fm_end(two):], two[:700])

    # 4. a second place
    rc, out, res = rec(deck, surface="artifact", id_="https://zorg.example/artifact/one",
                       url="https://zorg.example/artifact/one", at="2026-11-03T09:31")
    rc2, out2, res2, found = find(deck)
    check("4.1 a second place is its own entry, version 1", rc == 0 and len(found) == 2 and
          [e["surface"] for e in found] == ["atlassian", "artifact"] and found[1]["version"] == 1, found)
    rc2, out2, res2, only = find(deck, "--surface", "artifact")
    check("4.2 find --surface filters", [e["surface"] for e in only] == ["artifact"], only)

    # 5. a place created anew
    rc, out, res = rec(deck, id_="zorg-art-0002", url="https://your-org.atlassian.net/artifacts/zorg-art-0002",
                       audience="shared", at="2026-11-04T08:00")
    rc2, out2, res2, found = find(deck, "--surface", "atlassian")
    check("5.1 another id for the same place: version 1, the old id in replaced, the new audience",
          rc == 0 and len(found) == 1 and found[0]["id"] == "zorg-art-0002" and found[0]["version"] == 1 and
          found[0].get("replaced") == ["zorg-art-0001"] and found[0]["audience"] == "shared", found)
    rc, out, res = rec(deck, id_="zorg-art-0003", url="https://your-org.atlassian.net/artifacts/zorg-art-0003")
    rc2, out2, res2, found = find(deck, "--surface", "atlassian")
    check("5.2 replaced keeps every earlier id, oldest first",
          found and found[0].get("replaced") == ["zorg-art-0001", "zorg-art-0002"], found)

    # 6. refusals — never written, never echoed
    snap = read(deck)
    for name, kw in (("a token in the query", {"url": "https://zorg.example/deck?" + TOKEN}),
                     ("a user and a password", {"url": USERINFO}),
                     ("a pre-signed query", {"url": "https://zorg-upload.example/put?" + SIG}),
                     ("a signature parameter", {"url": "https://zorg.example/d?sig=" + "Zz9" * 9}),
                     ("not a web link", {"url": "file:///Users/zorg/deck.html"}),
                     ("a key in the id", {"id_": "sk-" + "ant-" + "Zorg" * 6})):
        rc, out, res = rec(deck, **kw)
        val = list(kw.values())[0]
        check("6 %s is refused, the note unchanged, the value never echoed" % name,
              rc == 2 and read(deck) == snap and val not in out and res.get("error"), out)
    for name, args in (("an audience outside the list", {"audience": "everyone"}),
                       ("a lower-case space key", {"audience": "space:zorg"}),
                       ("a surface that is no slug", {"surface": "Atlassian Artifacts"}),
                       ("a kind outside the list", {"kind": "slides"})):
        rc, out, res = rec(deck, **args)
        check("6 %s is exit 2, the note unchanged" % name, rc == 2 and read(deck) == snap, out)
    rc, out, res = rec(deck, audience="space:SPACE", surface="confluence", kind="page", id_="7654321",
                       url="https://your-org.atlassian.net/wiki/spaces/SPACE/pages/7654321")
    check("6.9 a space audience is kept as it is", rc == 0 and
          [e for e in find(deck)[3] if e["surface"] == "confluence"][0]["audience"] == "space:SPACE", out)
    rc, out, res = rec(os.path.join(d, "missing.md"))
    check("6.10 a note that is not there is exit 2", rc == 2 and not os.path.exists(os.path.join(d, "missing.md")), out)

    # 7. a note without a frontmatter (a deck's outline companion)
    outline = os.path.join(d, "zorg-outline.md")
    o0 = read(outline)
    rc, out, res = rec(outline)
    o1 = read(outline)
    check("7.1 a frontmatter is added in front, the text after it byte for byte",
          rc == 0 and o1.startswith(b"---\npublished:\n") and o1.endswith(b"---\n" + o0), o1[:300])
    check("7.2 and it reads back", find(outline)[3][0]["version"] == 1 if find(outline)[3] else False, find(outline))

    # 8. CRLF
    crlf = os.path.join(d, "zorg-crlf.md")
    with open(crlf, "wb") as f:
        f.write(orig.replace(b"\n", b"\r\n"))
    c0 = read(crlf)
    rc, out, res = rec(crlf)
    c1 = read(crlf)
    e0 = fm_end(c0)
    block = c1[e0:fm_end(c1)]
    check("8.1 a CRLF note keeps CRLF in the block and every other byte",
          rc == 0 and c1.startswith(c0[:e0]) and c1.endswith(c0[e0:]) and block and
          b"\n" not in block.replace(b"\r\n", b""), block)

    # 9. a YAML state file (the Focus Board)
    board = os.path.join(d, "zorg-board.yaml")
    b0 = read(board)
    rc, out, res = rec(board, surface="artifact", kind="dashboard", id_="https://zorg.example/artifact/board",
                       url="https://zorg.example/artifact/board")
    b1 = read(board)
    rc2, out2, res2 = rec(board, surface="artifact", kind="dashboard", id_="https://zorg.example/artifact/board",
                          url="https://zorg.example/artifact/board", at="2026-11-05T07:00")
    rc3, out3, res3, found = find(board)
    check("9.1 a YAML state file gets the field at its end, its other keys byte for byte",
          rc == 0 and b1.startswith(b0) and b1[len(b0):].startswith(b"published:\n"), b1)
    check("9.2 its next refresh is version 2 of the same entry", rc2 == 0 and len(found) == 1 and
          found[0]["version"] == 2, found)

    # 10. a note whose own `published` is something else
    foreign = os.path.join(d, "zorg-foreign.md")
    f0 = read(foreign)
    rc, out, res, found = find(foreign)
    check("10.1 find: no record, and it says the field is the note's own", rc == 0 and found == [] and
          res.get("foreign") is True, out)
    rc, out, res = rec(foreign)
    check("10.2 record refuses to write over it", rc == 2 and read(foreign) == f0, out)

    # 11. a `published` field that does not read
    broken = os.path.join(d, "zorg-broken.md")
    with open(broken, "w", encoding="utf-8") as f:
        f.write('---\ntitle: "Zorg"\npublished:\n  - surface: atlassian\n    kind: [deck\n---\nbody\n')
    k0 = read(broken)
    rc, out, res = rec(broken)
    check("11.1 an unreadable field is never overwritten", rc == 2 and read(broken) == k0 and res.get("error"), out)
    rc, out, res, found = find(broken)
    check("11.2 find says it does not read", rc == 2 and res.get("error"), out)

    # 12. the older fields
    legacy = os.path.join(d, "zorg-legacy.md")
    l0 = read(legacy)
    rc, out, res, found = find(legacy)
    check("12.1 published_to + confluence_page_id read as a confluence record of version 1",
          rc == 0 and len(found) == 1 and found[0]["surface"] == "confluence" and found[0]["id"] == "1234567" and
          found[0]["version"] == 1 and found[0].get("legacy") is True, found)
    rc, out, res = rec(legacy, surface="confluence", kind="page", id_="1234567",
                       url="https://your-org.atlassian.net/wiki/spaces/SPACE/pages/1234567/Zorg+Sprint",
                       audience="space:SPACE")
    l1 = read(legacy)
    check("12.2 the same page again is version 2; the older fields stay as they were",
          rc == 0 and res.get("recorded", {}).get("version") == 2 and b"published_to:" in l1 and
          b'confluence_page_id: "1234567"' in l1 and l1.startswith(l0[:fm_end(l0)]), l1)
    rc, out, res, found = find(legacy)
    check("12.3 then find gives the record, not the older fields twice", len(found) == 1 and
          found[0]["version"] == 2 and not found[0].get("legacy"), found)

    # 13. digest
    blob = os.path.join(d, "zorg-deck.html")
    with open(blob, "wb") as f:
        f.write(("<!doctype html><title>Zorg</title>" + "slide " * 4000).encode())
    rc, out, res = run("digest", blob)
    want = base64.b64encode(hashlib.sha256(read(blob)).digest()).decode()
    check("13.1 digest: the byte length and the base64 SHA-256", rc == 0 and res.get("bytes") == len(read(blob)) and
          res.get("sha256") == want, out)
    if shutil.which("openssl"):
        o = subprocess.run("openssl dgst -sha256 -binary %s | base64" % blob, shell=True, capture_output=True,
                           text=True).stdout.strip()
        check("13.2 the same as openssl dgst -sha256 -binary | base64", o == res.get("sha256"), (o, res))
    rc, out, res = run("digest", os.path.join(d, "none.html"))
    check("13.3 digest of a missing file is exit 2", rc == 2, out)

    # 14. a mutated script that skips the link check is caught by the same check
    src = open(SCRIPT, encoding="utf-8").read()
    mut = os.path.join(d, "publications_mutated.py")
    mutated = src.replace("def link_problem(url):", "def link_problem(url):\n    return None\n\ndef _orig_link_problem(url):", 1)
    with open(mut, "w", encoding="utf-8") as f:
        f.write(mutated)
    for dep in ("ctx_never.py", "ctx_common.py"):
        shutil.copy(os.path.join(ROOT, "scripts", dep), os.path.join(d, dep))
    m_note = os.path.join(d, "zorg-mut.md")
    shutil.copy(os.path.join(FIX, "zorg-deck.md"), m_note)
    rc, out, res = rec(m_note, url="https://zorg-upload.example/put?" + SIG, script=mut)
    rc_real, out_real, _ = rec(os.path.join(d, "zorg-legacy.md"), url="https://zorg-upload.example/put?" + SIG)
    check("14.1 the mutation is real (it writes the pre-signed link)", mutated != src and rc == 0, out)
    check("14.2 the refusal check of section 6 tells them apart: the real script refuses what the mutant writes",
          rc_real == 2 and rc == 0, (rc_real, rc))

    # 16. the review of tasks 1–4 (B1, B2, I1–I5, M1–M4)
    n16 = os.path.join(d, "n16.md")
    def fresh(text=None):
        with open(n16, "wb") as f:
            f.write(text if text is not None else read(os.path.join(FIX, "zorg-deck.md")))
    S3 = "https://zorg-upload.example/put?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ZORGKEY%2F20261102&X-Amz-" + "Signature=" + "a1b2" * 16
    GCS = "https://zorg.example/d?X-Goog-" + "Signature=" + "a1b2" * 16
    FRAG = "https://zorg.example/d#access_" + "token=" + "Zorg9" * 4
    for name, kw in (("B1 an S3 pre-signed link as the id", {"id_": S3}), ("B1 a GCS signed link as the id", {"id_": GCS}),
                     ("B1 a fragment token as the id", {"id_": FRAG}),
                     ("I1 a fragment token in the link", {"url": FRAG}),
                     ("I1 a ;-separated query", {"url": "https://zorg.example/d?a=1;sig=" + "Zz9" * 8}),
                     ("I1 a ;jsessionid path parameter", {"url": "https://zorg.example/d;jsessionid=" + "ABC123" * 4}),
                     ("I1 a double-encoded parameter name", {"url": "https://zorg.example/d?x%2561mz-signature%3D" + "a1" * 10}),
                     ("I1 an encoded user and password", {"url": "https://zorg%3Apw%40zorg.example/d"})):
        fresh()
        before = read(n16)
        val = list(kw.values())[0]
        rc, out, res = rec(n16, **kw)
        check("16 %s is refused, never echoed" % name, rc == 2 and read(n16) == before and val not in out, out)
    fresh()
    rec(n16, at="2026-11-02T10:00:00Z")
    rc, out, res = run("share", "--note", n16, "--surface", "atlassian", "--kind", "deck", "--audience", "shared")
    e = find(n16)[3][0]
    check("16 I2 share changes the audience only — no new version, no new time",
          rc == 0 and e["audience"] == "shared" and e["version"] == 1 and e["published"] == "2026-11-02T10:00:00Z", (out, e))
    rc, out, res = run("share", "--note", n16, "--surface", "artifact", "--kind", "deck", "--audience", "shared")
    check("16 I2 share of a place that is not recorded is exit 2", rc == 2, out)
    fresh()
    rec(n16)
    e = find(n16)[3][0]
    rc, out, res = run("record", "--note", n16, "--surface", "atlassian", "--kind", "deck", "--id", "zorg-art-0001",
                       "--url", "https://your-org.atlassian.net/artifacts/zorg-art-0001", "--audience", "private")
    check("16 I3 a version's time is UTC with seconds, and --at takes an offset",
          rc == 0 and re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", res["recorded"]["published"]) and
          rec(n16, at="2026-11-02T10:00+02:00")[0] == 0, res)
    rc, out, res = rec(n16, "--remote-version", "7")
    check("16 I3 the place's own version is kept as remote_version", find(n16)[3][0].get("remote_version") == "7", find(n16))
    tail = "---\ntitle: \"Zorg\"\npublished:\n  - surface: atlassian\n    kind: deck\n    id: \"a\"\n    url: \"https://your-org.atlassian.net/a\"\n    version: 1\n\n# the author's comment\n\nnext: 1\n\n---\nbody\n"
    fresh(tail.encode())
    rec(n16, id_="a", url="https://your-org.atlassian.net/a")
    after = read(n16).decode()
    check("16 I4 blank lines and a column-0 comment after the block, and a blank line before the fence, stay",
          after.endswith("\n\n# the author's comment\n\nnext: 1\n\n---\nbody\n") and "version: 2" in after, after)
    fresh(b'---\ntitle: "Zorg"\nconfluence_url: "https://your-org.atlassian.net/wiki/spaces/SPACE/pages/555/Zorg"\n---\nb\n')
    f1 = find(n16)[3]
    fresh(b'---\ntitle: "Zorg"\npublished_to: "https://www.notion.so/zorg/Plan-0123"\n---\nb\n')
    f2 = find(n16)[3]
    fresh(b'---\ntitle: "Zorg"\npublished_to: "https://your-org.atlassian.net/wiki/spaces/SPACE/pages/777/Zorg"\n---\nb\n')
    rc, out, res = rec(n16, surface="confluence", kind="page", id_="777",
                       url="https://your-org.atlassian.net/wiki/spaces/SPACE/pages/777/Zorg", audience="space:SPACE")
    check("16 I5 confluence_url is read; a Notion published_to is not Confluence; a page id from the link continues at 2",
          f1 and f1[0]["id"] == "555" and f2 == [] and res.get("recorded", {}).get("version") == 2, (f1, f2, res))
    prev = os.path.join(d, "prev.md")
    shutil.copy(os.path.join(FIX, "zorg-deck.md"), prev)
    rec(prev, at="2026-11-01T10:00:00Z")
    rec(prev, surface="docs", kind="document", id_="doc-1", url="https://zorg.example/doc/doc-1")
    fresh()
    rc, out, res = rec(n16, "--carry", prev, at="2026-11-03T10:00:00Z")
    got = find(n16)[3]
    check("16 B2 --carry starts a new note from the previous note's record: version 2, the other place carried",
          rc == 0 and res.get("carried") == 2 and [e["version"] for e in got] == [2, 1] and
          read(prev) != read(n16), (out, got))
    old_r = os.path.join(d, "old-report.md")
    with open(old_r, "w", encoding="utf-8") as f:
        f.write('---\ntitle: "Zorg Sprint 42"\nconfluence_url: "https://your-org.atlassian.net/wiki/spaces/SPACE/pages/4242/Zorg"\n---\nb\n')
    fresh()
    rec(n16, "--carry", old_r, surface="docs", kind="document", id_="doc-42", url="https://zorg.example/doc/doc-42")
    rc, out, res = rec(n16, surface="confluence", kind="page", id_="4242",
                       url="https://your-org.atlassian.net/wiki/spaces/SPACE/pages/4242/Zorg", audience="space:SPACE")
    check("16 B2 a previous note's older Confluence fields are carried as a record: its page goes on at version 2",
          rc == 0 and res["recorded"]["version"] == 2 and
          [e for e in find(n16)[3] if e["surface"] == "confluence"][0]["version"] == 2, (out, find(n16)[3]))
    fresh()
    before = read(n16)
    rc, out, res = rec(n16, "--carry", os.path.join(d, "nothere.md"))
    check("16 B2 a new note whose previous note is not there is refused — the counter never restarts silently",
          rc == 2 and read(n16) == before, out)
    fresh()
    rec(n16, surface="artifact", id_="https://zorg-a.example/a/1", url="https://zorg-a.example/a/1")
    rec(n16, surface="artifact", id_="https://zorg-b.example/s/9", url="https://zorg-b.example/s/9")
    got = find(n16, "--surface", "artifact")[3]
    check("16 I6 the same surface and kind on two hosts are two places, nothing replaced",
          len(got) == 2 and not any(e.get("replaced") for e in got), got)
    fresh(b'---\ntitle: "Zorg"\npublished:\n  - draft\n  - web\n---\nb\n')
    check("16 M1 a list of words is the note's own property", find(n16)[2].get("foreign") is True and rec(n16)[0] == 2, find(n16))
    fresh(b'---\npublished:\n  - surface: atlassian\n    kind: deck\n    id: 123\n    url: "https://your-org.atlassian.net/x"\n    version: 2.0\n    replaced: "old-1"\n    note: "keep me"\n---\nb\n')
    e = find(n16)[3]
    rc, out, res = rec(n16, id_="123", url="https://your-org.atlassian.net/x")
    after = read(n16).decode()
    check("16 M2 a hand-edited entry: version 2.0 → 3, a scalar replaced kept whole, an id as a string, a field someone added kept",
          e and e[0]["id"] == "123" and rc == 0 and res["recorded"]["version"] == 3 and 'replaced: ["old-1"]' in after
          and 'note: "keep me"' in after, (e, out, after))
    fresh("\ufeff# Zorg outline\n".encode())
    rec(n16)
    b = read(n16)
    check("16 M3 a BOM stays first when a frontmatter is added", b.startswith("\ufeff---\n".encode()) and
          b.endswith("---\n# Zorg outline\n".encode()), b[:40])
    fresh()
    os.chmod(n16, 0o600)
    link = os.path.join(d, "n16-link.md")
    os.symlink(n16, link)
    rec(link)
    check("16 M4 the mode stays, a linked note is written where it lives and the link stays a link",
          (os.stat(n16).st_mode & 0o777) == 0o600 and os.path.islink(link) and b"published:" in read(n16), oct(os.stat(n16).st_mode))

    # 17. the review of tasks 5–7 — one record per result (the key file), the note a mirror
    st = os.path.join(d, "store17")
    K = ["--key", "design-bridge/zorg/new-delivery-feature", "--store", st]
    a, b, c = (os.path.join(d, "run-%s.md" % x) for x in "abc")
    for x in (a, b, c):
        shutil.copy(os.path.join(FIX, "zorg-deck.md"), x)
    rc, out, res = rec(a, *K)
    keyf = os.path.join(st, "design-bridge", "zorg", "new-delivery-feature.yaml")
    check("17.1 B1 the first publication goes to the key file and is mirrored into the note",
          rc == 0 and os.path.isfile(keyf) and res.get("mirror") == "written" and b"published:" in read(a), out)
    b0 = read(b)                                    # run 2: «лише файл» — a note saved, nothing recorded
    rc, out, res = rec(c, *K)
    check("17.2 B1 publish → «лише файл» → publish: the third run finds the key file — version 2 of the same id",
          rc == 0 and res["recorded"]["version"] == 2 and res["recorded"]["id"] == "zorg-art-0001" and read(b) == b0, out)
    rc, out, res = run("find", *K)
    check("17.3 find by key alone, no note at all (I1: no vault, the record still lives)",
          rc == 0 and res.get("source") == "key" and res["found"][0]["version"] == 2, out)
    rc, out, res = rec(os.path.join(d, "nothing.md"), *K)
    check("17.4 a note that is not there with a key: the key file is the record (the mirror is said skipped)",
          rc == 0 and res.get("mirror", "").startswith("skipped") and res["recorded"]["version"] == 3, out)
    foreign = os.path.join(d, "foreign17.md")
    shutil.copy(os.path.join(FIX, "zorg-foreign.md"), foreign)
    f0 = read(foreign)
    rc, out, res = rec(foreign, *K)
    check("17.5 a note whose own published is something else: the key file records, the note untouched",
          rc == 0 and read(foreign) == f0 and res.get("mirror", "").startswith("skipped"), out)
    # B2: the deck note that already holds a record (the real case of acceptance item 2) is read when no key file exists yet
    st2 = os.path.join(d, "store17b")
    deckn = os.path.join(d, "deck17.md")
    shutil.copy(os.path.join(FIX, "zorg-deck.md"), deckn)
    rec(deckn)                                         # a v4.3.0 note recorded without a key
    rc, out, res = rec(deckn, "--key", "design-bridge/zorg/new-delivery-feature", "--store", st2)
    check("17.6 B2 a note that already holds the record starts the key file — the next version, no copy",
          rc == 0 and res["recorded"]["version"] == 2 and res.get("from") == "note", out)
    # I4: audience kept across versions
    st3 = os.path.join(d, "store17c"); K3 = ["--key", "zorg/aud", "--store", st3]
    aud = os.path.join(d, "aud17.md")
    shutil.copy(os.path.join(FIX, "zorg-deck.md"), aud)
    rec(aud, *K3)
    run("share", *K3, "--surface", "atlassian", "--kind", "deck", "--audience", "shared")
    rc, out, res = run("record", *K3, "--surface", "atlassian", "--kind", "deck", "--id", "zorg-art-0001",
                       "--url", "https://your-org.atlassian.net/artifacts/zorg-art-0001")
    check("17.7 I4 a new version keeps the place's audience (shared stays shared)",
          rc == 0 and res["recorded"]["audience"] == "shared" and res["recorded"]["version"] == 2, out)
    rc, out, res = run("record", *K3, "--surface", "docs", "--kind", "document", "--id", "d-1",
                       "--url", "https://zorg.example/doc/d-1")
    check("17.8 I4 a place recorded for the first time needs --audience", rc == 2, out)
    # I5: typed and page on one host are two places
    st4 = os.path.join(d, "store17d"); K4 = ["--key", "zorg/levels", "--store", st4]
    run("record", *K4, "--surface", "artifact", "--kind", "deck", "--level", "typed", "--id", "https://zorg-host.example/a/t1",
        "--url", "https://zorg-host.example/a/t1", "--audience", "private")
    run("record", *K4, "--surface", "artifact", "--kind", "deck", "--level", "page", "--id", "https://zorg-host.example/s/p1",
        "--url", "https://zorg-host.example/s/p1", "--audience", "private")
    rc, out, res = run("find", *K4)
    check("17.9 I5 a typed deck and a page deck on one host are two places, nothing replaced",
          len(res.get("found", [])) == 2 and not any(e.get("replaced") for e in res["found"]), res)
    # I6: a v4.2.0 board.yaml
    bo = os.path.join(d, "board17.yaml")
    with open(bo, "w", encoding="utf-8") as f:
        f.write("board: zorg-focus\nartifact_id: https://zorg-host.example/artifact/ZorgBoard01\n")
    rc, out, res, found = find(bo)
    rc2, out2, res2 = run("record", "--note", bo, "--surface", "artifact", "--kind", "dashboard", "--level", "typed",
                          "--id", "https://zorg-host.example/artifact/ZorgBoard01",
                          "--url", "https://zorg-host.example/artifact/ZorgBoard01")
    check("17.10 I6 a v4.2.0 board.yaml's artifact_id is the live board — its next refresh is version 2 of it",
          found and found[0]["surface"] == "artifact" and rc2 == 0 and res2["recorded"]["version"] == 2 and
          res2["recorded"]["audience"] == "unknown", (found, out2))
    # I7: entries copied on are checked like new ones
    bad = os.path.join(d, "bad17.md")
    with open(bad, "w", encoding="utf-8") as f:
        f.write('---\npublished:\n  - surface: artifact\n    kind: deck\n    id: "a1"\n    url: "https://zorg.example/d?X-Amz-'
                + 'Signature=' + "a1b2" * 16 + '"\n    version: 1\n    audience: "private"\n'
                + 'published_to: "https://your-org.atlassian.net/wiki/spaces/SPACE/pages/9/Z?to' + 'ken=' + "Zorg9" * 5 + '"\n---\nb\n')
    newn = os.path.join(d, "new17.md")
    shutil.copy(os.path.join(FIX, "zorg-deck.md"), newn)
    rc, out, res = rec(newn, "--carry", bad, surface="docs", kind="document", id_="d-9", url="https://zorg.example/doc/d-9")
    check("17.11 I7 a signed link or a token in a carried entry or older field is dropped, never written on",
          rc == 0 and res.get("dropped") == 1 and b"X-Amz" not in read(newn) and b"ken=" not in read(newn), (out, read(newn)[-500:]))
    # M9 / M10
    fresh()
    for name, url in (("access_key", "https://zorg.example/d?access_key=" + "Zz9" * 6), ("pwd", "https://zorg.example/d?pwd=" + "x7" * 6),
                      ("hmac", "https://zorg.example/d?hmac=" + "ab12" * 8), ("token[]", "https://zorg.example/d?to" + "ken[]=" + "Zz9" * 6),
                      ("an e-mail", "https://zorg.example/d?user=fay%40zorg.example")):
        rc, out, res = rec(n16, url=url)
        check("17.12 M9 %s in the query is refused" % name, rc == 2, out)
    rc, out, res = rec(n16, url="https://zorg.example/d?sp=r&st=2026-11-02&se=2026-12-01")
    check("17.13 M9 an Azure link's clean permission and date parameters pass (its secret is sig)", rc == 0, out)
    fresh(b'---\npublished_to: "https://wiki.zorg.example/wiki/x/AbC"\n---\nb\n')
    check("17.14 M10 a /wiki/ link with no page id is not read as Confluence", find(n16)[3] == [], find(n16))

    # 15. check 24 — the schema in three places
    import publications as pub  # noqa: E402
    errs = pub.check_schema(ROOT)
    check("15.1 check_schema is clean on the repo", errs == [], errs)
    r2 = os.path.join(d, "root")
    for rel in ("references/vault-schema.md", "references/artifact-publishing.md", "scripts/publications.py",
                "scripts/tools_scan.py"):
        os.makedirs(os.path.dirname(os.path.join(r2, rel)), exist_ok=True)
        shutil.copy(os.path.join(ROOT, rel), os.path.join(r2, rel))
    vs = os.path.join(r2, "references", "vault-schema.md")
    t = open(vs, encoding="utf-8").read()
    with open(vs, "w", encoding="utf-8") as f:
        f.write(t.replace("· `board` · `design` |", "· `board` · `design` · `slides` |", 1))
    errs = pub.check_schema(r2)
    check("15.2 a kind the vault-schema adds alone is named", any("slides" in e for e in errs), errs)
    with open(vs, "w", encoding="utf-8") as f:
        f.write(t.replace("`private` · `shared` · `space:<KEY>` · `unknown`", "`private` · `space:<KEY>` · `unknown`", 1))
    errs = pub.check_schema(r2)
    check("15.3 an audience the vault-schema drops is named", any("shared" in e for e in errs), errs)
    os.remove(vs)
    check("15.4 a missing vault-schema is an error, not silence", pub.check_schema(r2) != [], pub.check_schema(r2))
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""TC-mirror-sync — testing/mirror_sync.sh.

The mirror takes the releases itself: a scheduled job on the mirror's own CI runs the
script, which reads the branch and the tags from the canonical repository and pushes what
the mirror lacks — never by force. The script must say what it did in one line, leave a
mirror that went its own way untouched, and hand its token to the mirror's host only.

Built on throw-away git repositories: bare remotes on disk, and for the token two small
HTTP servers on 127.0.0.1 that run `git http-backend` behind Basic auth. stdlib + git only.
"""
import base64, os, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC = os.path.join(ROOT, "testing", "mirror_sync.sh")
TOKEN = "tok-3f9a-not-a-real-one"
fails = 0
def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))

# No proxy and no user configuration between the script and 127.0.0.1.
ENV = {k: v for k, v in os.environ.items() if not k.lower().endswith("_proxy") and not k.startswith("MIRROR_")}
ENV.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@example.com", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

def git(cwd, *a, ok=True):
    p = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, env=ENV)
    assert not ok or p.returncode == 0, (a, p.stderr)
    return p.stdout.strip()

def commit(work, text):
    with open(os.path.join(work, "notes.txt"), "a") as f:
        f.write(text + "\n")
    git(work, "add", "."); git(work, "commit", "-q", "-m", text)
    return git(work, "rev-parse", "HEAD")

def ref(repo, name):
    return git(repo, "rev-parse", "-q", "--verify", name, ok=False)

def sync(source, target, **env):
    e = dict(ENV, **env)
    if source is not None:
        e["MIRROR_SOURCE_URL"] = source
    if target is not None:
        e["MIRROR_TARGET_URL"] = target
    try:
        p = subprocess.run(["sh", SYNC], capture_output=True, text=True, env=e, timeout=60, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as x:
        return 124, "", "timed out: %s" % x
    return p.returncode, p.stdout, p.stderr


class GitHTTP(BaseHTTPRequestHandler):
    """`git http-backend` behind Basic auth. The server keeps every Authorization header it was sent."""
    def serve(self):
        srv = self.server
        auth = self.headers.get("Authorization")
        srv.seen.append(auth)
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        want = "Basic " + base64.b64encode(("%s:%s" % (srv.user, srv.token)).encode()).decode()
        if auth != want:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="git"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        path, _, query = self.path.partition("?")
        env = dict(ENV, GIT_PROJECT_ROOT=srv.root, GIT_HTTP_EXPORT_ALL="1", REQUEST_METHOD=self.command,
                   PATH_INFO=path, QUERY_STRING=query, CONTENT_TYPE=self.headers.get("Content-Type", ""),
                   CONTENT_LENGTH=str(len(body)), REMOTE_USER=srv.user, REMOTE_ADDR="127.0.0.1")
        for header, var in (("Content-Encoding", "HTTP_CONTENT_ENCODING"), ("Git-Protocol", "GIT_PROTOCOL")):
            if self.headers.get(header):
                env[var] = self.headers[header]
        out = subprocess.run(["git", "http-backend"], input=body, capture_output=True, env=env).stdout
        head, _, payload = out.partition(b"\r\n\r\n")
        status, headers = 200, []
        for line in head.decode().split("\r\n"):
            k, _, v = line.partition(": ")
            if k.lower() == "status":
                status = int(v.split()[0])
            elif k:
                headers.append((k, v))
        self.send_response(status)
        for k, v in headers:
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
    do_GET = do_POST = serve
    def log_message(self, *a):
        pass

def http(root, token, user="oauth2"):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), GitHTTP)
    srv.root, srv.token, srv.user, srv.seen = root, token, user, []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


with tempfile.TemporaryDirectory() as d:
    source, mirror, work = (os.path.join(d, n) for n in ("source.git", "mirror.git", "work"))
    for bare in (source, mirror):
        git(d, "init", "-q", "--bare", "-b", "main", bare)
    git(d, "init", "-q", "-b", "main", work)
    git(work, "remote", "add", "origin", source); git(work, "remote", "add", "mirror", mirror)
    c1 = commit(work, "release: v1.0.0"); git(work, "tag", "v1.0.0")
    git(work, "push", "-q", "origin", "main", "v1.0.0"); git(work, "push", "-q", "mirror", "main", "v1.0.0")

    # --- nothing to do ------------------------------------------------------------------
    rc, out, err = sync(source, mirror)
    check("a mirror that has everything: exit 0 and «up to date»", rc == 0 and "up to date" in out, (rc, out, err))

    # --- the mirror is one release behind -------------------------------------------------
    c2 = commit(work, "release: v1.1.0"); git(work, "tag", "-a", "v1.1.0", "-m", "v1.1.0")
    git(work, "push", "-q", "origin", "main", "v1.1.0")
    git(work, "checkout", "-q", "-b", "draft"); commit(work, "not for the mirror"); git(work, "push", "-q", "origin", "draft")
    git(work, "checkout", "-q", "main")
    rc, out, err = sync(source, mirror)
    check("a mirror one release behind gets the branch", rc == 0 and ref(mirror, "refs/heads/main") == c2, (rc, out, err))
    check("… and the tag, as the same tag object",
          ref(mirror, "refs/tags/v1.1.0") == ref(source, "refs/tags/v1.1.0") != "", (out, err))
    check("… and the line says what was pushed", "pushed" in out and "v1.1.0" in out and c2[:7] in out, out)
    check("another branch of the source stays off the mirror", ref(mirror, "refs/heads/draft") == "", out)
    rc, out, err = sync(source, mirror)
    check("the next run has nothing to push", rc == 0 and "up to date" in out and "pushed" not in out, (rc, out, err))

    # --- a tag that exists only on the mirror is not the script's business ---------------------
    git(mirror, "tag", "mirror-only", c1)
    rc, out, err = sync(source, mirror)
    check("a tag only the mirror has is left alone", rc == 0 and ref(mirror, "refs/tags/mirror-only") == c1, (rc, out, err))

    # --- a tag that differs: nothing is pushed --------------------------------------------------
    c3 = commit(work, "release: v1.2.0"); git(work, "tag", "v1.2.0"); git(work, "push", "-q", "origin", "main", "v1.2.0")
    git(mirror, "tag", "v1.2.0", c1)
    rc, out, err = sync(source, mirror)
    check("a tag that points elsewhere on the mirror: exit 1, the tag named", rc == 1 and "v1.2.0" in err, (rc, out, err))
    check("… and nothing is pushed: the branch stays, the tag stays",
          ref(mirror, "refs/heads/main") == c2 and ref(mirror, "refs/tags/v1.2.0") == c1, (out, err))
    git(mirror, "tag", "-d", "v1.2.0")
    rc, out, err = sync(source, mirror)
    check("with the tag out of the way the release arrives", rc == 0 and ref(mirror, "refs/heads/main") == c3
          and ref(mirror, "refs/tags/v1.2.0") == c3, (rc, out, err))

    # --- the mirror went its own way: nothing is pushed -----------------------------------------
    own = os.path.join(d, "own")
    git(d, "clone", "-q", mirror, own)
    c_own = commit(own, "a commit made on the mirror"); git(own, "push", "-q", "origin", "main")
    c4 = commit(work, "release: v1.3.0"); git(work, "tag", "v1.3.0"); git(work, "push", "-q", "origin", "main", "v1.3.0")
    rc, out, err = sync(source, mirror)
    check("a mirror with a commit the source lacks: exit 1, said plainly",
          rc == 1 and "commits the source does not" in err, (rc, out, err))
    check("… and nothing is pushed, not even the new tag",
          ref(mirror, "refs/heads/main") == c_own and ref(mirror, "refs/tags/v1.3.0") == "", (out, err))

    # --- an empty mirror gets everything --------------------------------------------------------
    fresh = os.path.join(d, "fresh.git")
    git(d, "init", "-q", "--bare", "-b", "main", fresh)
    rc, out, err = sync(source, fresh)
    check("an empty mirror gets the branch and every tag", rc == 0 and ref(fresh, "refs/heads/main") == c4
          and all(ref(fresh, "refs/tags/" + t) for t in ("v1.0.0", "v1.1.0", "v1.2.0", "v1.3.0")), (rc, out, err))

    # --- the mirror refuses one ref: none of the push lands --------------------------------------
    c5 = commit(work, "release: v1.4.0"); git(work, "tag", "v1.4.0"); git(work, "push", "-q", "origin", "main", "v1.4.0")
    hook = os.path.join(fresh, "hooks", "update")
    with open(hook, "w") as f:
        f.write('#!/bin/sh\ncase "$1" in refs/tags/*) echo "tags are protected here" >&2; exit 1;; esac\n')
    os.chmod(hook, 0o755)
    rc, out, err = sync(source, fresh)
    check("a mirror that refuses the tag: exit 1 with the mirror's own words", rc == 1 and "tags are protected here" in err, (rc, out, err))
    check("… and the branch did not go without its tag", ref(fresh, "refs/heads/main") == c4, (out, err))
    os.remove(hook)

    # --- what the job was not given ---------------------------------------------------------------
    rc, out, err = sync(None, fresh)
    check("no source address: exit 1, the variable named", rc == 1 and "MIRROR_SOURCE_URL" in err, (rc, out, err))
    rc, out, err = sync(source, None)
    check("no mirror address: exit 1, the variable named", rc == 1 and "MIRROR_TARGET_URL" in err, (rc, out, err))
    rc, out, err = sync(os.path.join(d, "nowhere.git"), fresh)
    check("a source that cannot be read: exit 1, said plainly", rc == 1 and "cannot read" in err and "source" in err, (rc, out, err))

    # --- the token --------------------------------------------------------------------------------
    served = os.path.join(d, "served"); os.makedirs(served)
    git(d, "init", "-q", "--bare", "-b", "main", os.path.join(served, "mirror.git"))
    git(d, "clone", "-q", "--bare", source, os.path.join(served, "source.git"))
    probe = subprocess.run(["git", "http-backend"], capture_output=True, env=dict(
        ENV, GIT_PROJECT_ROOT=served, GIT_HTTP_EXPORT_ALL="1", REQUEST_METHOD="GET",
        PATH_INFO="/mirror.git/info/refs", QUERY_STRING="service=git-upload-pack"))
    backend = probe.returncode == 0 and b"git-upload-pack" in probe.stdout
    check("this machine's git has `git http-backend` — the token checks below need it", backend, probe.stderr[-300:])
    if backend:
        target_srv, target_url = http(served, TOKEN)
        held = os.path.join(served, "mirror.git")

        rc, out, err = sync(source, target_url + "/mirror.git")
        check("a mirror over HTTP and no token: exit 1 at once, the variable named",
              rc == 1 and "MIRROR_PUSH_TOKEN" in err and target_srv.seen == [], (rc, out, err, target_srv.seen))

        rc, out, err = sync(source, target_url + "/mirror.git", MIRROR_PUSH_TOKEN="wrong-" + TOKEN)
        check("a token the mirror refuses: exit 1, the token is what the line points at",
              rc == 1 and "MIRROR_PUSH_TOKEN" in err and ref(held, "refs/heads/main") == "", (rc, out, err))
        check("… and the token's text is not in the output", TOKEN not in out + err, (out, err))

        rc, out, err = sync(source, target_url + "/mirror.git", MIRROR_PUSH_TOKEN=TOKEN)
        check("the right token: the push goes through", rc == 0 and ref(held, "refs/heads/main") == c5
              and ref(held, "refs/tags/v1.4.0") == c5, (rc, out, err))
        check("… and the token's text is not in the output", TOKEN not in out + err, (out, err))

        # A source that asks for a password must not be answered with the mirror's token.
        source_srv, source_url = http(served, "the-source-wants-its-own")
        secret = base64.b64encode(("oauth2:" + TOKEN).encode()).decode()
        rc, out, err = sync(source_url + "/source.git", target_url + "/mirror.git", MIRROR_PUSH_TOKEN=TOKEN)
        check("a source that asks for a password: exit 1 without waiting for a prompt", rc == 1, (rc, out, err))
        check("… and the source never sees the mirror's token",
              source_srv.seen != [] and not any(h and secret in h for h in source_srv.seen), source_srv.seen)
        # … nor a source on the mirror's own host: the source is read without credentials.
        del target_srv.seen[:]
        rc, out, err = sync(target_url + "/source.git", target_url + "/mirror.git", MIRROR_PUSH_TOKEN=TOKEN)
        check("a source on the mirror's own host that asks for a password: exit 1, the source named",
              rc == 1 and "from the source" in err, (rc, out, err))
        check("… and it is not answered with the token either", not any(h and secret in h for h in target_srv.seen), target_srv.seen)
        for srv in (target_srv, source_srv):
            srv.shutdown()

# --- the job that runs it ---------------------------------------------------------------------------
import json, re
ci_path = os.path.join(ROOT, ".gitlab-ci.yml")
ci = open(ci_path).read() if os.path.isfile(ci_path) else ""
code = "\n".join(l for l in ci.splitlines() if not l.lstrip().startswith("#"))
check("the mirror's CI file runs the script", re.search(r"^\s+- sh testing/mirror_sync\.sh\s*$", code, re.M), code)
sources = re.findall(r'\$CI_PIPELINE_SOURCE == "(\w+)"', code)
check("… on a schedule or a manual run, on nothing else", "workflow:" in code and sorted(sources) == ["schedule", "web"], sources)
with open(os.path.join(ROOT, ".codex-plugin", "plugin.json")) as f:
    repository = json.load(f)["repository"]
check("… from the repository the manifest names", 'MIRROR_SOURCE_URL: "%s.git"' % repository in code, repository)
check("… to the project the job runs in, whatever its address", 'MIRROR_TARGET_URL: "${CI_PROJECT_URL}.git"' in code, code)
check("… one run at a time", re.search(r"^\s+resource_group: \S+", code, re.M), code)
pushes = [l for l in open(SYNC).read().splitlines() if re.match(r"\s*g push\b", l)]
check("the script pushes in one place, without force",
      len(pushes) == 1 and not re.search(r"--force|\s-f\b|\+", pushes[0]) and "--atomic" in pushes[0], pushes)

print()
print("RESULT:", "GREEN ✅ (0 failed)" if not fails else "RED ❌ (%d failed)" % fails)
sys.exit(1 if fails else 0)

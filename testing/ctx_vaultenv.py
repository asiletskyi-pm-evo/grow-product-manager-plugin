#!/usr/bin/env python3
"""A temp HOME and vault from testing/fixtures/<graph|audit>/ for the vault tests since v4.0.0 (audit, normalize, serve).

`VaultEnv(dir, fixture)` copies the fixture vault (the plugin folder Notes/, the core ZorgCore/ registered as zorg-core),
fills {{VAULT}} in, writes ~/.grow-pm/local-context.md; `run(*args)` runs scripts/ctx.py in this process — with the
notes named in `evicted` taken as iCloud-evicted (ctx_index.is_dataless replaced for the run) — and returns (exit code,
output, CTX_RESULT); `tree()` is {relative path: sha1} of every file of the vault, to tell what a run wrote. Not a test
file (no `_test` suffix): the runner skips it. Stdlib only.
"""
import contextlib, hashlib, io, json, os, shutil, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx as ctx_cli  # noqa: E402
import ctx_index as ci  # noqa: E402

FIXTURES = os.path.join(ROOT, "testing", "fixtures")


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8", newline="").write(text)


class VaultEnv:
    def __init__(self, d, fixture="audit", evicted=("Evicted note.md",)):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        shutil.copytree(os.path.join(FIXTURES, fixture, "vault"), self.vault)
        reg = os.path.join(self.vault, "Notes", "_System", "providers", "zorg-core.yaml")
        write(reg, read(reg).replace("{{VAULT}}", self.vault))
        self.text = read(FIXTURES, fixture, "context.md").replace("{{VAULT}}", self.vault)
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        write(self.ctx, self.text)
        self.evicted = tuple(evicted)

    def note(self, rel):
        return os.path.join(self.vault, *rel.split("/"))

    def run(self, *args):
        saved = {k: os.environ.pop(k, None) for k in ("GROW_PM_CONTEXT_PATH", "GROW_PM_PROVIDER_PATHS")}
        real = ci.is_dataless
        ev = self.evicted
        ci.is_dataless = lambda p: any(unicodedata.normalize("NFC", str(p)).endswith(e) for e in ev)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                try:
                    rc = ctx_cli.main(list(args) + ["--home", self.home, "--context", self.ctx])
                except SystemExit as e:
                    rc = e.code
        finally:
            ci.is_dataless = real
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v
        out = buf.getvalue()
        last = [l for l in out.splitlines() if l.startswith("CTX_RESULT ")]
        return rc, out, json.loads(last[-1][len("CTX_RESULT "):]) if last else None

    def tree(self, top=None):
        top = top or self.vault
        out = {}
        for dp, _, names in os.walk(top):
            for n in names:
                p = os.path.join(dp, n)
                with open(p, "rb") as f:
                    out[unicodedata.normalize("NFC", os.path.relpath(p, top))] = hashlib.sha1(f.read()).hexdigest()
        return out

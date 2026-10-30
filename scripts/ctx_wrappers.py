#!/usr/bin/env python3
"""Grow PM — `.md` wrappers of a provider kit's own files (since v3.24.0; references/context-provider-protocol.md §9).

A notes server serves `.md` only, so the two files the team block is built from — `provider-manifest.yaml` and the
role model `access-bundles.json` — never reach a copy of the core (ctx_copy). The kit convention: the core owner
publishes each beside it as a note whose frontmatter says `kind: provider-file` and `file: <name>` and whose text holds
exactly one fenced code block (```yaml for a `.yaml` name, ```json for a `.json` one) with the file's content. The copy
unpacks it into the same folder as `<name>`; `ctx repo kit-check` checks that a wrapper and the file beside it agree.

- unwrap(fm, body, allowed)   (name, text, "") or (name, None, why not) — reads only
- allowed_names(manifest)      the names a wrapper may carry: the two fixed ones and the basename of `bundles_file`
- is_wrapper(fm)               does a frontmatter mark a wrapper?

Stdlib only.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402

KIND = "provider-file"
MANIFEST, MODEL = "provider-manifest.yaml", "access-bundles.json"
FIXED = (MANIFEST, MODEL)
LANGS = {".yaml": ("yaml", "yml"), ".yml": ("yaml", "yml"), ".json": ("json",)}
FENCE = re.compile(r"^(`{3,}|~{3,})[ \t]*([^\s`]*)[ \t]*$")


def is_wrapper(fm):
    return isinstance(fm, dict) and str(fm.get("kind") or "").strip() == KIND


def allowed_names(manifest=None):
    """The file names a wrapper may unpack: provider-manifest.yaml, access-bundles.json, the basename of the
    manifest's `bundles_file` (a role model under another name) and, since v4.2.0, of its `tools_file` (the team's
    tools list, tool-registry.md §5)."""
    names = list(FIXED)
    for key in ("bundles_file", "tools_file"):
        val = (manifest or {}).get(key) if isinstance(manifest, dict) else None
        if isinstance(val, str) and val.strip():
            base = os.path.basename(val.strip())
            if base and base not in names and os.path.splitext(base)[1] in LANGS:
                names.append(base)
    return names


def _blocks(body):
    """[(lang, text)] of the fenced code blocks of `body`, and whether one was never closed."""
    out, cur, opener, lang = [], None, None, ""
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        mo = FENCE.match(line)
        if cur is None:
            if mo:
                cur, opener, lang = [], mo.group(1), mo.group(2).lower()
        elif mo and not mo.group(2) and mo.group(1)[0] == opener[0] and len(mo.group(1)) >= len(opener):
            out.append((lang, "\n".join(cur)))
            cur = None
        else:
            cur.append(line)
    return out, cur is not None


def unwrap(fm, body, allowed=FIXED):
    """(name, text, "") of a sound wrapper — the text with one final newline — or (name, None, why) in words that name
    no path: an unknown name, not exactly one code block, a block never closed, a language tag that does not fit the
    name, a block whose JSON or YAML cannot be read."""
    name = str((fm or {}).get("file") or "").strip()
    if not name or name not in allowed or "/" in name or "\\" in name:
        return name, None, "невідоме ім'я файлу %r (можна: %s)" % (name, ", ".join(allowed))
    blocks, open_ = _blocks(body)
    if open_:
        return name, None, "блок коду не закритий"
    if len(blocks) != 1:
        return name, None, "блоків коду %d, а має бути рівно один" % len(blocks)
    lang, text = blocks[0]
    want = LANGS.get(os.path.splitext(name)[1], ())
    if lang not in want:
        return name, None, "мовний тег %r, а для %s — %s" % (lang, name, " або ".join(want))
    text = text.rstrip("\n") + "\n"
    if want[0] == "json":
        try:
            json.loads(text)
        except ValueError as e:
            return name, None, "JSON не читається (%s)" % type(e).__name__
    else:
        try:
            cc.read_yaml_subset(text)
        except ValueError as e:
            try:                                            # a tools list (since v4.2.0) is a list of mappings
                if not cc.read_yaml_records(text, "tools"):
                    return name, None, "YAML не читається (%s)" % e
            except ValueError:
                return name, None, "YAML не читається (%s)" % e
    return name, text, ""

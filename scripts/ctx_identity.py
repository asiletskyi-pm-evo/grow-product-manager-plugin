#!/usr/bin/env python3
"""Grow PM — «e-mail → team → role» from a core against your own words (since v3.23.0; context-protocol.md §5r).

The bundle builder resolves your e-mail to a team and a role (`provider_bundle.py --propose-only`, its JSON with
`team_from` and `role_from`). `compare` puts each beside yours — the role in your profile, the team your registration
names — with the source of both sides; `.state/identity.json` (schema context-identity/1) keeps what you answered:

    {"schema": "context-identity/1",
     "answers": {"<repo>": {"role": {"chosen": "mine" | "core", "core": "<value>", "mine": "<value>", "at": "YYYY-MM-DD"}}}}

An answer holds while the core says the same; a new value of the core asks again. A file that cannot be read, holds a
key nobody knows or another schema is never rewritten (StoreError). Stdlib only.
"""
import json
import os

import ctx_store as cs

SCHEMA = "context-identity/1"
FIELDS = ("team", "role")
CHOSEN = ("mine", "core")
_ANSWER_KEYS = ("chosen", "core", "mine", "at")


def empty():
    return {"schema": SCHEMA, "answers": {}}


def _path(store):
    return os.path.join(store.state_dir, "identity.json")


def _clean(raw):
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA or set(raw) - {"schema", "answers"}:
        raise ValueError("not %s" % SCHEMA)
    answers = raw.get("answers") or {}
    if not isinstance(answers, dict):
        raise ValueError("answers is not an object")
    for repo, per in answers.items():
        if not isinstance(per, dict) or set(per) - set(FIELDS):
            raise ValueError("answers of %s: a field that is none of %s" % (repo, ", ".join(FIELDS)))
        for f, a in per.items():
            if not isinstance(a, dict) or set(a) - set(_ANSWER_KEYS) or a.get("chosen") not in CHOSEN:
                raise ValueError("the answer %s/%s is not {chosen, core, mine, at}" % (repo, f))
    return {"schema": SCHEMA, "answers": answers}


def load(store):
    path = _path(store)
    if not os.path.lexists(path):
        return empty()
    try:
        return _clean(json.loads(cs.read_text(path)))
    except (OSError, UnicodeDecodeError, cs.StoreError, ValueError) as e:
        raise cs.StoreError("identity memory not readable: .state/identity.json (%s) — left as it is" % e)


def save(store, mem):
    cs.atomic_write(_path(store), json.dumps(_clean(mem), ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def read_bundle(path):
    """The builder's JSON: {team, team_title?, team_from, role, role_from, email?}; ValueError for anything else."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        data = json.loads(text[text.index("{"):] if "{" in text else text)
    except (OSError, ValueError) as e:
        raise ValueError("the bundle's JSON is not readable: %s (%s)" % (path, e))
    if not isinstance(data, dict) or not all(isinstance(data.get(k), str) and data.get(k) for k in ("team", "role")):
        raise ValueError("the bundle's JSON has no team and role: %s" % path)
    return data


def _same(a, b):
    return " ".join(str(a or "").split()).casefold() == " ".join(str(b or "").split()).casefold()


def compare(bundle, mine, mem, repo_id):
    """[{field, core, core_from, mine, mine_from, state: same | ask | kept | taken}] — `mine` is {field: (value, source)}
    (a value None: you said nothing — no question). `kept` / `taken`: your answer still holds (the core says what it said
    then); a new value of the core is `ask` again."""
    out = []
    answers = (mem.get("answers") or {}).get(repo_id) or {}
    for f in FIELDS:
        core = bundle.get(f)
        title = bundle.get("team_title") if f == "team" else None
        val, src = mine.get(f, (None, None))
        row = {"field": f, "core": core, "core_title": title, "core_from": bundle.get("%s_from" % f) or "—", "mine": val,
               "mine_from": src or "—"}
        if val is None or _same(val, core):
            row["state"] = "same" if val is not None else "none"
        else:
            ans = answers.get(f)
            row["state"] = ("kept" if ans["chosen"] == "mine" else "taken") if ans and _same(ans.get("core"), core) else "ask"
            if ans:
                row["answer"] = ans
        out.append(row)
    return out


WORDS = {"team": "команда", "role": "роль"}


def render(rows, repo_id):
    lines = []
    for r in rows:
        w = WORDS[r["field"]]
        core = r["core"] + (" (%s)" % r["core_title"] if r.get("core_title") and r["core_title"] != r["core"] else "")
        if r["state"] == "same":
            lines.append("%s: збігається (%s)" % (w, r["mine"]))
        elif r["state"] == "none":
            lines.append("%s: ядро — %s · %s (у тебе не вказано)" % (w, core, r["core_from"]))
        elif r["state"] == "kept":
            lines.append("%s: лишено твоє (%s); ядро каже %s — відкладено %s" % (w, r["mine"], r["core"], r["answer"].get("at") or ""))
        elif r["state"] == "taken":
            lines.append("%s: взято з ядра (%s)" % (w, r["core"]))
        else:
            lines += ["%s: ядро — %s · %s" % (w, core, r["core_from"]),
                      "%s: ти — %s · %s" % (w, r["mine"], r["mine_from"]),
                      "  відповісти: ctx identity keep %s %s · ctx identity take %s %s" % (repo_id, r["field"], repo_id, r["field"])]
    return "\n".join(lines)


def answer(mem, repo_id, field, chosen, core, mine, day):
    mem.setdefault("answers", {}).setdefault(repo_id, {})[field] = {"chosen": chosen, "core": core, "mine": mine, "at": day}

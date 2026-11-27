#!/usr/bin/env python3
"""jira_rows.py — a saved Jira response as compact rows, one JSON line per issue (since v4.12.2).

A Jira search over a sprint or a quarter is larger than a host shows inline, so the host saves it to a file
(references/jira-data-protocol.md → Large-response extraction). This script reads that file and prints what a report
or a plan computes from. It reads the shape of Atlassian MCP v2: `fields.customFields`, keyed by the field's display
name, each `{"id": "customfield_N", "value": …}`; a field with no value is absent, and has no key in the row's `cf`.

Since v4.15.0 the plugin speaks v2 only (references/integration-strategy.md 1c). A response of the v1 server —
`fields.customfield_N` beside the system fields — is refused with exit 2 and the reason, never read as an issue with
no custom fields: that would report every estimate as missing.

    python3 jira_rows.py <saved-file> [<saved-file> …] [--sprint-history]
    python3 jira_rows.py -            # the response on stdin

A row: `key`, the system fields that came (`summary`, `status`, `category` — the status category's key, `type`,
`assignee`, `resolved`, `versions`, …), `cf` — the custom fields by id, and `closed_sprints` — how many closed sprints
the issue's sprint history holds (0 = new in its sprint, ≥1 = carried over). A user is `{"id", "name"}`: the account id
and the display name; the e-mail address, the avatar links and the profile's other fields never reach a row. A sprint
is `{"id", "name", "state"}`, and only the sprints that are not closed are printed — the closed ones are the count;
`--sprint-history` prints every sprint of the history, with its dates. A description and a comment's text are never
printed: `comments` is their count.

After a file's rows comes one line `{"_page": …}`: the file's name, the number of issues, `shape` (`v2`, `none` when
no issue carries a custom field), `has_next` and `next_page_token` for the next page, and `cf_names` — the display
name of each custom field id.

It reads and prints; it writes nothing and calls nothing. A file that is not a v2 Jira response: exit 2. Stdlib only
(Python 3.9).
"""
import json, os, re, sys

CF = re.compile(r"^customfield_\d+$")
SPRINT_DATES = ("startDate", "endDate", "completeDate")
SKIP = ("description", "environment")            # bodies: never printed
RENAME = {"issuetype": "type", "resolutiondate": "resolved", "fixVersions": "versions"}


class Bad(Exception):
    pass


def reduce(v, history=False):
    """A field's value without what a report never reads: avatars, links to the API, e-mail addresses."""
    if isinstance(v, list):
        return [reduce(x, history) for x in v
                if history or not (isinstance(x, dict) and x.get("state") == "closed" and "name" in x)]
    if not isinstance(v, dict):
        return v
    if "accountId" in v:                         # a user
        return {"id": v.get("accountId"), "name": v.get("displayName") or ""}
    if "state" in v and "name" in v:             # a sprint
        out = {"id": v.get("id"), "name": v.get("name"), "state": v.get("state")}
        if history:
            out.update({k: v[k][:10] for k in SPRINT_DATES if isinstance(v.get(k), str)})
        return out
    if "releaseDate" in v or "released" in v:    # a version
        return {k: v[k] for k in ("name", "releaseDate", "released") if k in v}
    keep = {k: v[k] for k in ("id", "key", "name", "value") if isinstance(v.get(k), (str, int, float, bool))}
    return keep or None


def closed_sprints(values):
    return sum(1 for v in values if isinstance(v, list)
               for s in v if isinstance(s, dict) and s.get("state") == "closed")


def row(issue, history=False):
    """(the row, the issue's shape, the names of its custom fields by id)."""
    fields = issue.get("fields")
    if not isinstance(fields, dict):
        fields = {}
    out, cf, names, raw, shape = {"key": issue.get("key")}, {}, {}, [], "none"
    for name, value in fields.items():
        if name == "customFields" and isinstance(value, dict):          # v2
            for label, cell in value.items():
                if isinstance(cell, dict) and CF.match(str(cell.get("id", ""))):
                    shape = "v2"
                    names[cell["id"]] = label
                    raw.append(cell.get("value"))
                    cf[cell["id"]] = reduce(cell.get("value"), history)
        elif CF.match(name):                                            # the v1 server's shape
            raise Bad("a response of Atlassian MCP v1 (fields.%s): the plugin reads v2 only — reconnect Atlassian "
                      "(references/integration-strategy.md 1c)" % name)
        elif name in SKIP:
            continue
        elif name == "status" and isinstance(value, dict):
            out["status"] = value.get("name")
            out["category"] = (value.get("statusCategory") or {}).get("key")
        elif name == "comment":
            got = value.get("comments") if isinstance(value, dict) else value
            out["comments"] = len(got) if isinstance(got, list) else 0
        elif name in ("issuetype", "priority", "resolution", "project"):
            out[RENAME.get(name, name)] = value.get("name") if isinstance(value, dict) else value
        elif name == "parent":
            out["parent"] = value.get("key") if isinstance(value, dict) else value
        elif name == "components" and isinstance(value, list):
            out["components"] = [c.get("name") for c in value if isinstance(c, dict)]
        else:
            out[RENAME.get(name, name)] = reduce(value, history)
    out["cf"] = cf
    out["closed_sprints"] = closed_sprints(raw)
    return out, shape, names


def issues_of(doc):
    """The issues of a saved response, and its page info: a search (`issues.nodes`), a plain list, one issue."""
    if isinstance(doc, dict) and isinstance(doc.get("data"), (dict, list)) and "issues" not in doc:
        doc = doc["data"]
    if isinstance(doc, dict) and "issues" in doc:
        box = doc["issues"]
        if isinstance(box, dict):
            nodes = box.get("nodes")
            page = box.get("pageInfo") if isinstance(box.get("pageInfo"), dict) else {}
        else:
            nodes, page = box, doc
        if isinstance(nodes, list):
            return nodes, page
    if isinstance(doc, dict) and "key" in doc and "fields" in doc:
        return [doc], {}
    if isinstance(doc, list) and all(isinstance(i, dict) and "key" in i for i in doc):
        return doc, {}
    raise Bad("not a Jira response: no issues, no issue")


def read(text, history=False):
    try:
        doc = json.loads(text)
    except ValueError as e:
        raise Bad("not JSON: %s" % e)
    nodes, page = issues_of(doc)
    rows, shapes, names = [], set(), {}
    for issue in nodes:
        if not isinstance(issue, dict):
            continue
        r, shape, n = row(issue, history)
        rows.append(r)
        shapes.add(shape)
        names.update(n)
    shapes.discard("none")
    token = page.get("endCursor") or page.get("nextPageToken")
    return rows, {"issues": len(rows), "shape": "+".join(sorted(shapes)) or "none",
                  "has_next": bool(page.get("hasNextPage")) if "hasNextPage" in page else bool(token),
                  "next_page_token": token, "cf_names": names}


def main(argv):
    args = [a for a in argv if a != "--sprint-history"]
    if not args or any(a.startswith("--") for a in args):
        sys.stderr.write("usage: jira_rows.py <saved-file> [<saved-file> …] [--sprint-history]   (- reads stdin)\n")
        return 2
    code = 0
    for path in args:
        try:
            text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
            rows, page = read(text, "--sprint-history" in argv)
        except (OSError, Bad) as e:
            sys.stderr.write("jira_rows: %s: %s\n" % (path, e))
            code = 2
            continue
        for r in rows:
            print(json.dumps(r, ensure_ascii=False, separators=(",", ":")))
        page = dict({"file": "stdin" if path == "-" else os.path.basename(path)}, **page)
        print(json.dumps({"_page": page}, ensure_ascii=False, separators=(",", ":")))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

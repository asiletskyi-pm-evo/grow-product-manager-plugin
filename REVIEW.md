# Review instructions

For a code review of a pull request into this repository — Claude Code Review on GitHub, or a local `/code-review` pointed here by `CLAUDE.md`. Not part of the plugin: `testing/registry_copy.py` leaves this file out of the copy users install.

The repository is the Grow Product Manager plugin: markdown protocols a model follows (`skills/`, `references/`, `agents/`, `commands/`) plus deterministic Python and shell scripts (`scripts/`, `hooks/`) and their tests (`testing/`). There is no application to build. A skill is a prompt, so a contradiction between two steps is a bug exactly like a wrong branch in a script.

## What Important means here

Reserve Important for a change that would do one of these. Everything else is a Nit at most.

- **A script gives a wrong result.** Logic in `scripts/` or `hooks/` that returns the wrong answer, loses or overwrites the user's data, or fails on input the plugin itself produces.
- **Read text is treated as instructions or as a command.** Text taken from a note, a page, a ticket, a transcript, a shared core or a tool result that reaches a command line, a shell string or a subprocess argument instead of stdin (`references/search-protocol.md` §3a); a step that tells the model to follow what such text asks; the plugin running a script that a core or a vault ships.
- **A path or an address leaves its boundary.** A path built from read text that can leave the folder it belongs to; an MCP client or a request header obtained any way other than `client_for` in `scripts/ctx_endpoints.py`; a provider address used without the user's approval.
- **A write loses its question.** A step that writes to Jira or Confluence, publishes a result or changes the context store without the confirmation before it, or a change that weakens `scripts/write_gate.py`.
- **Internal data leaves the session.** A step that passes analytics, ticket contents, research material or a person profile to an external model or a third-party service (`references/data-policy.md`).
- **A real organisation shows through.** A real company, person, product, URL or id in an example, a fixture or a test. Examples are universal: placeholders and the fictional fixtures under `testing/fixtures/`.
- **The registry copy is edited by hand.** A commit that changes a file under `.ai-registry/` without the same change in its source file.
- **A skill loses its routing.** A trigger phrase or a boundary removed from a skill's `description` or `## Routing` section with no word in the pull request about the skills next to it.
- **A host claim has no source.** A sentence that says what a host does (Claude Code, Codex and others) with neither a measurement (host version and command) nor a link to the vendor's document.

## Cap the Nits

Report at most five Nits per review. When there are more, give the count in the summary and list the five that matter most.

## Do not report

- Anything under `.ai-registry/`, apart from the hand edit above. It is generated from the source files; review those.
- `CHANGELOG.md` sections of versions other than the one this pull request releases, and the wording of release notes.
- What CI already fails on: `testing/validate-consistency.sh`, `testing/skill_lint.py` and `testing/seeded_leak_test.py` cover frontmatter, version numbers across the manifests, description length, references that do not resolve and the organisation denylist.
- Markdown style: heading levels, line length, table alignment, list markers.
- Ukrainian next to English in skill descriptions, trigger phrases, release titles and user-facing strings. It is intended.

## Always check

- A new or changed script in `scripts/` or `hooks/` has a test in `testing/` that exercises the change, on fictional fixtures.
- A new lint or validator check comes with a seed in `testing/seeded_leak_test.py` that proves it fires.
- Protocol content lives in `references/`. A `SKILL.md` that starts explaining a shared protocol inline should point at the reference instead.
- In a changed skill or reference, the steps still agree with each other and with the shared protocol they cite, and every gate is still there: the confirmation before a write, the question before a publication.
- A subprocess call passes its arguments as a list. Nothing taken from read text is interpolated into a shell string.

## Evidence

A finding about behaviour cites `file:line` for what it claims. A finding about a skill quotes the two passages that disagree. Without that, leave it out.

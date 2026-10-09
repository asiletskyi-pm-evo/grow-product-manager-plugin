#!/usr/bin/env python3
"""TC-ctx-3100-common — scripts/ctx_common.py, the helpers the context-provider
scripts share (references/context-provider-protocol.md): the YAML subset reader,
managed-region stripping, the Obsidian Vaults and Vault Search MCP parsers,
provider registrations and the component-wise write boundary.

Stdlib only; run from the repo root. Prints one line per case and a RESULT line.
"""
import importlib.util, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("ctx_common", os.path.join(ROOT, "scripts", "ctx_common.py"))
cc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cc)

MANIFEST = """schema: provider-manifest/1
id: zorg-core   # kebab-case
title: "Zorg shared core"
plugin_folder: Core
playbook:
  - Core/Playbook/01 Rules.md
  - "Core/Playbook/03 Routes.md"
mcp:
  url: https://context.zorg.example/mcp
  access: vpn
role_hints:
  leadership: "\\\\bCPO\\\\b|head of"
stale_after_days: 30
deny_patterns: []
"""

CONTEXT = """# Local Context
### Team: Alpha (A)
<!-- zorg-core:begin id=team v=0.4 -->
### Team: Alpha Team (A)
- members
<!-- zorg-core:end id=team -->
## Obsidian Vaults (Optional)
| # | Vault Path | Folder Name | Products | Sync Mode | Last Artifact |
|---|------------|------------|----------|-----------|--------------|
| 1 | /tmp/vault-one | Notes | Product 1 | auto | 2026-04-16 |

```yaml
vaults:
  - path: "~/vault-two"
    plugin_folder: Core
```

### Vault Search MCP
- zorg-brain: scope = own vault (Notes/, ZorgCore/), tools = vault_* + brain_*, index = ~/.zorg-brain/brain.sqlite
- zorg-core: scope = shared core snapshot, mode = snapshot, VPN only, read-only

## Custom Sections
"""

cases = []
def case(name):
    def deco(fn): cases.append((name, fn)); return fn
    return deco

@case("yaml subset parses lists and one nesting level")
def _():
    d = cc.read_yaml_subset(MANIFEST)
    assert d["id"] == "zorg-core", d["id"]
    assert d["title"] == "Zorg shared core", d["title"]
    assert d["playbook"] == ["Core/Playbook/01 Rules.md", "Core/Playbook/03 Routes.md"], d["playbook"]
    assert d["mcp"]["access"] == "vpn" and d["mcp"]["url"].startswith("https://"), d["mcp"]
    assert d["role_hints"]["leadership"] == "\\bCPO\\b|head of", d["role_hints"]
    assert d["stale_after_days"] == 30 and d["deny_patterns"] == [], (d["stale_after_days"], d["deny_patterns"])

@case("unsupported yaml line names its line")
def _():
    try:
        cc.read_yaml_subset("id: x\nmcp:\n  url: a\n  deep:\n    more: b\n")
    except ValueError as e:
        assert "line 4" in str(e), str(e)
        return
    raise AssertionError("no ValueError for two-level nesting")

@case("strip keeps line count and removes region text")
def _():
    out = cc.strip_managed_regions(CONTEXT)
    assert out.count("\n") == CONTEXT.count("\n"), (out.count("\n"), CONTEXT.count("\n"))
    assert "Alpha Team (A)" not in out and "### Team: Alpha (A)" in out

@case("strip handles section markers without id")
def _():
    t = "a\n<!-- zorg-core:section:begin -->\n## Core\n<!-- zorg-core:begin id=x v=1 -->\nx\n<!-- zorg-core:end id=x -->\n<!-- zorg-core:section:end -->\nb\n"
    out = cc.strip_managed_regions(t)
    assert "## Core" not in out and out.startswith("a\n") and out.rstrip("\n").endswith("b"), out
    assert out.count("\n") == t.count("\n")

@case("vault entries from table and yaml")
def _():
    v = cc.vault_entries(CONTEXT)
    assert ("/tmp/vault-one", "Notes") in v, v
    assert (os.path.expanduser("~/vault-two"), "Core") in v, v

@case("vault search bullets with commas and flags")
def _():
    b = {x["id"]: x for x in cc.vault_search_bullets(CONTEXT)}
    assert b["zorg-brain"]["mode"] == "live" and b["zorg-brain"]["access"] == "local", b["zorg-brain"]
    assert b["zorg-brain"]["scope"] == "own vault (Notes/, ZorgCore/)", b["zorg-brain"]["scope"]
    assert b["zorg-core"]["mode"] == "snapshot" and b["zorg-core"]["access"] == "vpn", b["zorg-core"]
    assert b["zorg-core"]["read_only"] is True and b["zorg-brain"]["read_only"] is False

@case("registrations, roots and the write boundary")
def _():
    with tempfile.TemporaryDirectory() as d:
        core = os.path.join(d, "ZorgCore"); os.makedirs(os.path.join(core, "Core", "_personal"))
        regdir = os.path.join(d, "Notes", "_System", "providers"); os.makedirs(regdir)
        open(os.path.join(regdir, "zorg-core.yaml"), "w").write(
            "schema: provider-registration/1\nid: zorg-core\nkind: bundle\npaths:\n  - %s\nwritable:\n  - Core/Now.md\n  - Core/_personal/\nstatus: active\n" % core)
        open(os.path.join(regdir, "broken.yaml"), "w").write("id: x\na:\n  b:\n    c: d\n")
        regs = cc.find_registrations([(d, "Notes")], extra_dirs=[])
        assert [r["id"] for r in regs] == ["zorg-core"], regs
        assert cc.provider_roots(regs) == [core], cc.provider_roots(regs)
        assert cc.boundary_hit(os.path.join(core, "Core", "Teams", "a.md"), regs)["id"] == "zorg-core"
        assert cc.boundary_hit(os.path.join(core, "Core", "Now.md"), regs) is None
        assert cc.boundary_hit(os.path.join(core, "Core", "_personal", "x", "y.md"), regs) is None
        assert cc.boundary_hit(os.path.join(d, "Notes", "Meetings", "m.md"), regs) is None

@case("is_under is component-wise")
def _():
    assert not cc.is_under("/v/Zorg_X-notes/x.md", ["/v/Zorg_X"])
    assert cc.is_under("/v/Zorg_X/a/b.md", ["/v/Zorg_X"])
    assert cc.is_under("/v/Zorg_X", ["/v/Zorg_X"])

# --- v3.11.0: helpers for the context store (references/context-protocol.md)
@case("slugify transliterates and dashes")
def _():
    assert cc.slugify("Структура команди") == "struktura-komandy", cc.slugify("Структура команди")
    assert cc.slugify("Team: Alpha (A)") == "team-alpha-a", cc.slugify("Team: Alpha (A)")
    assert cc.slugify("!!!") == "section"

@case("vault modes and storage root")
def _():
    t = ("## Obsidian Vaults (Optional)\n\n| # | Vault Path | Folder Name | Products | Sync Mode | Last Artifact |\n"
         "|---|---|---|---|---|---|\n| 1 | /v/one | Notes | all | off | never |\n| 2 | /v/two | Work | all | auto | never |\n")
    assert cc.vault_modes(t) == [("/v/one", "Notes", "off"), ("/v/two", "Work", "auto")], cc.vault_modes(t)
    assert cc.storage_root(t, home="/h") == "/v/two/Work", cc.storage_root(t, home="/h")
    assert cc.storage_root("## User Profile\n", home="/h") == "/h/.grow-pm"
    y = "## Obsidian Vaults (Optional)\n\n- path: /v/three\n  plugin_folder: \"GrowPM\"\n  sync_mode: off\n"
    assert cc.vault_modes(y) == [("/v/three", "GrowPM", "off")], cc.vault_modes(y)
    assert cc.storage_root(y, home="/h") == "/h/.grow-pm"

@case("managed spans cover begin..end")
def _():
    s = "a\n<!-- zorg-core:begin id=team v=1 -->\nx\n<!-- zorg-core:end id=team -->\nb\n"
    assert [s[a:b] for a, b in cc.managed_spans(s)] == [
        "<!-- zorg-core:begin id=team v=1 -->\nx\n<!-- zorg-core:end id=team -->"], cc.managed_spans(s)

@case("find_context: explicit, then env, then home")
def _():
    with tempfile.TemporaryDirectory() as d:
        home = os.path.join(d, "home"); os.makedirs(os.path.join(home, ".grow-pm"))
        hp = os.path.join(home, ".grow-pm", "local-context.md"); open(hp, "w").write("x")
        other = os.path.join(d, "other.md"); open(other, "w").write("y")
        old = os.environ.get("GROW_PM_CONTEXT_PATH")
        try:
            os.environ["GROW_PM_CONTEXT_PATH"] = other
            assert cc.find_context(home=home) == other
            assert cc.find_context(explicit=hp, home=home) == hp
            os.environ["GROW_PM_CONTEXT_PATH"] = os.path.join(d, "missing.md")
            assert cc.find_context(home=home) == hp
        finally:
            if old is None:
                os.environ.pop("GROW_PM_CONTEXT_PATH", None)
            else:
                os.environ["GROW_PM_CONTEXT_PATH"] = old

fails = 0
for name, fn in cases:
    try:
        fn(); print("✅", name)
    except Exception as e:
        fails += 1; print("❌", name, "->", type(e).__name__, e)
print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d/%d)" % (len(cases) - fails, len(cases)))
sys.exit(1 if fails else 0)

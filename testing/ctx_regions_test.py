#!/usr/bin/env python3
"""TC-ctx-4000-regions — scripts/ctx_regions.py, the generated regions of a note (since v4.0.0).

One parser for the audit, the normaliser and the write gate: the regions of a note and what is wrong with them — a
begin with no end, an end with no begin, two regions of one namespace and id, a namespace outside the registry, two
regions of one namespace without an id, a heading both inside a region and outside it, a region inside another; a
region without an id alone in its namespace is fine (the user's own scripts write one). `touches` — does an edit's old
text lie on a region; `changed` — does a whole new text change a region. And the registry: the table of
references/vault-schema.md is the constant. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_regions_test.py
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
try:
    import ctx_regions as rg  # noqa: E402
except ImportError:
    rg = None
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


if rg is None:
    check("v4.0.0 scripts/ctx_regions.py exists", False, "no module ctx_regions")
    print("RESULT: RED ❌")
    sys.exit(1)

GOOD = """# Note

Text of mine.

<!-- ctx:begin id=related -->
## Пов'язане
- [[A]]
<!-- ctx:end id=related -->

<!-- related:begin -->
- [[B]]
<!-- related:end -->

<!-- zorg-core:begin id=org v=0.1 -->
Org.
<!-- zorg-core:end id=org -->
"""

regs, probs = rg.parse(GOOD, providers=["zorg-core"])
check("v4.0.0 parse: three regions — ns, id (None without one), the text inside, the offsets of the markers",
      [(r["ns"], r["id"]) for r in regs] == [("ctx", "related"), ("related", None), ("zorg-core", "org")]
      and regs[0]["inner"] == "\n## Пов'язане\n- [[A]]\n" and GOOD[regs[0]["start"]:].startswith("<!-- ctx:begin")
      and GOOD[:regs[0]["end"]].endswith("<!-- ctx:end id=related -->"), regs)
check("…a sound note has no problem; a region without an id alone in its namespace is no problem", probs == [], probs)
check("…a provider's namespace is known only when it is registered",
      [p["why"] for p in rg.parse(GOOD)[1]] == ["unknown-ns"], rg.parse(GOOD)[1])


def whys(text, **k):
    return sorted(p["why"] for p in rg.parse(text, **k)[1])


check("v4.0.0 a begin with no end → unclosed", whys("<!-- ctx:begin id=a -->\nx\n") == ["unclosed"])
check("…an end with no begin → stray-end", whys("x\n<!-- ctx:end id=a -->\n") == ["stray-end"])
check("…the end of another id → stray-end and unclosed",
      whys("<!-- ctx:begin id=a -->\nx\n<!-- ctx:end id=b -->\n") == ["stray-end", "unclosed"])
check("…one namespace and id twice → dup-id",
      whys("<!-- ctx:begin id=a -->\n<!-- ctx:end id=a -->\n<!-- ctx:begin id=a -->\n<!-- ctx:end id=a -->\n") == ["dup-id"])
check("…two regions of one namespace without an id → no-id",
      whys("<!-- related:begin -->\n<!-- related:end -->\n<!-- related:begin -->\n<!-- related:end -->\n") == ["no-id"])
check("…a namespace nobody registered → unknown-ns", whys("<!-- foo:begin id=a -->\n<!-- foo:end id=a -->\n") == ["unknown-ns"])
check("…a region inside another → nested",
      whys("<!-- ctx:begin id=a -->\n<!-- generated:begin id=b -->\n<!-- generated:end id=b -->\n<!-- ctx:end id=a -->\n")
      == ["nested"])
check("…a heading inside a region and outside it → heading-twice",
      whys("## Пов'язане\nmine\n<!-- ctx:begin id=r -->\n## Пов'язане\n- [[A]]\n<!-- ctx:end id=r -->\n") == ["heading-twice"])
check("…a section wrapper (`ns:section:begin`) is a region without an id",
      [(r["ns"], r["id"]) for r in rg.parse("<!-- generated:section:begin -->\nx\n<!-- generated:section:end -->\n")[0]]
      == [("generated", None)])
check("…markers inside a code block are text, not regions",
      rg.parse("```\n<!-- ctx:begin id=a -->\n```\n") == ([], []))

check("v4.0.0 touches: an edit's old text on a region's text or marker — yes; outside every region — no",
      rg.touches(GOOD, "- [[A]]") and rg.touches(GOOD, "<!-- related:end -->") and rg.touches(GOOD, "mine.\n\n<!-- ctx:begin")
      and not rg.touches(GOOD, "Text of mine.") and not rg.touches(GOOD, "not in the note"))
check("…a text found twice touches when any of its places does",
      rg.touches("x\n<!-- ctx:begin id=a -->\nx\n<!-- ctx:end id=a -->\n", "x"))
check("v4.0.0 changed: the same regions in a new text — no; a region's text, a marker or a region gone — yes",
      not rg.changed(GOOD, GOOD.replace("Text of mine.", "Other text."))
      and rg.changed(GOOD, GOOD.replace("- [[A]]", "- [[C]]"))
      and rg.changed(GOOD, GOOD.replace("<!-- related:begin -->\n- [[B]]\n<!-- related:end -->\n", ""))
      and not rg.changed("no regions", "still none"))

errs = rg.check_registry(ROOT)
check("v4.0.0 the registry table of references/vault-schema.md is the constant NAMESPACES", errs == [], errs)
check("…the registry holds the namespaces of the concept and the plugin's own",
      {"related", "person-context", "person-profile", "ff-summary", "generated", "audit", "ctx"} == set(rg.NAMESPACES),
      rg.NAMESPACES)

print("RESULT:", "GREEN ✅ — 0 failure(s)" if not fails else "RED ❌ — %d failure(s)" % fails)
sys.exit(1 if fails else 0)

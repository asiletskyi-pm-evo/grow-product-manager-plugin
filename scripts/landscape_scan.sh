#!/bin/sh
# landscape_scan.sh — candidates for the product-landscape registry, one JSON line each.
# Sources: Mac apps in /Applications (scan-mac), iPhone apps installed from the Mac App Store
# (scan-iphone-on-mac: /Applications/*.app/Wrapper/*.app), packages of an attached Android
# device (scan-adb), and — ONLY with --bookmarks, i.e. after the user said yes in this scan —
# Chrome/Safari bookmark domains (bookmarks). Never reads browser history. Fail-open: exit 0.
want_bm=0; [ "${1:-}" = "--bookmarks" ] && want_bm=1
esc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
bid() { defaults read "$1/Info.plist" CFBundleIdentifier 2>/dev/null; }
for app in /Applications/*.app; do
  [ -d "$app" ] || continue
  name=$(basename "$app" .app)
  if [ -d "$app/Wrapper" ]; then
    inner=$(ls -d "$app/Wrapper/"*.app 2>/dev/null | head -1)
    printf '{"source":"scan-iphone-on-mac","name":"%s","bundle_id":"%s","path":"%s"}\n' "$(esc "$name")" "$(esc "$(bid "$inner")")" "$(esc "$app")"
  else
    printf '{"source":"scan-mac","name":"%s","bundle_id":"%s","path":"%s"}\n' "$(esc "$name")" "$(esc "$(bid "$app/Contents")")" "$(esc "$app")"
  fi
done
adb=$(command -v adb 2>/dev/null); [ -z "$adb" ] && [ -x "$HOME/Library/Android/sdk/platform-tools/adb" ] && adb="$HOME/Library/Android/sdk/platform-tools/adb"
if [ -n "$adb" ] && [ "$("$adb" devices 2>/dev/null | awk 'NR>1 && $2=="device"' | wc -l | tr -d ' ')" = "1" ]; then
  "$adb" shell pm list packages -3 2>/dev/null | sed 's/^package://' | while read -r pkg; do
    printf '{"source":"scan-adb","name":"%s","bundle_id":"%s","path":""}\n' "$(esc "$pkg")" "$(esc "$pkg")"
  done
fi
if [ "$want_bm" = "1" ]; then
  ch="$HOME/Library/Application Support/Google/Chrome/Default/Bookmarks"
  [ -f "$ch" ] && python3 - "$ch" <<'PY' 2>/dev/null
import json,sys,re
def walk(n):
    if isinstance(n,dict):
        u=n.get("url")
        if u:
            m=re.match(r"https?://([^/]+)",u)
            if m: print(json.dumps({"source":"bookmarks","name":n.get("name",""),"bundle_id":"","path":"","domain":m.group(1)}, ensure_ascii=False))
        for c in n.get("children",[]): walk(c)
d=json.load(open(sys.argv[1]))
for r in d.get("roots",{}).values(): walk(r)
PY
  sf="$HOME/Library/Safari/Bookmarks.plist"
  [ -f "$sf" ] && plutil -convert json -o - "$sf" 2>/dev/null | python3 -c '
import json,sys,re
def walk(n):
    if isinstance(n,dict):
        u=n.get("URLString")
        if u:
            m=re.match(r"https?://([^/]+)",u)
            if m: print(json.dumps({"source":"bookmarks","name":n.get("URIDictionary",{}).get("title",""),"bundle_id":"","path":"","domain":m.group(1)}, ensure_ascii=False))
        for c in n.get("Children",[]): walk(c)
try: walk(json.load(sys.stdin))
except Exception: pass' 2>/dev/null
fi
exit 0

#!/bin/sh
# walkthrough_preflight.sh — what can this machine drive? One line per surface:
#   SURFACE | STATUS | MISSING | WHO
# STATUS: ready | partial | missing | n/a   WHO: agent | user | -
# Fail-open: always exit 0; the flow-walkthrough skill turns the table into setup steps.
# Browser tools are NOT checked here — the skill reads them from its tool list.
os=$(uname -s 2>/dev/null); arch=$(uname -m 2>/dev/null)
row() { printf '%s | %s | %s | %s\n' "$1" "$2" "$3" "$4"; }

row web ready "-" "-"

if [ "$os" = "Darwin" ]; then
  row desktop ready "-" "-"
  if [ "$arch" = "arm64" ]; then
    row iphone-on-mac partial "install the app from the Mac App Store (its App Store page must list Mac under Compatibility)" user
  else
    row iphone-on-mac n/a "Apple Silicon required" "-"
  fi
  xc=$(ls -d /Applications/Xcode*.app 2>/dev/null | head -1)
  if [ -n "$xc" ]; then
    dev="$xc/Contents/Developer"
    sel=$(xcode-select -p 2>/dev/null)
    ndev=$(DEVELOPER_DIR="$dev" xcrun simctl list devices available 2>/dev/null | grep -c '(')
    nrt=$(DEVELOPER_DIR="$dev" xcrun simctl list runtimes 2>/dev/null | grep -c 'iOS')
    miss=""
    [ "$sel" = "$dev" ] || miss="sudo xcode-select -s $dev"
    [ "${nrt:-0}" -gt 0 ] || miss="${miss:+$miss; }download an iOS runtime in Xcode > Settings > Components"
    [ "${ndev:-0}" -gt 0 ] || miss="${miss:+$miss; }create a simulator: xcrun simctl create 'iPhone' <device-type> <runtime>"
    if [ -z "$miss" ]; then row ios-simulator partial "a simulator build (.app) from the mobile team" user
    else row ios-simulator partial "$miss; then a simulator build (.app) from the mobile team" user; fi
  else
    row ios-simulator missing "install Xcode from the App Store" user
  fi
else
  row desktop n/a "macOS only in v1" "-"
  row iphone-on-mac n/a "macOS on Apple Silicon required" "-"
  row ios-simulator n/a "macOS required" "-"
fi

adb=$(command -v adb 2>/dev/null)
[ -z "$adb" ] && [ -x "$HOME/Library/Android/sdk/platform-tools/adb" ] && adb="$HOME/Library/Android/sdk/platform-tools/adb"
if [ -n "$adb" ]; then
  n=$("$adb" devices 2>/dev/null | awk 'NR>1 && $2=="device"{c++} END{print c+0}')
  if [ "$n" -eq 1 ]; then row android-adb ready "-" "-"
  elif [ "$n" -gt 1 ]; then row android-adb partial "more than one device attached — keep exactly one" user
  else row android-adb partial "plug in a phone with USB debugging on, or start an emulator" user; fi
else
  if command -v brew >/dev/null 2>&1; then row android-adb missing "brew install --cask android-platform-tools" agent
  else row android-adb missing "install Android platform-tools (adb)" user; fi
fi
exit 0

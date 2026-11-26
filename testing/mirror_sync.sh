#!/bin/sh
# Mirror sync — the mirror takes the releases itself.
#
# Reads one branch and every tag from the canonical repository and pushes to the mirror
# what the mirror lacks. Run by the mirror's own scheduled CI job (.gitlab-ci.yml), so no
# release waits for a push from somebody's machine. Never by force: a mirror whose branch
# holds commits the source does not, or whose tag points at another object, is left exactly
# as it is and the job fails — somebody has to look. Nothing is pushed in part.
#
#   MIRROR_SOURCE_URL   the canonical repository, read without credentials
#   MIRROR_TARGET_URL   the mirror
#   MIRROR_BRANCH       the branch to carry (default: main)
#   MIRROR_PUSH_TOKEN   the mirror's token; required when the mirror is reached over HTTP(S)
#   MIRROR_PUSH_USER    the user name sent with the token (default: oauth2)
#
# The token is read from the environment by a git credential helper that answers for the
# mirror's host alone and is set up after the source has been read: the token is never in
# a URL, an argument or the output, and a source that asks for a password gets none, on
# whatever host it is. Exit 0 — in sync or pushed; 1 — anything else, one line
# on stderr saying what. POSIX sh + git; the test is testing/mirror_sync_test.py.
set -eu

say() { printf 'mirror: %s\n' "$*"; }
fail() { printf 'mirror: FAILED — %s\n' "$*" >&2; exit 1; }
shown() { printf '%s' "$1" | sed -E 's#//[^/@]*@#//#'; }   # an address without its user part
short() { printf '%.7s' "$1"; }

SOURCE=${MIRROR_SOURCE_URL:-}
TARGET=${MIRROR_TARGET_URL:-}
BRANCH=${MIRROR_BRANCH:-main}
[ -n "$SOURCE" ] || fail "MIRROR_SOURCE_URL is not set: the address of the canonical repository."
[ -n "$TARGET" ] || fail "MIRROR_TARGET_URL is not set: the address of the mirror."

over_http=
case "$TARGET" in
  http://*|https://*)
    over_http=1
    [ -n "${MIRROR_PUSH_TOKEN:-}" ] || fail "MIRROR_PUSH_TOKEN is not set: a CI/CD variable with a token of the mirror that may write to the repository. A protected variable reaches a pipeline on a protected branch only."
    ;;
esac

export GIT_TERMINAL_PROMPT=0   # no credentials is an error, never a prompt nobody will answer
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
trap 'exit 1' INT TERM
git init -q --bare "$work/repo"
g() { git --git-dir="$work/repo" "$@"; }
why() { tr '\n' ' ' <"$work/err" | sed -E 's/ +/ /g; s/ $//' | cut -c 1-400; }

token_hint() {
  if [ -n "$over_http" ] && grep -Eqi 'authentication failed|could not read (username|password)|returned error: 40[13]' "$work/err"; then
    printf ' Check MIRROR_PUSH_TOKEN: still valid, not expired, allowed to write to the repository and to push to %s.' "$BRANCH"
  fi
}

# The source is read before the token's helper exists: whatever its host, it gets no credentials.
g fetch -q --no-tags "$SOURCE" "+refs/heads/$BRANCH:refs/source/heads/$BRANCH" '+refs/tags/*:refs/source/tags/*' 2>"$work/err" \
  || fail "cannot read $BRANCH and the tags from the source $(shown "$SOURCE"): $(why)"

if [ -n "$over_http" ]; then
  host=$(printf '%s' "$TARGET" | sed -E 's#^(https?://[^/]+).*#\1#')
  # An empty value first: no helper configured elsewhere answers for the mirror.
  g config "credential.$host.helper" ''
  # The value names the variables; their contents are read when git asks, in the helper's own shell.
  g config --add "credential.$host.helper" \
    '!f() { test "$1" = get && printf "username=%s\npassword=%s\n" "${MIRROR_PUSH_USER:-oauth2}" "$MIRROR_PUSH_TOKEN"; }; f'
fi

g ls-remote "$TARGET" "refs/heads/$BRANCH" 'refs/tags/*' >"$work/target" 2>"$work/err" \
  || fail "cannot read the mirror $(shown "$TARGET"): $(why).$(token_hint)"

on_mirror() { awk -v r="$1" '$2 == r { print $1 }' "$work/target"; }

# Tags first: one that differs stops everything.
missing= differing= total=0
for tag in $(g for-each-ref --format='%(refname:lstrip=3)' refs/source/tags/); do
  total=$((total + 1))
  there=$(on_mirror "refs/tags/$tag")
  if [ -z "$there" ]; then
    missing="$missing $tag"
  elif [ "$there" != "$(g rev-parse "refs/source/tags/$tag")" ]; then
    differing="$differing $tag"
  fi
done
[ -z "$differing" ] || fail "on the mirror these tags point at another object than at the source:$differing. Nothing was pushed. A tag is never moved by this job: compare them by hand."

head=$(g rev-parse "refs/source/heads/$BRANCH")
there=$(on_mirror "refs/heads/$BRANCH")
branch_behind=
if [ "$there" != "$head" ]; then
  if [ -n "$there" ] && ! { g cat-file -e "$there^{commit}" 2>/dev/null && g merge-base --is-ancestor "$there" "$head"; }; then
    fail "the mirror's $BRANCH ($(short "$there")) is not behind the source's ($(short "$head")): it holds commits the source does not. Nothing was pushed. This job never pushes by force: bring the two together by hand."
  fi
  branch_behind=1
fi

if [ -z "$branch_behind" ] && [ -z "$missing" ]; then
  say "up to date — $BRANCH at $(short "$head"), $total tags."
  exit 0
fi

set --
[ -z "$branch_behind" ] || set -- "refs/source/heads/$BRANCH:refs/heads/$BRANCH"
for tag in $missing; do
  set -- "$@" "refs/source/tags/$tag:refs/tags/$tag"
done
# No `+` and no --force: the mirror refuses what is not a fast-forward. --atomic: all of it or none.
g push -q --atomic "$TARGET" "$@" 2>"$work/err" \
  || fail "the mirror $(shown "$TARGET") refused the push: $(why).$(token_hint)"

done_line=
[ -z "$branch_behind" ] || done_line=" $BRANCH ${there:+$(short "$there")..}$(short "$head")"
[ -z "$missing" ] || done_line="$done_line${done_line:+;} tags:$missing"
say "pushed$done_line."

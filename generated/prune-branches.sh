#!/usr/bin/env bash
#
# prune-branches.sh — retention policy for the generated/ fallback namespace.
#
# Deletes disposable `resolve/goal-plan-*` branches in THIS repo (the
# attractor-pipelines non-GitHub-target fallback landing zone) whose tip
# commit is older than a cutoff age. See generated/README.md for the why.
#
# There is no CI cron in this repo, so this is a manual tool. It is DRY-RUN
# BY DEFAULT and only deletes remote branches when you pass --delete.
#
# Usage:
#   ./generated/prune-branches.sh                 # dry run, 30-day default
#   ./generated/prune-branches.sh --delete        # delete >30d branches on origin
#   ./generated/prune-branches.sh --days 14 --delete
#   ./generated/prune-branches.sh --remote upstream --delete
#
# Options:
#   --days N        Age threshold in days (default: 30).
#   --delete        Actually delete matching branches (default: dry run only).
#   --remote NAME   Remote to prune (default: origin).
#   -h, --help      Show this help and exit.

set -euo pipefail

DAYS=30
DELETE=0
REMOTE=origin

while [ $# -gt 0 ]; do
  case "$1" in
    --days)   DAYS="${2:?--days needs a value}"; shift 2 ;;
    --delete) DELETE=1; shift ;;
    --remote) REMOTE="${2:?--remote needs a value}"; shift 2 ;;
    -h|--help)
      sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *)
      echo "prune-branches.sh: unknown argument: $1" >&2
      echo "Try --help." >&2
      exit 2 ;;
  esac
done

case "$DAYS" in
  ''|*[!0-9]*) echo "prune-branches.sh: --days must be a whole number, got: $DAYS" >&2; exit 2 ;;
esac

PATTERN="refs/remotes/${REMOTE}/resolve/goal-plan-*"
cutoff=$(( $(date +%s) - DAYS * 24 * 60 * 60 ))

echo "Refreshing remote-tracking refs (git fetch --prune ${REMOTE})..."
git fetch --prune "$REMOTE" >/dev/null 2>&1 || {
  echo "prune-branches.sh: 'git fetch --prune ${REMOTE}' failed — is '${REMOTE}' a valid remote?" >&2
  exit 1
}

stale=()
while read -r ref ts; do
  [ -z "${ref:-}" ] && continue
  if [ "$ts" -lt "$cutoff" ]; then
    # Strip the "<remote>/" prefix to get the pushable branch name.
    stale+=("${ref#"${REMOTE}"/}")
  fi
done < <(git for-each-ref \
  --format='%(refname:short) %(committerdate:unix)' \
  "$PATTERN")

if [ "${#stale[@]}" -eq 0 ]; then
  echo "No resolve/goal-plan-* branches older than ${DAYS} days on '${REMOTE}'. Nothing to prune."
  exit 0
fi

echo "Found ${#stale[@]} resolve/goal-plan-* branch(es) older than ${DAYS} days on '${REMOTE}':"
for b in "${stale[@]}"; do
  echo "  - ${b}"
done

if [ "$DELETE" -ne 1 ]; then
  echo
  echo "Dry run — nothing deleted. Re-run with --delete to remove the branches above."
  exit 0
fi

echo
for b in "${stale[@]}"; do
  echo "Deleting ${REMOTE}/${b} ..."
  git push "$REMOTE" --delete "$b"
done
echo "Done. Deleted ${#stale[@]} branch(es) from '${REMOTE}'."

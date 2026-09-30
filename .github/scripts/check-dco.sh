#!/usr/bin/env bash
# Verify that every non-merge commit in BASE..HEAD carries a DCO sign-off
# ("Signed-off-by: Name <email>") matching its author, as created by `git commit -s`.
#
# Usage: .github/scripts/check-dco.sh <base-sha> <head-sha>
set -euo pipefail

base="${1:?base commit required}"
head="${2:?head commit required}"
missing=0

for commit in $(git rev-list --no-merges "${base}..${head}"); do
  author="$(git log -1 --format='%an <%ae>' "$commit")"
  if git log -1 --format='%B' "$commit" | grep -qxF "Signed-off-by: ${author}"; then
    echo "ok       $(git log -1 --format='%h %s' "$commit")"
  else
    echo "MISSING  $(git log -1 --format='%h %s' "$commit")  (expected: Signed-off-by: ${author})"
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  cat <<'EOF'

Some commits are not signed off. Add the sign-off with:
  git rebase --signoff <base-branch>
and force-push your branch. See CONTRIBUTING.md (Developer Certificate of Origin).
EOF
  exit 1
fi
echo "All commits are signed off."

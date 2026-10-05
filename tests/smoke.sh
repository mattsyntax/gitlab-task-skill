#!/usr/bin/env bash
# Offline smoke test for scripts/gitlab.py: runs every command against the eval fixtures
# in mock mode, plus the safety checks (unknown labels, plain HTTP). No token, no network.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
gl="$repo/scripts/gitlab.py"
ws="$(mktemp -d)"
trap 'rm -rf "$ws"' EXIT
cd "$ws"
bash "$repo/evals/fixtures/scaffold.sh"

fail() { echo "FAIL: $*" >&2; exit 1; }
expect() { grep -q -- "$1" <<<"$2" || fail "expected '$1' in: $2"; }

expect "BUG 🐛" "$(python3 "$gl" labels)"
expect "#87	closed" "$(python3 "$gl" issues)"
python3 "$gl" issues --out "$ws/issues.json" >/dev/null && [ -s "$ws/issues.json" ] || fail "issues --out"
expect "employee photo" "$(python3 "$gl" issue 87)"
expect "2 issues with" "$(python3 "$gl" relabel "BUG 🐛" "Improvement" --dry-run)"
[ "$(python3 "$gl" dates --from 2026-09-21 --to 2026-09-25 --count 3 --seed 1 | wc -l)" -eq 3 ] || fail "dates"

mkdir -p docs/tasks
printf -- '---\ntitle: Period filter (backend)\nlabels: Backend, Feature ✨\n---\n## Description\nx\n' > docs/tasks/01-filter.md
printf -- '---\ntitle: Period filter (frontend)\nlabels: FrontEnd\ndepends_on: 01-filter.md\n---\nNeeds "Period filter (backend)".\n' > docs/tasks/02-filter-frontend.md
expect '(#<iid>)' "$(python3 "$gl" create-all docs/tasks --dry-run)"
out="$(python3 "$gl" create-all docs/tasks)"
expect "#91" "$out"
expect "linked #91" "$out"
! grep -q '^iid:' docs/tasks/*.md || fail "mock mode wrote iid back into a draft"

printf -- '---\ntitle: Bad\nlabels: No such label\n---\nx\n' > docs/tasks/03-bad.md
! python3 "$gl" create docs/tasks/03-bad.md --dry-run 2>/dev/null || fail "unknown label accepted"

rm .env
! GITLAB_API=http://gitlab.example.com/api/v4 GITLAB_TOKEN=x python3 "$gl" labels 2>/dev/null || fail "plain HTTP accepted"
expect "Refusing plain HTTP" "$(GITLAB_API=http://gitlab.example.com/api/v4 GITLAB_TOKEN=x python3 "$gl" labels 2>&1 || true)"

echo "smoke test passed"

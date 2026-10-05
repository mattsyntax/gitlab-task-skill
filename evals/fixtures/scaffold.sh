#!/usr/bin/env bash
# Seeds an eval workspace: a small demo app in a git repo whose origin is a GitLab
# project, with the gitlab.py mock mode pointed at canned labels and issues.
set -euo pipefail
fixtures="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp -R "$fixtures/app/." .
mkdir -p .gitlab-mock
cp "$fixtures/gitlab/"*.json .gitlab-mock/
printf 'GITLAB_MOCK=.gitlab-mock\n' > .env
printf '.env\n.gitlab-mock/\nnode_modules/\n' > .gitignore

git init -q
git remote add origin git@gitlab.example.com:demo/app.git
git add -A
git -c user.name=eval -c user.email=eval@example.com commit -qm "Initial commit"

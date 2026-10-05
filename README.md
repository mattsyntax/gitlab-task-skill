# gitlab-task

[![CI](https://github.com/mattsyntax/gitlab-task-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/mattsyntax/gitlab-task-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-d97757)](https://code.claude.com/docs/en/plugins)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776ab)](scripts/gitlab.py)
[![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](scripts/gitlab.py)

English | [Русский](README.RU.md)

A Claude Code skill that turns a plain request like "add a ticket: managers need a week/month filter on the leaderboard" into well-written GitLab issues. It checks existing issues and labels, reads the code, writes drafts to `docs/tasks/` for your review, and sends them to GitLab only after an explicit "ok".

## Example

> **You:** add a ticket: the recruiter leaderboard only shows all-time numbers, managers need to filter it by week and month

Claude finds the labels and the related issue #85, reads `server/routes/leaderboard.js` and `web/src/pages/Leaderboard.jsx`, and writes two linked drafts. This is the backend one, written by the skill against the demo project in [`evals/fixtures`](evals/fixtures):

```markdown
---
title: Leaderboard: filter by week and month (backend)
labels: Backend, Feature ✨, To Do 📋
---
## Description
The recruiter leaderboard only shows totals for all time, so managers can't see who performed best this week or this month. Recent results get lost behind years of history, and the leaderboard can't be used for weekly or monthly reviews.

## Goal
Let managers compare recruiters over a recent period, so the leaderboard reflects current performance and can be used in regular team reviews.

## Implementation plan
**Technical details:** `GET /api/leaderboard` in `server/routes/leaderboard.js` counts closed vacancies per recruiter with no date condition. The query needs an optional period that limits vacancies by the date they were closed. Related: #85 (CSV export of the leaderboard) - the export should use the same period once both are done.

*What to change:*
- [ ] Agree with the product owner: does "week" mean the calendar week starting on Monday or the last 7 days, and the same for "month"?
- [ ] Accept an optional `period` query parameter: `week`, `month` or `all` (default `all`, so current clients keep working).
- [ ] Filter vacancies by their closing date for `week` and `month`; check that `vacancies` stores that date and add a column with a migration if it doesn't.
- [ ] Answer 422 on an unknown `period` value.

## Acceptance criteria
*How to tell the task is done:*
1. `GET /api/leaderboard` without parameters returns the same all-time numbers as before.
2. `GET /api/leaderboard?period=week` and `?period=month` count only vacancies closed in that period.
3. `GET /api/leaderboard?period=year` returns 422.
```

<details>
<summary>The frontend draft</summary>

```markdown
---
title: Leaderboard: filter by week and month (frontend)
labels: FrontEnd, Feature ✨, To Do 📋
depends_on: 01-leaderboard-period-filter.md
---
## Description
Managers need a way to switch the recruiter leaderboard between this week, this month and all time, so they can see who is performing best right now.

## Goal
Make recent results visible on the leaderboard without leaving the page.

## Implementation plan
**Technical details:** `web/src/pages/Leaderboard.jsx` always loads `/api/leaderboard` without parameters. Depends on "Leaderboard: filter by week and month (backend)", which adds the `period` parameter.

*What to change:*
- [ ] Add a Week / Month / All time switch above the table, All time selected by default.
- [ ] Reload the table with `?period=week|month|all` when the switch changes.
- [ ] Show which period is selected in the table caption.

## Acceptance criteria
*How to tell the task is done:*
1. The leaderboard opens with All time selected and shows the same numbers as before.
2. Choosing Week or Month updates the table without reloading the page.
3. The selected period is visible above the table.
```

</details>

> **You:** ok, push it to gitlab

```
#91  Leaderboard: filter by week and month (backend)   https://gitlab.example.com/demo/app/-/issues/91
#92  Leaderboard: filter by week and month (frontend)  https://gitlab.example.com/demo/app/-/issues/92  linked #91
```

The frontend issue now says `Depends on "Leaderboard: filter by week and month (backend)" (#91)`.

## Features

- Checks existing issues for duplicates: on an exact match it asks "reopen #N or file a new one?", adjacent issues are mentioned as "Related: #N".
- Uses only labels that already exist in the project and follows the style of recent issues. An unknown label blocks sending, because GitLab would otherwise silently create a new one.
- Writes the issue in the language of the request (Russian or English) and for two audiences: "Description" and "Goal" in plain language for QA and managers, "Implementation plan" with technical details from the code for the developer.
- Splits backend and frontend work into two linked issues: the backend issue number is filled into the frontend one, plus a `relates_to` link in GitLab.
- Bugs noticed along the way are not buried in the task; the skill offers to file them separately.
- Imports earlier work with its history: on request, sets `created_at` in the past, on working days and hours, never in the future and never before an issue it references.
- Never creates an issue twice: after sending, the issue number (`iid`) is written back into the draft.

## Installation

As a Claude Code plugin (recommended, updates via `/plugin`):

```
/plugin marketplace add mattsyntax/gitlab-task-skill
/plugin install gitlab-task@gitlab-task-skill
```

Or as a plain skill:

```bash
git clone https://github.com/mattsyntax/gitlab-task-skill.git ~/.claude/skills/gitlab-task
```

Requires `python3` 3.9+ (standard library only) and `git`. Restart Claude Code after installing.

## Project setup

In the root `.env` of the repository you file issues for (keep it in `.gitignore`):

```
GITLAB_ACCESS_TOKEN_WRITE=<personal access token with api scope>
# only if the API is not at https://<origin host>/api/v4:
GITLAB_API=https://gitlab.example.internal/api/v4
```

- The project is taken from `git remote get-url origin`. Override with `GITLAB_PROJECT=group/repo`.
- `GITLAB_TOKEN` works instead of `GITLAB_ACCESS_TOKEN_WRITE`. Environment variables take precedence over `.env`.
- `created_at` is only honoured if the token belongs to an admin or project owner; otherwise GitLab uses the current date.
- The issue template is the project's `docs/tasks/00-index.md`. If it doesn't exist, the skill creates it from `assets/task-template.en.md` or `assets/task-template.ru.md`, depending on the language of the request.

### Try it without a token

Set `GITLAB_MOCK` to a folder with `labels.json` and `issues.json` (see [`evals/fixtures/gitlab`](evals/fixtures/gitlab) for the format). The script then answers from those files, never touches the network, and `create` only prints what it would send:

```
GITLAB_MOCK=.gitlab-mock
```

## Usage

Just ask Claude Code in Russian or English, in your own words. Examples:

- `create an issue: make the picker list endpoints kebab-case`
- `file a bug: uploading an employee photo returns 404`
- `add a ticket: the leaderboard needs a week/month filter`
- `создай задачу: в рейтинге нужен фильтр по неделе и месяцу`
- `push it to gitlab` / `закинь в гитлаб` - after reviewing the drafts

Russian and English are supported, both for trigger phrases ("create an issue", "file a bug", "создай задачу", "заведи таск") and for confirmations ("ok", "go ahead", "push it to gitlab", "ок", "закинь в гитлаб"). The issue is written in the language you asked in: English sections are Description / Goal / Implementation plan / Acceptance criteria, Russian ones are Описание / Цель / План реализации / Критерии приёмки. Labels stay as they are in the project.

The flow is always the same: research (labels, duplicates, code), drafts in `docs/tasks/`, review and `--dry-run` validation, your "ok", sending, list of links.

## Script

`scripts/gitlab.py` can also be run by hand from inside the repository:

| Command | What it does |
|---|---|
| `labels` | list project labels |
| `issues [--state all\|opened\|closed] [--out file.json]` | all issues, paginated by 100 |
| `issue <iid>` | one issue with its description |
| `create <file.md> [--dry-run]` | send one draft |
| `create-all [dir] [--dry-run]` | send all drafts without `iid`: dependencies first, the rest by date |
| `dates --from YYYY-MM-DD [--to YYYY-MM-DD] --count N [--tz +03:00] [--seed N]` | pick timestamps on working days and hours |
| `relabel "Old" "New" [--dry-run]` | replace a label on every issue |

## Draft format

```markdown
---
title: Short clear title
labels: BUG 🐛, Backend, To Do 📋, 🔴 High priority
created_at: 2026-09-23T14:26:00+03:00   # optional, when importing earlier work
depends_on: 11-manual-bonuses.md        # optional, for the frontend half
---
## Description
## Goal
## Implementation plan
**Technical details:** ...
- [ ] ...
## Acceptance criteria
1. ...
```

After sending, the script adds `iid: <number>` to the front matter, and reruns skip that file.

## Security

- The token is read from the environment or `.env` and is never printed. The skill tells Claude never to print or `cat` `.env`.
- Plain `http://` API URLs are refused, because the token would travel unencrypted. For an internal GitLab that only speaks HTTP, opt in yourself with `GITLAB_ALLOW_INSECURE=1` in `.env`; the skill never suggests it.
- Nothing is sent without your explicit confirmation, and `--dry-run` validation runs before every send.

## Development

```bash
bash tests/smoke.sh                          # offline test of every script command in mock mode
claude plugin validate --strict .            # manifests
claude plugin eval . --scaffold --allow-tools Bash Write Edit --trust-plugin   # behaviour evals, paid model calls
```

CI runs the first two on every push. The evals in [`evals/`](evals) seed a demo repository with mocked GitLab data and check that the skill splits backend/frontend work, catches a duplicate bug, picks valid historical dates, and never sends anything without confirmation. They call the model on your account, so they run by hand before a release. On Linux they need `bubblewrap` and `socat` for the Bash sandbox.

The sandbox also refuses to start if `~/.docker` contains symbolic links (the error mentions the Docker credential store). Docker Desktop's WSL integration creates two of them, `contexts` and `features.json`. Move them out of `~/.docker` for the duration of the run and put them back afterwards; renaming them inside `~/.docker` is not enough:

```bash
mkdir -p /tmp/docker-links && mv ~/.docker/contexts ~/.docker/features.json /tmp/docker-links/
claude plugin eval . --scaffold --allow-tools Bash Write Edit --trust-plugin
mv /tmp/docker-links/* ~/.docker/
```

`--case` takes one glob; pass it once (`--case duplicate-bug`), a repeated flag keeps only the last value.

Releasing:

1. Bump `version` in `.claude-plugin/plugin.json` (users who installed via `/plugin` stay on the old version until it changes).
2. Run the evals.
3. `git tag vX.Y.Z && git push origin master --tags`, then create a GitHub Release from the tag with the changes.

## Limitations

- "blocks / is blocked by" links require GitLab Premium, so `relates_to` is used.
- The issue number (`iid`) is always the next one at send time, even if `created_at` is in the past.

## Layout

```
gitlab-task-skill/
├── .claude-plugin/
│   ├── plugin.json              Claude Code plugin manifest
│   └── marketplace.json         lets the repo act as a plugin marketplace
├── .github/workflows/ci.yml     manifest validation and smoke test
├── SKILL.md                     instructions for Claude
├── scripts/gitlab.py            GitLab API client (with mock mode)
├── assets/task-template.*.md    issue templates, English and Russian
├── evals/                       claude plugin eval cases and the demo project fixtures
├── tests/smoke.sh               offline smoke test
├── README.md / README.RU.md
└── LICENSE
```

## License

MIT, see [LICENSE](LICENSE).

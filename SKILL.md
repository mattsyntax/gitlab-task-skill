---
name: gitlab-task
description: Create GitLab issues (tasks, bugs, improvements) for the current repository - researches existing issues for duplicates, picks existing labels, drafts issues as markdown files in docs/tasks/ for review, splits backend/frontend work into linked issues, and only after explicit approval sends them via the GitLab API (optionally with historical created_at dates when importing or backfilling earlier work). Supports Russian and English - the issue is written in the language of the request. Use this whenever the user wants to create, file or draft a task, issue, ticket or bug report in Russian or English, in any phrasing - e.g. "создай задачу", "заведи таск", "заведи баг", "закинь в гитлаб", "create an issue", "file a bug", "add a ticket", "push it to gitlab" - or turns review/audit findings into tasks, even if they don't say "GitLab" explicitly but the repo's origin is a GitLab instance.
---

# GitLab task

Turn a request ("+ таск: эндпоинты через тире", "сделай задачи по найденному") into well-written GitLab issues. The flow is always: **research -> drafts on disk -> user approval -> send**. Drafts first, because issues are visible to the whole team instantly, notify people, and can't be cleanly un-created; a file in `docs/tasks/` costs nothing to fix.

Helper script (bundled): `python3 "${CLAUDE_SKILL_DIR}/scripts/gitlab.py" <command>` - run it from inside the repository. Run it with no arguments for the full usage text. Templates: `${CLAUDE_SKILL_DIR}/assets/task-template.ru.md` and `${CLAUDE_SKILL_DIR}/assets/task-template.en.md`.

## 1. Setup check

- The script reads the project from `git remote get-url origin`, the token from `GITLAB_ACCESS_TOKEN_WRITE` (or `GITLAB_TOKEN`) and the API base from `GITLAB_API`, each from the environment or the repo's root `.env`. Never print, echo or cat the token or the `.env` file; grep for key names only.
- If the API can't be reached over HTTPS, report the error and stop. Don't suggest switching to plain HTTP: the token would travel unencrypted. The script only accepts an `http://` `GITLAB_API` when the user has set `GITLAB_ALLOW_INSECURE=1` themselves.
- If `GITLAB_MOCK` is set (in the environment or `.env`), the script answers from local JSON fixtures and never sends anything. Follow the same flow, and say in the final report that nothing reached GitLab.
- Tasks live in `docs/tasks/` of the repo. If the folder or its `00-index.md` template is missing, create them from the bundled template in the language of the request (`task-template.ru.md` or `task-template.en.md`). The project's own `00-index.md` wins if it exists - it may have been customised.

## 2. Research before writing

1. `gitlab.py labels` - only use labels that already exist; the script refuses unknown ones because GitLab would silently create new labels. When there are near-duplicates (e.g. `Backend` vs `Backend ⚙️`), copy the style of the most recent issues.
2. `gitlab.py issues --out <scratch>/issues.json` (paginates at 100/page) - scan titles for overlap. Save the list to a scratch/temp dir, never next to the drafts: everything in the tasks folder looks like something to send. For likely duplicates read the body with `gitlab.py issue <iid>`.
   - **Same work already filed** (same symptom/steps, open or closed): stop before drafting and ask the user: reopen/comment on #N, or file a new issue anyway (e.g. it regressed after a fix). Write the draft only after the answer - a draft written "just in case" is wasted effort and invites sending a duplicate.
   - **Only adjacent** (overlapping area, different work): go ahead and mention it as "Связано: #N" in the technical details.
3. Look at the code enough to fill the technical details accurately (file paths, classes, routes, tables). Wrong technical details waste the implementer's time more than missing ones.
   - Bugs you notice along the way that are not part of the request (e.g. a crash on deleted users while researching a filter feature) don't get buried inside the requested task: list them separately in the review message and offer to file each as its own BUG draft. Separate issues get their own priority and owner, and a bug hidden in a feature task is usually forgotten.
4. Write the issue in the language the user wrote the request in: Russian or English (the two supported languages; for anything else ask which of the two to use). The user knows who will read the issue; the language of older issues doesn't override that. Template headings, the "Technical details" label, the backend/frontend title suffixes and "related to" wording follow that language (see section 3). Labels stay exactly as they exist in the project.

## 3. Draft format

One file per issue: `docs/tasks/NN-short-slug.md`, numbered after the last existing draft. Front matter, then the body following the template (shown in Russian; for an English request use `## Description`, `## Goal`, `## Implementation plan` with `**Technical details:**` and `*What to change:*`, `## Acceptance criteria`, split titles suffixed `(backend)` / `(frontend)`):

```markdown
---
title: Короткий понятный заголовок
labels: BUG 🐛, Backend, To Do 📋, 🔴 High priority
created_at: 2026-09-23T14:26:00+03:00   # only if dates were requested, see section 5
depends_on: 11-manual-bonuses.md        # only for the dependent half of a split task
---
## Описание
## Цель
## План реализации
**Технические детали:** ...
*Что нужно изменить:*
- [ ] ...
## Критерии приёмки
*Как понять что задача готова:*
1. ...
```

The audience differs per section, which is why the split matters:

- **Описание** and **Цель** are read by QA, managers and the product owner. Plain human language: what is wrong or missing, who is affected, why it matters, reference to the spec (ТЗ п. X) if there is one. No class names, methods, tables, env vars or code. Bad: "Бонус считается в CalcRecruiterTasksJob по коэффициентам из таблицы bonuses". Good: "Сейчас вручную начислить бонус нельзя: система считает бонус сама по количеству выполненных задач."
- **План реализации** is for the developer. Start with a `**Технические детали:**` paragraph (where in the code, how it works now, related issues), then checkboxes with concrete changes. Free text is fine here, not only checkboxes.
- **Критерии приёмки**: observable behaviour a tester can verify; endpoints are fine when that is what gets tested.
- Typography: straight quotes `"..."` and a plain hyphen `-`. No `«»`, no em dash, no `…`, so issue text looks the same whoever drafted it.
- Product decisions you cannot make (e.g. "should closed leads ever reopen?") go in as the first checkbox "Согласовать с владельцем продукта: ...", not as an assumption.

### Backend / frontend split

If the work touches both backend and frontend, make two issues: `NN-slug.md` (label `Backend`) and `NNf-slug-frontend.md` (label `FrontEnd`), titles suffixed `(бэкенд)` / `(фронт)` (`(backend)` / `(frontend)` in English) when the base title is shared. The backend issue covers logic, permissions and the data the UI needs (e.g. "отдавать признак can_edit"). The frontend issue describes what the user sees, and its technical details say it depends on the backend issue by quoting its exact title in straight quotes. Add `depends_on: NN-slug.md` to the frontend file: on send, the script appends "(#iid)" after the quoted title and creates a `relates_to` link (blocks/is_blocked_by needs GitLab Premium).

## 4. Review gate

After writing drafts, validate them: `gitlab.py create-all docs/tasks --dry-run` (checks labels, dependency order and title substitution without sending). Then show the user a compact table: file, title, labels, date if any, plus adjacent issues you linked, side bugs found along the way (with an offer to file them separately) and decisions that need their input. Stop and wait for an explicit go-ahead in Russian or English ("ок", "да", "закинь в гитлаб", "go ahead", "push it to gitlab"). Feedback on drafts means editing the files, not sending.

## 5. Optional: historical created_at

For importing or backfilling work that really happened earlier (tasks moved from another tracker, drafts written before the GitLab project existed), only when the user asks for dates in the past. Rules: working days Mon-Fri, 09:20-12:00 and 13:00-17:30 local time (+03:00 unless told otherwise), never in the future. Generate them with `gitlab.py dates --from YYYY-MM-DD [--to YYYY-MM-DD] --count N`, then assign in a logical order:
- a backend issue gets an earlier time than its frontend counterpart;
- an issue that says "Связано: #N" must not be dated before issue #N was created (a reference to an issue that did not exist yet makes the history inconsistent) - move such issues to dates after the referenced ones.

`created_at` is only honoured for admins / project owners; otherwise GitLab silently uses "now". Issue numbers (iid) are always sequential at send time regardless of dates - mention this once.

## 6. Send

`gitlab.py create-all docs/tasks` sends every draft without an `iid`, dependencies first, then by `created_at`. After each issue is created its `iid` is written back into the draft's front matter, so a rerun after a failure never duplicates anything. Report the resulting `#iid` + URL list to the user.

## Other commands

- `gitlab.py relabel "Old" "New" [--dry-run]` - swap a label on every issue (all states). Always dry-run first and report the count; it touches many issues and notifies watchers.
- `gitlab.py issue <iid>` - read one issue with its description.

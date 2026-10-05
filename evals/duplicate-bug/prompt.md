---
description: Bug report that matches an already closed issue
expected_outcome: Finds closed #87 with the same symptom and asks whether to reopen it or file a new issue, before writing any draft. Nothing is sent.
tags: [bug, duplicate]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Bash, Write, Edit]
---

file a bug: uploading a profile photo for an employee returns 404, QA reproduced it on staging

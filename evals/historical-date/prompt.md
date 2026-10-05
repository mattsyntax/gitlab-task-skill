---
description: Small backend task with a creation date in the past
expected_outcome: One English backend draft with created_at produced by the dates command, on a weekday inside 09:20-12:00 or 13:00-17:30, not in the future. Nothing is sent.
tags: [dates]
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Bash, Write, Edit]
---

create an issue to move the fake-data library from dev dependencies to regular ones, production seeding fails without it. we discussed it last week, so date it to last week

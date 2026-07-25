---
name: plan
description: "Create a lightweight file-backed plan only when the user explicitly requests one or a Louie task needs durable cross-session handoff. Use normal in-conversation planning for ordinary work."
---

# Durable Task Plans

Create `plans/<task>/plan.md` only for an explicit request, multi-session work, or handoff. Do not create one merely because a task has several steps.

Record the goal, constraints, repositories/environments, success criteria, and a short ordered checklist. Mark exactly one item `IN PROGRESS`.

Update at meaningful boundaries: a completed step, decision, blocker, failed validation, or handoff. Keep durable facts and reproducible validation commands; do not log every read or command. Preserve prior context when adding a new phase. Finish by recording validation evidence, unresolved risks, and the next action.

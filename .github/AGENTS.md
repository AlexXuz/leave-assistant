# Contributor workflow

Keep the Day1–26 sequence and preserve learner-owned answers. main is an
unlearned starter; alexstudy is the author's personal study branch. Never reset
learner code or data to make a demo pass. Use an isolated worktree for releases.

Runnable references live under app/course/examples. Reference checks never
complete a lesson; learner tasks require independent evidence and review.
Prefer browser-based practice with real persisted business state. Keep database
identity, authorization, explicit confirmation and idempotency server-owned.

Run the relevant checks listed in README and docs/contributing.md. Never commit
credentials, local environments, model weights or private learner artifacts.
No force push or history rewrite. Do not publish or message others without
authorization. See app/AGENTS.md and course/AGENTS.md for scoped rules.

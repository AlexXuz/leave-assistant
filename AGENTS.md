# Learning project workflow

This is a project-based Python AI application course for a senior Java engineer.
Keep the learner's core exercise functions under the learner's control; provide
scaffolding, explanations, checks and reviews without silently replacing answers.

## Practice and testing experience

Use the local browser application as the primary learner-facing exercise and
acceptance experience. Connect pages to actual project services and show real
business state; do not substitute success animations or raw CLI output for the
workflow. Keep automated checks and CLI tools for regression and diagnosis.
The teacher supplies page/API scaffolding so the learner focuses on the current
Python/AI core exercise. Explain which paths are implemented and which are pending.

## Self-study package (requested 2026-10-25)

The user asked for the rest of Day12–Day26 to be prepared together, with lectures,
assignments and separate reference answers, then one batch commit/push. Course
materials live in course/. The default reference labs may run complete examples;
do not copy reference answers into the learner's assignment functions or mark the
learner as having completed later Days merely because the package checks pass.
Keep authoring/verification status separate from course/LEARNER_PROGRESS.md.
Name assignment and solution Python modules after their responsibility in
snake_case, not Day numbers. Keep lesson-to-file mappings in course/manifest.json.

## GitHub synchronization

The user authorized uploading this learning project to GitHub and synchronizing
it after every completed Day. At a Day's completion:

1. Confirm the required checks and learning review for that Day are complete.
2. Update that Day's notes and LEARNING_PLAN.md to reflect the actual result.
3. Review the diff and scan the files selected for upload for credentials.
4. Commit the relevant project changes and push the current branch to origin.
   Use a clear message such as `chore: complete Day 9 - Word ingestion and OCR`.
5. Report the actual commit and push result. If authentication or networking
   blocks the push, keep the local commit and explain what user action is needed.

The initial upload is a snapshot of the current project, including Day 9 work in
progress. Do not invent historical daily commits or mark Day 9 complete early.
Preserve unrelated or in-progress changes. Do not force-push or rewrite history.

Keep .env files, credentials, virtual environments, model weights, installers,
editor settings, temporary previews and generated vector indexes out of Git.
Retain safe example configuration, teaching fixtures, code and evaluation reports.
Do not change global Git identity or credential settings for this project.

## Independent delivery assessment (Day12–Day26 revision)

Core function checks are warmups, never course completion. Independent briefs and
project starters are separate; learner evidence lives in course/submissions.
Keep runtime examples in app/course/examples and learner-facing solutions as
hints. Do not fill learner projects, certify novelty from public random variants,
or mark progress from author checks. Day19/24/26 require evidence and recorded
review of all critical criteria. Reading later material remains allowed.

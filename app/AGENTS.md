# Application and learner-code workflow

This repository has an initialized teaching branch (main) and a personal study
branch (alexstudy). Check course/profile.json before changing learner code.
Never clear a learner's implementation or database to repair a demo.

Modules listed in course/foundation_exercises.json and app/leave_graph_routing.py
are learner-facing exercises. app/course/examples contains explicit runnable
reference implementations. Keep those roles separate; reference checks do not
complete a lesson. Preserve learner answers when reviewing, unless the human
explicitly asks you to implement or reset them.

Use the browser for learning/acceptance and CLI checks for regression. Keep
identity, confirmation and transaction boundaries deterministic and server-owned.
Never log credentials or copy private state into the public template.

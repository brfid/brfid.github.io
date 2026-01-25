# Agent Notes (Repo)

## WIP Sync Workflow (multi-host)

Use a dedicated WIP branch to sync in-progress work between machines without
deploying/publishing it from `main`.

- Create a WIP branch per task (recommended):
  - `wip/<topic>` or `wip/<host>/<topic>`
- Commit early/often on the WIP branch and push it to the remote:
  - `git checkout -b wip/<topic>`
  - `git add -A && git commit -m "WIP: <message>"`
  - `git push -u origin wip/<topic>`
- On another host, pull the WIP branch:
  - `git fetch origin`
  - `git checkout -t origin/wip/<topic>`
- When ready, merge into `main` (or fast-forward `main` to the WIP branch).

Notes:
- Prefer WIP branches over `git stash` for multi-day work (stash is local-only
  unless you explicitly move it).
- If you must stash: `git stash push -u -m "wip"` and `git stash pop`.


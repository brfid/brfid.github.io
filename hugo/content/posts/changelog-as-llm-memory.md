---
title: "Using CHANGELOG.md as LLM session memory"
date: 2026-02-21
draft: false
tags: ["llm", "documentation", "workflow"]
---

Most LLM coding assistants have no memory between sessions. You reload the conversation,
re-explain the project, re-establish context, and hope the model picks up where it left off.
The usual workaround — a large `CLAUDE.md` or `AGENTS.md` with everything in it — breaks
down quickly: it grows without discipline, becomes a dumping ground, and gives the model
no signal about what is *currently* changing.

Treating `CHANGELOG.md [Unreleased]` as the primary mutable state document is a cleaner
approach.

## How it works

[Keep a Changelog](https://keepachangelog.com/) defines a format most LLMs recognize on
sight: a fenced `[Unreleased]` block at the top, dated releases below. The convention is
self-describing — LLMs understand without being told that `[Unreleased]` is active work
and dated entries are history.

That structure maps directly onto session continuity:

- **`[Unreleased]`** — mutable, updated every session. Current state, active priorities,
  blockers, decisions pending. The model reads this first.
- **Dated entries** — append-only history. Evidence that decisions happened and why,
  available when the model needs depth.

The `AGENTS.md` or `CLAUDE.md` file becomes stable configuration: conventions, file paths,
source-of-truth map. It changes rarely. The changelog absorbs the churn.

## The session start instruction

One line at the top of `AGENTS.md` is sufficient:

```
Read CHANGELOG.md [Unreleased] at session start.
```

With that, the model knows where it is, what is in flight, and what to do next without
requiring re-explanation each session.

## What goes in [Unreleased]

Explicit subsections help keep it readable:

```markdown
## [Unreleased]

### Current State
One-paragraph snapshot. Where things stand right now.

### Active Priorities
Ordered list of what needs to happen next.

### In Progress
What the model started in the current session.

### Blocked
Anything waiting on external action.

### Decisions Needed
Open questions the model should surface, not resolve unilaterally.

### Recently Completed
What just shipped. Moves to a dated entry on the next commit.
```

The model updates `[Unreleased]` at the end of each session, and the next session
reads it cold and picks up cleanly.

## Scope and limits

This is not a replacement for good project documentation. Architectural decisions,
integration details, and source-of-truth maps still belong in stable docs. The changelog
is a session state layer, not the full context layer.

It also does not solve context window limits on large projects — it reduces the cost of
context loading by giving the model a small, structured, current-state document instead
of a stale megafile to scan.

The format is version-controlled, well-understood by most tools, and if you are already
using Keep a Changelog, the incremental cost to adopt this pattern is low.

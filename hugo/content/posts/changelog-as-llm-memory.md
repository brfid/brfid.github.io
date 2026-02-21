---
title: "Using CHANGELOG.md as LLM session memory"
date: 2026-02-21
draft: false
tags: ["llm", "documentation", "workflow"]
---

Most LLM assistants don't maintain memory between sessions. The standard workaround — a large `CLAUDE.md` or `AGENTS.md` with everything in it — breaks down quickly. What's more, it duplicates other content in your repo, growing the documentation maintenance surface without adding value.

Lately I avoid this problem by treating `CHANGELOG.md` as my LLM's memory — specifically the `[Unreleased]` section from the format standardized by [Keep a Changelog](https://keepachangelog.com/), which becomes the primary mutable state document.

## Why it works

[Keep a Changelog](https://keepachangelog.com/) defines a format most LLMs recognize on sight: a fenced `[Unreleased]` block at the top, dated releases below. Most LLMs recognize the convention: `[Unreleased]` is active work, dated entries are history.

That maps directly onto what you need for session continuity:

- **`[Unreleased]`** — mutable, updated every session. Current state, active priorities, blockers, decisions pending. The model reads this first.
- **Dated entries** — append-only history. Evidence that decisions happened and why. The model reads these to reconstruct context if it needs depth.

The AGENTS.md (or CLAUDE.md) file becomes stable configuration: conventions, file paths, source-of-truth map. It changes rarely. The CHANGELOG takes on everything that does change.

## The session start instruction

One line at the top of `AGENTS.md` is enough:

```
Read CHANGELOG.md [Unreleased] at session start.
```

From there the model knows where it is, what's in flight, and what to do next — without re-explanation.

## What goes in [Unreleased]

I use explicit subsections:

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

The model updates `[Unreleased]` at the end of each session. The next session reads it cold and picks up cleanly.

## What this is not

This is not a replacement for good project documentation. Architectural decisions, integration details, and source-of-truth maps still belong in stable docs. The changelog is the *session state layer*, not the full context layer.

It also does not solve the problem of context window limits on large projects. It reduces the cost of context: the model loads a small, structured, current-state document instead of scanning a stale megafile.

## Result

Sessions are shorter to start, more reliable to hand off, and easier to audit. The changelog does the work it was always supposed to do — track what changed and when — and the LLM does less redundant orientation work each time.

The format is well-understood, self-describing, and version-controlled. If you're already using Keep a Changelog, the only addition is a discipline: update `[Unreleased]` at the end of each session.

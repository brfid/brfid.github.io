# Documentation Index

Central hub for all project documentation.

## Quick Start

New to the project? Start here:

1. **`../STATUS.md`** - Current project status
2. **`COLD-START.md`** - Quick onboarding for new sessions
3. **`../README.md`** - Project overview
4. This index

## Project Documentation

### Core
- **`COLD-START.md`** - Quick start guide for LLM agents
- **`../AGENTS.md`** - Repository workflow and coding instructions

### Project Management
- **`project/transport-archive.md`** - Archived VAX console/FTP transfer approaches

## Domain-Specific Documentation

### ARPANET Stage
- **`arpanet/INDEX.md`** - ARPANET documentation hub
- **`arpanet/progress/NEXT-STEPS.md`** - Current active execution path
- **`arpanet/progress/PHASE3-PROGRESS.md`** - Timeline and progress log
- **`arpanet/progress/PHASE1-PROGRESS.md`** - Historical Phase 1 (completed)
- **`arpanet/progress/PHASE2-PROGRESS.md`** - Historical Phase 2 (completed)

### VAX/SIMH Stage
- Implementation in `../vax/` directory (scripts and `bradman.c`)
- Transport history: `project/transport-archive.md`
- Current approach: Tape (TS11) transfer via Docker SIMH

## Source of Truth Map

| Topic | File |
|-------|------|
| Project snapshot | `../STATUS.md` |
| Documentation hub | This file |
| ARPANET next steps | `arpanet/progress/NEXT-STEPS.md` |
| ARPANET progress | `arpanet/progress/PHASE3-PROGRESS.md` |
| VAX transport history | `project/transport-archive.md` |
| Agent workflow | `../AGENTS.md` |

## Adding New Documentation

When creating new docs:

1. Add to appropriate section in this index
2. If domain-specific, also add to domain INDEX (`arpanet/INDEX.md`, etc.)
3. Update `../STATUS.md` if it represents a milestone
4. Use clear headers and follow existing doc patterns

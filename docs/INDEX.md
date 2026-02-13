# Documentation Index

Central hub for all project documentation.

## Quick Start

New to the project? Start here:

1. **`../README.md`** - Project overview
2. **`COLD-START.md`** - Quick onboarding for new sessions
3. **`../STATUS.md`** - Current project status
4. This index
5. **`vax/INDEX.md`** - VAX/BSD documentation

Then apply repository workflow constraints from `../AGENTS.md`.

## Project Documentation

### Core
- **`COLD-START.md`** - Quick start guide for LLM agents
- **`../AGENTS.md`** - Repository workflow and coding instructions

### Project Management
- **`project/transport-archive.md`** - Archived VAX console/FTP transfer approaches
- **`project/PLAN.md`** - Project planning document

## Machine-Specific Documentation

### VAX / BSD
- **`vax/INDEX.md`** - VAX/BSD documentation hub
- **`vax/README.md`** - VAX implementation details
- **`vax/examples/`** - VAX YAML examples

### PDP Systems
- **`pdp/INDEX.md`** - PDP documentation hub (PDP-10, PDP-11)
- **`pdp/pdp10/`** - PDP-10/KS10/KL10 systems
- **`pdp/pdp11/`** - PDP-11/2.11BSD systems

### Integration / ARPANET
- **`integration/INDEX.md`** - Multi-machine connection documentation
- **`integration/progress/`** - Progress tracking and timelines
- **`integration/operations/`** - Integration operational guides
- **`integration/research/`** - Integration research notes

### AWS / Cloud Infrastructure
- **`aws/INDEX.md`** - AWS infrastructure documentation
- **`aws/aws-cost-optimization.md`** - Cost management

## Source of Truth Map

| Topic | File |
|-------|------|
| Project snapshot | `../STATUS.md` |
| Documentation hub | This file |
| VAX documentation | `vax/INDEX.md` |
| PDP documentation | `pdp/INDEX.md` |
| Integration/ARPANET | `integration/INDEX.md` |
| AWS infrastructure | `aws/INDEX.md` |
| Agent workflow | `../AGENTS.md` |

## Adding New Documentation

When creating new docs:

1. Add to appropriate section in this index
2. If domain-specific, also add to domain INDEX (e.g., `vax/INDEX.md`, `pdp/INDEX.md`)
3. Update `../STATUS.md` if it represents a milestone
4. Use clear headers and follow existing doc patterns

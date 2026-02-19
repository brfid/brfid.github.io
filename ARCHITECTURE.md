# Architecture

Companion docs:
- `README.md`
- `WORKFLOWS.md`
- `docs/integration/INDEX.md`

This repo builds a static resume site from `resume.yaml` and optionally runs a vintage VAX stage.

---

## Overview

1. Input: `resume.yaml`
2. Host build (`resume_generator`): HTML, PDF, VAX-stage inputs
3. Optional VAX stage (`vax/bradman.c`): generates `build/vax/brad.1`
4. Host render: `brad.1` → `site/brad.man.txt`
5. Output: deployable site artifacts in `site/`

---

## Pipeline (Diagram)

```mermaid
flowchart LR
  A[resume.yaml] --> B[Host Python: resume-gen]
  B --> C[site/resume/ (HTML)]
  B --> D[site/resume.pdf]
  B --> E[build/vax/resume.vax.yaml]

  E --> F[VAX step (bradman.c)]
  F --> G[build/vax/brad.1]
  G --> H[Host render brad.1 -> brad.man.txt]

  H --> I[site/brad.man.txt]
  B --> J[site/vax-build.log]
  C --> K[site/index.html]
  I --> K
  J --> K
```

---

## Core components

### 1) Host generator (Python)
- Entry point: `resume-gen` (see `resume_generator/cli.py`)
- Reads `resume.yaml`, generates HTML/PDF, and prepares `resume.vax.yaml`.
- Renders `brad.1` into `site/brad.man.txt` for the landing page.

### 2) VAX generator (C)
- Source: `vax/bradman.c`
- Reads `resume.vax.yaml`, produces a roff manpage (`brad.1`).
- Designed for 4.3BSD/K&R C compatibility.

### 3) VAX stage runner
- `resume_generator/vax_stage.py`
- Modes:
  - `local`: compile/run on host
  - `docker`: compile/run in SIMH 4.3BSD guest
  - `transcript`: replay stored console transcript
- Docker mode uses tape transfer by default.

### 4) ARPANET/integration context

- Multi-hop ARPANET paths are not part of active CI.
- Historical integration evidence remains under `docs/integration/`.

---

## Data formats

**Input**
- `resume.yaml` (human-edited)

**Derived**
- `build/vax/resume.vax.yaml` (simple YAML subset for the VAX C parser)
- `build/vax/brad.1` (roff manpage source)
- `site/brad.man.txt` (rendered manpage summary)
- `site/vax-build.log` (muted transcript)

---

## Runtime modes

### Local mode
```bash
.venv/bin/resume-gen --out site --with-vax --vax-mode local
```
- Compiles `bradman.c` on host
- No emulator needed


### Docker (SIMH) mode
```bash
.venv/bin/resume-gen --out site --with-vax --vax-mode docker
```
- Runs VAX 11/780 emulator
- 4.3BSD UNIX (1986)
- K&R C compiler
- TS11 tape transfer


### Production deployment (`publish-vintage*` tags)
- Single `t3a.medium` edcloud host (managed via `edcloud` CLI from sibling repo)
- Both VAX + PDP-11 containers on single Docker network (`docker-compose.production.yml`)
- Shared volume (`build-shared`) for artifact transfer between containers
- GitHub Actions workflow: SCP compose file → start containers → telnet consoles → retrieve artifacts


### Tag behavior
- `publish` or `publish-*`: Local mode (fast)
- `publish-vintage` or `publish-vintage-*`: edcloud backend (authentic 4.3BSD + 2.11BSD pipeline)


### Notes
- Docker mode uses pinned SIMH image (`jguillaumes/simh-vaxbsd`)
- File transfer via TS11 tape image
- Production backend: single edcloud host with both VAX + PDP-11 containers
- Shared volume pattern enables console-based transfer preservation
- ARPANET multi-hop removed from CI (archived)


## Historical records

Historical implementation records are intentionally retained under `docs/integration/` and `docs/legacy/`.

---

## Outputs

**Published (in `site/`)**
- `site/index.html`
- `site/resume/`
- `site/resume.pdf`
- `site/brad.man.txt`
- `site/vax-build.log`
- `site/arpanet-transfer.log` (when `--with-arpanet` is enabled)

**Internal (in `build/`)**
- `build/vax/resume.vax.yaml`
- `build/vax/brad.1`
- `build/vax/arpanet-transfer-exec.log` (execute mode scaffold output)

---

## CI/publish behavior

- `main` branch: runs checks only (no deploy).
- `publish` / `publish-*` tags: run full build + deploy to GitHub Pages.

---

## Next references

- `README.md` for quickstart commands.
- `STATUS.md` for current architecture and lifecycle boundary.
- `resume_generator/` for pipeline implementation.

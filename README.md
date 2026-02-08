# brfid.github.io

This repo deploys a minimal GitHub Pages landing/redirect for `brfid.github.io`.

- LinkedIn: `https://linkedin.com/in/brfid/`
- Architecture: see `ARCHITECTURE.md`.

## Documentation Guide

Use this map to find the current source of truth quickly.

### Start here

- `README.md` (this file): quickstart and build commands
- `ARCHITECTURE.md`: end-to-end pipeline and artifact flow
- `WORKFLOWS.md`: CI/test/publish workflow behavior

### Subsystems

- `vax/README.md`: VAX manpage generator contract (`resume.vax.yaml` → `brad.1`)
- `arpanet/README.md`: ARPANET integration overview and links to phase docs
- `arpanet_logging/README.md`: centralized logging package usage and layout
- `test_infra/README.md`: AWS test infrastructure (CDK + helper scripts)

### Historical / archived context

- `docs/transport-archive.md`: removed console/FTP transfer paths and restoration notes
- `docs/archive/`: historical design/implementation notes kept for provenance

### “Which doc should I read?”

- "How does the pipeline work?" → `ARCHITECTURE.md`
- "How do I publish?" → `WORKFLOWS.md`
- "What is current ARPANET status?" → `arpanet/README.md` then `arpanet/PHASE3-PROGRESS.md`
- "How is logging structured?" → `arpanet_logging/README.md`
- "What old approaches were removed?" → `docs/transport-archive.md`

## Local build (venv-only)

Do not install dependencies globally or modify system Python. Use the repo-local virtualenv.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m playwright install chromium
```

Generate the site:

```bash
.venv/bin/resume-gen --out site --with-vax --vax-mode local
```

### VAX/SIMH transfer mode status

Docker mode uses tape (TS11 image attached via SIMH).
Console/FTP transports were removed from the active path and archived here:
`docs/transport-archive.md`.

Implementation notes:

- VAX-side `vax/bradman.c` uses K&R-compatible fallbacks (varargs/stdlib/size_t/void* and `_doprnt`).
- Host uuencode decoding is tolerant of trailing garbage in console output.
- Docker image is pinned by digest in code for reproducibility.

Preview:

```bash
.venv/bin/python -m http.server --directory site 8000
```

Open `http://127.0.0.1:8000/`.

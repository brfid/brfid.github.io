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

## Testing quick reference (for refactor safety)

Run all tests and typing checks with the repo-local virtualenv:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m mypy resume_generator arpanet_logging tests
.venv/bin/python -m ruff check .
```

Docstrings are linted with Ruff (`D` rules) using Google convention.

Generate API docs from docstrings:

```bash
make docs
```

Output: `site/api/`

CI lanes use marker-based selection:

- Unit quality lane: `-m "unit and not docker and not slow"`
- Integration lane: `-m "integration and not docker and not slow"`

Recent high-priority characterization coverage additions are in:

- `tests/test_vax_stage.py` (VAX stage helper utilities and tape/telnet edge behavior)
- `tests/test_uudecode.py` (marker/header/end-line error handling and tolerant malformed input)
- `tests/test_pdf.py` (Playwright success path and navigation failure propagation)

Latest additions in this batch:

- `tests/test_vax_stage.py`: `TelnetSession` internals (`_read_until`, `_read_until_any`,
  `_ingest_data`, `_wait_for_xon`) plus `_pause()` and truncated telnet IAC handling.
- `tests/test_uudecode.py`: direct `_decode_uu_line()` characterization for empty/zero-length
  and truncated-line behavior.

Additional runner-level characterization now covered:

- `tests/test_vax_stage.py`: `_emit_resume_vax_yaml()` emission path, compiler/source failure
  branches, subprocess command construction (`_compile_bradman`, `_run_bradman`,
  `_run_bradman_html`), and docker-live quick-mode control flow with mocked container/session
  hooks.

Newest docker orchestration unit coverage in `tests/test_vax_stage.py`:

- non-quick `_run_docker_live()` control flow (transfer/capture/decode/render ordering)
- container cleanup on wait failure (`_stop_docker_container` in `finally` path)
- `_start_docker_container()` command construction and context values
- `_stop_docker_container()` best-effort behavior (`check=False`)
- `_container_ip()` success and empty-output failure
- `_compile_and_capture()` guest command sequencing and transcript markers

Newest characterization batch adds:

- `_write_diagnostics()` command/section loop verification
- `_transfer_guest_inputs_tape()` success-path device selection and no-device failure
- `_wait_for_console()` key branches:
  - container exits before login
  - inspect failure retry path + `vax-wait.log` evidence
  - timeout when telnet never comes up
- `TelnetSession._recv_filtered()` timeout/EOF handling

Current targeted coverage snapshot after this batch:

- `resume_generator/vax_stage.py`: **76%**
- `resume_generator/uudecode.py`: **87%**
- `resume_generator/pdf.py`: **100%**
- targeted combined total: **78%**

Highest-priority remaining test gap:

- `resume_generator/vax_stage.py` deeper interactive telnet/session control paths (`login_root`,
  `ensure_shell_prompt`, `_recover_prompt`, `_send_bytes_throttled`, and nuanced `_read_until*`
  branching), plus select host-mode orchestration lines in `_run_local` / `_run_docker` wrappers.

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

ARPANET stage scaffolding (Phase 3 incremental path):

```bash
# Safe default: dry-run scaffold only (writes site/arpanet-transfer.log)
.venv/bin/resume-gen --out site --with-vax --with-arpanet --vax-mode local

# Explicit execution mode (runs docker/logging scaffold commands)
.venv/bin/resume-gen --out site --with-vax --with-arpanet --arpanet-execute --vax-mode local
```

Notes:
- `--with-arpanet` requires `--with-vax`.
- `--arpanet-execute` requires `--with-arpanet`.
- Execution mode currently targets scaffold orchestration and writes transfer details to:
  - `site/arpanet-transfer.log`
  - `build/vax/arpanet-transfer-exec.log`
- Execute mode now includes basic resilience checks:
  - one retry for transient `docker exec` transfer failures
  - transfer output classification (empty/fatal marker detection)
  - attempt-by-attempt status breadcrumbs in `site/arpanet-transfer.log`

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

# Agent notes (repo workflow)

## Virtualenv-only

- Use the repo-local venv at `.venv/` for all Python commands.
- Do not install anything globally or modify system Python.

## Commit cadence

Commit at significant milestones so the history stays readable and bisectable. Examples:

- Landing page / UX milestone complete
- VAX stage milestone complete (local mode, then docker/SIMH mode)
- CI workflow changes
- Artifact format changes (`resume.vax.yaml`, transcript parsing, manifest format)

Before committing:

- Run `.venv/bin/python -m pytest -q`
- Run `.venv/bin/python -m ruff check .`
- Run `.venv/bin/python -m mypy resume_generator tests`

## No accidental publishing

- GitHub Pages deploy is tag-triggered (`publish` / `publish-*`). Avoid creating/pushing those tags unless you intend to deploy.

## Current VAX/SIMH status (handoff notes)

- Tape (TS11 image) is the working transfer path and is now the default for docker mode.
- Console transfer remains unreliable due to XON/XOFF flow control and SIMH telnet/DZ input drops.
- FTP transfer is not working in this setup (guest cannot reliably reach container-hosted FTP).
- `vax/bradman.c` was updated for 4.3BSD/K&R C (varargs/stdlib/size_t/void* fallbacks, `_doprnt` + `sys_errlist` stubs).
- Host uuencode decoding is tolerant of trailing garbage in console output.
- Docker image is pinned by digest in code; wait loops avoid fixed sleeps.

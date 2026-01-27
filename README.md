# brfid.github.io

This repo deploys a minimal GitHub Pages landing/redirect for `brfid.github.io`.

- LinkedIn: `https://linkedin.com/in/brfid/`

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

Docker mode defaults to tape (`--transfer tape`).

- `tape`: Working (TS11 tape image attached via SIMH).
- `console`: Unreliable — SIMH telnet/DZ line drops input without proper XON/XOFF pacing.
- `ftp`: Not working in this setup — VAX cannot reliably reach a container-hosted FTP service.

Implementation notes:
- VAX-side `vax/bradman.c` uses K&R-compatible fallbacks (varargs/stdlib/size_t/void* and `_doprnt`).
- Host uuencode decoding is tolerant of trailing garbage in console output.
- Docker image is pinned by digest in code for reproducibility.

Preview:

```bash
.venv/bin/python -m http.server --directory site 8000
```

Open `http://127.0.0.1:8000/`.

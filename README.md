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

Preview:

```bash
.venv/bin/python -m http.server --directory site 8000
```

Open `http://127.0.0.1:8000/`.

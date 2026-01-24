# Redirect

This repo deploys a minimal GitHub Pages landing/redirect for `brfid.github.io`.

- LinkedIn: `https://linkedin.com/in/brfid/`

Local generation:

```bash
python -m pip install -e .
python -m playwright install chromium
python -m resume_generator --out site
```

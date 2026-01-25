# brfid.github.io

This repo deploys a minimal GitHub Pages landing/redirect for `brfid.github.io`.

- LinkedIn: `https://linkedin.com/in/brfid/`

## Plan: generated man page (VAX/SIMH artifact)

The long-term goal (see `PLAN.md`) is to publish a small Unix man-page–style summary
(`brad(1)`) as a “quiet technical signal”.

Idea validation: yes, a VAX-side C program can take YAML and follow deterministic
transformation rules, **as long as the YAML is a constrained, host-generated subset**
(so the guest does not need a full YAML implementation).

Proof-of-concept:

- `vax/bradman.c`: tiny YAML-subset parser → `man(7)` roff (`brad.1`)
- `vax/resume.vax.example.yaml`: example “VAX-YAML” input for the guest
- `vax/README.md`: notes + intended workflow

Local generation:

```bash
python -m pip install -e .
python -m playwright install chromium
python -m resume_generator --out site
```

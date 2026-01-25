# PLAN

## Goal

Recruiter-friendly landing page that also provides a quiet technical signal via a generated Unix man page.

## Public site (UX)

- Conventional landing page:
  - Clear name/title
  - Links: LinkedIn + resume PDF
- Secondary artifact on the page:
  - A Unix man-page–style summary (`brad(1)`) rendered on-page (as some kind of resume summary or greatest hits)
  - A short, muted build transcript proving generation (compile → generate → nroff/man output)
- Tone: understated/professional (docs-as-code + CI automation), not retro cosplay.

## Source of truth

- `resume.yaml` (JSON Resume data, stored as YAML).

## Build outputs (generated; not committed)

- Static deploy root: `site/`
- Planned outputs:
  - `site/resume.pdf`
  - `site/brad.1` (man page source, or preformatted text)
  - `site/brad.txt` (rendered man page shown on the landing page)
  - `site/vax-build.log` (muted transcript)

## Generator (local-first)

- Primary interface: Python CLI
- Rendering:
  - HTML/CSS via Jinja2
  - PDF via Playwright
- Task runner: `nox` (planned) to provide a single local/CI entrypoint.
- Quality gates (run frequently): ruff, mypy, pytest, pylint, vulture.

## CI/CD

- GitHub Actions publishes on a `publish` tag (`publish` or `publish-*`).
- Publish pipeline (tag-triggered):
  1. Run quality checks (ruff/mypy/pytest/pylint/vulture).
  2. Generate site (HTML + PDF) into `site/`.
  3. Deploy `site/` to GitHub Pages.
- Non-publish pushes to `main` do not deploy.

## SIMH stage (technical artifact)

- v1 target: VAX via SIMH (BSD 4.3 family; prefer Quasijarus for CI reliability).
- Build behavior:
  1. Convert `resume.yaml` to a compact intermediate (if needed).
  2. In SIMH guest: compile a small C program that emits `brad(1)` from structured data.
  3. Run nroff/man tools in the guest to produce the rendered text.
  4. Copy artifacts back to host (log + rendered manpage) for publishing in `site/`.
- Keep licensing/redistribution in mind for any OS images.

## Inspiration / compatibility

- Compatible with historical networking/system reconstruction work such as the ARPANET simulation project:
  - `https://github.com/obsolescence/arpanet`

## Open questions (next)

- `nox` sessions:
  - Which sessions are mandatory on `publish` (vs “occasional”)?
- SIMH inputs:
  - Which VAX BSD image (exact release + checksums) is acceptable to download/cache in CI?
  - Where do we store/pin it (repo vs release artifacts vs cached download)?
- Artifact contract:
  - Exact filenames and minimal transcript content for `site/vax-build.log`.
  - Whether the landing page renders `brad.txt` inline or links out.

## VAX “Box” Abstraction (host ↔ guest transforms)

Goal: keep the main build conventional (Python/Jinja2/Playwright) while allowing one or more
SIMH/VAX steps to perform small, deterministic transformations or verifications in C, returning
artifacts that the pipeline then uses/publishes.

### Host ↔ VAX contract (portable across steps)

Treat each SIMH step as a box with a stable envelope:

- Host builds an input payload (directory + metadata) and packages it (e.g. `vax_in.tar.gz`).
- SIMH/VAX job unpacks, runs a transformation, and produces an output payload (e.g. `vax_out.tar.gz`).
- Host extracts outputs and *enforces* them (pipeline fails if required outputs are missing/invalid).

Recommended envelope layout:

- `spec.json`: serialized job spec (name/version/params + declared inputs/outputs + checks).
- `in/`: input files for the job.
- `out/`: output files produced by the job.
- `transcript.log`: short guest transcript snippet for publication/audit (optional).

### Where VAX boxes can plug into the pipeline

Because the interface is “payload in / payload out”, boxes can be inserted at multiple points:

- After quality gates: VAX verifies/attests to host-generated summary metadata.
- After HTML render: VAX canonicalizes/normalizes a text artifact (stable wrapping, newline rules).
- Before deploy: VAX produces a deterministic manifest/checksum file for published outputs.

### Transport mechanisms (CI-friendly)

From most robust to fastest to prototype:

1. Exchange disk image: host writes files into a small image; guest mounts it; guest writes outputs back.
2. Host-attached output file via simulated device: guest writes bytes to a device backed by a host file.
3. Console-log encoding: guest prints base64 between markers; host extracts/decodes (best for small outputs).

### “Trivial but necessary” VAX C transformations (not resume parsing)

Keep v1 transformations small and obviously useful:

- `canonicalize_text`: normalize newlines, trim trailing whitespace, wrap at N columns.
- `hash_manifest`: compute checksums + sizes for a declared file list.
- `validate_envelope`: verify required inputs exist/within bounds; emit a compact pass/fail report.
- `render_nroff`: take a `.1` file and emit a rendered text view for the landing page.

### Typed host-side abstraction (dataclass-based)

Define a host-side “box” interface:

- `VaxJobSpec` dataclass: `name`, `version`, `inputs`, `outputs`, `params`, `checks`.
- `VaxResult` dataclass: parsed outputs + transcript summary + metrics.

Host responsibilities:

- Serialize `VaxJobSpec` → `spec.json`.
- Package the envelope, run SIMH, extract and validate `out/`.
- Expose results to later pipeline stages (and/or publish them into `site/`).

### First box candidates (v1)

- `hash_manifest` (lowest risk): output `site/vax-manifest.txt` + short transcript.
- `render_nroff` (most visible): output `site/brad.txt` + transcript proving “compile → generate → nroff”.





# PLAN

## Goal

Recruiter-friendly landing page that also provides a quiet technical signal via a generated Unix man page.

## Public site (UX)

- Conventional landing page:
  - Clear name/title
  - Links: LinkedIn + resume PDF
- Secondary artifact on the page:
  - A Unix man-page–style summary (`brad(1)`) rendered on-page (as some kind of resume summary or greatest hits)
  - A short, muted build transcript proving generation (boot → compile → generate)
- Tone: understated/professional (docs-as-code + CI automation), not retro cosplay.

## Source of truth

- `resume.yaml` (JSON Resume data, stored as YAML).

## Outputs (generated; not committed)

### Published (deployed in `site/`)

- Static deploy root: `site/`
- Planned published outputs:
  - `site/resume.pdf`
  - `site/brad.man.txt` (plain text “manpage-style” blurb shown on the landing page)
  - `site/vax-build.log` (muted transcript; GitHub runner timestamps initially)

### Internal-only (not deployed)

- Intermediate artifacts (kept out of `site/`):
  - `build/vax/brad.1` (roff source returned from the VAX stage; used to render `site/brad.man.txt`)

## Generator (local-first)

- Primary interface: Python CLI
- Rendering:
  - HTML/CSS via Jinja2
  - PDF via Playwright
- Task runner: optional `nox` (or a simple `Makefile`) to provide a single local/CI entrypoint.
  - (`nox` is a Python automation runner, similar to `tox`, for repeatable “sessions” like lint/typecheck/test.)
- Quality gates (run frequently): ruff, mypy, pytest, pylint, vulture.
- Test-first expectation: when adding a new module/feature, add/extend `pytest` coverage in the same batch (CI blocks publish on failures).
- Code style guidance:
  - Google-style docstrings (`Args:`, `Returns:`, `Raises:`).
  - PEP 8 + ruff formatting/linting.
  - Prefer small, modular functions; use dataclasses/classes when there is stateful orchestration (e.g., VAX stage runner).

## CI/CD

- GitHub Actions publishes on a `publish` tag (`publish` or `publish-*`).
- Publish pipeline (tag-triggered):
  1. Run quality checks (ruff/mypy/pytest/pylint/vulture).
  2. Generate site (HTML + PDF) into `site/`.
  3. Run VAX/SIMH manpage stage (Docker) to generate `build/vax/brad.1` and `site/vax-build.log`.
  4. Host renders `build/vax/brad.1` → `site/brad.man.txt` (deterministic, test-covered).
  5. Deploy `site/` to GitHub Pages.
- Non-publish pushes to `main` do not deploy.

## SIMH stage (technical artifact)

- v1 target: VAX via SIMH (BSD 4.3 family) using a Dockerized SIMH environment.
- v1 implementation choice:
  - Container: `jguillaumes/simh-vaxbsd` (4.3BSD on VAX under SIMH).
  - Control channel: host drives the guest over the container’s exposed DZ line via telnet.
  - Transport: file exchange via console transcript with hard markers + uuencode blocks.
- Build behavior:
  1. Host converts `resume.yaml` → `resume.vax.yaml` (constrained, versioned YAML subset; full summary, single-line).
  2. Host boots the VAX guest (preinstalled “golden” disk; no reinstall each run).
  3. Host sends `bradman.c` + `resume.vax.yaml` into the guest via console (`cat > ...`).
  4. Guest compiles `bradman` each run (part of the evidence signal).
  5. Guest runs `bradman` to produce `brad.1` (roff/man source).
  6. Guest prints `brad.1` back to the host via uuencode blocks between hard markers.
  7. Host decodes, writes `build/vax/brad.1`, renders `site/brad.man.txt`, and writes `site/vax-build.log`
     (runner-timestamped milestones for v1).
- Keep licensing/redistribution in mind for any OS images.
- Policy:
  - Runs locally for testing, but only runs in GitHub Actions on `publish`/`publish-*`.
  - Deploy fails if this stage fails or required artifacts are missing/empty.

### VAX manpage generator: YAML-in → roff + text-out

Yes: the VAX-side C program can accept YAML, as long as the YAML is constrained to a
simple “VAX-YAML” subset that the host *generates* (so the guest does not need a full YAML
library).

Input contract (host-produced `resume.vax.yaml`; not committed):

- UTF-8 text, LF newlines, no tabs.
- 2-space indentation only.
- Mappings + sequences only (no anchors/tags/aliases).
- Scalars are **single-line strings** only (no `|`/`>` blocks); host flattens whitespace.
- Host emits **double-quoted strings** and escapes `\\` and `\"` so the guest parser is trivial.
- Include a `schemaVersion: "v1"` field so the C program can fail fast on incompatible input.

`resume.vax.yaml` schema (v1):

- Required: `schemaVersion`, `name`, `label`, `summary`
- Optional: `contact.email`, `contact.url`, `contact.linkedin`

Transformation rules (v1; implemented in the guest C program, not “templated”):

- Emit roff `man(7)` source as `brad.1`.
- Host renders `brad.1` → `site/brad.man.txt` for landing page display (deterministic, test-covered):
  - Wrap to 66 columns.
  - `DESCRIPTION` is max 4 wrapped lines, then truncate with `...`.
  - Sections: `NAME`, `DESCRIPTION`, `CONTACT`.
- `name` + `label` → `.TH` + `NAME` section line (`brad \\- <label>`), plus optional `AUTHOR`.
- `contact` (email/URL/LinkedIn) → `CONTACT` section.
- `summary` → `DESCRIPTION` section.

Escape rules (guest output safety):

- Lines that would start with `.` or `'` get prefixed with `\\&` (troff “zero-width” escape).
- Backslashes are doubled, and hyphen-minus in the `NAME` synopsis uses `\\-`.

## Inspiration / compatibility

- Compatible with historical networking/system reconstruction work such as the ARPANET simulation project:
  - `https://github.com/obsolescence/arpanet`

## Open questions (next)

- `nox` sessions:
  - Which sessions are mandatory on `publish` (vs “occasional”)?
- Docker/SIMH details:
  - Pin the Docker image by digest once stable (vs tag during prototyping).
  - Confirm the boot/login “readiness” signal for telnet driving (avoid fixed sleeps).
- Landing page:
  - How much of `site/vax-build.log` to show inline (first N lines vs curated excerpt).

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
3. Console-log encoding: guest prints uuencoded data between markers; host extracts/decodes (best for small outputs).

### “Trivial but necessary” VAX C transformations (not resume parsing)

Keep v1 transformations small and obviously useful:

- `canonicalize_text`: normalize newlines, trim trailing whitespace, wrap at N columns.
- `hash_manifest`: compute checksums + sizes for a declared file list.
- `validate_envelope`: verify required inputs exist/within bounds; emit a compact pass/fail report.
- `render_nroff` (optional later): take a `.1` file and emit a rendered text view for the landing page.
- `yaml_to_roff_and_text` (v1): take `resume.vax.yaml` and emit `brad.1` + `brad.man.txt` in-guest.
  - (Updated): emit `brad.1` in-guest; render to `brad.man.txt` on the host for portability/testing.

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
- `yaml_to_roff` (most visible): output `build/vax/brad.1` + transcript proving “boot → compile → generate”.

## Console protocol (v1)

Hard markers + uuencode blocks in the telnet transcript:

- `<<<BRAD_1_UU_BEGIN>>>` then `uuencode brad.1 brad.1` then `<<<BRAD_1_UU_END>>>`

Host decodes and writes `build/vax/brad.1`, then renders `site/brad.man.txt`.

## TODO (local success checklist)

Goal: be able to run one command locally and open a “successful” webpage (landing page + resume + manpage-style excerpt).

### Phase 0: Local “green path” (no SIMH/VAX required)

- [x] Add a landing-page template (`templates/index.html.j2`) and generator code that writes `site/index.html`.
  - Links: LinkedIn, `/resume/`, `/resume.pdf`.
  - Embed `site/brad.man.txt` if present (a muted `<pre>` block); otherwise omit the section.
  - Embed a muted excerpt of `site/vax-build.log` if present; otherwise omit the section.
- [x] Add a single “build everything” entrypoint (CLI) that:
  - Generates resume HTML + CSS into `site/resume/`.
  - Generates `site/resume.pdf`.
  - Runs the local VAX stage (or later docker/SIMH stage) to produce `build/vax/brad.1` and `site/vax-build.log`.
  - Renders `build/vax/brad.1` → `site/brad.man.txt` (using `resume_generator.manpage`).
  - Writes/refreshes `site/index.html`.
  - Writes `site/.nojekyll` (if missing) and preserves existing `site/robots.txt` + `site/404.html`.
- [x] Add a local-only helper path to produce `build/vax/brad.1` *without* SIMH:
  - `resume-gen --with-vax --vax-mode local` compiles `vax/bradman.c` on the host and runs it against the emitted `build/vax/resume.vax.yaml`.
  - This is strictly for local preview; CI/publish uses the docker/SIMH path once implemented.
- [x] Tests (same batch as each addition):
  - Landing page rendering: ensures `brad.man.txt` is conditionally included and HTML is valid-ish.
  - “Build everything” CLI: smoke-test path writes expected files into a temp dir.
- [x] Local smoke run instructions (document in `README.md`):
  - Use a local virtualenv (`.venv/`); do not install anything globally or modify system Python.
  - Setup: `python3 -m venv .venv` then `.venv/bin/python -m pip install -e '.[dev]'`
  - Browser deps: `.venv/bin/python -m playwright install chromium`
  - build: one command
  - preview: `.venv/bin/python -m http.server --directory site 8000` then open `http://127.0.0.1:8000/`
- [x] Write a deterministic published-file manifest before deploy (host-side for now): `site/vax-manifest.txt`.

### Phase 1: SIMH/VAX stage (real artifact generation)

- [x] Implement host emitter: `resume.yaml` → `resume.vax.yaml` (v1 schema + constraints).
- [ ] Implement `resume_generator.vax_stage`:
  - Run SIMH container, drive via telnet, send sources, compile, run, extract uuencode block.
  - Write `build/vax/brad.1` and `site/vax-build.log`.
  - Write `site/vax-manifest.txt` from the VAX-side `hash_manifest` box (later), or keep host-side.
- [ ] Tests:
  - [x] Unit-test `resume.vax.yaml` emitter (schema/versioning + quoting/escaping rules).
  - [x] Unit-test transcript parsing + uudecode extraction (pure string fixtures).

### Phase 2: CI + publish

- [x] GitHub Actions workflow:
  - On `publish` / `publish-*` tags: run gates → build site → run VAX stage → deploy Pages.
  - On `main`: run gates only (no deploy).
- [ ] Verify CI (main) is green after refactors.
- [ ] Hardening: wait-for-prompt loops (no sleeps), pin Docker image by digest, deterministic logs.
  - Interim: CI may use `--vax-mode local` until the docker/SIMH transport is implemented and verified.

## TODO (milestones)

These are coarse implementation batches; the “local success checklist” above is the day-to-day TODO.

### Batch 1: Host driver + schema emitter

- Add `python -m resume_generator.vax_stage --out site` (modular, PEP 8, DRY-with-clarity):
  - Emit `resume.vax.yaml` v1 from `resume.yaml`.
  - Boot the Dockerized VAX/SIMH environment and drive it via telnet (no external `telnet` dependency).
  - Send `bradman.c` + `resume.vax.yaml`, compile, generate `brad.1`.
  - Extract uuencode blocks between markers; decode; write `build/vax/brad.1`.
  - Render `build/vax/brad.1` → `site/brad.man.txt` (unit-tested; deterministic).
  - Write `site/vax-build.log` with runner timestamps and milestones (v1).
  - Fail hard on missing markers, decode failure, or empty outputs.

### Batch 2: Landing page integration

- Render `site/brad.man.txt` in a subtle codeblock below the header.
- Render a muted excerpt of `site/vax-build.log` as “pipeline evidence”.
- Do not publish/download-link the roff source (`brad.1`); keep it as an internal intermediate.

### Batch 3: CI wiring + hardening

- GitHub Actions: run the VAX stage only on `publish`/`publish-*` tags; fail deploy if it fails.
- Replace fixed sleeps with “wait for login prompt” loops (telnet-driven).
- Pin the Docker image by digest once stable.

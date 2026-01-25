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

## Build outputs (generated; not committed)

- Static deploy root: `site/`
- Planned outputs:
  - `site/resume.pdf`
  - `site/brad.1` (man page roff source; “proof artifact”)
  - `site/brad.man.txt` (plain text “manpage-style” blurb shown on the landing page)
  - `site/vax-build.log` (muted transcript; GitHub runner timestamps initially)

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
  3. Run VAX/SIMH manpage stage (Docker) to generate `site/brad.1`, `site/brad.man.txt`, and `site/vax-build.log`.
  4. Deploy `site/` to GitHub Pages.
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
  5. Guest runs `bradman` to produce:
     - `brad.1` (roff/man source; proof artifact)
     - `brad.man.txt` (plain text for `<pre><code>` on the landing page)
  6. Guest prints both files back to the host via uuencode blocks between hard markers.
  7. Host decodes, writes artifacts into `site/`, and writes `site/vax-build.log` (runner-timestamped milestones for v1).
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

- Emit roff `man(7)` source as `brad.1` (“proof artifact”).
- Emit plain text as `brad.man.txt` for landing page display:
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
  - Whether to link `site/brad.1` as a “proof artifact” download.

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
- `yaml_to_roff` (most visible): output `site/brad.1` + `site/brad.man.txt` + transcript proving “boot → compile → generate”.

## Console protocol (v1)

Hard markers + uuencode blocks in the telnet transcript:

- `<<<BRAD_1_UU_BEGIN>>>` then `uuencode brad.1 brad.1` then `<<<BRAD_1_UU_END>>>`
- `<<<BRAD_MAN_TXT_UU_BEGIN>>>` then `uuencode brad.man.txt brad.man.txt` then `<<<BRAD_MAN_TXT_UU_END>>>`

Host decodes and writes `site/brad.1` and `site/brad.man.txt`.

## TODO (batches)

### Batch 1: Host driver + schema emitter

- Add `python -m resume_generator.vax_stage --out site` (modular, PEP 8, DRY-with-clarity):
  - Emit `resume.vax.yaml` v1 from `resume.yaml`.
  - Boot the Dockerized VAX/SIMH environment and drive it via telnet (no external `telnet` dependency).
  - Send `bradman.c` + `resume.vax.yaml`, compile, generate `brad.1` + `brad.man.txt`.
  - Extract uuencode blocks between markers; decode; write required artifacts into `site/`.
  - Write `site/vax-build.log` with runner timestamps and milestones (v1).
  - Fail hard on missing markers, decode failure, or empty outputs.

### Batch 2: Landing page integration

- Render `site/brad.man.txt` in a subtle codeblock below the header.
- Render a muted excerpt of `site/vax-build.log` as “pipeline evidence”.
- Link to `site/brad.1` (optional; recommended as a proof artifact).

### Batch 3: CI wiring + hardening

- GitHub Actions: run the VAX stage only on `publish`/`publish-*` tags; fail deploy if it fails.
- Replace fixed sleeps with “wait for login prompt” loops (telnet-driven).
- Pin the Docker image by digest once stable.

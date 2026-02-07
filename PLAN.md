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
  - `site/brad.man.txt` (plain text "manpage-style" blurb shown on the landing page)
  - `site/vax-build.log` (muted transcript; GitHub runner timestamps initially)

### Internal-only (not deployed)

- Intermediate artifacts (kept out of `site/`):
  - `build/vax/brad.1` (roff source returned from the VAX stage; used to render `site/brad.man.txt`)

## Generator (local-first)

- Primary interface: Python CLI
- Rendering:
  - HTML/CSS via Jinja2
  - PDF via Playwright
- Task runner: `Makefile` provides single entrypoint for local/CI tasks
- Quality gates (run frequently): ruff, mypy, pytest, pylint, vulture
- Test-first expectation: when adding a new module/feature, add/extend `pytest` coverage in the same batch (CI blocks publish on failures)
- Code style guidance:
  - Google-style docstrings (`Args:`, `Returns:`, `Raises:`)
  - PEP 8 + ruff formatting/linting
  - Prefer small, modular functions; use dataclasses/classes when there is stateful orchestration (e.g., VAX stage runner)

## CI/CD

- GitHub Actions publishes on a `publish` tag (`publish` or `publish-*`)
- Publish pipeline (tag-triggered):
  1. Run quality checks (ruff/mypy/pytest/pylint/vulture)
  2. Generate site (HTML + PDF) into `site/`
  3. Run VAX/SIMH manpage stage (Docker) to generate `build/vax/brad.1` and `site/vax-build.log`
  4. Host renders `build/vax/brad.1` → `site/brad.man.txt` (deterministic, test-covered)
  5. Deploy `site/` to GitHub Pages
- Non-publish pushes to `main` do not deploy

## SIMH stage (technical artifact)

- v1 target: VAX via SIMH (BSD 4.3 family) using a Dockerized SIMH environment
- v1 implementation choice:
  - Container: `jguillaumes/simh-vaxbsd` (4.3BSD on VAX under SIMH)
- Control channel: host drives the guest over the container's exposed DZ line via telnet
- Transport: **tape by default** (TS11 image attached); console transcript remains the output path for `brad.1`
- Build behavior:
  1. Host converts `resume.yaml` → `resume.vax.yaml` (constrained, versioned YAML subset; full summary, single-line)
  2. Host boots the VAX guest (preinstalled "golden" disk; no reinstall each run)
  3. Host sends `bradman.c` + `resume.vax.yaml` into the guest (TS11 tape image; console/FTP are fallbacks)
  4. Guest compiles `bradman` each run (part of the evidence signal)
  5. Guest runs `bradman` to produce `brad.1` (roff/man source)
  6. Guest prints `brad.1` back to the host via uuencode blocks between hard markers
  7. Host decodes, writes `build/vax/brad.1`, renders `site/brad.man.txt`, and writes `site/vax-build.log`
     (runner-timestamped milestones for v1)
- Keep licensing/redistribution in mind for any OS images
- Policy:
  - Runs locally for testing, but only runs in GitHub Actions on `publish`/`publish-*`
  - Deploy fails if this stage fails or required artifacts are missing/empty

### VAX manpage generator: YAML-in → roff + text-out

Yes: the VAX-side C program can accept YAML, as long as the YAML is constrained to a
simple "VAX-YAML" subset that the host *generates* (so the guest does not need a full YAML
library).

Input contract (host-produced `resume.vax.yaml`; not committed):

- UTF-8 text, LF newlines, no tabs
- 2-space indentation only
- Mappings + sequences only (no anchors/tags/aliases)
- Scalars are **single-line strings** only (no `|`/`>` blocks); host flattens whitespace
- Host emits **double-quoted strings** and escapes `\\` and `\"` so the guest parser is trivial
- Include a `schemaVersion: "v1"` field so the C program can fail fast on incompatible input

`resume.vax.yaml` schema (v1):

- Required: `schemaVersion`, `name`, `label`, `summary`
- Optional: `contact.email`, `contact.url`, `contact.linkedin`

Transformation rules (v1; implemented in the guest C program, not "templated"):

- Emit roff `man(7)` source as `brad.1`
- Host renders `brad.1` → `site/brad.man.txt` for landing page display (deterministic, test-covered):
  - Wrap to 66 columns
  - `DESCRIPTION` is max 4 wrapped lines, then truncate with `...`
  - Sections: `NAME`, `DESCRIPTION`, `CONTACT`
- `name` + `label` → `.TH` + `NAME` section line (`brad \\- <label>`), plus optional `AUTHOR`
- `contact` (email/URL/LinkedIn) → `CONTACT` section
- `summary` → `DESCRIPTION` section

Escape rules (guest output safety):

- Lines that would start with `.` or `'` get prefixed with `\\&` (troff "zero-width" escape)
- Backslashes are doubled, and hyphen-minus in the `NAME` synopsis uses `\\-`

## Console protocol (v1)

Hard markers + uuencode blocks in the telnet transcript:

- `<<<BRAD_1_UU_BEGIN>>>` then `uuencode brad.1 brad.1` then `<<<BRAD_1_UU_END>>>`

Host decodes and writes `build/vax/brad.1`, then renders `site/brad.man.txt`.

## Implementation notes (current state)

- Docker/SIMH transfer uses **tape** (TS11 image attached). Console/FTP are archived.
- Docker image is pinned by digest in code (deterministic)
- VAX-side `bradman.c` was updated for 4.3BSD/K&R C: varargs/stdlib fallbacks, `size_t`/`void*` compatibility, `_doprnt`/`sys_errlist` stubs
- Host uuencode decoding is tolerant of trailing garbage on lines (SIMH console occasionally appends)
- Console/FTP transfer code has been removed from the active path and archived in `docs/transport-archive.md`
- Build log retains elapsed timing (non-deterministic but useful for debugging)

## AWS Testing Infrastructure

**Purpose**: Development and debugging environment for ARPANET orchestration

The AWS infrastructure provides on-demand x86_64 EC2 instances for testing ARPANET builds before they run in the GitHub Actions pipeline. This remains a permanent part of the development workflow for:
- Debugging ARPANET integration issues
- Testing pipeline expansions (new nodes, protocols)
- Iterating on orchestration before CI/CD runs

**Architecture**:
- Orchestration from small Linux systems (Raspberry Pi, ARM devices)
- Python-based AWS CDK for ephemeral EC2 instances
- Cost: ~$0.04/hour when testing, $0 when idle
- See `test_infra/` for implementation details

**Workflow**: Develop on AWS EC2 → Deploy to GitHub Actions pipeline → Debug on AWS EC2 as needed

## Implementation Status

### ✅ Phases 0-2: Complete

- **Phase 0**: Local build pipeline (HTML, PDF, landing page)
- **Phase 1**: VAX/SIMH stage with Docker integration
- **Phase 2**: CI/CD with GitHub Actions, hardening (wait loops, digest pinning)
- **AWS testing infrastructure**: CDK-based ephemeral EC2 provisioning

### Phase 3: Future enhancements (when needed)

- Additional ARPANET nodes (IMP, PDP-10, etc.)
- Enhanced artifact verification
- Build provenance attestation

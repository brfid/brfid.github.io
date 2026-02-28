# Changelog

All notable changes to this project are documented in this file.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with date-based entries because this repository does not currently publish
semantic version tags.

## [Unreleased]

### Current State
- Hugo is the site generator (`hugo/`); the vintage pipeline (VAX/PDP-11 via SIMH)
  is an on-demand artifact generator only — it feeds `hugo/static/brad.man.txt`.
- **Pexpect pipeline VALIDATED end-to-end (2026-02-28, run `manual-20260228-200507`).**
  Stage B (VAX) → Stage A (PDP-11) → `brad.man.txt` produced. Output is a correctly
  formatted `BRAD(1)` UNIX Programmer's Manual man page rendered by 2.11BSD nroff.
- **Architecture decision (2026-02-28):** screen/telnet/sleep orchestration retired;
  pexpect is the permanent replacement.
- **PDP-11 networking constraint (permanent):** The `unix` kernel has no working
  Ethernet. File transfer between stages is host-mediated.
- Cold-start doc order: `README.md` → this file → `docs/integration/INDEX.md`
  → `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md`.

### Active Priorities
1. **CI smoke test**: Trigger a `publish-vintage-*` tag and confirm the GitHub
   Actions workflow produces `hugo/static/brad.man.txt` from CI.

### In Progress
- None.

### Blocked
- None.

### Decisions Needed
- None.

### Recently Completed
- **Iterative VAX injection debugging (2026-02-28):** Five debug runs. Issues
  found and fixed in sequence:
  1. UnicodeDecodeError — resume.vintage.yaml not ASCII; fixed with UTF-8 read +
     NFKD transliteration.
  2. SIMH instant exit — disk images gzipped (RA81.000.gz); added gunzip in
     Dockerfile. Created static vax780-pexpect.ini (no network/DZ terminals).
  3. False prompt match — "# " needed (not "#"); kernel banner contains "#10".
  4. YAML tty overflow — lines up to 571 chars exceed 256-byte tty CANBSIZ;
     switched to uuencode injection.
  5. UUE stall — single 94-line heredoc stalls PTY echo after ~180s; fixed with
     10-line batches per heredoc (chunked injection).
  6. ERASE/KILL corruption — 4.3BSD default ERASE is `#` (0x23) and KILL is `@`
     (0x40), both in UUE character range. Every `#` in a UUE line erased the
     previous char; every `@` killed the line. Fix: `stty erase \x7f kill \x15`
     immediately after login (DEL and Ctrl-U are outside UUE range).
  7. Root shell is csh, not sh — root logs into /bin/csh by default. csh heredoc
     `<< 'HEREDOC_EOF'` uses the QUOTED string as the terminator (not unquoted
     HEREDOC_EOF), so the heredoc hangs indefinitely. Also, `PS1=...` is not
     valid csh syntax, causing pexpect to match `VAXsh> ` in the csh error
     message rather than a real prompt. Fix: `exec /bin/sh` immediately after
     login, before any stty, prompt, or heredoc work. Applied to BOTH VAX and
     PDP-11 pexpect scripts.
  8. Marker capture matches command echo — `child.sendline("echo '__BEGIN__'; cat ...")`
     causes the tty to echo the command text before the shell executes it; pexpect
     matches `__BEGIN__` in the echo rather than in actual output. Fix: `stty -echo`
     as a separate command first, then send the capture command (not echoed),
     then `stty echo` at end of the capture command. Applied to both scripts.
  9. PDP-11 boot prompt is `\r: ` not `Boot:` — the 2.11BSD 2-stage boot shows
     `73Boot from xp(0,0,0) at 0176700\n\r: `. Fixed pdp11_pexpect.py to match
     `["\r: ", "Boot:"]` and also removed `set cpu idle` from pdp11-pexpect.ini
     (SIMH idle detection calls `ps` which is absent in Debian bookworm-slim).
- **Stage A PDP-11 debugging (2026-02-28):** Three additional fixes after Stage B was working:
  10. nroff BEL spam + hang — 2.11BSD nroff rings BEL and waits for keypress at page
      breaks when stderr is a tty. Fix: `nroff ... < /dev/null` so stdin returns EOF
      immediately, suppressing page-pause behaviour.
  11. brad.1 CANBSIZ truncation — `brad.1` has lines >256 bytes (DESCRIPTION ~500 chars).
      2.11BSD tty driver silently truncates them and sends BEL per overflow char. Fix:
      `_inject_file_uue()` for brad.1 (same approach as VAX resume.vintage.yaml); UUE
      lines are ≤62 chars.
  12. Non-fatal EOF — 2.11BSD restarts getty/login after shell exits; pexpect.EOF never
      arrives. Fix: wrap EOF wait in non-fatal try/except; finally block force-terminates.
- **Pipeline VALIDATED end-to-end (2026-02-28, run `manual-20260228-200507`):**
  Stage B VAX → brad.1 (61 lines troff source) → Stage A PDP-11 → brad.man.txt.
  Output: correctly formatted `BRAD(1)` UNIX Programmer's Manual man page.
- **Docker images built on edcloud (2026-02-28):** Both `pdp11-pexpect` and
  `vax-pexpect` images built successfully. Images cached with `KEEP_IMAGES=1`.
- **CI timeout extended (2026-02-28):** `deploy.yml` job timeout 40→70 min,
  SSM polling 30→50 min to accommodate first-run docker builds.
- **Documentation pass (2026-02-28):** Removed 21 dead MD files; rewrote key
  docs; created `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md`.
- **Diagnostic run (2026-02-28):** Confirmed both VAX and PDP-11 guest machines
  boot and reach root shells on edcloud; chose pexpect as replacement.
- **Architecture decision:** Retired screen/telnet/sleep orchestration entirely.
  Added to `docs/archive/DEAD-ENDS.md`.

## [2026-02-21]

### Added
- Hugo site (`hugo/`) with PaperMod theme, dark mode, `www.jockeyholler.net`
  canonical URL, and Blog / Work / Resume / About navigation.
- Hugo-native resume page rendered from `resume.yaml` data source; custom layout
  (`hugo/layouts/_default/resume.html`) and CSS; PDF download at `/resume.pdf`.
- Portfolio page (Work nav) drawn from `portfolio.yaml` structured data.
- Blog posts: "How I Use Changelogs as LLM Memory" and "Why Do We Call Them
  Packets?" (with local image assets).
- CI/deploy: GitHub Actions Hugo build pipeline with tag-triggered publish
  (`publish`, `publish-vintage`); Python/Playwright gated on vintage mode only.
- Vintage artifact pipeline integrated as an optional CI stage: VAX compiles and
  encodes resume → PDP-11 typesets with `nroff` → output committed to
  `hugo/static/brad.man.txt` for Hugo to serve.
- Research archive (`docs/archive/`): exploratory emulation notes organized by
  host type (VAX, PDP-11, PDP-10, ARPANET); see `docs/archive/README.md`.

### Changed
- Architectural decision: Hugo as site generator for all content; vintage
  pipeline scoped to artifact-only role.
- DNS: apex A/AAAA and www CNAME switched from CloudFront aliases to GitHub
  Pages; orphaned alias records removed.
- edcloud lifecycle management centralized into shared Python CLI
  (`scripts/edcloud_lifecycle.py`) with thin shell wrappers for operator use.
- Deploy workflow refactored to run console orchestration from edcloud repo
  checkout; Tailscale SSH replaces public-IP key-based access.
- PDP-11 readiness checks updated to avoid one-shot TCP probes that triggered
  SIMH TTI disconnect/reboot loops; log-signal–based gating used instead.

## [2026-02-14]

### Added
- VAX ↔ PDP-11 uuencode console transfer pipeline; end-to-end artifact flow
  validated on single-host edcloud with Docker Compose.
- Cold-start diagnostics runbook (`docs/integration/operations/VAX-PDP11-COLD-START-DIAGNOSTICS.md`)
  standardizing serialized console session discipline and log-based readiness gating.
- edcloud single-host deployment model: VAX and PDP-11 containers co-located on
  one EC2 instance, reducing operational surface area and Tailscale SSH dependency.

### Changed
- Evaluated ARPANET IMP, KL10/KS10 (TOPS-20), and Chaosnet emulation paths as
  potential pipeline stages; documented findings and convergence decision in
  `docs/archive/arpanet/` and `docs/archive/pdp-10/`.

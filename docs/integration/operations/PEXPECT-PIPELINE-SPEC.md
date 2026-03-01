# Pexpect Pipeline Spec

Purpose: as-built implementation reference for the pexpect-based vintage pipeline.
Primary cold-start doc for debugging or rebuilding the pipeline.

---

## Implementation status (2026-03-01)

Both stages validated end-to-end on edcloud. All architectural improvements merged to `main`.

| File | Role | Status |
|------|------|--------|
| `scripts/vax_pexpect.py` | Stage B: VAX compile+run+UUE | **Validated** |
| `scripts/pdp11_pexpect.py` | Stage A: PDP-11 nroff | **Validated** |
| `scripts/simh_session.py` | Shared session utilities | **Implemented 2026-03-01** |
| `resume_generator/bio_yaml.py` | bio.yaml parser (host-side) | **Implemented 2026-03-01** |
| `vintage/machines/vax/Dockerfile.vax-pexpect` | VAX Docker image | SIMH SHA-pinned |
| `vintage/machines/pdp11/Dockerfile.pdp11-pexpect` | PDP-11 Docker image | SIMH SHA-pinned |
| `vintage/machines/vax/configs/vax780-pexpect.ini` | VAX pexpect ini | Static; no network/telnet |
| `vintage/machines/pdp11/configs/pdp11-pexpect.ini` | PDP-11 pexpect ini | Static; no telnet |
| `scripts/edcloud-vintage-runner.sh` | Orchestrator | No screen/telnet |
| `.github/workflows/build-images.yml` | Image build + cache workflow | Implemented 2026-03-01 |

**Key implementation learnings:**

1. **VAX disk images are gzipped** in `jguillaumes/simh-vaxbsd:latest` (`RA81.000.gz`,
   `RA81VHD.001.gz`). SIMH cannot attach `.gz` files — decompress at Docker build time.
   Without decompression, BSD panics immediately (no root disk), `run 2` returns, `quit`
   fires, and SIMH exits — appearing to pexpect as instant `EOF`.

2. **Network and DZ terminals must be disabled** in the pexpect ini. The original
   `vax780.ini` opens TCP ports (`attach dz 2323`, `set remote telnet=2324`,
   `attach xu eth0`) that are unnecessary for the pipeline and may fail in Docker.
   The static `vax780-pexpect.ini` disables all of these.

3. **`resume.vintage.yaml` contains non-ASCII characters** (em-dashes, curly quotes
   from `resume.yaml`). Read as UTF-8 and transliterate to ASCII before injection —
   the VAX 4.3BSD guest is ASCII-only.

4. **4.3BSD tty canonical input buffer is 256 bytes**: resume.vintage.yaml has lines
   up to 571 characters. Lines exceeding ~255 bytes trigger BEL spam and get silently
   truncated by the tty driver. Fix: use uuencode injection for the YAML (`_inject_file_uue`
   in `vax_pexpect.py`) — UUE lines are always ≤62 chars. bradman.c lines are short and
   use the plain heredoc path. 4.3BSD ships `uudecode` in `/usr/bin`.

5. **Custom shell prompt prevents false matches**: `PS1='VAXsh> '` is set immediately
   after login. The 4.3BSD kernel version string (`BSD UNIX #10`) contains `#` — using
   `"#"` as a prompt pattern causes early false match. Use `"# "` (hash space) instead,
   which is the actual root shell prompt format.

6. **4.3BSD ERASE/KILL characters corrupt UUE injection**: 4.3BSD's default tty ERASE
   character is `#` (0x23) and KILL is `@` (0x40). Both fall in the UUE character range
   (0x20–0x60). Every `#` in a UUE-encoded line silently erases the previous character;
   every `@` kills the entire input line. This corrupts UUE payloads without any visible
   error — the heredoc appears to complete, but the decoded file is wrong or empty.
   `bradman.c` injection was unaffected because it uses the plain heredoc path (not UUE).
   Fix: immediately after login, run `stty erase DEL kill Ctrl-U` (send the actual bytes
   `\x7f` and `\x15`, not caret notation) to move both special chars outside the UUE range.
   This must happen before any UUE heredoc injection.

7. **Root shell is /bin/csh, not /bin/sh**: 4.3BSD root's default login shell is csh.
   Two csh behaviors break the pipeline:
   - `PS1='VAXsh> '` (Bourne sh prompt idiom) fails in csh with `PS1=...: Command not
     found.`. Pexpect matches `VAXsh> ` in the error text instead of a real prompt —
     making subsequent expects unreliable.
   - csh heredoc `<< 'HEREDOC_EOF'` uses the quoted string `'HEREDOC_EOF'` (WITH
     the single quotes) as the terminator. We send the unquoted `HEREDOC_EOF`, so
     the heredoc NEVER terminates — causing the pipeline to stall indefinitely.
   Fix: immediately after login, run `exec /bin/sh` before any stty, prompt, or
   heredoc work. /bin/sh heredoc uses the unquoted delimiter and PS1 works correctly.

8. **UUE heredoc PTY echo stall**: A single heredoc with 90+ UUE lines can cause the PTY
   echo to stall. Fix: inject UUE in batches of 10 lines (10 × 62 = 620 chars per heredoc),
   appending to the `.uu` file between batches. Each small heredoc completes promptly.

9. **nroff interactive page-break hang (Stage A)**: 2.11BSD nroff rings BEL and waits
   for a keypress on stdin at page breaks when stderr is a tty. Since pexpect never sends
   a keystroke, nroff waits indefinitely while continuously ringing BEL. The pexpect
   buffer fills with `\x07` bytes; `expect(PROMPT)` never matches.
   Fix: `nroff -man -Tlp /tmp/brad.1 < /dev/null > /tmp/brad.man.txt` — redirecting
   stdin from `/dev/null` causes nroff to receive EOF instead of blocking on keypress,
   suppressing interactive page-pause behaviour. `-Tlp` (line printer mode) prevents
   terminal-specific control sequences.

10. **brad.1 CANBSIZ truncation (Stage A)**: `brad.1` contains lines exceeding 256 bytes
    (the `.SH DESCRIPTION` paragraph is ~500 chars; one `.IP` bullet is ~270 chars).
    2.11BSD's tty CANBSIZ=256 silently truncates them during plain heredoc injection and
    sends BEL per overflow character. The injected file is corrupt (truncated content).
    Fix: `_inject_file_uue()` for `brad.1` — UUE lines are always ≤62 chars. Same
    pattern as `resume.vintage.yaml` on the VAX. Use `binascii.b2a_uu` (not the
    deprecated Python `uu` module) for encoding; output is identical and compatible with
    2.11BSD `uudecode`.

11. **Non-fatal EOF after shell exit**: 2.11BSD restarts getty/login after the root
    shell exits rather than returning EOF to SIMH. `child.expect(pexpect.EOF)` times out.
    Fix: wrap EOF wait in non-fatal `try/except pexpect.TIMEOUT`; the `finally` block
    force-terminates SIMH regardless. Applied to both `vax_pexpect.py` and
    `pdp11_pexpect.py`.

---

## Why pexpect

The previous approach used GNU `screen` + `telnet` + fixed `sleep` timings to inject
commands and files into SIMH guest consoles via heredoc. It was timing-based with no
handshake — it blindly sent characters and hoped the remote was ready. Every failure
was a race condition or a missed login prompt.

`pexpect` is designed for exactly this pattern: automating interactive terminal sessions
by waiting for specific output strings before sending input. It replaces all sleeps with
deterministic prompt detection.

---

## SIMH console mode

Use SIMH with console on **stdin/stdout** (no telnet port). Remove `set console telnet=NNNN`
from `.ini` files for the pexpect stages. The pexpect process connects directly to the
SIMH process via a pty — no separate telnet listener, no port contention, no timeout.

---

## UUCP framing

The file transfer from VAX to PDP-11 uses UUCP-era uuencode/uudecode, host-mediated:

```
VAX:  uuencode brad.1 brad.1 > brad.1.uu
      (pexpect captures brad.1.uu from console output)
Host: writes brad.1.uu to build/vintage/brad.1.uu
PDP-11: uudecode brad.1.uu  →  brad.1
        nroff -man -Tlp brad.1 < /dev/null > brad.man.txt
```

Why not FTP: the PDP-11 2.11BSD `unix` kernel has no working Ethernet. The `netnix`
kernel crashes on `xq` (Ethernet controller) initialization. See `docs/archive/DEAD-ENDS.md`.

The `validate_uu_spool()` utility in `scripts/simh_session.py` validates the captured
spool (line count, `begin`/`end` markers) before injection into the PDP-11 session.

---

## Bio mode

`bradman.c` supports `-mode bio` to emit a plain-text bio excerpt instead of troff:

```
./bradman -i resume.vintage.yaml -mode bio -o brad.bio.txt
```

The VAX pexpect script runs both modes and captures `brad.bio.txt` alongside `brad.1.uu`.
The host `resume_generator/bio_yaml.py` parser converts `brad.bio.txt` + build log header
into `hugo/data/bio.yaml` for the Hugo landing page.

---

## Shared session utilities (`scripts/simh_session.py`)

Both pexpect scripts import common utilities from `scripts/simh_session.py`:

- `make_logger(name)` — structured logger with UTC timestamps and machine-boundary markers
- `validate_uu_spool(spool_text)` — validates UUE spool: checks `begin`/`end` markers
  and line count; raises `ValueError` on corrupt spool (fast-fail before PDP-11 injection)
- `inject_batched_heredoc(child, dest_path, lines, batch_size, prompt, logger)` — injects
  lines in batches of `batch_size` (default 10), appending to `dest_path` between batches;
  prevents PTY echo stall on large payloads

---

## Stage A+B — Connected (as-built)

```
Host builds resume.vintage.yaml
          ↓
Stage B (vax_pexpect.py):
  VAX 4.3BSD ← pexpect → bradman compiles, runs
  VAX uuencodes brad.1 → brad.1.uu captured by host
  VAX runs -mode bio → brad.bio.txt captured by host
          ↓
Stage A (pdp11_pexpect.py):
  PDP-11 2.11BSD ← pexpect → brad.1.uu injected, uudecode, nroff
  brad.man.txt captured by host
          ↓
Host emits brad.man.txt, brad.bio.txt, build.log.txt as base64 markers
GitHub Actions extracts artifacts → bio_yaml.py → bio.yaml → Hugo build
```

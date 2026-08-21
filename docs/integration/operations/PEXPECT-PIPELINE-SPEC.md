# Pexpect Pipeline Spec

As-built implementation reference for the pexpect-based vintage pipeline: the cold-start doc for debugging or rebuilding it. The pipeline renders one artifact, the landing-page bio; for the data-flow map and artifact list see [`../INDEX.md`](../INDEX.md).

## Components

| File | Role |
|------|------|
| `resume_generator/vintage_yaml.py` | Host: `site.yaml` → `bio.vintage.yaml` (flat ASCII subset) |
| `vintage/machines/vax/bradman.c` | Guest (VAX): bio YAML → troff (`brad.bio.roff`) |
| `scripts/vax_pexpect.py` | Stage B: VAX compile + run + `uuencode` |
| `scripts/pdp11_pexpect.py` | Stage A: PDP-11 `uudecode` + `nroff` |
| `scripts/simh_session.py` | Shared session utilities |
| `resume_generator/bio_yaml.py` | Host: `brad.bio.txt` → `hugo/data/bio.yaml` |
| `resume_generator/build_log.py` | Host: published build-log renderer |
| `vintage/machines/{vax,pdp11}/Dockerfile.*-pexpect` | SIMH images (SHA-pinned) |
| `vintage/machines/{vax,pdp11}/configs/*-pexpect.ini` | Static inis; no network/telnet |
| `scripts/edcloud-vintage-runner.sh` | Orchestrator + marker transport |

## As-built learnings

1. **VAX disk images are gzipped** in `jguillaumes/simh-vaxbsd:latest` (`RA81.000.gz`, `RA81VHD.001.gz`). SIMH cannot attach `.gz` files — decompress at Docker build time. Without decompression, BSD panics immediately (no root disk), `run 2` returns, `quit` fires, and SIMH exits — appearing to pexpect as instant `EOF`.

2. **Network and DZ terminals must be disabled** in the pexpect ini. The original `vax780.ini` opens TCP ports (`attach dz 2323`, `set remote telnet=2324`, `attach xu eth0`) that are unnecessary here and may fail in Docker. The static `vax780-pexpect.ini` disables all of these.

3. **`bio.vintage.yaml` may contain non-ASCII characters** (em-dashes, curly quotes if the `resume.yaml` blurb was pasted from Word). `vintage_yaml.py` transliterates to ASCII on emit — the VAX 4.3BSD guest is ASCII-only.

4. **4.3BSD tty canonical input buffer is 256 bytes**: the `bioProfile` line (the blurb) can exceed it on a single line. Lines over ~255 bytes trigger BEL spam and get silently truncated by the tty driver. Fix: inject the YAML with uuencode (`_inject_file_uue` in `vax_pexpect.py`) — UUE lines are always ≤62 chars. `bradman.c` lines are short and use the plain heredoc path. 4.3BSD ships `uudecode` in `/usr/bin`.

5. **Custom shell prompt prevents false matches**: `PS1='VAXsh> '` is set immediately after login. The 4.3BSD kernel version string (`BSD UNIX #10`) contains `#`, so matching on `"#"` false-matches early; match on `"# "` (hash space), the actual root shell prompt.

6. **4.3BSD ERASE/KILL characters corrupt UUE injection**: the default tty ERASE is `#` (0x23) and KILL is `@` (0x40) — both inside the UUE range (0x20–0x60). Every `#` in a UUE line silently erases the previous character; every `@` kills the line. The heredoc appears to complete but the decoded file is wrong or empty; `bradman.c` (plain heredoc, not UUE) is unaffected. Fix: right after login, `stty erase DEL kill Ctrl-U` (send the bytes `\x7f` and `\x15`, not caret notation), before any UUE heredoc.

7. **Root shell is /bin/csh, not /bin/sh**: run `exec /bin/sh` immediately after login, before any stty, prompt, or heredoc work — two csh behaviors otherwise break the pipeline:
   - `PS1='VAXsh> '` (a Bourne idiom) fails in csh with `PS1=...: Command not found.`, and pexpect then matches the `VAXsh>` prompt in the error text instead of a real one.
   - csh heredoc `<< 'HEREDOC_EOF'` uses the quoted string `'HEREDOC_EOF'` (with quotes) as the terminator; we send unquoted `HEREDOC_EOF`, so it never terminates and the pipeline stalls.

8. **UUE heredoc PTY echo stall**: a single heredoc with 90+ UUE lines can stall the PTY echo. Fix: inject UUE in ten-line batches, appending to the `.uu` file between batches (`inject_batched_heredoc`). Each small heredoc completes promptly.

9. **nroff interactive page-break hang (Stage A)**: 2.11BSD nroff rings BEL and waits for a keypress at page breaks when stderr is a tty. pexpect never sends one, so nroff blocks forever while the buffer fills with `\x07`. Fix: `nroff -Tlp /tmp/brad.bio.roff < /dev/null > /tmp/brad.bio.txt` — `< /dev/null` gives nroff EOF instead of a keypress; `-Tlp` (line printer) avoids terminal control sequences. Note **no `-man`**: the bio troff uses only base requests (`.ll 60n`, `.po 0`, `.nh`, `.nf`/`.fi`, `.ad b`), so a macro package would wrongly impose man-page structure.

10. **The PDP-11 receives a UUE spool, never raw troff**: the VAX uuencodes `brad.bio.roff` into `brad.bio.uu` before the host couriers it, so the PDP-11 always injects UUE (≤62-char lines) and `uudecode`s — the 256-byte CANBSIZ limit is sidestepped by construction, even though the blurb line itself is long.

11. **Non-fatal EOF after shell exit**: 2.11BSD restarts getty/login after the root shell exits rather than returning EOF to SIMH, so `child.expect(pexpect.EOF)` times out. Fix: wrap the EOF wait in a non-fatal `try/except pexpect.TIMEOUT`; the `finally` block force-terminates SIMH regardless. Applied to both pexpect scripts.

12. **Marker base64 must be portable**: the runner encodes stdout markers with `base64 | tr -d '\n'`, not GNU-only `base64 -w 0` (which BSD/macOS `base64` rejects). Output is identical on the Linux CI runner; the portable form also lets the pipeline run natively on an arm64 Mac.

## Why pexpect

The previous approach used GNU `screen` + `telnet` + fixed `sleep` timings to drive the SIMH consoles: timing-based, no handshake, every failure a race. `pexpect` waits for specific output before sending input, replacing all sleeps with deterministic prompt detection.

## SIMH console mode

Run SIMH with its console on **stdin/stdout** (no telnet port); remove `set console telnet=NNNN` from the pexpect `.ini` files. pexpect connects directly to the SIMH process via a pty — no listener, no port contention.

## UUCP framing

VAX → PDP-11 transfer uses UUCP-era uuencode/uudecode, host-mediated:

```
VAX:    uuencode brad.bio.roff brad.bio.roff > brad.bio.uu
        (pexpect captures brad.bio.uu from console output)
Host:   writes brad.bio.uu to build/vintage/brad.bio.uu
PDP-11: uudecode brad.bio.uu  →  brad.bio.roff
        nroff -Tlp brad.bio.roff < /dev/null > brad.bio.txt
```

Why not FTP: the PDP-11 2.11BSD `unix` kernel has no working Ethernet (the `netnix` kernel crashes on `xq` init). See [`../../archive/DEAD-ENDS.md`](../../archive/DEAD-ENDS.md). `validate_uu_spool()` in `simh_session.py` checks the captured spool (line count, `begin`/`end` markers) before injection.

## Shared session utilities (`scripts/simh_session.py`)

- `make_logger(name)` — structured logger with UTC timestamps and machine-boundary markers
- `validate_uu_spool(spool_text)` — validates a UUE spool (`begin`/`end` markers, line count); raises `ValueError` on corruption, fast-failing before PDP-11 injection
- `inject_batched_heredoc(child, remote_path, lines, prompt, timeout)` — injects lines in ten-line batches, appending between batches; prevents the PTY echo stall

## Stage A+B — as built

```
Host builds bio.vintage.yaml
          ↓
Stage B (vax_pexpect.py):
  VAX 4.3BSD ← pexpect → bradman compiles, runs → brad.bio.roff (troff)
  VAX uuencodes brad.bio.roff → brad.bio.uu captured by host
          ↓
Stage A (pdp11_pexpect.py):
  PDP-11 2.11BSD ← pexpect → brad.bio.uu injected, uudecode, nroff (no -man)
  brad.bio.txt captured by host
          ↓
Host emits brad.bio.txt, pipeline-status.json, build.log.html as base64 markers
GitHub Actions extracts them → bio_yaml.py + run URL → bio.yaml → Hugo build
```

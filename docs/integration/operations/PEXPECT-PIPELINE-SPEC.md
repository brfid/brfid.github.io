# Pexpect Pipeline Spec

Purpose: implementation reference for rebuilding the vintage pipeline with pexpect.
This is the primary cold-start doc for anyone implementing or debugging the pipeline.

---

## Implementation status (2026-02-28)

Both stages are implemented on `feat/pexpect-pipeline`. Validation is in progress on edcloud.

| File | Role | Status |
|------|------|--------|
| `scripts/vax_pexpect.py` | Stage B: VAX compile+run | Implemented; validation in progress |
| `scripts/pdp11_pexpect.py` | Stage A: PDP-11 nroff | Implemented; validation in progress |
| `vintage/machines/vax/Dockerfile.vax-pexpect` | VAX Docker image | Implemented; disk decompress fixed |
| `vintage/machines/pdp11/Dockerfile.pdp11-pexpect` | PDP-11 Docker image | Implemented |
| `vintage/machines/vax/configs/vax780-pexpect.ini` | VAX pexpect ini | Static; no network/telnet |
| `vintage/machines/pdp11/configs/pdp11-pexpect.ini` | PDP-11 pexpect ini | Static; no telnet |
| `scripts/edcloud-vintage-runner.sh` | Orchestrator | Rewritten; no screen/telnet |

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

The current `docker-compose.production.yml` uses telnet ports for both machines.
For pexpect, run SIMH directly (not in a container with a telnet port) or remove the
`set console telnet` directive and drive SIMH via `pexpect.spawn('pdp11 pdp11.ini')`.

---

## Stage A — PDP-11 nroff (implement first)

**What it does:** Renders `brad.1` (troff man page source) to `brad.man.txt` using
`nroff -man` on 2.11BSD.

**Why first:** nroff on the PDP-11 is the most historically authentic step (nroff was
written at Bell Labs for the PDP-11). It is also the simplest stage — single machine,
one tool, no compilation.

**Known working (2026-02-28 diagnostic run):**
- 2.11BSD boots to root `#` prompt after Enter at `Boot:` prompt
- `mount /usr` makes tools available
- `/usr/bin/nroff` present and functional
- `/usr/bin/uudecode` present (not needed for this stage)

**Input:** `build/vintage/brad.1` — generated by Python from `resume.yaml`.
Python template renders troff macros directly; no vintage compilation needed for Stage A.

**Pexpect script outline:**

```python
import pexpect

child = pexpect.spawn('pdp11 pdp11.ini', timeout=120)

# Boot: prompt — press Enter to boot unix kernel (not netnix)
child.expect('Boot:')
child.sendline('')

# Wait for root shell
child.expect('#')
child.sendline('mount /usr')
child.expect('#')

# Inject brad.1 via heredoc
child.sendline('cat > /tmp/brad.1 << \'HEREDOC_EOF\'')
for line in brad1_content.splitlines():
    child.sendline(line)
child.sendline('HEREDOC_EOF')
child.expect('#')

# Render
child.sendline('nroff -man /tmp/brad.1 > /tmp/brad.man.txt')
child.expect('#', timeout=60)

# Read output back
child.sendline('cat /tmp/brad.man.txt')
child.expect('#')
output = child.before.decode()

child.sendline('exit')
```

**PDP-11 ini change needed:** Remove `set console telnet=2327` from `pdp11.ini`
(or create a separate `pdp11-pexpect.ini` without it).

**Critical constraint:** SIMH exits if no client connects within ~60 seconds when
telnet mode is active. In stdin/stdout mode (no telnet directive), this constraint
does not apply — pexpect is the console from the start.

---

## Stage B — VAX bradman.c (implement after A works)

**What it does:** Compiles `bradman.c` on 4.3BSD VAX and runs it to transform
`build/vintage/resume.vintage.yaml` into `build/vintage/brad.1` (troff source).

**Known working (2026-02-28 diagnostic run):**
- 4.3BSD boots to login prompt on telnet console
- Root login works (no password)
- `cc` compiler available
- VAX console confirmed: root shell, echo marker test passed

**Inputs:**
- `vintage/machines/vax/bradman.c` — C source for the man page generator
- `build/vintage/resume.vintage.yaml` — generated by Python from `resume.yaml`

**Pexpect script outline:**

```python
child = pexpect.spawn('simh-vax vax.ini', timeout=120)

# VAX 4.3BSD boot sequence
child.expect('login:')
child.sendline('root')
child.expect('#')

# Inject bradman.c via heredoc
child.sendline('cat > /tmp/bradman.c << \'HEREDOC_EOF\'')
for line in bradman_c.splitlines():
    child.sendline(line)
child.sendline('HEREDOC_EOF')
child.expect('#')

# Inject resume.vintage.yaml
child.sendline('cat > /tmp/resume.vintage.yaml << \'HEREDOC_EOF\'')
for line in resume_yaml.splitlines():
    child.sendline(line)
child.sendline('HEREDOC_EOF')
child.expect('#')

# Compile
child.sendline('cd /tmp && cc -O -o bradman bradman.c')
child.expect('#', timeout=120)  # compilation takes ~30-60s on VAX

# Run
child.sendline('./bradman -i resume.vintage.yaml -o brad.1')
child.expect('#')

# Read output
child.sendline('cat /tmp/brad.1')
child.expect('#')
brad1_output = child.before.decode()
```

**Note on heredoc and special characters:** `resume.vintage.yaml` and `bradman.c` may
contain characters that need escaping in heredoc. Use pexpect's `sendline` with careful
quoting, or consider base64-encoding the content and decoding on the VAX with `uudecode`.

---

## Stage A+B — Connected

**Transfer mechanism:** Host-mediated via pexpect. FTP directly to PDP-11 is not viable
(see constraints below). The host reads `brad.1` out of the VAX pexpect session, writes
it to a temp file, then injects it into the PDP-11 pexpect session.

```
VAX pexpect session → brad.1 text → host temp file → PDP-11 pexpect session → brad.man.txt
```

**Ordering:**
1. Run Stage B pexpect script → capture `brad.1` text
2. Write to `build/vintage/brad.1`
3. Run Stage A pexpect script with that `brad.1` as input

**Why not FTP:** The PDP-11 2.11BSD disk image uses the `unix` kernel (not `netnix`).
The `netnix` kernel crashes on `xq` (Ethernet controller) initialization. The `unix`
kernel has no working Ethernet. FTP to the PDP-11 guest is not viable.
See `docs/archive/DEAD-ENDS.md`.

---

## Integration into edcloud-vintage-runner.sh

The runner script replaces its current screen/telnet stages with calls to pexpect scripts.
The overall CI/SSM/edcloud control plane stays the same; only the execution plane changes.

Suggested structure:
- `scripts/pdp11_pexpect.py` — Stage A implementation
- `scripts/vax_pexpect.py` — Stage B implementation
- `scripts/edcloud-vintage-runner.sh` — orchestrator: calls Python scripts, handles
  artifact extraction and cleanup

---

## Evidence from 2026-02-28 diagnostic run

Both machines were confirmed working on edcloud:

- **VAX:** Connected via telnet 127.0.0.1:2323, logged in as root, echo marker confirmed.
  Boot sequence: `4.3 BSD UNIX (vaxbsd)` login prompt → root shell.
- **PDP-11:** Connected via telnet 127.0.0.1:2327, pressed Enter at `Boot:`, booted to
  root `#` prompt. `mount /usr` successful. Both `/usr/bin/nroff` and `/usr/bin/uudecode`
  confirmed present.
- **PDP-11 container exit:** When telnet mode is active (`set console telnet=2327`),
  SIMH exits if no client connects within ~60s. Switching to stdin/stdout mode
  eliminates this constraint entirely.
- **VAX uploads:** All four file uploads via heredoc completed successfully in the
  diagnostic run. The build session login failure (blank terminal after upload sessions)
  was a timing/TTY state issue — consistent with the screen/sleep approach being
  fundamentally unreliable.

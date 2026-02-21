# Transport Archive (Console + FTP)

This document records **removed** transfer approaches so they can be restored later
without digging through old commits.

Current active transport is **TS11 tape** (see `resume_generator/vax_stage.py`).

---

## Console transfer (removed)

**What it did**
- Sent `bradman.c` and `resume.vax.yaml` into the VAX guest by writing to a shell
  session over the SIMH DZ telnet line.
- Used `cat >> file` / `ed -s` to stream file contents.

**Why it was removed**
- The SIMH DZ/telnet line drops input for larger pastes unless XON/XOFF flow control
  is perfectly respected.
- Even with throttling, larger files would stall (prompt never returned).

**Where the code lived**
- `resume_generator/vax_stage.py`:
  - `_transfer_guest_inputs`
  - `TelnetSession.send_file`
  - `TelnetSession.send_file_ed`
  - `TelnetSession.send_file_heredoc`
  - Helpers: `_chunk_lines`
- CLI flags:
  - `--transfer console`

**Notes**
- This can probably work if a proper XON/XOFF aware sender is used, or if the console
  transfer is reduced to very small paced chunks.

---

## FTP transfer (removed)

**What it did**
- Started a lightweight FTP server container and had the VAX guest fetch
  `bradman.c` + `resume.vax.yaml` via `/usr/ucb/ftp`.

**Why it was removed**
- The VAX guest could not reliably reach the FTP server/container.
- Attempts to connect to the container IP or Docker gateway timed out in this setup.

**Where the code lived**
- `resume_generator/vax_stage.py`:
  - `_transfer_guest_inputs_ftp`
  - `_start_ftp_container`
  - `FtpContainer` dataclass
  - Helpers: `_sh_single_quote`, `_parse_default_gateway`
- CLI flags:
  - `--transfer ftp`
  - `--ftp-image`

**Notes**
- Networking and routing inside the SIMH container are the likely issues.
- This could be revisited if the container is run in host mode or if the guest
  gets a stable route to a known FTP host.

---

## Restoration checklist

To restore either method:

1. Reintroduce the removed functions/CLI flags from git history.
2. Update `resume_generator/vax_stage.py` to allow selecting transfer modes again.
3. Add status notes in README and update `PLAN.md` to reflect the chosen transport.

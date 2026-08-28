# Debug the pexpect pipeline

Use this reference to diagnose SIMH console and artifact failures. For commands, data flow, artifacts, and image promotion, see [the pipeline operations guide](../INDEX.md).

## Components

| Path | Function |
|---|---|
| `resume_generator/vintage_yaml.py` | Emit the fixed five-scalar guest input |
| `resume_generator/vintage_contract.py` | Validate public inputs and the rendered bio |
| `resume_generator/image_manifest.py` | Bind the promoted image pair to image-owned source |
| `vintage/machines/vax/bradman.c` | Convert guest input to troff on VAX 4.3BSD |
| `scripts/vax_pexpect.py` | Boot the VAX, run `bradman`, and capture a UUCP spool |
| `scripts/pdp11_pexpect.py` | Boot the PDP-11, decode the spool, and run `nroff` |
| `scripts/simh_session.py` | Provide logging, checked commands, spool checks, and batched heredocs |
| `resume_generator/bio_yaml.py` | Convert the rendered bio to Hugo data |
| `resume_generator/build_log.py` | Render the published build log |
| `scripts/vintage-runner.sh` | Orchestrate containers and write final host artifacts |

## Session behavior

- Spawn SIMH through a pseudo-terminal and use its standard input and output. Do not configure network, DZ terminals, remote consoles, or telnet listeners.
- Wait for explicit boot, login, prompt, status, and artifact markers. Use the 5 ms per-line delay only to protect the guest tty during heredoc transfer.
- Switch the guest to `/bin/sh` before setting `PS1` or sending heredocs. The default root shell can be csh, which handles both operations differently.
- Before sending any file, set ERASE to DEL and KILL to Ctrl-U. The Python session sends literal `0x7f` and `0x15` bytes to `stty`; the defaults, `#` and `@`, occur in source and UUE data and corrupt input.
- Use distinct prompts: `VAXsh> ` for VAX and `PDPsh> ` for PDP-11. Do not match a bare `#`; the VAX kernel banner contains that character.
- Use `run_checked()` for every guest command that creates or validates an artifact. It appends a numeric status marker and raises before the next stage on a nonzero exit status.
- Treat a timeout after guest shell exit as nonfatal. Both guests can restart login instead of returning EOF; the cleanup path terminates SIMH.

## Stage B: VAX 4.3BSD

The VAX image records the SIMH binary and configuration paths under `/opt/`. Its build expands the base image's gzipped RA81 disks because SIMH cannot attach them directly. `vax780-pexpect.ini` leaves only the local console, time-of-day clock, and two attached MSCP disks enabled.

The VAX script performs these operations:

1. Start SIMH and wait for the BSD login prompt.
2. Log in as root, switch to `/bin/sh`, set safe tty control characters, and set `VAXsh> `.
3. Inject `bradman.c` with a quoted heredoc.
4. Encode `bio.vintage.yaml` on the host, inject it in ten-line UUE heredocs, and decode it in the guest. This avoids the 256-byte canonical tty line limit.
5. Compile and run `bradman`.
6. Encode `/tmp/brad.bio.roff` as `/tmp/brad.bio.uu` and capture it between explicit markers with tty echo disabled.

For the equivalent guest commands, see [the VAX stage reference](../../vax/README.md#run-the-guest-commands).

## UUCP spool transfer

The VAX produces the spool in its stage-only output mount. The host rejects links, special files, and empty output, copies the spool to `build/vintage/brad.bio.uu`, and exposes that copy to the PDP-11 as a read-only input. The PDP-11 script checks that it has a `begin` line, at least one encoded line, and a final `end` line, then injects it in ten-line heredoc batches.

This transfer uses printable UUE lines no longer than 62 characters. The host does not decode or rewrite the troff payload.

## Stage A: PDP-11 2.11BSD

The PDP-11 script performs these operations:

1. Start SIMH, select the `unix` kernel at the boot prompt, and wait for root login.
2. Switch to `/bin/sh`, set safe tty control characters, and set `PDPsh> `.
3. Mount `/usr` and require `/usr/bin/nroff` and `/usr/bin/uudecode`.
4. Inject and decode `brad.bio.uu`.
5. Run `nroff` without a macro package.
6. Capture the result between explicit markers with tty echo disabled.
7. Normalize line endings and remove terminal control characters, overstrikes, form feeds, trailing whitespace, and boundary blank lines.

The root-prompt wait has a five-minute safety bound for CPU contention on shared hosted runners. State transitions still depend on explicit guest output rather than fixed delays.

The render command is:

```sh
nroff -Tlp /tmp/brad.bio.roff < /dev/null > /tmp/brad.bio.txt
```

`-Tlp` prevents terminal-specific control sequences. Redirecting standard input from `/dev/null` prevents `nroff` from waiting for a key at page breaks.

## Host output contracts

- `vintage_yaml.py` emits exactly `schemaVersion`, `buildDate`, `bioName`, `bioHeadline`, and `bioProfile`, in that order, as quoted printable ASCII strings.
- `bradman.c` writes name and headline without fill, then fills and justifies the summary at a 60-column measure with no page offset or hyphenation.
- The build date appears only in a troff comment. With unchanged public text, orchestration, and pinned images, `nroff` produces stable rendered bytes.
- The runner clears its owned outputs before starting and records success or failure in `pipeline-status.json`.
- The runner gives each guest only read-only inputs and a separate output mount, then copies validated final artifacts under `build/vintage/`; workflows consume those host-owned files directly.
- Guest containers run one at a time on a build-specific internal bridge with no external route, drop all capabilities, disallow privilege gain, and use process and memory limits. The runner removes the bridge during cleanup.
- Production validates one source-bound manifest of immutable image digests and disables local builds and environment bootstrap.

## Failure guide

| Symptom | Check |
|---|---|
| VAX reaches EOF immediately after `run 2` | Confirm that the image expanded both RA81 disk files and cached the correct SIMH paths. |
| `pexpect` matches a prompt before login finishes | Match `# ` for the initial root prompt, then require the custom prompt. |
| A heredoc never terminates | Confirm that the session switched from csh to `/bin/sh`. |
| Injected source or UUE data is corrupt | Confirm that ERASE and KILL changed before the first file transfer. |
| A long UUE transfer stalls | Confirm that `inject_batched_heredoc()` uses ten-line batches and the per-line throttle. |
| `nroff` emits BEL characters and hangs | Confirm `-Tlp` and `< /dev/null` are present. |
| A command returns to the prompt without an artifact | Confirm that the call uses `run_checked()` and tests the output file. |
| A retry reports an older successful build | Confirm that the runner clears owned artifacts and rewrites failure status before emitting diagnostics. |
| Deployment uses stale orchestration | Confirm that both guest scripts and `simh_session.py` are bind-mounted from the checkout. |

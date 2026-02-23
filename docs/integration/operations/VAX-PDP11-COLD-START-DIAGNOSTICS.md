# VAX ↔ PDP-11 Cold-Start Diagnostics (Single-Host edcloud Path)

Purpose: provide a **fast, repeatable** diagnostic path when resuming work on the
distributed vintage pipeline and trying to determine whether Stage 1→3 is currently
viable.

This runbook is focused on the active architecture:

- `docker-compose.production.yml`
- VAX console on `localhost:2323`
- PDP-11 console on `localhost:2327`
- Stage flow implemented in `.github/workflows/deploy.yml`

---

## Status (2026-02-23)

**Docker root on edcloud is `/opt/edcloud/state/docker`** (not `/var/lib/docker/`).
If ghost containers appear in `docker ps -a` but can't be inspected or removed, stop
Docker, delete the stale dirs from `/opt/edcloud/state/docker/containers/`, restart.

**PDP-11 boot has two known failure modes:**

1. *Probe TTI disconnect* (old bug, fixed): one-shot `echo > /dev/tcp/.../2327` probes
   during early boot → SIMH TTI interrupt → reboot loop.
2. *SIMH console telnet timeout* (fixed): `set console telnet=2327` blocks the simulation
   until a client connects. Auto-boot handler solves this by holding the connection.
   `BUFFERED` SIMH option is NOT supported in this build (v4.0-0 commit 627e6a6b).

**Auto-boot handler** (`vintage/machines/pdp11/auto-boot.exp`) is deployed and working:
- Connects immediately to prevent SIMH timeout
- Answers `Boot:` prompt (sends `\r`)
- Detects single-user shell (`erase, kill ^U`), waits for `# `, sends `exit`
- Phase 3: waits for `login:` with **unlimited timeout** (`set timeout -1`)

**fsck timing**: First boot on the 167MB 2.11BSD image takes **40+ minutes** on emulated
PDP-11/73. This is normal — fsck runs in preen mode with no console output. Docker block I/O
stats stay flat after initial cache warmup (SIMH reads from page cache), which is NOT
evidence the emulator is idle. Container CPU stays at ~2-3% during emulation.

**As of 2026-02-23 ~02:10 UTC**: container is Up 39+ minutes; auto-boot sent `exit`
at ~1 min mark; `/etc/rc` + fsck have been running ~38+ min silently. `login:` has not
yet appeared but is expected. **Remaining unknowns**: (1) how long until `login:`
appears; (2) whether SIMH handles disconnect cleanly once multi-user is ready.

**Do NOT** connect to port 2327 manually while auto-boot.exp is still running —
SIMH only accepts one telnet client at a time. Check with:
```bash
docker exec pdp11-host /bin/bash -c 'ls /proc/*/exe 2>/dev/null | xargs -I{} readlink {} 2>/dev/null | grep expect'
```
If `expect` appears, auto-boot is still running. If it's gone, port 2327 is free.

**grep for `login:` in docker logs will false-positive** on the startup echo in
`pdp11-boot.sh`. Use `grep "2.11BSD\|login:" docker logs` or look for
`[auto-boot] 2.11BSD multi-user ready` instead.

---

## 0) Baseline checks (first 2 minutes)

```bash
git status --short
docker compose -f docker-compose.production.yml ps
```

Expect both `vax-host` and `pdp11-host` to be `Up`.

If containers are stale/noisy, restart cleanly:

```bash
docker compose -f docker-compose.production.yml up -d --build vax pdp11
```

---

## 1) Critical known constraints (read before testing)

1. **Do not probe PDP-11 console with one-shot TCP connects** (e.g. `echo > /dev/tcp/...2327`).
   - This can trigger SIMH TTI disconnect/reboot behavior during early boot.
   - Readiness should be based on container state + logs, not probe connect/disconnect.

2. **Keep console session count minimal and serialized.**
   - One active screen/telnet session per target console at a time.
   - Before new attempts, clear stale screen sessions:

   ```bash
   screen -ls
   screen -wipe
   ```

3. **`build/` ownership can break local generation.**
   - If `build/` became root-owned from container activity, local resume generation can fail.
   - Use an alternate build dir for local generation, e.g. `/tmp/brfid-local-build`.

---

## 2) PDP-11 readiness and stability gate

Use log-based readiness checks only:

```bash
docker compose -f docker-compose.production.yml ps pdp11
docker logs --tail 120 pdp11-host 2>&1
```

Healthy signal:

- `%SIM-INFO: Listening on port 2327`
- then console session reaches boot/login when one persistent client attaches.

Unhealthy signals (current blocker class):

- `%SIM-ERROR: ... Console Telnet connection lost`
- `%SIM-ERROR: sim_check_console () returned: Console Telnet connection timed out`

If unhealthy, restart `pdp11` and retry with stricter single-session handling.

---

## 3) Minimal PDP-11 smoke (single session)

```bash
screen -S pdp11-smoke -X quit 2>/dev/null || true
screen -dmS pdp11-smoke telnet 127.0.0.1 2327

# press Enter at Boot:, then verify tools
screen -S pdp11-smoke -X stuff $'\n'
sleep 2
screen -S pdp11-smoke -X stuff $'mount /usr\n'
sleep 2
screen -S pdp11-smoke -X stuff $'ls -l /usr/bin/uudecode /usr/bin/nroff\n'
sleep 2
screen -S pdp11-smoke -X hardcopy /tmp/pdp11-smoke-verify.txt
```

Expected evidence in hardcopy:

- `2.11 BSD UNIX` boot text
- shell prompt
- both `/usr/bin/uudecode` and `/usr/bin/nroff` listed.

---

## 4) VAX console sanity gate before Stage 1

```bash
screen -S vax-line1 -X quit 2>/dev/null || true
screen -dmS vax-line1 telnet 127.0.0.1 2323
sleep 6
screen -S vax-line1 -X stuff $'\n'
sleep 2
screen -S vax-line1 -X stuff $'root\n'
sleep 2
screen -S vax-line1 -X stuff $'echo __LINE1__\n'
sleep 2
screen -S vax-line1 -X hardcopy /tmp/vax-line1.txt
```

Expected evidence:

- successful root login on a tty line
- echoed marker appears (`__LINE1__`).

If this fails, do not proceed to Stage 1 automation; stabilize VAX console sessioning first.

---

## 5) Stage 1 local rehearsal notes

When generating `resume.vintage.yaml` locally, prefer:

```bash
python -m resume_generator --out site --html-only --with-vintage --vintage-mode local --build-dir /tmp/brfid-local-build
```

Reason: avoids local write failures if repo `build/` is root-owned.

If VAX upload automation appears to succeed but files are missing in guest `/tmp`,
capture hardcopy evidence and stop. This indicates session/line-target mismatch or
timing drift and should be diagnosed before Stage 2.

---

## 6) Evidence bundle to save after each attempt

- `/tmp/pdp11-smoke-verify.txt`
- `/tmp/vax-line1.txt`
- `/tmp/vax-stage1.txt` (if Stage 1 attempted)
- `/tmp/vax-cat-output.txt` (if extraction attempted)
- `docker logs --tail 120 pdp11-host`

These are the minimum artifacts for a productive next cold start.

---

## 7) Current practical next step (operator)

**DONE**: `auto-boot.exp` Phase 3 now uses `set timeout -1` (unlimited). Container is
currently running (Up 39+ min as of 2026-02-23 ~02:10 UTC) waiting for `login:`.

**Remaining steps to verify stable PDP-11 boot:**

1. Check if `login:` has appeared yet:
   ```bash
   docker logs --tail 20 pdp11-host 2>&1
   ```
   Look for `[auto-boot] 2.11BSD multi-user ready — disconnecting` — NOT just "login:"
   (grep for "login:" will false-positive on the startup echo).

2. Check if auto-boot is still running (if yes, port 2327 is occupied):
   ```bash
   docker exec pdp11-host /bin/bash -c 'ls /proc/*/exe 2>/dev/null | xargs -I{} readlink {} 2>/dev/null | grep expect'
   ```
   Empty output = expect exited = auto-boot done.

3. If `login:` appeared and auto-boot exited, verify SIMH handled disconnect cleanly:
   ```bash
   docker compose -f docker-compose.production.yml ps pdp11
   ```
   Expect `Up` (not restarting/exited). If SIMH rebooted on disconnect, the container
   will show a new start time or be in a reboot loop.

4. If container is still Up after disconnect, connect and smoke-test:
   ```bash
   screen -dmS pdp11-smoke telnet 127.0.0.1 2327
   sleep 2
   screen -S pdp11-smoke -X stuff $'\n'
   sleep 2
   screen -S pdp11-smoke -X stuff $'mount /usr\n'
   sleep 2
   screen -S pdp11-smoke -X stuff $'ls -l /usr/bin/uudecode /usr/bin/nroff\n'
   sleep 2
   screen -S pdp11-smoke -X hardcopy /tmp/pdp11-smoke-verify.txt
   ```
   Expected: `login:` prompt (multi-user mode), `/usr` mounts, both binaries present.

5. Only after smoke test passes proceed to Stage 1→3 rehearsal.

**If the container is in a reboot loop** after auto-boot disconnects: SIMH is still
crashing on disconnect. Investigate SIMH TTI error in logs. One option: add a
`sleep 5` after `close` in auto-boot.exp to let 2.11BSD flush before disconnect.
Another option: use `send_user` to signal readiness then have an external watchdog
manage the lifecycle rather than auto-boot.exp disconnecting.

**Note on subsequent boots**: Once the disk is cleanly unmounted (via proper
multi-user shutdown), subsequent boots go directly to `login:` much faster (no
full fsck needed). The first boot is the slow one.

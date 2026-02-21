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

Run a **strictly serialized** Stage 1→3 rehearsal (single session per console,
no parallel screen/telnet clients) on edcloud/GitHub path, since that execution
model is closest to production workflow timing.

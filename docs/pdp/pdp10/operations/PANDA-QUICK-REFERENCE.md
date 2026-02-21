# Panda TOPS-20 Quick Reference

**Last updated**: 2026-02-12 (strict validation rerun)
**Status**: ⚠️ System boots to BOOT prompt; config command mismatch fixed (`mount`→`devmount`), but strict attach-based handoff has not yet proven a real `@` prompt

---

## Current State

✅ **Working**:
- KLH10 emulator builds and runs
- Disk image (RH20.RP07.1) loads correctly
- System boots to BOOT V11.0(315) prompt
- VAX operational at 172.20.0.10
- PDP-10 at BOOT prompt at 172.20.0.40
- Runtime TTY confirmed: `stdin_open=true`, `tty=true`, `/proc/1/fd/0 -> /dev/pts/0`

⚠️ **Strict validation result (latest)**:
- `arpanet/scripts/panda_boot_handoff.py --retries 3 --timeout 50`
- `boot_seen=False`
- `sent_commands=[]`
- No proven `@` prompt

⚠️ **Next**: capture one known-good manual `docker attach` transcript to `@`, then encode exact timing/command behavior into automation

⚠️ **Important finding**:
- In this KLH10 build, `mount dsk0 ...` is invalid; use `devmount dsk0 ...`
- `arpanet/configs/panda.ini` has been corrected accordingly

---

## Quick Start (Next Session)

### 1. Connect to AWS
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@34.202.231.142
```

### 2. Check Container Status
```bash
cd brfid.github.io
docker compose -f docker-compose.panda-vax.yml ps

# Should show:
# panda-vax     Up   2323/tcp
# panda-pdp10   Up   2326/tcp, 21/tcp, 23/tcp
```

### 3. Connect to PDP-10 Console
```bash
# Preferred first attempt (true interactive TTY)
docker attach panda-pdp10

# Fallback
telnet localhost 2326
```

> Note: host-mapped `localhost:2326` can accept then close immediately in some runs. Treat `docker attach` as primary for debugging BOOT handoff.

### 4. Boot TOPS-20
At the `BOOT>` prompt, type:
```
/G143
```

Or for standalone mode:
```
/E
dbugsw/ 2
147$G
```

### 5. Login (after boot completes)
```
@log operator dec-20
@enable
!terminal vt100
```

### 6. Configure Network
Edit these files with IP 172.20.0.40:
- `SYSTEM:INTERNET.ADDRESS`
- `SYSTEM:INTERNET.GATEWAYS` (gateway: 172.20.0.1)
- `SYSTEM:HOSTS.TXT`

### 7. Test from VAX
In another terminal:
```bash
telnet localhost 2323  # VAX console
```

From VAX BSD prompt:
```bash
ftp 172.20.0.40
```

---

## File Locations

**On Local Machine**:
- Dockerfile: `arpanet/Dockerfile.pdp10-panda`
- Config: `arpanet/configs/panda.ini`
- Compose: `docker-compose.panda-vax.yml`
- Tests: `arpanet/scripts/test_panda_vax.py`

**On AWS**:
- Project: `~/brfid.github.io/`
- Logs: `docker logs panda-pdp10`

**In Container** (`/opt/tops20/`):
- Emulator: `kn10-kl`
- Disk: `RH20.RP07.1` (498MB)
- Boot: `boot.sav`
- Config: `panda.ini`
- Device processes: `dpni20`, `dprpxx`

---

## Network Topology

```
Docker Bridge: 172.20.0.0/16
    Gateway: 172.20.0.1

    ┌──────────────────┐          ┌──────────────────┐
    │   VAX/4.3BSD     │          │  PDP-10/TOPS-20  │
    │  172.20.0.10     │◄────────►│  172.20.0.40     │
    │  Port: 2323      │  TCP/IP  │  Ports: 2326,21  │
    │  (jguillaumes)   │          │  (KLH10 Panda)   │
    └──────────────────┘          └──────────────────┘
         │                              │
         └──────────────┬───────────────┘
                        │
                   Docker Host
              AWS: 34.202.231.142
```

---

## Troubleshooting

### Container won't start
```bash
docker compose -f docker-compose.panda-vax.yml down
docker compose -f docker-compose.panda-vax.yml up -d
docker logs panda-pdp10 --tail 50
```

### Stuck at BOOT prompt
- Check logs: `docker logs panda-pdp10 | tail -100`
- Should see: `BOOT V11.0(315)` and `BOOT>`
- If telnet session closes immediately, use true TTY attach (`docker attach panda-pdp10`) and send `/G143`
- If command scripts show `mount dsk0 ...`, replace with `devmount dsk0 ...`

### Network issues
- Verify IP config: `docker network inspect panda-test`
- Check VAX: `telnet localhost 2323` then `ifconfig de0`
- Check PDP-10 after boot: `@info sys:internet.address`

### Need to rebuild
```bash
docker compose -f docker-compose.panda-vax.yml build pdp10-panda --no-cache
docker compose -f docker-compose.panda-vax.yml up -d
```

---

## AWS Management

**Current Instance**:
- ID: i-013daaa4a0c3a9bfa
- IP: 34.202.231.142
- Type: t3.medium
- Cost: ~$0.04/hr

**Destroy when done**:
```bash
cd test_infra/cdk && source ../../.venv/bin/activate
cdk destroy --force
```

**Check status**:
```bash
cd test_infra/cdk && source ../../.venv/bin/activate
aws ec2 describe-instances --instance-ids i-013daaa4a0c3a9bfa
```

---

## Key Documentation

**Start here**:
1. This file (quick reference)
2. `docs/arpanet/PANDA-TEST-RESULTS-2026-02-12.md` (comprehensive)
3. `docs/arpanet/progress/NEXT-STEPS.md` (next actions)

**Background**:
- `CHANGELOG.md` - Project status
- `docs/arpanet/PANDA-APPROACH.md` - Why this approach
- `docs/arpanet/PANDA-BUILD-STATUS-2026-02-12.md` - Build log

---

## Success Criteria

- [x] KLH10 builds successfully
- [x] Disk image loads
- [x] System boots to BOOT prompt
- [ ] TOPS-20 completes boot to login
- [ ] Network configured (172.20.0.40)
- [ ] FTP service available
- [ ] VAX can connect to PDP-10 FTP

**Hard proof criterion for this stage**: observe a real TOPS-20 `@` prompt (not just banner text such as `TOPS-20` in logs)

---

## Common Commands Reference

```bash
# Docker operations
docker compose -f docker-compose.panda-vax.yml ps
docker compose -f docker-compose.panda-vax.yml up -d
docker compose -f docker-compose.panda-vax.yml down
docker compose -f docker-compose.panda-vax.yml restart pdp10-panda
docker logs panda-pdp10 --tail 100 --follow

# Console access
telnet localhost 2326  # PDP-10
telnet localhost 2323  # VAX
# Ctrl-] then "quit" to exit telnet

# File sync from local
rsync -avz -e "ssh -i ~/.ssh/id_ed25519" \
  arpanet/configs/panda.ini \
  ubuntu@34.202.231.142:~/brfid.github.io/arpanet/configs/

# Container inspection
docker exec panda-pdp10 ls -la /opt/tops20/
docker network inspect panda-test
```

---

## Boot Commands Explained

**`/G143`** - Quick boot to normal operation
- Goes directly to TOPS-20 startup
- Default boot path

**`/E` then `147$G`** - Standalone boot
- `/E` - Enter debugger to modify parameters
- `dbugsw/ 2` - Set debug switch
- `147$G` - Go to address 147 (ESC-G in EDDT)
- Used for initial setup or maintenance

---

## Notes

- System successfully loads 498MB disk image with pre-installed TOPS-20
- Config file requires `go` command to start emulation after loading boot.sav
- Device processes (dpni20, dprpxx) are present but not explicitly configured
- Boot loader appears to handle disk I/O automatically
- No ARPANET 1822 protocol needed - uses direct TCP/IP via dpni20

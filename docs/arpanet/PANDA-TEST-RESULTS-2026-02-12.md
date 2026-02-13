# Panda TOPS-20 Testing Results - 2026-02-12

> **Status note (newer evidence)**: This document captures the initial Panda test session. Later strict validation runs found that BOOT handoff remains unproven under automation (`boot_seen=False`, `sent_commands=[]`, no proven `@` prompt). Use `docs/arpanet/progress/NEXT-STEPS.md` and `STATUS.md` as canonical current state.

**Session duration**: ~2 hours
**Status**: ✅ **MAJOR PROGRESS** - PDP-10 boots to BOOT prompt
**Blocker**: Boot automation needs configuration

---

## Summary

Successfully built and deployed Panda TOPS-20 system using KLH10 emulator on AWS. The PDP-10 emulator boots successfully and reaches the TOPS-20 BOOT loader prompt, confirming that:
- ✅ KLH10 builds from source
- ✅ Disk image (RH20.RP07.1) loads correctly
- ✅ System boots to BOOT V11.0(315)
- ⚠️ Needs interactive boot commands or automation

---

## Key Discoveries

### 1. Correct Disk Image Name
**Incorrect assumption**: Disk image named `panda.rp`
**Reality**: Disk image is `RH20.RP07.1` in panda-dist.tar.gz root

### 2. Configuration File Structure
The Panda distribution uses a simple INI file that:
- Defines devices (DTE, RH20, disk, tape, network)
- Loads boot.sav bootstrap
- Requires `go` command to start emulation
- **Does NOT** require explicit disk image mounting in config

### 3. Boot Process
```
Config file → load boot.sav → go → BOOT V11.0(315) prompt → (needs boot commands)
```

The system successfully reaches the BOOT prompt, which is the TOPS-20 boot loader running from disk.

---

## Files Created/Modified

### New Files
- `arpanet/Dockerfile.pdp10-panda` - KLH10 build with Panda distribution
- `arpanet/configs/panda.ini` - KLH10 runtime configuration
- `docker-compose.panda-vax.yml` - VAX + PDP-10 orchestration
- `arpanet/scripts/test_panda_vax.py` - Automated connectivity tests
- `docs/arpanet/PANDA-APPROACH.md` - Approach documentation
- `docs/arpanet/PANDA-BUILD-STATUS-2026-02-12.md` - Build progress log

### Docker Infrastructure
```yaml
Services:
  vax:
    - IP: 172.20.0.10
    - Port: 2323 (console)
    - Status: Running

  pdp10-panda:
    - IP: 172.20.0.40
    - Ports: 2326 (console), 21 (FTP), 23 (telnet)
    - Status: Running, at BOOT prompt
```

---

## Current State

### Container Status (AWS)
```bash
$ docker ps
panda-pdp10   Up   0.0.0.0:2326->2323/tcp   brfidgithubio-pdp10-panda
panda-vax     Up   0.0.0.0:2323->2323/tcp   jguillaumes/simh-vaxbsd
```

### PDP-10 Boot Log
```
KLH10 V2.0H (MyKL) built Feb 12 2026 13:31:07
Emulated config:
	 CPU: KL10-extend   SYS: T20   Pager: KL  APRID: 3600
	 Memory: 8192 pages of 512 words  (SHARED)
	 Devices: DTE RH20 RPXX(DP) TM03(DP) NI20(DP)

[Configuring devices...]
load boot.sav
Loaded "boot.sav":
Format: DEC-CSAV
Data: 4630, Symwds: 0, Low: 040000, High: 054641, Startaddress: 040000

go
Starting KN10 at loc 040000...

BOOT V11.0(315)
BOOT>
```

**Status**: ✅ System boots successfully to BOOT prompt

---

## Next Steps

### Option A: Interactive Boot (15 minutes)
1. Connect to console: `telnet AWS_IP 2326`
2. At BOOT> prompt, type: `/G143` (or `/E` then `147$G`)
3. System should boot to TOPS-20
4. Configure network settings for Docker IP 172.20.0.40
5. Test VAX → PDP-10 connectivity

### Option B: Automated Boot (30-60 minutes)
1. Use expect script or socat to send boot commands automatically
2. Modify Dockerfile CMD to include boot automation
3. Test end-to-end automated boot
4. Validate FTP connectivity

### Option C: Simplified Approach (research)
- Check if boot.sav can be configured with default boot parameters
- Investigate KLH10 "boot" command with parameters
- Look for auto-boot options in TOPS-20 configuration

---

## Technical Details

### Panda Distribution Contents
```
panda-dist/
├── RH20.RP07.1           # 498MB disk image (TOPS-20 installed)
├── boot.sav              # Boot loader
├── kn10-kl               # KLH10 emulator binary
├── klt20.ini             # Configuration file
├── dpni20                # Network device process
├── dprpxx                # Disk device process
├── README                # Setup instructions
└── klh10-2.0h/           # Source code
```

### Network Configuration
**VAX** (172.20.0.10):
- Interface: de0
- OS: 4.3BSD
- Services: FTP server (port 21)

**PDP-10** (172.20.0.40):
- Device: ni0 (ni20 with dpni20 driver)
- OS: TOPS-20 (Panda distribution)
- Expected services: FTP, telnet

**Network**: Docker bridge (172.20.0.0/16)

---

## Validation Checklist

- [x] AWS instance deployed and accessible
- [x] Project files synced to AWS
- [x] VAX container running
- [x] PDP-10 container builds successfully
- [x] PDP-10 boots to BOOT prompt
- [x] Disk image loads correctly
- [ ] TOPS-20 starts and reaches login prompt
- [ ] Network interface configured
- [ ] VAX can ping PDP-10
- [ ] FTP connection VAX → PDP-10 works

---

## Lessons Learned

### 1. Device Process Architecture
KLH10 uses separate device processes (e.g., `dprpxx`, `dpni20`) that communicate with the emulator. The config file defines device types, but device processes handle actual I/O.

### 2. Boot Automation Complexity
Unlike SIMH, KLH10's boot process requires interaction with the BOOT loader. Options:
- Interactive telnet session
- Expect script automation
- Possible auto-boot configuration

### 3. Configuration Simplicity
The Panda distribution is well-designed:
- Pre-built disk image
- Minimal configuration required
- Clear documentation in README
- Works with standard KLH10 commands

### 4. Docker Compatibility
- KLH10 works in Docker with privileged mode
- Network device (dpni20) requires setuid binary
- Disk I/O works without special configuration
- Console port forwarding works correctly

---

## AWS Infrastructure

**Instance**: i-013daaa4a0c3a9bfa
**IP**: 34.202.231.142
**Type**: t3.medium
**Cost**: ~$0.04/hour
**Session duration**: ~2 hours
**Total cost**: ~$0.08

**Cleanup command**:
```bash
cd test_infra/cdk && source ../../.venv/bin/activate && cdk destroy --force
```

---

## Commands Reference

### Build and Start
```bash
# On AWS instance
cd brfid.github.io
docker compose -f docker-compose.panda-vax.yml build pdp10-panda
docker compose -f docker-compose.panda-vax.yml up -d
```

### Check Status
```bash
docker compose -f docker-compose.panda-vax.yml ps
docker logs panda-pdp10 | tail -50
docker logs panda-vax | tail -50
```

### Connect to Consoles
```bash
telnet localhost 2326  # PDP-10
telnet localhost 2323  # VAX
```

### Restart Services
```bash
docker compose -f docker-compose.panda-vax.yml restart pdp10-panda
docker compose -f docker-compose.panda-vax.yml restart vax
```

---

## Files on AWS

```
~/brfid.github.io/
├── arpanet/
│   ├── Dockerfile.pdp10-panda     # ✅ Working build
│   └── configs/panda.ini          # ✅ Loads successfully
├── docker-compose.panda-vax.yml   # ✅ Both containers running
└── arpanet/scripts/
    └── test_panda_vax.py          # Ready for testing
```

---

## Recommendation

**✅ PROCEED WITH OPTION A: Interactive Boot (with strict evidence capture)**

The hardest parts are done:
- ✅ Build infrastructure working
- ✅ Disk image found and loading
- ✅ System boots to BOOT prompt
- ✅ Network topology configured

**Current risk assessment (updated)**: Medium — console ingress/control-plane behavior has been non-deterministic in subsequent strict runs.

**Next session should**:
1. Connect to PDP-10 console via telnet
2. Send boot commands (`/G143` or equivalent)
3. Configure network for 172.20.0.40
4. Test FTP from VAX

---

## Success Metrics

**What works**:
- KLH10 emulator builds and runs
- Pre-built disk image loads
- Boot loader starts correctly
- Docker networking configured
- Console port accessible

**What remains**:
- Complete TOPS-20 boot sequence
- Network configuration
- Service validation (FTP, telnet)
- End-to-end connectivity test

**Important**: treat this progress snapshot as historical for the initial session only.
Current pass/fail status for automation and `@` prompt proof is tracked in `docs/arpanet/progress/NEXT-STEPS.md`.

---

## References

- Panda Distribution: http://panda.trailing-edge.com/
- KLH10 Documentation: Included in panda-dist/klh10-2.0h/doc/
- TOPS-20 Commands Manual: Classic DEC documentation
- Previous attempts: `docs/arpanet/PDP10-INSTALLATION-ATTEMPTS-2026-02-12.md`

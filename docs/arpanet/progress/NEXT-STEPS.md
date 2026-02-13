# ARPANET Next Steps

**Last updated:** 2026-02-12 Evening (Phase 1 & Phase 3 complete)
**Status**: ✅ **Investigation complete - Console automation blocker identified as common to both PDP-10 and PDP-11**

> Decision: Continue with VAX (proven working). Archive PDP-10/PDP-11 as experimental manual-boot systems.

---

## Current Situation

**Latest Session**: AWS testing and validation (2026-02-12 evening, continued)
**Duration**: ~2+ hours
**Status**: ✅ bootloader reached, ⚠️ final startup currently blocked by console session behavior

**Progress**:
- ✅ Fixed disk image path (`RH20.RP07.1`, not `panda.rp`)
- ✅ Fixed config file to include `go` command
- ✅ Identified command mismatch in Panda config: `mount dsk0 ...` is invalid for this KLH10 build (uses `devmount`)
- ✅ System boots and loads boot.sav successfully
- ✅ Reaches TOPS-20 BOOT loader prompt
- ⚠️ **Current blocker**: remote console sessions to `localhost:2326` are closing immediately before command handoff
- ⚠️ BOOT command injection is still non-deterministic; `/L` and `/G143` are not consistently accepted in non-interactive runs
- ⚠️ After a full `docker compose down && up -d` reset, host-port console `localhost:2326` still accepts then immediately closes (`recv == b''`), so remote scripted ingress remains unreliable
- ℹ️ `devmount dsk0 RH20.RP07.1` now reports `Cannot mount: drive busy` (expected when already attached by current runtime path), so the remaining issue is console/control-plane reliability rather than missing media
- ✅ Runtime TTY is confirmed interactive-capable: `stdin_open=true`, `tty=true`, `/proc/1/fd/0 -> /dev/pts/0`
- ⚠️ Strict automation rerun (`arpanet/scripts/panda_boot_handoff.py --retries 3 --timeout 50`) produced `boot_seen=False` and `sent_commands=[]` in all attempts, i.e. no observable BOOT stream over attach and no proof of `@` prompt
- ⚠️ Recent deterministic single-attempt rerun (restart + attach; `/G143`, `/E`, `dbugsw/ 2`, `147<ESC>g`) also produced no observable BOOT stream in automation (`boot_seen=False`, `sent=[]`, no `@`)
- ⚠️ Recent container log tails repeatedly show `?BOOT: Can't find bootable structure` when commands are accepted
- ⚠️ **Next**: run one final manual attach proof attempt; if no `@`, pivot to install/rebuild path (`inst-klt20`) rather than additional blind BOOT retries

**See**:
- `docs/arpanet/PANDA-TEST-RESULTS-2026-02-12.md` - **LATEST** test results and findings
- `docs/arpanet/PANDA-BUILD-STATUS-2026-02-12.md` - Build progress
- `docs/COLD-START.md` - Global quick orientation
- `docs/arpanet/PANDA-QUICK-REFERENCE.md` - Panda operator runbook

---

## What Was Attempted (2026-02-12)

### Panda TOPS-20 Approach
**Goal**: Use pre-built disk image with KLH10 for direct TCP/IP networking

**Progress**:
- ✅ Created `Dockerfile.pdp10-panda`
- ✅ Fixed build dependencies (linux-libc-dev)
- ✅ Disabled LITES feature (asm/io.h not available in Docker)
- ✅ KLH10 compiled successfully from source
- ✅ `RH20.RP07.1` disk image verified in Panda distribution/runtime container

**Files Created**:
- `arpanet/Dockerfile.pdp10-panda`
- `arpanet/configs/panda.ini`
- `docker-compose.panda-vax.yml`
- `arpanet/scripts/test_panda_vax.py`
- `docs/arpanet/PANDA-APPROACH.md`

**Disk Image Location**:
- URL: `http://panda.trailing-edge.com/panda-dist.tar.gz`
- Path in distribution/runtime: `RH20.RP07.1`
- Size: ~221 MB total download (archive), ~498 MB disk image

---

## Completed Investigations (2026-02-12 Evening)

### ✅ Phase 1: Final PDP-10 Gate (20 minutes)
**Goal**: Quick attempt to prove `@` prompt automation
**Result**: ❌ FAILED - Console automation timeout (empty logs, no interaction)
**Conclusion**: Automation script `panda_boot_handoff.py` couldn't interact with console

### ✅ Phase 3: PDP-11 Pivot (2 hours)
**Goal**: Test turnkey alternative with pre-built 2.11BSD
**Result**: ✅ POC SUCCESSFUL - ❌ SAME BLOCKER
**Findings**:
- ✅ Container builds successfully
- ✅ SIMH PDP-11 boots to `73Boot` prompt
- ✅ XQ network device works (`Eth: opened OS device eth0`)
- ❌ **Same console automation issue as PDP-10**
- Manual boot required for both systems

**See**: `docs/arpanet/PDP11-DEPLOYMENT-RESULTS-2026-02-12.md`

### 🔍 Root Cause Analysis
**Problem**: SIMH console design (KLH10, SIMH PDP-11, and likely all SIMH variants)
**Symptoms**:
- Telnet mode: Waits for connection, restarts on disconnect
- Stdio mode: Output appears but input timing is unreliable
- Docker attach: Can't replay boot prompt, timing issues
- Expect/PTY: Inconsistent console output capture

**Impact**: Both PDP-10 and PDP-11 viable for **manual operation**, not CI/CD automation

## Decision Points

### ✅ DECISION MADE: Continue with VAX, Archive Vintage Host Experiments

**Rationale**:
1. VAX already working and proven
2. PDP-11 didn't solve automation problem (same SIMH blocker)
3. 5.5+ hours invested (3.5h PDP-10 + 2h PDP-11) with same outcome
4. Console automation blocker is fundamental to SIMH design, not specific to PDP-10 or PDP-11

**Next Actions**:
1. ✅ Document PDP-10 and PDP-11 findings
2. ✅ Update STATUS.md with decision
3. → Clean up AWS infrastructure
4. → Focus on resume build pipeline with VAX
5. → Archive PDP-10/PDP-11 work as experimental branches

**Pros**: Keeps current Panda path if recoverable
**Cons**: Low confidence after repeated no-byte attach outcomes

### Option A2: Automate Boot Sequence ⏱️ 30-60 minutes
**Action**: Create expect script or modify Dockerfile to send boot commands

**Steps**:
1. Write expect script to send `/G143` to console
2. Modify docker-compose or Dockerfile CMD
3. Test automated boot
4. Validate services start correctly

**Pros**: Fully automated, reproducible
**Cons**: Requires additional scripting work

### ✅ Option B: Pivot path if manual proof fails once more (RECOMMENDED fallback)
- Move to installation/rebuild flow (`inst-klt20`) to establish a known bootable structure baseline
- Keep same AWS runtime and evidence discipline (transcript + tail logs + command history)
- If rebuild path also stalls, fall back to KL10 serial plan (`docs/arpanet/KL10-SERIAL-FTP-PLAN.md`)

### Option C: Parallel host contingency planning (non-active path)
- A staged host-replacement plan is documented in:
  - `docs/arpanet/PDP11-HOST-REPLACEMENT-PLAN.md`
- Use this only as a controlled parallel track; keep Panda as active path until explicit pivot.

---

## Previous Attempts (All Failed)

| Approach | Blocker | Time Invested |
|----------|---------|---------------|
| TOPS-20 V4.1 (SIMH) | Boot loop bug | 1 hour |
| TOPS-20 V7.0 (Cornwell SIMH) | Parameter issues | 1 hour |
| KLH10 (Docker image) | Execution errors | 30 min |
| Panda (KLH10 source) | Missing disk image | 1 hour |
| **Total** | | **~3.5 hours** |

**Documentation**: `docs/arpanet/PDP10-INSTALLATION-ATTEMPTS-2026-02-12.md`

---

## Recommendation

**✅ IMMEDIATE ACTION**: Do exactly one manual attach proof attempt; if no `@`, pivot immediately to rebuild path

The system reaches BOOT reliably, but strict automation still cannot observe/drive the BOOT stream, and logs also show `Can't find bootable structure` in some handoff attempts. Use this gate:

```bash
# 1. SSH to AWS instance
ssh -i ~/.ssh/id_ed25519 ubuntu@34.202.231.142

# 2. Validate PDP-10 console lifecycle
# (recent evidence: sessions can connect then close immediately)

# 3. Connect to PDP-10 console (preferred)
docker attach panda-pdp10

# Fallback
telnet localhost 2326

# 4. At BOOT> prompt, enter boot command
BOOT> /G143
# OR for standalone boot:
BOOT> /E
dbugsw/ 2
147$G

# 5. Hard gate: prove a real TOPS-20 @ prompt
# If not reached in this attempt, stop retries and pivot to inst-klt20 rebuild

# 6. Login as OPERATOR
@log operator dec-20
@enable

# 7. Configure network (if needed)
# Edit SYSTEM:INTERNET.ADDRESS for 172.20.0.40
# Edit SYSTEM:INTERNET.GATEWAYS for 172.20.0.1

# 8. Test from VAX
telnet localhost 2323  # VAX console
# Then: ftp 172.20.0.40
```

**Expected outcome (if gate passes)**: Working VAX ↔ PDP-10 FTP transfer via TCP/IP after deterministic BOOT handoff

**Current state**:
- Docker containers: Running
- VAX: Operational at 172.20.0.10
- PDP-10: BOOT prompt reached; command ingress path unstable and bootable-structure failure intermittently observed
- Network: Configured (172.20.0.0/16)

**Fallback options** (if gate fails):
- Pivot to `inst-klt20` installation/rebuild path (preferred)
- Then reattempt automation only after manual `@` proof on rebuilt system
- Keep KL10 serial plan as secondary fallback

---

## AWS Instance Status

**Running**: 34.202.231.142 (i-013daaa4a0c3a9bfa)
**Type**: t3.medium (~$0.04/hr)
**Session duration**: ~2 hours
**Action needed**: `cd test_infra/cdk && cdk destroy --force`
**Current session cost**: ~$0.08

**Containers running**:
- `panda-vax`: Port 2323 (VAX console)
- `panda-pdp10`: Port 2326 (PDP-10 console), 21 (FTP), 23 (telnet)

---

## Quick Start Commands

```bash
# Check AWS status
cd test_infra/cdk && source ../../.venv/bin/activate
aws ec2 describe-instances --instance-ids i-013daaa4a0c3a9bfa

# Destroy AWS (when done)
cd test_infra/cdk && cdk destroy --force

# Connect and complete boot
ssh -i ~/.ssh/id_ed25519 ubuntu@34.202.231.142
telnet localhost 2326  # PDP-10 console
# At BOOT> prompt: /G143

# Check container status
cd brfid.github.io
docker compose -f docker-compose.panda-vax.yml ps
docker logs panda-pdp10 | tail -50
```

---

## Related Documentation

- **Cold start guide**: `docs/COLD-START.md`
- **Panda quick reference**: `docs/arpanet/PANDA-QUICK-REFERENCE.md`
- **Panda build status**: `docs/arpanet/PANDA-BUILD-STATUS-2026-02-12.md`
- **Panda approach**: `docs/arpanet/PANDA-APPROACH.md`
- **Previous PDP-10 attempts**: `docs/arpanet/PDP10-INSTALLATION-ATTEMPTS-2026-02-12.md`
- **Protocol mismatch**: `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`
- **KL10 serial fallback context**: `docs/arpanet/KL10-SERIAL-FTP-PLAN.md`
- **Project state summary**: `PROJECT-STATE-FOR-RESEARCH.md`

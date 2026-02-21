# TOPS-20 Tape Boot Failure on SIMH KS10 - Technical Analysis

> **⚠️ ARCHIVED**: 2026-02-11 - KS10 emulator incompatible, superseded by KL10
> See: `docs/arpanet/archive/ks10/README.md`

**Date**: 2026-02-08 23:45 UTC
**Status**: ~~BLOCKED~~ **ARCHIVED** (KS10 incompatibility)
**Context**: Follow-up to TOPS20-INSTALLATION-PROBLEM.md

---

## Executive Summary

After solving the telnet console timing issue by using Docker TTY (interactive console), we now face a **different problem**: The TOPS-20 V4.1 installation tape **fails to boot** on SIMH KS10 simulator.

**Error**: `Unknown KS-10 simulator stop code 7, PC: 000100`

The boot command executes but immediately halts with an unknown stop code, preventing us from reaching the MTBOOT boot loader prompt needed for installation.

---

## Current State

### What Works ✅

1. **Container Launch**: Docker container starts successfully
2. **SIMH Startup**: Simulator loads configuration without critical errors
3. **Tape Attachment**: Installation tape recognized and attached
   ```
   %SIM-INFO: TUA0: Tape Image '/machines/pdp10/tops20_v41.tap' scanned as SIMH format
   ```
4. **Disk Attachment**: RP06 disk attached successfully
5. **Console Access**: Direct TTY console working (no telnet timing issues)
6. **sim> Prompt**: SIMH command prompt accessible and responsive

### What Fails ❌

1. **Tape Boot**: `boot tua0` command fails immediately
2. **Stop Code 7**: Unknown halt condition
3. **MTBOOT Unreachable**: Boot loader never starts
4. **Installation Blocked**: Cannot proceed past boot stage

---

## Technical Details

### Environment

**Emulator:**
```
KS-10 simulator V4.0-0 Current
git commit id: 627e6a6b
```

**Platform:**
- Host: AWS EC2 t3.medium (x86_64)
- OS: Ubuntu (Docker container)
- Docker Image: brfidgithubio-pdp10

**SIMH Configuration** (`install.ini`):
```ini
set debug stdout

; CPU configuration - GIVES ERROR
set cpu tops-20
%SIM-ERROR: CPU device: Non-existent parameter - TOPS-20

; WRU configuration - GIVES ERROR
set wru 006
%SIM-ERROR: Non-existent device: WRU

; Disable unused devices
set dz disabled
set lp20 disabled

; Tape drive with installation tape
set tua enable
set tua0 locked
attach tua0 /machines/pdp10/tops20_v41.tap
# SUCCESS: Tape attached

; RP06 system disk
set rpa enable
set rpa0 rp06
attach rpa0 /machines/data/tops20.dsk
# SUCCESS: Disk attached

; Boot from tape
boot tua0
# FAILS: Unknown stop code 7
```

### Installation Tape

**Source**: http://pdp-10.trailing-edge.com/tapes/bb-d867e-bm_tops20_v41_2020_instl.tap.bz2

**File Details**:
- Size: 21 MB (decompressed)
- Format: SIMH tape format (recognized by simulator)
- Location in container: `/machines/pdp10/tops20_v41.tap`
- Attachment status: Successfully attached to TUA0

**Verification**:
```bash
docker exec pdp10-install ls -lh /machines/pdp10/tops20_v41.tap
# -rw-r--r-- 1 root root 21M
```

---

## Error Analysis

### Primary Error

```text
sim> boot tua0

Unknown KS-10 simulator stop code 7, PC: 000100
sim>
```

**Breakdown:**
- **Command**: `boot tua0` (boot from tape unit 0)
- **Result**: Immediate halt
- **Stop Code**: 7 (unknown/undocumented)
- **Program Counter**: 000100 (octal, = 64 decimal)
- **Behavior**: Returns to sim> prompt instead of continuing to MTBOOT

### Secondary Errors

**1. CPU Configuration Error**:
```text
set cpu tops-20
%SIM-ERROR: CPU device: Non-existent parameter - TOPS-20
```

**Analysis:**
- This command may be specific to KL10, not KS10
- Gunkies recipe (which works) uses this command
- Our KS10 build doesn't support this parameter
- **Impact**: Unknown - may be why boot fails

**2. WRU Device Error**:
```text
set wru 006
%SIM-ERROR: Non-existent device: WRU
```

**Analysis:**
- WRU = "Who aRe yoU" character (interrupt character)
- Should be set via `set console wru=006` not `set wru`
- **Impact**: Unlikely to affect boot (console configuration only)

---

## Boot Sequence Analysis

### Expected Boot Sequence (from working installations)

```text
sim> boot tua0

BOOT V11.0(315)

MTBOOT>
```

**Should happen:**
1. SIMH loads tape bootstrap into memory
2. Bootstrap reads first tape file (MTBOOT.EXB)
3. MTBOOT program starts and prints banner
4. MTBOOT> prompt appears
5. User can type `/L`, `/G143`, etc.

### Actual Boot Sequence (our failure)

```text
sim> boot tua0

Unknown KS-10 simulator stop code 7, PC: 000100
sim>
```

**What happens:**
1. SIMH attempts to load tape bootstrap
2. CPU halts immediately at PC=000100
3. Stop code 7 indicates unexpected halt condition
4. No BOOT banner, no MTBOOT prompt
5. Returned to SIMH sim> prompt

**Program Counter 000100**:
- Octal 000100 = Decimal 64
- Very low memory address
- Likely in bootstrap loader code
- Suggests failure during initial tape boot block execution

---

## Comparison with Working Setups

### Gunkies Recipe (Works)

**Configuration:**
```ini
set cpu tops-20    # Sets CPU to TOPS-20 mode
d wru 006          # Deposit WRU character
att tu i.tap       # TU instead of TUA
set rp rp06
att rp t20.dsk
boot tu            # Boot from TU
```

**Key Differences:**
1. Uses `d wru 006` (deposit command) instead of `set wru`
2. Uses `TU` device instead of `TUA`
3. Uses `set cpu tops-20` (which our build rejects)
4. Boots from `tu` not `tua0`

### Our Configuration (Fails)

```ini
set cpu tops-20    # ERROR: Not supported
set wru 006        # ERROR: No such device
set tua enable
attach tua0 /machines/pdp10/tops20_v41.tap
boot tua0          # FAILS: Stop code 7
```

---

## Hypotheses

### Hypothesis 1: Wrong Boot Device

**Theory**: TUA vs TU device naming difference matters

**Evidence**:
- Gunkies uses `tu` (singular)
- We use `tua0` (specific unit)
- SIMH may have different boot paths for TU vs TUA

**Test**:
```
sim> boot tu
```

### Hypothesis 2: Missing CPU Mode Configuration

**Theory**: `set cpu tops-20` is required but our build doesn't support it

**Evidence**:
- Gunkies recipe has this command
- Our SIMH build rejects it with error
- CPU may be in wrong mode for TOPS-20 tape

**Potential Solutions**:
- Use different SIMH build that supports this parameter
- Find alternative CPU configuration method for KS10
- Use KL10 simulator instead of KS10

### Hypothesis 3: SIMH Version Incompatibility

**Theory**: Our SIMH build (V4.0-0) has boot issues with this tape

**Evidence**:
- Specific git commit: 627e6a6b
- Unknown stop code suggests unhandled condition
- May need newer or different SIMH version

**Version Info**:
```text
KS-10 simulator V4.0-0 Current
git commit id: 627e6a6b
```

**Test**: Try building SIMH from different commit or version

### Hypothesis 4: Tape Format Mismatch

**Theory**: Tape format incompatible with KS10 bootstrap

**Evidence**:
- Tape scanned successfully as "SIMH format"
- But boot still fails
- May be formatted for KL10 not KS10

**Questions**:
- Is this tape image KL10-specific?
- Does KS10 require different tape format?
- Are there KS10-specific TOPS-20 tapes?

### Hypothesis 5: Bootstrap Code Issue

**Theory**: KS10 bootstrap has bug or limitation at PC 000100

**Evidence**:
- Halt at very low memory address (100 octal = 64 decimal)
- Likely in initial bootstrap loader
- Stop code 7 is "unknown" = unhandled condition

**Implications**:
- This might be a known SIMH KS10 bug
- May need patch or workaround
- Could be why pre-built images are rare

---

## Diagnostic Commands Attempted

### Configuration Check
```text
sim> show tua0
TUA0, UNIT=0, attached to /machines/pdp10/tops20_v41.tap, read only, SIMH format, 2048B records
```

### Device Status
```text
sim> show rpa0
RPA0, UNIT=0, RP06, attached to /machines/data/tops20.dsk
```

### CPU Status
```text
sim> show cpu
(output not captured in logs)
```

---

## What We've Tried

1. ✅ **Direct TTY Console** - Works (solved previous issue)
2. ✅ **Interactive Boot** - Works (can issue boot command)
3. ✅ **Tape Attachment** - Works (tape recognized)
4. ✅ **Disk Attachment** - Works (disk attached)
5. ❌ **boot tua0** - Fails with stop code 7
6. ❌ **Alternative Commands** - `/L`, `/G143` fail (wrong prompt level)

---

## Questions for Research LLM

1. **What is SIMH KS10 stop code 7?**
   - What halt condition does it represent?
   - Is it documented anywhere?
   - Known bugs or issues?

2. **TU vs TUA device naming?**
   - What's the difference?
   - Does boot behavior differ?
   - Should we use `boot tu` instead of `boot tua0`?

3. **CPU TOPS-20 mode on KS10?**
   - Is `set cpu tops-20` required for KS10?
   - Why does our build reject this command?
   - Alternative way to set CPU mode?

4. **Is this tape compatible with KS10?**
   - Is bb-d867e-bm_tops20_v41 for KL10 only?
   - Are there KS10-specific TOPS-20 tapes?
   - Different tape format needed?

5. **SIMH version issues?**
   - Is V4.0-0 commit 627e6a6b known to have boot issues?
   - Better SIMH version for KS10 TOPS-20?
   - Need to build from different source?

6. **Working KS10 TOPS-20 examples?**
   - Has anyone successfully booted TOPS-20 V4.1 on SIMH KS10?
   - What configuration did they use?
   - Are there alternative approaches?

7. **Bootstrap debugging?**
   - How to debug halt at PC 000100?
   - SIMH debugging commands to trace boot?
   - Can we see what instruction caused the halt?

8. **Alternative: Should we use KL10 instead?**
   - Would KLH10 emulator work better?
   - Is KL10 better supported for TOPS-20?
   - What's the path to switch emulators?

---

## Relevant Files

### On AWS Instance

**Logs**:
- `/home/ubuntu/tops20-install-live.log` - Installation attempt log
- Container logs: `docker logs pdp10-install`

**Configuration**:
- `/machines/pdp10/install.ini` - SIMH config (in Docker volume)
- `/machines/pdp10/tops20_v41.tap` - Installation tape (in volume)
- `/machines/data/tops20.dsk` - Target disk (in volume, empty)

**Container**:
- Name: `pdp10-install`
- Status: Running (waiting at sim> prompt)
- Image: `brfidgithubio-pdp10`

### In Repository

**Documentation**:
- `arpanet/TOPS20-INSTALLATION-PROBLEM.md` - Previous issue (telnet timing)
- `arpanet/TOPS20-SOLUTION.md` - Solution for console access
- `arpanet/TOPS20-INSTALLATION-GUIDE.md` - Full installation guide
- `arpanet/Dockerfile.pdp10` - Container build

**Scripts**:
- `arpanet/scripts/tops20-interactive-install.exp` - Automated install script
- `arpanet/scripts/start-interactive-install.sh` - Manual install launcher

---

## Container Status (Current)

```bash
# Container is RUNNING and accessible
docker ps | grep pdp10-install
# 539500bd2483   Up 53 minutes

# Can connect to SIMH prompt
docker attach pdp10-install
# Will see: sim>

# Can try commands manually
sim> show version
sim> show tua0
sim> show cpu
sim> boot tu     # Try alternate boot command
```

---

## Next Steps Options

### Option A: Debug Boot Failure (Research Needed)

**Tasks**:
1. Research SIMH KS10 stop code 7
2. Try alternative boot commands (`boot tu` vs `boot tua0`)
3. Test different SIMH builds/versions
4. Enable SIMH debugging to trace boot failure
5. Try different tape images or formats

**Commands to Try**:
```
sim> set cpu history=100
sim> boot tua0
sim> show history
```

```
sim> set debug -n pdp10.debug
sim> set cpu debug=trace
sim> boot tua0
sim> (exit and examine pdp10.debug file)
```

### Option B: Use KL10 Emulator Instead

**Rationale**:
- Gunkies recipe is for KL10
- KL10 may have better TOPS-20 support
- Panda distribution has pre-built KL10 images

**Tasks**:
1. Use KLH10 emulator instead of SIMH KS10
2. Or build SIMH KL10 target
3. Adapt Docker container for different emulator
4. May solve boot issue entirely

### Option C: Try TOPS-10 Instead

**Rationale**:
- TOPS-10 has pre-built images available
- Might boot successfully where TOPS-20 fails
- Still provides PDP-10 OS with networking

**Source**: https://steubentech.com/~talon/pdp10/

### Option D: Simplify Phase 3 (Bypass Full OS)

**Rationale**:
- Focus on validating ARPANET routing
- Don't need full OS for proof-of-concept
- Complete Phase 3, enhance later

---

## References

**Working Recipes**:
- [Gunkies - Running TOPS-20 V4.1 under SIMH](https://gunkies.org/wiki/Running_TOPS-20_V4.1_under_SIMH)
- [Supnik's alt.sys.pdp10 Post](https://groups.google.com/g/alt.sys.pdp10/c/og-_kNunWHo)

**SIMH Documentation**:
- [PDP-10 Simulator User's Guide](https://simh.trailing-edge.com/pdf/pdp10_doc.pdf)
- [SIMH V4 Documentation](https://tangentsoft.com/pidp8i/uv/doc/simh/main.pdf)

**Tape Source**:
- [PDP-10 Archive](http://pdp-10.trailing-edge.com/)
- [Bitsavers TOPS-20](http://www.bitsavers.org/bits/DEC/pdp10/TOPS20/)

**Community**:
- [SIMH GitHub Issues](https://github.com/simh/simh/issues)
- [alt.sys.pdp10 Google Group](https://groups.google.com/g/alt.sys.pdp10)

---

## Success Criteria for Solution

A working solution should:

1. ✅ Boot the TOPS-20 installation tape without errors
2. ✅ Reach the `MTBOOT>` prompt
3. ✅ Allow `/L` and `/G143` commands to work
4. ✅ Complete disk formatting
5. ✅ Restore files from tape via DUMPER
6. ✅ Boot installed system from disk

---

## Time Invested

- **Telnet Console Issue**: 6 hours (solved)
- **Tape Boot Issue**: 1 hour (ongoing)
- **Total**: 7 hours
- **Status**: Need expert/community help

---

**Document Version**: 1.0
**Last Updated**: 2026-02-08 23:45 UTC
**Container Status**: Running, waiting at sim> prompt
**Ready For**: Research LLM analysis and troubleshooting

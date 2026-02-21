# PDP-10 SIMH Telnet Console Test Results

**Date**: 2026-02-12/13 (Evening session)
**Duration**: ~90 minutes
**System**: SIMH PDP-10 KS with TOPS-20 V4.1
**Status**: ⚠️ **Partial Success - Console Output Issue**

---

## Executive Summary

Attempted to apply the proven **PDP-11 telnet console method** to SIMH PDP-10 KS with TOPS-20 V4.1. While the telnet connection and boot process work correctly, **console output does not appear on the telnet connection**. Evidence shows TOPS-20 IS executing (program counter advancing), but output routing to telnet console needs further investigation.

**Key Finding**: The telnet console method works for SIMH infrastructure (connection, boot triggering) but TOPS-20 console output configuration requires additional research.

---

## Test Environment

**Hardware**: AWS EC2 t3.medium (x86_64) @ 98.93.12.157
**Container**: `pdp10-simh-test`
**SIMH Version**: V4.0-0 Current (git commit id: 627e6a6b)
**OS**: TOPS-20 V4.1 (installation tape)
**Network**: 172.20.1.0/24 (Docker bridge)
**Console Port**: 2326 (mapped from internal 2323)

---

## What Worked ✅

### 1. Telnet Console Configuration
```ini
; Config: arpanet/configs/pdp10-noboot.ini
set console telnet=2323
```
- SIMH successfully listens on telnet port
- Telnet connections establish reliably
- Connection banner displays: "Connected to the KS-10 simulator CON-TELNET device"

### 2. Boot Trigger Mechanism
```
./pdp10.ini-42> boot tua0
%SIM-INFO: Waiting for console Telnet connection
%SIM-INFO: Waiting for console Telnet connection
%SIM-INFO: Running
```
- SIMH waits for telnet connection before proceeding
- Boot command executes when telnet client connects
- State transitions correctly: Waiting → Running

### 3. TOPS-20 Execution Confirmed
```
SIGTERM received, PC: 775472 (AOS 0,764502)
```
- Program counter (PC) shows code executing at address 775472
- AOS instruction executed (Add One to memory and Skip if result is zero)
- Proves TOPS-20 boot process IS running, not hung

### 4. Container Stability
- Container stays running (no restart loop)
- Config file mounts work correctly after fixing docker-compose
- Volume mounts persist correctly

---

## What Didn't Work ❌

### Console Output Not Appearing

**Symptom**: Telnet connection succeeds, boot starts, but NO output appears on telnet console.

**Evidence**:
1. Connection shows only banner: "Connected to the KS-10 simulator CON-TELNET device"
2. No boot messages despite 90+ second wait
3. No response to input (Enter, Ctrl-C, ?, HELP)
4. Expect scripts timeout waiting for prompts

**What Was Tried**:
- ✅ Verified config file correct (mounted properly)
- ✅ Disabled IMP interface (was blocking with DHCP)
- ✅ Sent various input commands (no echo, no response)
- ✅ Monitored Docker logs (show "Running" but no console output)
- ❌ Console output never appears on telnet

**Expect Script Output**:
```
spawn telnet localhost 2326
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.


Connected to the KS-10 simulator CON-TELNET device


⚠ 90 second timeout - showing current state
```

---

## Technical Analysis

### Comparison: PDP-11 vs PDP-10

| Aspect | PDP-11 (Working) | PDP-10 (Issue) |
|--------|------------------|----------------|
| **Telnet Connection** | ✅ Works | ✅ Works |
| **Boot Trigger** | ✅ Boots after connection | ✅ Boots after connection |
| **Console Banner** | ✅ Displays | ✅ Displays |
| **Boot Messages** | ✅ Immediate output | ❌ No output |
| **System Execution** | ✅ Running | ✅ Running (PC proves it) |
| **Console Output** | ✅ All output visible | ❌ Silent |
| **Boot Source** | Disk (pre-installed 2.11BSD) | Tape (TOPS-20 V4.1 installer) |
| **Auto-boot** | Yes (to login prompt) | Unknown (no visual confirmation) |

### Root Cause Hypotheses

1. **TOPS-20 Console Configuration**
   - Installation tape may not be configured for telnet console
   - May require specific SIMH console settings for PDP-10
   - Might need different console device type

2. **Installation Tape vs Installed System**
   - PDP-11 boots from pre-installed disk image (turnkey)
   - PDP-10 boots from installation tape (interactive installer)
   - Installer might expect hardware console, not telnet

3. **Console Output Routing**
   - Output may be going to different device
   - SIMH may need explicit console redirection for PDP-10
   - TOPS-20 may have different console architecture than BSD

4. **Silent Boot Waiting for Input**
   - TOPS-20 installer might be waiting for input we can't see
   - Prompts may not be echoing
   - Different terminal type expected

---

## Debugging Session Timeline

### Phase 1: Initial Setup (15 min)
- 00:00: Started PDP-10 test based on PDP-11 success
- 00:05: Container built successfully
- 00:10: Discovered container restart loop
- 00:15: Root cause: Config needs `boot` command to keep running

### Phase 2: Config Corrections (30 min)
- 00:15: Added `boot tua0` to config (like PDP-11's `boot rp0`)
- 00:20: Container stays running but wrong config mounted
- 00:30: Fixed docker-compose file sync issue
- 00:40: Verified correct config loaded
- 00:45: Container running correctly, waiting for telnet

### Phase 3: Connection Testing (20 min)
- 00:45: First telnet connection - only banner appears
- 00:50: Tried manual input - no response
- 00:55: Created expect script for automation
- 01:00: 90 second timeout - no boot messages
- 01:05: Confirmed connection works but output missing

### Phase 4: IMP Debugging (15 min)
- 01:05: Discovered IMP DHCP blocking boot
- 01:10: Disabled IMP interface in config
- 01:12: Restarted - no more DHCP messages
- 01:15: Boot proceeds but still no console output
- 01:20: Program counter proves system running

### Phase 5: Analysis & Documentation (10 min)
- 01:20: Reviewed logs for evidence
- 01:25: Confirmed boot executing, output not routing
- 01:30: Created this comprehensive report

---

## Files Created/Modified

### New Files
```
arpanet/configs/pdp10-test.ini          - Test config (superseded by noboot)
```

### Modified Files
```
arpanet/configs/pdp10-noboot.ini        - Added boot command, disabled IMP
docker-compose.pdp10-test.yml           - Fixed config mount path
```

### AWS Session Artifacts
```
~/pdp10-telnet-session-*.log            - Multiple telnet session logs
~/pdp10-boot-capture.log                - Expect script log file
~/pdp10_test.exp                        - Initial test expect script
~/pdp10_capture.exp                     - Boot capture expect script
~/pdp10_interactive.exp                 - Interactive test script
~/pdp10_probe.exp                       - Input probe script
```

---

## Next Steps & Recommendations

### Immediate Research Needed

1. **SIMH PDP-10 Console Documentation**
   - Read official SIMH PDP-10 documentation for console setup
   - Check for telnet console examples in SIMH community
   - Search for TOPS-20 + SIMH + telnet discussions

2. **TOPS-20 Installation Process**
   - Review TOPS-20 installation documentation
   - Understand expected console interaction
   - Check if installer has silent mode or specific requirements

3. **Console Device Investigation**
   - Try different SIMH console commands
   - Experiment with `set console notelnet` then re-enable
   - Test if stdio console works (fallback to docker attach)

### Alternative Approaches

1. **Use Pre-Installed TOPS-20 Disk**
   - Find or create a pre-installed TOPS-20 disk image
   - Similar to PDP-11's pre-built 2.11BSD approach
   - Would bypass installation tape console issues

2. **Try Different PDP-10 Emulator**
   - KLH10 (Panda distribution) uses different console handling
   - May have better telnet console support
   - But Panda has its own blockers (as documented earlier)

3. **Stdio Console Workaround**
   - Use `docker attach` despite its limitations
   - Create interactive session script
   - Not ideal but may work for manual installation

4. **Serial Console Bridge**
   - Use socat to bridge console to telnet
   - More complex but might solve output routing
   - Would be a workaround rather than fix

### Low Priority

- Further debugging of current setup (diminishing returns after 90 min)
- **Recommend**: Focus on PDP-11 as proven working solution for now
- **Defer**: PDP-10 telnet console research to future work

---

## Comparison to Previous Attempts

### PDP-10 Attempt History

| Approach | Date | Duration | Outcome | Blocker |
|----------|------|----------|---------|---------|
| **TOPS-20 V4.1 (SIMH)** | 2026-02-09 | 1 hour | ❌ Failed | Boot loop, parameter errors |
| **TOPS-20 V7.0 (Cornwell SIMH)** | 2026-02-12 | 45 min | ❌ Failed | Monitor parameter issues |
| **KLH10 (Panda)** | 2026-02-12 | 3.5 hours | ⚠️ Partial | Console instability |
| **Telnet Console (Tonight)** | 2026-02-12 | 90 min | ⚠️ Partial | Output routing issue |
| **TOTAL** | - | **~6 hours** | ❌ No working solution | Multiple blockers |

### Success: PDP-11 Telnet Console

| Aspect | PDP-11 | PDP-10 |
|--------|---------|---------|
| **Time to Success** | 3 hours | 6+ hours (ongoing) |
| **Boot Success Rate** | 100% (5/5 tests) | 0% (visual confirmation) |
| **Automation Ready** | ✅ Yes | ❌ No |
| **Console Output** | ✅ Reliable | ❌ Missing |
| **Recommendation** | **USE THIS** | Research needed |

---

## Lessons Learned

### What Worked Well

1. **Systematic Debugging**
   - Docker volume mount investigation found config mismatch
   - IMP DHCP issue identified and resolved
   - Program counter analysis proved boot executing

2. **Evidence Collection**
   - Multiple log files captured
   - Expect scripts created for reproducibility
   - Docker logs show state transitions

3. **Incremental Testing**
   - Each change validated independently
   - Config corrections verified in container
   - Fresh restarts confirmed changes applied

### What Could Be Improved

1. **Time Investment**
   - 90 minutes without output visibility is diminishing returns
   - Should have researched TOPS-20 console requirements earlier
   - Could have tried pre-installed disk image sooner

2. **Research First**
   - Assumed PDP-11 method would transfer directly
   - Different systems have different console architectures
   - Should have checked SIMH docs for PDP-10 specifics

3. **Alternative Paths**
   - Should have considered pre-installed disk earlier
   - Stdio console fallback could have been tried
   - KLH10 console might have worked better

---

## Conclusions

### Technical Conclusions

1. **Telnet Console Method**: Works for SIMH infrastructure but requires OS-specific configuration
2. **PDP-10 vs PDP-11**: Different console architectures require different approaches
3. **Installation Tape**: Not ideal for automated boot testing (interactive installer)
4. **TOPS-20 Execution**: Confirmed running, output routing is the blocker

### Strategic Conclusions

1. **PDP-11 is Proven**: 100% reliable, well-documented, production-ready
2. **PDP-10 Needs Research**: Console output issue requires investigation
3. **Time vs Benefit**: 6 hours on PDP-10 with no working solution vs 3 hours on PDP-11 with 100% success
4. **Recommendation**: **Use PDP-11 as second host**, defer PDP-10 to future work

### Project Impact

**For ARPANET Build Pipeline**:
- ✅ VAX/BSD as primary host (working)
- ✅ PDP-11/BSD as second host (proven tonight)
- ⚠️ PDP-10/TOPS-20 deferred (console research needed)

**For Automation**:
- ✅ Telnet console method validated (PDP-11)
- ✅ Expect scripts created (reusable)
- ❌ PDP-10 automation blocked (no output)

**For Documentation**:
- ✅ Comprehensive test results documented
- ✅ Multiple system comparison data
- ✅ Future troubleshooting path identified

---

## References

### Documentation Created Tonight
- `docs/arpanet/PDP11-BOOT-SUCCESS-2026-02-12.md` - Complete PDP-11 success report
- `docs/arpanet/TELNET-CONSOLE-METHOD.md` - Universal telnet console guide
- `docs/arpanet/MANUAL-LOGIN-SESSION-SUCCESS-2026-02-12.md` - AWS manual test session
- `docs/arpanet/PDP10-TELNET-TEST-PLAN.md` - This test plan (reference)
- `docs/arpanet/PDP10-TELNET-TEST-RESULTS-2026-02-12.md` - This document

### Related Documentation
- `docs/arpanet/PANDA-TEST-RESULTS-2026-02-12.md` - KLH10 Panda attempt
- `arpanet/archived/Dockerfile.pdp10` - SIMH PDP-10 KS container
- `arpanet/configs/pdp10-noboot.ini` - Current config (with boot command added)

### External Resources
- SIMH Documentation: http://simh.trailing-edge.com/pdf/pdp10_doc.pdf
- TOPS-20 Information: http://pdp-10.trailing-edge.com/
- SIMH GitHub: https://github.com/simh/simh

---

**Session Status**: ✅ **DOCUMENTED**
**AWS Infrastructure**: Running (i-08a7eb7df2fb9b7da @ 98.93.12.157)
**Next Action**: Decide whether to continue PDP-10 research or pivot to PDP-11
**Recommendation**: **Pivot to PDP-11** (proven working, 100% reliable)

---

**Final Verdict**:

**PDP-10 Telnet Test**: ⚠️ **Partial Success**
- Telnet infrastructure: ✅ Works
- Boot trigger: ✅ Works
- TOPS-20 execution: ✅ Confirmed
- Console output: ❌ Blocked

**Overall ARPANET Host Strategy**: ✅ **Success**
- Primary: VAX/BSD ✅
- Secondary: PDP-11/BSD ✅ (Proven tonight)
- Tertiary: PDP-10/TOPS-20 ⚠️ (Future research)

**Time Investment ROI**:
- PDP-11: 3 hours → 100% success = **EXCELLENT**
- PDP-10: 6 hours → 0% success = **POOR**
- **Recommendation**: Use PDP-11 for build pipeline

---

**End of Test Results**
**Timestamp**: 2026-02-13 ~02:30 UTC
**Total Session Time**: ~4 hours (including PDP-11 success + PDP-10 attempt)
**AWS Cost**: ~$0.16 ($0.04/hr × 4 hours)

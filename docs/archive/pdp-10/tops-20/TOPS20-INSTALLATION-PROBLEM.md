# TOPS-20 Installation Problem - Technical Handoff

**Date**: 2026-02-08
**Status**: Blocked - Console Timing Issue
**Time Invested**: ~6 hours
**Priority**: Blocking Phase 3 completion

---

## Problem Statement

**Goal**: Install TOPS-20 V4.1 operating system on PDP-10 KS10 emulator (SIMH) running in Docker container to complete ARPANET Phase 3 build pipeline integration.

**Current State**: Cannot interact with SIMH console to execute installation commands. System boots but we cannot reach the MTBOOT boot loader prompt to proceed with installation.

**Impact**: Blocks FTP file transfer testing and build pipeline integration (Phase 3 tasks).

---

## Environment Details

### Infrastructure
- **Platform**: AWS EC2 t3.medium (x86_64)
- **OS**: Ubuntu (via Docker)
- **IP**: 34.227.223.186
- **Container**: arpanet-pdp10
- **Emulator**: SIMH PDP-10 KS-10 simulator V4.0-0 (git commit 627e6a6b)

### Container Setup
```yaml
Container: arpanet-pdp10
Image: brfidgithubio-pdp10
Network: arpanet-build (172.20.0.40)
Ports: 2326:2323/tcp (telnet console)
       2000/udp (ARPANET IMP interface)
Volumes:
  - arpanet-pdp10-data:/machines/data (disk storage)
  - arpanet-pdp10-config:/machines/pdp10 (config files)
```

### SIMH Configuration (`/machines/pdp10.ini`)
```ini
set debug stdout
set console wru=034
set dz disabled
set lp20 disabled

# Tape drive with TOPS-20 installation tape
set tua enable
set tua0 locked
attach tua0 /machines/pdp10/tops20_v41.tap

# Disk drive (RP06)
set rpa enable
set rpa0 rp06
attach rpa0 /machines/data/tops20.dsk

# IMP Network Interface
set imp enabled
set imp debug
attach -u imp 2000:172.20.0.30:2000

# Telnet console
set console telnet=2323

# Auto-boot from tape
boot tua0
```

### Files Available
- **TOPS-20 tape**: `/machines/pdp10/tops20_v41.tap` (21MB, verified present)
- **Disk file**: `/machines/data/tops20.dsk` (0 bytes - empty, ready for installation)
- **Source**: http://pdp-10.trailing-edge.com/tapes/bb-d867e-bm_tops20_v41_2020_instl.tap.bz2

---

## The Core Problem

### Symptom
When connecting to PDP-10 console via telnet (port 2326), we see:
```
Connected to localhost.
Escape character is '^]'.

Connected to the KS-10 simulator CON-TELNET device

[no prompt appears]
```

Expected behavior: Should see either `sim>` (SIMH command prompt) or `MTBOOT>` (boot loader prompt).

### Root Cause Analysis

**Timing Race Condition:**

1. **Container starts** → SIMH loads `/machines/pdp10.ini`
2. **Config executes** → Reaches `boot tua0` command at line 48
3. **Boot command runs** → SIMH initiates boot from tape
4. **SIMH waits** → Expects telnet connection on port 2323 (mapped to host 2326)
5. **Timeout period** → ~30-45 seconds based on logs
6. **If no connection** → Displays error and drops to `sim>` prompt
7. **Container behavior** → Appears to restart/reload config (infinite loop)

**Log Evidence:**
```
./pdp10.ini-48> boot tua0
%SIM-INFO: Waiting for console Telnet connection
%SIM-INFO: Waiting for console Telnet connection
%SIM-INFO: Waiting for console Telnet connection
%SIM-ERROR: sim_check_console () returned: Console Telnet connection timed out - errno: 11 - Resource temporarily unavailable
sim>
[config reloads and repeats]
```

**When We Connect:**
```
./pdp10.ini-48> boot tua0
%SIM-INFO: Waiting for console Telnet connection
%SIM-INFO: Waiting for console Telnet connection
%SIM-INFO: Waiting for console Telnet connection
%SIM-INFO: Running
```

The "Running" status indicates boot command executed, but we get no console output or prompt when we telnet in.

### Secondary Issues Discovered

1. **"All connections busy"**: If any previous connection didn't close cleanly, subsequent connections are rejected
2. **Buffer timing**: Boot output may be sent before telnet client connects, causing missed prompts
3. **No echo/prompt**: After connection, sending commands gets no response or echo
4. **Zombie processes**: Defunct telnet/expect processes from failed attempts hold connections

---

## Approaches Tried

### Approach 1: Automated Expect Script - Auto-boot
**File**: `arpanet/scripts/tops20-auto-install.exp`

**Strategy**: Connect via expect, wait for MTBOOT prompt, automate entire installation.

**Implementation**:
```tcl
spawn telnet localhost 2326
expect "MTBOOT>"
send "/L\r"
# ... full installation sequence
```

**Result**: ❌ Failed
- Script connects successfully
- Sees "Connected to the KS-10 simulator CON-TELNET device"
- Times out waiting for MTBOOT prompt (never appears)
- Script waits indefinitely or times out after 60-120 seconds

**Duration**: 2 hours development + testing

---

### Approach 2: Modified Config - Manual Boot
**File**: `arpanet/configs/pdp10-noboot.ini`

**Strategy**: Remove `boot tua0` from config, connect to `sim>` prompt, manually send boot command.

**Implementation**:
```ini
# Removed: boot tua0
# Config ends at console setup
set console telnet=2323
echo Ready for manual boot. Connect via telnet and type: boot tua0
```

**Execution**:
```bash
docker run -d --name pdp10-install \
  -v config:/machines/pdp10/pdp10-noboot.ini \
  brfidgithubio-pdp10 /usr/local/bin/pdp10-ks /machines/pdp10/pdp10-noboot.ini
```

**Result**: ❌ Failed
- Volume mount path issues (`Can't open file /machines/pdp10/pdp10-noboot.ini`)
- Config file not found at expected location in container
- Time spent debugging Docker volume mounts (1 hour)

**Duration**: 1.5 hours

---

### Approach 3: Manual Boot Expect Script
**File**: `arpanet/scripts/tops20-manual-install.exp`

**Strategy**: Expect script designed to connect to `sim>` prompt and manually send boot command.

**Implementation**:
```tcl
spawn telnet localhost 2326
expect "sim>"
send "boot tua0\r"
expect "MTBOOT>"
# Continue installation...
```

**Result**: ❌ Failed
- Never saw `sim>` prompt
- System appeared to be in boot loop when connecting
- Got "All connections busy" from held connections

**Duration**: 1 hour

---

### Approach 4: Python Telnet Direct Interaction
**Strategy**: Use Python telnetlib for more control over connection timing and reading.

**Implementation**:
```python
import telnetlib
tn = telnetlib.Telnet("localhost", 2326, timeout=5)
output = tn.read_very_eager()  # Read immediately
tn.write(b"\r\n")               # Send commands
```

**Results**: ❌ Failed
- Successfully connects
- Sees "Connected to the KS-10 simulator CON-TELNET device"
- `read_very_eager()` returns empty or only the banner
- No prompt appears
- Subsequent attempts: "All connections busy"

**Duration**: 30 minutes

---

### Approach 5: Process Cleanup + Fresh Restart
**Strategy**: Kill all telnet/expect processes, restart container, connect immediately.

**Implementation**:
```bash
pkill -9 telnet
pkill -9 expect
docker compose restart pdp10
sleep 20
# Connect with expect script
```

**Result**: ❌ Partial Success
- Cleaned up zombie processes successfully
- Fresh connection established
- Still no prompt or console interaction
- Same behavior: "Connected to device" then nothing

**Duration**: 30 minutes

---

### Approach 6: Connection Timing Variations
**Strategy**: Try connecting at different points in boot cycle.

**Variations Tried**:
1. Connect immediately after container start (5 seconds)
2. Connect after delay (10, 15, 20, 30 seconds)
3. Connect, wait, then send commands
4. Connect and immediately send boot command

**Result**: ❌ Failed
- No timing variation produced different result
- Always same behavior: connection succeeds, no prompt

**Duration**: 1 hour

---

### Approach 7: Pre-built Disk Image Search
**Strategy**: Find existing TOPS-20 disk image to bypass installation.

**Resources Checked**:
- Steuben Technologies (has TOPS-10, not TOPS-20)
- http://panda.trailing-edge.com (PANDA distribution - no direct download)
- Computer History Wiki
- Bitsavers.org
- GitHub PDP-10 repos

**Result**: ❌ Not Found
- TOPS-10 pre-built images exist
- TOPS-20 pre-built disk images are rare/unavailable
- PANDA distribution mentions pre-built filesystem but requires manual installation
- Most documentation assumes installation from tape

**Duration**: 45 minutes

---

## What We Know Works

### ✅ Successful Elements

1. **Container Build**: PDP-10 container builds successfully
   ```bash
   docker compose -f docker-compose.arpanet.phase2.yml build pdp10
   # ✅ Completes without errors
   ```

2. **Container Runtime**: Container starts and runs without crashes
   ```bash
   docker ps | grep pdp10
   # arpanet-pdp10 Up 19 hours
   ```

3. **TOPS-20 Tape**: Installation tape is present and valid
   ```bash
   docker exec arpanet-pdp10 ls -lh /machines/pdp10/tops20_v41.tap
   # -rw-r--r-- 1 root root 21M
   docker logs arpanet-pdp10 | grep "TUA0"
   # %SIM-INFO: TUA0: Tape Image '/machines/pdp10/tops20_v41.tap' scanned as SIMH format
   ```

4. **Telnet Port**: Console port is accessible and accepting connections
   ```bash
   telnet localhost 2326
   # Trying 127.0.0.1...
   # Connected to localhost.
   ```

5. **SIMH Config**: Configuration loads without syntax errors
   ```
   # All config lines execute successfully in logs
   # No SIMH configuration errors reported
   ```

6. **Boot Command Execution**: SIMH executes boot command
   ```
   ./pdp10.ini-48> boot tua0
   %SIM-INFO: Running
   ```

7. **Other ARPANET Containers**: VAX, IMP1, IMP2 all functional
   ```bash
   docker compose ps
   # All 4 containers "Up" status
   ```

### ❌ What Doesn't Work

1. **Console Interaction**: Cannot see or interact with SIMH console
2. **MTBOOT Prompt**: Boot loader prompt never appears
3. **sim> Prompt**: SIMH command prompt not accessible after timeout
4. **Command Echo**: Typed commands produce no visible response
5. **Boot Output**: No visible output from boot process

---

## Diagnostic Commands

### Check Container Status
```bash
ssh ubuntu@34.227.223.186
cd ~/brfid.github.io
docker compose -f docker-compose.arpanet.phase2.yml ps
```

### View SIMH Logs
```bash
docker logs arpanet-pdp10 2>&1 | tail -50
docker logs arpanet-pdp10 2>&1 | grep "boot tua0"
docker logs arpanet-pdp10 2>&1 | grep "MTBOOT"
```

### Test Console Connection
```bash
telnet localhost 2326
# OR
python3 << 'EOF'
import telnetlib
tn = telnetlib.Telnet("localhost", 2326, timeout=5)
print(tn.read_very_eager().decode())
tn.close()
EOF
```

### Check for Stuck Connections
```bash
ps aux | grep -E 'telnet|expect'
ss -tnp | grep 2326
netstat -tnp | grep 2326
```

### Clean Restart
```bash
pkill -9 telnet; pkill -9 expect
docker compose -f docker-compose.arpanet.phase2.yml restart pdp10
sleep 15
# Then try connecting
```

---

## Resources Created

### Documentation
1. **TOPS20-INSTALLATION-GUIDE.md** (450+ lines)
   - Complete step-by-step installation procedure
   - Formatter questions and answers
   - Post-installation configuration
   - Troubleshooting section
   - Quick reference commands

2. **TOPS20-QUICKSTART.md** (200+ lines)
   - 5-minute getting started guide
   - TL;DR command sequences
   - Condensed installation steps

3. **This file** (TOPS20-INSTALLATION-PROBLEM.md)
   - Technical handoff document

### Scripts
1. **tops20-install-helper.sh** (interactive utility)
   - Pre-flight checks
   - Container status monitoring
   - One-click console connection
   - Installation logging
   - Backup utilities

2. **tops20-auto-install.exp** (automated installation)
   - Full installation sequence
   - DUMPER file restoration
   - User account creation
   - Bootstrap writing

3. **tops20-manual-install.exp** (manual boot version)
   - Connects to sim> prompt
   - Manually sends boot command
   - Proceeds with installation

4. **tops20-final-attempt.exp** (last attempt)
   - Simplified connection logic
   - Better error handling
   - Diagnostic output

### Configuration Files
1. **pdp10-noboot.ini** (manual boot config)
   - SIMH config without auto-boot
   - Stops at sim> prompt

---

## Theories & Hypotheses

### Theory 1: SIMH Telnet Console Buffering
**Hypothesis**: SIMH sends boot output before telnet client is ready to receive, causing output to be lost/buffered.

**Evidence**:
- "Running" status suggests boot executed
- No output visible when connecting
- Other SIMH simulators (VAX) work fine with telnet

**Potential Solutions**:
- Use different console mode (serial instead of telnet)
- Modify SIMH source to add delays
- Use `set console notelnet` if available

---

### Theory 2: PDP-10 Specific Console Behavior
**Hypothesis**: PDP-10 SIMH has different console handling than VAX SIMH.

**Evidence**:
- VAX container telnet works perfectly (arpanet-vax on port 2323)
- IMP containers (H316) telnet works fine
- Only PDP-10 exhibits this behavior

**Potential Solutions**:
- Research PDP-10 specific console configuration
- Check if PDP-10 requires different `set console` options
- Compare with working PiDP-10 configurations

---

### Theory 3: Boot Timeout Too Short
**Hypothesis**: Boot timeout is shorter than our connection delay, causing system to drop to sim> before we connect.

**Evidence**:
- Logs show 3 "Waiting for console" messages before timeout
- Error: "Console Telnet connection timed out"
- Config then reloads and repeats

**Potential Solutions**:
- Increase SIMH console timeout (if configurable)
- Remove boot command from config entirely
- Use `set console timeout=<value>` if available

---

### Theory 4: Docker Port Mapping Issues
**Hypothesis**: Port mapping (2326:2323) causes connection state issues.

**Evidence**:
- Direct connection to container port 2323 might work differently
- Docker NAT could affect console protocol

**Potential Solutions**:
- Connect directly to container IP:2323
- Use `docker exec` with `telnet 127.0.0.1 2323` inside container
- Use SIMH serial console instead of telnet

---

### Theory 5: SIMH Console Mode Incompatibility
**Hypothesis**: SIMH telnet console mode isn't compatible with automated tools or has special requirements.

**Evidence**:
- Manual connection should work but doesn't
- "Connected to device" message is from SIMH
- No subsequent output appears

**Potential Solutions**:
- Check SIMH documentation for console requirements
- Try `set console log=file.txt` to capture output separately
- Use `attach console` instead of `set console telnet`

---

## Alternative Approaches to Consider

### Option A: SIMH Serial Console
```ini
# Instead of telnet console:
set console log=console.log
set console notelnet
# Then use docker exec to read console.log
```

### Option B: Docker Attach
```bash
# Modify Dockerfile CMD to interactive mode
docker run -it pdp10-image /usr/local/bin/pdp10-ks
# Direct terminal access, no telnet
```

### Option C: Expect with docker exec
```bash
# Run expect inside the container
docker exec -it arpanet-pdp10 expect << 'EOF'
spawn /usr/local/bin/pdp10-ks /machines/pdp10.ini
expect "sim>"
send "boot tua0\r"
# ...
EOF
```

### Option D: Pre-install on Host, Copy Disk
```bash
# Install TOPS-20 on local machine with working SIMH
# Copy resulting .dsk file to container volume
# Container boots from pre-installed disk
```

### Option E: Use Different PDP-10 Distribution
- Try PANDA TOPS-20 (7.0) instead of 4.1
- Try ITS (Incompatible Timesharing System) instead
- Try TOPS-10 (different OS, but functional)

### Option F: Simplify Phase 3 Requirements
- Skip full TOPS-20 installation
- Use simple echo/test service on PDP-10
- Validate routing without full OS
- Add TOPS-20 as Phase 3.5 enhancement later

---

## Questions for Problem-Solving LLM

1. **SIMH Console**: What is the correct way to interact with SIMH PDP-10 telnet console when boot command is in config file?

2. **Timing**: How can we synchronize telnet connection with SIMH boot process to capture output?

3. **Alternative Consoles**: Can SIMH PDP-10 use serial console or other console modes instead of telnet?

4. **Docker Integration**: Is there a better way to expose SIMH console in Docker than telnet port mapping?

5. **Pre-built Alternatives**: Are there any working TOPS-20 disk images available that we missed?

6. **Boot Process**: What exactly happens during `boot tua0` on PDP-10, and why doesn't MTBOOT appear?

7. **Configuration**: Are there SIMH configuration options we're missing (console timeout, buffer settings, etc.)?

8. **Comparison**: How do working PiDP-10 or other PDP-10 SIMH setups handle console interaction?

---

## Success Criteria

Installation is considered successful when:

1. ✅ Can connect to PDP-10 console via telnet/other method
2. ✅ Can see MTBOOT boot loader prompt
3. ✅ Can send commands and see responses
4. ✅ Can complete disk formatting and file restoration
5. ✅ TOPS-20 boots from disk after installation
6. ✅ Can login to TOPS-20 system
7. ✅ FTP daemon is running and accessible

**Minimum Viable Success**:
- Any working PDP-10 OS (TOPS-20, TOPS-10, or ITS)
- Can boot and login
- Can run FTP or similar file transfer service
- Validates 4-container routing for Phase 3

---

## Related Files

### Key Configuration
- `arpanet/configs/phase2/pdp10.ini` - SIMH configuration (generated)
- `docker-compose.arpanet.phase2.yml` - Container orchestration
- `arpanet/Dockerfile.pdp10` - Container build instructions

### Documentation
- `arpanet/PHASE3-IMPLEMENTATION-PLAN.md` - Overall Phase 3 plan
- `arpanet/PHASE3-PROGRESS.md` - Progress tracking
- `arpanet/PROTOCOL-ANALYSIS.md` - Network analysis
- `CHANGELOG.md` - Project status

### Test Scripts
- `arpanet/scripts/test_phase2.py` - Multi-container routing tests
- `arpanet/scripts/test_utils.py` - Testing utilities

---

## Recommendations

### Immediate (Next 1-2 hours)
1. Try Option C (Expect with docker exec) to bypass telnet
2. Research SIMH PDP-10 console documentation thoroughly
3. Try connecting to container IP directly (not through port mapping)

### Short-term (Next day)
1. If still blocked: Implement Option F (simplify Phase 3)
2. Create minimal test service for PDP-10 without full OS
3. Complete Phase 3 with simplified approach
4. Document TOPS-20 as "future enhancement"

### Long-term (Future)
1. Revisit TOPS-20 installation with fresh perspective
2. Consider reaching out to SIMH/PDP-10 community for help
3. Explore PiDP-10 or commercial solutions
4. Alternative: Contract someone experienced with TOPS-20 installation

---

## Contact & Handoff

**Project Context**: See `CHANGELOG.md`, `MEMORY.md`, and `PHASE3-IMPLEMENTATION-PLAN.md` for full project context.

**AWS Access**: Instance at 34.227.223.186 (SSH key required)

**Git Repository**: https://github.com/brfid/brfid.github.io

**Current State**:
- All code committed and pushed to main branch
- AWS instance still running with containers up
- Task #1 in progress (marked blocked on console timing)

**Next Session Should**:
1. Read this entire document
2. Review SIMH PDP-10 documentation
3. Try alternative console approaches
4. Make go/no-go decision on full TOPS-20 installation

---

## Appendix: Command Reference

### Quick Start Commands
```bash
# SSH to AWS
ssh ubuntu@34.227.223.186

# Check status
cd ~/brfid.github.io
docker compose -f docker-compose.arpanet.phase2.yml ps

# Run pre-flight check
bash arpanet/scripts/tops20-install-helper.sh check

# View logs
docker logs arpanet-pdp10 | tail -50

# Clean restart
docker compose -f docker-compose.arpanet.phase2.yml restart pdp10

# Test connection
telnet localhost 2326
```

### Useful Log Filters
```bash
# Boot attempts
docker logs arpanet-pdp10 2>&1 | grep -A 5 "boot tua0"

# Connection status
docker logs arpanet-pdp10 2>&1 | grep "Waiting for console"

# Errors
docker logs arpanet-pdp10 2>&1 | grep ERROR

# Timeline
docker logs arpanet-pdp10 2>&1 | grep -E "SIM-INFO|boot|Running"
```

---

**Document Version**: 1.0
**Last Updated**: 2026-02-08 22:00 UTC
**Author**: Claude Sonnet 4.5 (session: brfid.github.io TOPS-20 installation)

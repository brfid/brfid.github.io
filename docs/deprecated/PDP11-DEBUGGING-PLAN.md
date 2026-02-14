# PDP-11 Debugging Plan

**Date**: 2026-02-14
**Status**: PDP-11 receiving commands but not executing them
**Goal**: Get PDP-11 actually processing files (decode + validate)

---

## Current Problem

**Symptoms**:
- Console commands sent to PDP-11 (via screen session)
- No output file created: `/mnt/arpanet-logs/builds/<id>/pdp-output/brad.txt` not found
- No PDP-11 logs created: `PDP11.log` missing
- Fallback to VAX + Python rendering instead

**Evidence**:
```
Retrieving validated output from PDP-11...
scp: /mnt/arpanet-logs/builds/build-20260214-121649/pdp-output/brad.txt: No such file or directory
Warning: brad.txt not found, using original
Using VAX original output...
```

**What we know**:
- PDP-11 boots successfully (2.11BSD)
- Console accessible via telnet (port 2327)
- Commands being sent via screen session
- Screen session gets recreated (telnet timeout)
- Commands sent, but no results

**What we don't know**:
- Are commands actually executing on PDP-11?
- Is arpanet-log.sh present on PDP-11?
- Is EFS mounted in PDP-11 container?
- Is brad.1.uu file actually on PDP-11?
- Are there error messages we're not seeing?

---

## Debugging Approach

**Principle**: Interactive work first, automation second.

1. ✅ Log into PDP-11 directly (console)
2. ✅ Verify environment (files, mounts, scripts)
3. ✅ Run commands manually (one at a time)
4. ✅ See what fails and why
5. ✅ Fix issues
6. ✅ Document working procedure
7. ✅ Then automate

---

## Phase 1: Access and Environment Check

### Step 1.1: Start AWS Instances
```bash
# On local machine
./aws-start.sh

# Note the IPs:
# VAX IP: <shown in output>
# PDP-11 IP: <shown in output>
```

### Step 1.2: Access PDP-11 Console Directly
```bash
# From local machine
telnet <pdp11-ip> 2327

# Should see:
# 2.11 BSD UNIX (pdp11) (console)
#
# login:
```

### Step 1.3: Login as Root
```
login: root
Password: <press enter, usually no password>

# Should get shell prompt:
#
```

### Step 1.4: Check Basic Environment
```bash
# Check current directory
pwd
# Expected: /root or /

# Check date/time (for log timestamps)
date
# Should show current UTC time

# Check disk space
df -h
# Look for /mnt/arpanet-logs mount

# Check mounted filesystems
mount
# Should see EFS mounted at /mnt/arpanet-logs
```

**Document findings**: Note if EFS is mounted, what the mount point is

---

## Phase 2: Verify File Transfers

### Step 2.1: Check if Encoded File Exists
```bash
# Check for transferred file
ls -la /tmp/brad.1.uu

# If exists:
# - Note file size
# - Check if readable: cat /tmp/brad.1.uu

# If doesn't exist:
# - File was never transferred
# - Need to investigate console transfer
```

### Step 2.2: Check if arpanet-log.sh Exists
```bash
# Check for logging script
ls -la /tmp/arpanet-log.sh

# If exists:
# - Check if executable: ls -la /tmp/arpanet-log.sh
# - Try running it: echo "test" | /tmp/arpanet-log.sh PDP11 test-$(date +%s)

# If doesn't exist:
# - Script was never transferred
# - Need to transfer it manually
```

### Step 2.3: Check EFS Mount and Build Directories
```bash
# Check EFS mount
ls -la /mnt/arpanet-logs/

# Expected directories:
# vax/
# pdp11/
# shared/
# builds/

# Check builds directory
ls -la /mnt/arpanet-logs/builds/

# Note: Should see recent build directories
```

**Document findings**: Which files/directories exist, which are missing

---

## Phase 3: Manual Execution (One Command at a Time)

### Step 3.1: Test uudecode Manually
```bash
# If brad.1.uu exists, try decoding it
cd /tmp

# Decode
uudecode brad.1.uu

# Check if output created
ls -la brad.1

# If successful, check content
wc -l brad.1
wc -c brad.1
head -5 brad.1

# Expected: troff/nroff manpage source
```

**If uudecode fails**:
- Note exact error message
- Check if uudecode command exists: `which uudecode`
- Check file format: `cat brad.1.uu` (should start with "begin 644 brad.1")

### Step 3.2: Test Logging Script
```bash
# Create test build ID
TEST_BUILD="test-$(date +%s)"

# Test logging (if script exists)
echo "Test log entry" | /tmp/arpanet-log.sh PDP11 "$TEST_BUILD"

# Check if log was created
ls -la /mnt/arpanet-logs/builds/$TEST_BUILD/
cat /mnt/arpanet-logs/builds/$TEST_BUILD/PDP11.log
```

**If logging fails**:
- Note exact error message
- Check if build directory was created
- Check permissions on EFS mount
- Try creating directory manually: `mkdir -p /mnt/arpanet-logs/builds/$TEST_BUILD`

### Step 3.3: Test nroff Rendering
```bash
# If brad.1 exists from Step 3.1
nroff -man /tmp/brad.1 > /tmp/brad.txt

# Check output
ls -la /tmp/brad.txt
wc -l /tmp/brad.txt
head -10 /tmp/brad.txt

# Expected: Rendered text manpage
```

**If nroff fails**:
- Note exact error message
- Check if nroff exists: `which nroff`
- Try without -man flag: `nroff /tmp/brad.1`
- Check input file validity: `file /tmp/brad.1`

### Step 3.4: Test Output Copy to EFS
```bash
# Create output directory
mkdir -p /mnt/arpanet-logs/builds/$TEST_BUILD/pdp-output

# Copy file
cp /tmp/brad.txt /mnt/arpanet-logs/builds/$TEST_BUILD/pdp-output/

# Verify
ls -la /mnt/arpanet-logs/builds/$TEST_BUILD/pdp-output/
cat /mnt/arpanet-logs/builds/$TEST_BUILD/pdp-output/brad.txt | head -10
```

**If copy fails**:
- Check permissions: `ls -la /mnt/arpanet-logs/builds/`
- Try with sudo: `sudo mkdir -p ...` (note if sudo needed)
- Check ownership: `ls -la /mnt/arpanet-logs/`

**Document findings**: Which steps work, which fail, exact error messages

---

## Phase 4: End-to-End Manual Test

### Step 4.1: Create Clean Test Build
```bash
# Create test build ID
BUILD_ID="manual-test-$(date +%s)"

# Create build directory
mkdir -p /mnt/arpanet-logs/builds/$BUILD_ID

echo "=== PDP-11 MANUAL TEST ===" | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
echo "Build ID: $BUILD_ID" | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
echo "Date: $(date)" | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
```

### Step 4.2: Run Complete Workflow Manually
```bash
# Step 1: Check input file
echo "Checking for input file..." | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
ls -la /tmp/brad.1.uu | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"

# Step 2: Decode
echo "Decoding file..." | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
uudecode /tmp/brad.1.uu 2>&1 | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"

# Step 3: Verify decoded
echo "Verifying decode..." | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
if [ -f /tmp/brad.1 ]; then
    echo "✓ Decode successful" | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
    wc -l /tmp/brad.1 | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
else
    echo "✗ Decode failed" | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
fi

# Step 4: Render with nroff
echo "Rendering with nroff..." | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
nroff -man /tmp/brad.1 > /tmp/brad.txt 2>&1

# Step 5: Verify rendered
if [ -f /tmp/brad.txt ]; then
    echo "✓ Render successful" | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
    wc -l /tmp/brad.txt | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
else
    echo "✗ Render failed" | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
fi

# Step 6: Copy to EFS
mkdir -p /mnt/arpanet-logs/builds/$BUILD_ID/pdp-output
cp /tmp/brad.txt /mnt/arpanet-logs/builds/$BUILD_ID/pdp-output/
echo "✓ Output copied to EFS" | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"

# Step 7: Verify complete
echo "=== MANUAL TEST COMPLETE ===" | /tmp/arpanet-log.sh PDP11 "$BUILD_ID"
```

### Step 4.3: Verify from VAX
```bash
# Exit PDP-11, SSH to VAX
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<vax-ip>

# Check if PDP-11 output exists
ls -la /mnt/arpanet-logs/builds/manual-test-*/pdp-output/
cat /mnt/arpanet-logs/builds/manual-test-*/pdp-output/brad.txt | head -20

# Check PDP-11 log
cat /mnt/arpanet-logs/builds/manual-test-*/PDP11.log
```

**Document findings**: Complete working procedure with exact commands

---

## Phase 5: Identify Root Cause

Based on Phase 1-4 findings, determine:

### If brad.1.uu doesn't exist on PDP-11:
**Problem**: Console transfer not working
**Next**: Debug console-transfer.py
- Check if file is sent
- Check screen session persistence
- Check heredoc syntax

### If arpanet-log.sh doesn't exist:
**Problem**: Script not transferred to PDP-11
**Next**: Check workflow "Transfer scripts to AWS" step
- Verify scp to PDP-11 IP
- Check if file is executable

### If EFS not mounted:
**Problem**: PDP-11 container not mounting EFS
**Next**: Check docker-compose.production.yml
- Verify volume mount for PDP-11
- Check if mount happens at boot

### If uudecode fails:
**Problem**: File corruption or missing tool
**Next**:
- Check uudecode installation: `which uudecode`
- Verify file format is correct
- Test with simple file

### If nroff fails:
**Problem**: Missing tool or incompatible input
**Next**:
- Check nroff installation: `which nroff`
- Test with simple manpage
- Check 2.11BSD documentation

### If EFS write fails:
**Problem**: Permission issues
**Next**:
- Check directory ownership
- Check mount options
- May need to adjust permissions in CDK

---

## Phase 6: Document Working Procedure

Once all steps work manually, document:

1. **Prerequisites**:
   - Files needed on PDP-11
   - Environment variables
   - Directory structure

2. **Exact commands** (in order):
   - Copy/paste ready
   - With expected output
   - Error handling

3. **Verification**:
   - How to confirm each step
   - What to check on VAX

4. **Timing**:
   - How long between steps
   - Any delays needed

**Output**: `PDP11-MANUAL-PROCEDURE.md`

---

## Phase 7: Automate Working Procedure

Once manual procedure works:

1. Update `scripts/pdp11-validate.sh`:
   - Match working manual commands
   - Add timing from Phase 6
   - Add verification steps

2. Test automation:
   - Run via screen session
   - Verify same results as manual

3. Integrate into workflow:
   - Update `.github/workflows/deploy.yml`
   - Add better error checking
   - Add output verification

**Output**: Working automated PDP-11 validation

---

## Success Criteria

✅ PDP-11 validation complete when:

1. Can login to PDP-11 console
2. brad.1.uu file exists on PDP-11
3. arpanet-log.sh script exists and works
4. uudecode runs successfully
5. nroff renders manpage
6. Output copied to EFS
7. PDP11.log created and readable
8. Can verify output from VAX
9. Manual procedure documented
10. Automated procedure works

---

## Next Session Plan

### Session Start:
1. Start AWS instances: `./aws-start.sh`
2. Note IPs for VAX and PDP-11
3. Open this debugging plan: `docs/integration/PDP11-DEBUGGING-PLAN.md`

### Execute:
- Follow Phase 1-4 interactively
- Take notes on findings
- Document what works and what doesn't

### Session End:
- Document findings in this file
- Update plan with discoveries
- Stop AWS instances if done: `./aws-stop.sh`

---

## Findings Log

### 2026-02-14 (Initial Discovery)
- **Finding**: PDP-11 not producing output
- **Evidence**: `/mnt/arpanet-logs/builds/<id>/pdp-output/brad.txt` not found
- **Status**: Need interactive debugging

### [Add findings here as we debug]

---

## Related Files

- `scripts/console-transfer.py` - Sends file to PDP-11
- `scripts/pdp11-validate.sh` - Validation commands (not working)
- `scripts/arpanet-log.sh` - Logging script
- `.github/workflows/deploy.yml` - Stage 3 (PDP-11 Validation)
- `docker-compose.production.yml` - PDP-11 container config

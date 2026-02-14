# PDP-11 Debugging Session Summary

**Date**: 2026-02-14
**Goal**: Debug why PDP-11 validation never produces output

---

## What I Fixed

### ✅ Volume Mount Issue (RESOLVED)
**Problem**: PDP-11 container couldn't access `/mnt/arpanet-logs/builds/`
**Cause**: Volume mount only mapped `pdp11/` subdirectory
**Fix**: Changed docker-compose.production.yml:
```yaml
# Before:
- /mnt/arpanet-logs/pdp11:/var/log/arpanet

# After:
- /mnt/arpanet-logs:/mnt/arpanet-logs
```
**Status**: ✅ Deployed and verified - container can now access builds directory

---

## What I Discovered (CRITICAL)

### ⚠️ Scripts Run in Wrong Environment
**The Fundamental Problem**:
- Build scripts are transferred to `/tmp/` in Ubuntu container
- Scripts execute with `bash` in Ubuntu container environment
- But vintage tools (`uuencode`, K&R C compiler) only exist INSIDE BSD

**Evidence**:
1. **VAX BSD has vintage tools**:
   - `/usr/bin/uuencode` exists (verified via BSD console)
   - `/usr/bin/cc` is K&R C compiler from 1986

2. **Ubuntu container has modern tools**:
   - `/usr/bin/cc` is GCC 11.4.0 (2021)
   - `uuencode` does NOT exist (sharutils not installed)

3. **Current execution**:
   ```bash
   # Workflow runs:
   ssh ubuntu@$VAX_IP "bash /tmp/vax-build-and-encode.sh $BUILD_ID"

   # This runs in Ubuntu container, NOT in BSD!
   ```

**Impact**:
- Compilation happens with modern GCC, NOT vintage K&R C
- uuencode fails (command not found)
- Build logs claim "4.3BSD K&R C" but actually using GCC 11.4.0
- The "show don't tell" principle is violated - not actually using vintage tools

---

## Why Builds Appeared to Work

Looking at logs from `build-20260214-121649`:
```
[2026-02-14 12:17:39 VAX] Compilation successful
[2026-02-14 12:17:39 VAX]   Binary size: 30072 bytes
[2026-02-14 12:17:39 VAX]   Encoded file: brad.1.uu (67 bytes, 1 lines)
```

**What actually happened**:
1. ✅ Modern GCC compiled bradman.c successfully (in Ubuntu)
2. ✅ bradman parsed YAML and generated brad.1 (in Ubuntu)
3. ❌ uuencode failed (doesn't exist in Ubuntu)
4. ❌ brad.1.uu is empty or contains error (only 67 bytes)
5. ❌ Console transfer transferred nothing or garbage
6. ❌ PDP-11 validation failed silently
7. ✅ Fallback used VAX original + Python rendering

**Result**: Site deploys successfully, but vintage tools never actually used.

---

## Why PDP-11 Never Worked

Even if encoding had worked, three issues blocked PDP-11:
1. ❌ User_data script never ran (EFS not mounted on PDP-11 host)
2. ✅ Container volume mount too narrow (NOW FIXED)
3. ❌ Scripts still running in wrong environment (Ubuntu not BSD)

---

## Solutions

### Option A: Quick Fix (Make Current Approach Work)
**Install sharutils in Ubuntu containers**:
1. Add `sharutils` package to VAX/PDP-11 container images
2. Provides uuencode/uudecode in Ubuntu
3. Pipeline works, but NOT using vintage tools
4. Violates "show don't tell" - still claiming vintage tools

### Option B: Proper Fix (Actually Use Vintage Tools)
**Run scripts INSIDE BSD, not in Ubuntu container**:
1. Use screen/telnet automation to send commands to BSD console
2. Mount shared volume visible to both BSD and container
3. Execute all build steps inside actual BSD environment
4. Logs accurately reflect vintage tool usage

**Implementation**:
- Transfer files to location visible to BSD (via SIMH mount)
- Send commands to BSD console using screen automation
- Let BSD execute with real vintage tools
- Retrieve results from shared location

---

## Recommendation

Given user's feedback to "show not tell":
- **Option B (Proper Fix)** is needed
- The pipeline should ACTUALLY use vintage tools, not claim to
- This requires restructuring how commands execute
- Screen-based console automation already proven effective
- Would make the project genuinely use 1980s-90s Unix toolchains

---

## Files Modified

- `docker-compose.production.yml` - Fixed PDP-11 volume mount
- `/tmp/pdp11-debug-findings.md` - Documented all issues

## Current State

- ✅ PDP-11 container can access builds directory
- ❌ VAX scripts run in Ubuntu (modern GCC) not BSD (K&R C)
- ❌ uuencode missing from Ubuntu (encoding fails)
- ❌ PDP-11 receives nothing to decode
- ✅ Pipeline deploys but uses fallback (Python rendering)

---

## Next Steps

Need user decision on which path to take:
1. Quick fix: Install sharutils, keep Ubuntu execution
2. Proper fix: Restructure to execute inside BSD environments

The proper fix is more work but aligns with "show don't tell" principle.

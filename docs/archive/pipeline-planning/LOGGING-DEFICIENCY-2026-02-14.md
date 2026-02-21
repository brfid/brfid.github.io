# Logging Deficiency - Next Pass TODO

**Date**: 2026-02-14
**Status**: Identified as blocker for Phase 3

---

## Problem

The site build logs (`site/build-logs/*.log`) are incomplete and appear to be static/mock data rather than actual execution logs from the VAX → PDP-11 pipeline.

### Current State

**Files**: `VAX.log`, `PDP11.log`, `GITHUB.log` - all contain identical data:
```
[2026-02-13 15:45:23 GITHUB] Starting AWS VAX instance...
[2026-02-13 15:45:45 GITHUB] Transferring files to VAX...
[2026-02-13 15:46:02 VAX] cc -o bradman bradman.c
[2026-02-13 15:46:08 VAX] bradman: parsing resume.vax.yaml
[2026-02-13 15:46:12 VAX] bradman: truncating long title (warning)
[2026-02-13 15:46:15 VAX] bradman: generating roff output
[2026-02-13 15:46:18 VAX] Build complete
[2026-02-13 15:46:25 GITHUB] Retrieving build output...
[2026-02-13 15:46:30 GITHUB] Build successful
```

### What's Missing

1. **No PDP-11 Pipeline Steps**
   - ❌ No decode step (`uudecode`)
   - ❌ No rendering step (`nroff -man`)
   - ❌ No validation step
   - The PDP11.log should show completely different entries than VAX.log

2. **No Vintage Tool Evidence**
   - ❌ Missing compiler details: "Compiler: cc (4.3BSD K&R C)"
   - ❌ Missing tool versions
   - ❌ Missing file sizes and line counts
   - ❌ Missing section counts (.SH directives)

3. **No Transfer Step**
   - ❌ No VAX → PDP-11 transfer log entries
   - ❌ No console-based uuencode/uudecode confirmation

4. **Logs Are Identical**
   - VAX.log, PDP11.log, and GITHUB.log all have the same content
   - This indicates they're likely static/mock data, not actual pipeline execution

---

## Root Cause

1. **Scripts Not Logging to EFS**
   - `scripts/vintage-log.sh` may not be called from console build scripts
   - EFS mount point `/mnt/arpanet-logs` may not be accessible from BSD

2. **Logs Not Being Merged**
   - `scripts/merge-logs.py` may not be pulling from EFS builds directory
   - Pipeline may not be copying merged logs to `site/build-logs/`

3. **Pipeline Not Executed**
   - The full VAX → PDP-11 end-to-end pipeline may not have been run
   - Current logs may be placeholder/test data

---

## Required Fixes

### 1. Verify Script Execution

Check if these scripts are actually being called:
- `scripts/vax-console-build.sh` - should call `vintage-log.sh` for each step
- `scripts/pdp11-validate.sh` - should call `vintage-log.sh` for each step  
- `scripts/vintage-log.sh` - should write to `/mnt/arpanet-logs/builds/<id>/`

### 2. Fix EFS Logging

Ensure BSD can write to EFS mount:
- Verify `/mnt/arpanet-logs` is mounted inside BSD containers
- Check volume mounts in `docker-compose.production.yml`
- Consider writing to `/tmp` inside BSD, then copying to EFS from host

### 3. Update Merge Script

Verify `scripts/merge-logs.py`:
- Reads from correct EFS path: `/mnt/arpanet-logs/builds/<build-id>/`
- Copies merged output to `site/build-logs/merged.log`
- Updates `site/build-logs/VAX.log` and `site/build-logs/PDP11.log`

### 4. Add Vintage Tool Evidence

Each script should log:
- Tool name and version
- Input file details (size, lines)
- Output file details
- Success/failure status
- Timing information

---

## Expected Log Format

### VAX.log (during build)
```
[2026-02-14 10:00:00 GITHUB] Starting AWS VAX instance...
[2026-02-14 10:00:30 GITHUB] Transferring files to VAX...
[2026-02-14 10:01:00 VAX] Compiling bradman.c...
[2026-02-14 10:01:00 VAX]   Compiler: cc (4.3BSD K&R C)
[2026-02-14 10:01:00 VAX]   Source: bradman.c (1037 lines)
[2026-02-14 10:01:05 VAX] cc -o bradman bradman.c
[2026-02-14 10:01:10 VAX] Compilation successful
[2026-02-14 10:01:10 VAX]   Binary size: 45056 bytes
[2026-02-14 10:01:15 VAX] Generating manpage from resume.vax.yaml...
[2026-02-14 10:01:15 VAX]   Input: resume.vax.yaml (50 lines)
[2026-02-14 10:01:20 VAX]   Parser: bradman (VAX C YAML parser)
[2026-02-14 10:01:25 VAX] Manpage generated successfully
[2026-02-14 10:01:25 VAX]   Output: brad.1 (8192 bytes, 200 lines)
[2026-02-14 10:01:25 VAX]   Sections: 8 (.SH directives)
[2026-02-14 10:01:30 VAX] Encoding output for console transfer...
[2026-02-14 10:01:35 VAX] Encoding complete
[2026-02-14 10:01:35 VAX]   Original file: brad.1 (8192 bytes)
[2026-02-14 10:01:35 VAX]   Encoded file: brad.1.uu (10920 bytes, 340 lines)
[2026-02-14 10:01:40 GITHUB] Transferring encoded output to PDP-11...
[2026-02-14 10:02:30 GITHUB] Build complete
```

### PDP11.log (during validation)
```
[2026-02-14 10:02:30 GITHUB] Starting PDP-11 validation...
[2026-02-14 10:02:35 PDP11] System: 2.11BSD on PDP-11/73
[2026-02-14 10:02:40 PDP11] Step 1: Decoding uuencoded file...
[2026-02-14 10:02:40 PDP11]   Input: /tmp/brad.1.uu (10920 bytes, 340 lines)
[2026-02-14 10:02:45 PDP11] uudecode /tmp/brad.1.uu
[2026-02-14 10:02:50 PDP11]   ✓ Decode successful
[2026-02-14 10:02:50 PDP11]   Output: brad.1 (8192 bytes, 200 lines)
[2026-02-14 10:02:50 PDP11]   Sections: 8 (.SH directives)
[2026-02-14 10:02:55 PDP11] Step 2: Rendering with nroff...
[2026-02-14 10:02:55 PDP11]   Tool: nroff -man (2.11BSD troff suite)
[2026-02-14 10:03:00 PDP11] nroff -man brad.1 > brad.txt
[2026-02-14 10:03:05 PDP11]   ✓ Rendering successful
[2026-02-14 10:03:05 PDP11]   Output: brad.txt (4096 bytes, 120 lines)
[2026-02-14 10:03:10 PDP11] Validation Summary:
[2026-02-14 10:03:10 PDP11]   ✓ uuencode transfer: Successful
[2026-02-14 10:03:10 PDP11]   ✓ uudecode: Successful
[2026-02-14 10:03:10 PDP11]   ✓ nroff rendering: Successful
[2026-02-14 10:03:10 PDP11]   ✓ Cross-system validation: 2.11BSD tools
[2026-02-14 10:03:15 PDP11] Status: PASS
```

---

## Priority

**High** - Without proper logging, we cannot demonstrate that vintage tools are actually being used in the pipeline.

---

## References

- `scripts/vintage-log.sh` - Logging script
- `scripts/vax-console-build.sh` - VAX build script  
- `scripts/pdp11-validate.sh` - PDP-11 validation script
- `scripts/merge-logs.py` - Log merge utility
- `docs/integration/VAX-PDP11-VALIDATION-2026-02-14.md` - Last validation attempt

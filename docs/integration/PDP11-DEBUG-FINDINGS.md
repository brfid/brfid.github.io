# PDP-11 Debugging Findings

## Date: 2026-02-14

## Critical Issues Found

### Issue #0: VAX Scripts Run in Wrong Environment (ROOT CAUSE)
**Problem**: vax-build-and-encode.sh runs in Ubuntu container shell, not inside BSD
**Evidence**:
- Workflow runs: `bash /tmp/vax-build-and-encode.sh`
- This executes in Ubuntu container (outside SIMH/BSD)
- But `uuencode` only exists at `/usr/bin/uuencode` INSIDE BSD
- Running `which uuencode` in container returns nothing
- Running `ls /usr/bin/uu*` INSIDE BSD shows uuencode/uudecode exist

**Impact**:
- Compilation never happens (cc doesn't exist in Ubuntu)
- uuencode never works (command not found in Ubuntu)
- Entire VAX build process has never actually worked

**Solution Needed**: Scripts must run INSIDE BSD, not in container shell
Options:
- Use screen/telnet automation to send commands to BSD console
- Mount scripts into BSD filesystem and execute via console
- Or fix SIMH container to allow direct command execution in BSD

**Status**: ❌ BLOCKING - Explains why entire pipeline never worked

## Previously Identified Issues

### Issue #1: EFS Not Mounted on PDP-11 Host
**Problem**: User_data script never ran on PDP-11 instance
**Evidence**: 
- `/tmp/setup-complete` marker missing
- EFS utils not installed
- EFS not mounted at boot

**Cause**: CDK user_data script failure (needs investigation)

**Temporary Fix Applied**:
```bash
# Manually mounted EFS via NFS4
sudo mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport \
  fs-03cd0abbb728b4ad8.efs.us-east-1.amazonaws.com:/ /mnt/arpanet-logs
```

**Status**: ✅ Fixed temporarily, needs permanent solution

---

### Issue #2: PDP-11 Container Can't Access Builds Directory
**Problem**: Volume mount only maps pdp11/ subdirectory, not full EFS
**Evidence**: 
```yaml
# docker-compose.production.yml
volumes:
  - /mnt/arpanet-logs/pdp11:/var/log/arpanet
```

**Impact**:
- PDP-11 can't read `/mnt/arpanet-logs/builds/<id>/brad.1.uu`
- PDP-11 can't write `/mnt/arpanet-logs/builds/<id>/PDP11.log`
- PDP-11 can't write `/mnt/arpanet-logs/builds/<id>/pdp-output/`

**Solution Needed**: Mount full EFS or use different path
```yaml
# Option A: Mount full EFS
volumes:
  - /mnt/arpanet-logs:/mnt/arpanet-logs

# Option B: Use pdp11/ subdirectory for builds
# Change scripts to use /var/log/arpanet/ instead
```

**Status**: ❌ Not fixed, blocking PDP-11 validation

---

### Issue #3: Scripts Assume Wrong Paths
**Problem**: Validation scripts use `/mnt/arpanet-logs/builds/` which doesn't exist in container
**Files Affected**:
- `scripts/pdp11-validate.sh`
- `scripts/console-transfer.py`

**Current Paths** (won't work):
```bash
/mnt/arpanet-logs/builds/$BUILD_ID/PDP11.log
/mnt/arpanet-logs/builds/$BUILD_ID/pdp-output/
```

**Container Reality**:
- Only `/var/log/arpanet/` is available inside PDP-11
- This maps to `/mnt/arpanet-logs/pdp11/` on host

**Status**: ❌ Needs path refactoring

---

## Root Cause Analysis

### Why PDP-11 Validation Never Worked

1. **EFS not mounted** on PDP-11 host (user_data failure)
2. **Container can't access builds/** (volume mount too narrow)
3. **Scripts use wrong paths** (assume full EFS access)
4. **No error visibility** (commands sent but fail silently)

### Why Fallback Always Used

When Stage 4 tries to retrieve:
```bash
scp ubuntu@$VAX_IP:/mnt/arpanet-logs/builds/$BUILD_ID/pdp-output/brad.txt
```

File doesn't exist because PDP-11 never created it. Fallback triggers:
```bash
# Use VAX original + Python rendering instead
python -m resume_generator.manpage --in build/vax/brad.1 --out build/vax/brad.txt
```

---

## Solutions

### Quick Fix (for testing)
1. Mount full EFS in PDP-11 container
2. Transfer files to accessible location
3. Test manual commands

### Proper Fix (for automation)
1. Fix CDK user_data to run reliably
2. Change volume mount in docker-compose.production.yml
3. Update all scripts to use correct paths
4. Add error checking and logging

---

## Next Steps

1. [ ] Test manual console interaction with corrected paths
2. [ ] Verify uudecode/nroff work inside container
3. [ ] Document working manual procedure
4. [ ] Fix docker-compose volume mounts
5. [ ] Update scripts with correct paths
6. [ ] Fix CDK user_data reliability
7. [ ] Test automated workflow


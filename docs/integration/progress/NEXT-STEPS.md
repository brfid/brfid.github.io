# ARPANET Next Steps

> Historical planning log retained for evidence.
> Current production truth is in `STATUS.md`, `README.md`, and `WORKFLOWS.md`.
> Legacy two-host/EFS/CDK details below are not the active deployment model.

**Last updated:** 2026-02-14
**Status**: ✅ **Uuencode transfer operational** - Now improving observability

---

## Current Situation

**Date**: 2026-02-14
**Phase**: Uuencode console transfer fully deployed and operational

**Just Completed (2026-02-14)**:
- ✅ Uuencode console transfer system (VAX → PDP-11)
- ✅ EFS permissions fix (builds directory in CDK)
- ✅ Screen session auto-recovery (telnet timeout handling)
- ✅ All 4 stages completing successfully
- ✅ Build logs merged chronologically (VAX, COURIER, GITHUB)
- ✅ Build widget showing component stats
- ✅ Deployment: publish-vax-uuencode-v3 (successful)

**Current Focus**: Improve observability and clarify PDP-11 role
- Need: Better logging from VAX and PDP-11 machines
- Need: Clear documentation of what PDP-11 is doing
- Goal: Make the multi-machine build process transparent

**Infrastructure**:
- ✅ ArpanetProductionStack deployed to AWS
- ✅ 2x t3.micro instances (VAX + PDP-11)
- ✅ Shared EFS logging at `/mnt/arpanet-logs/`
- ✅ Uuencode console transfer operational
- ✅ IMP phase archived (protocol incompatibility)

**System Status**:
- **VAX**: 172.20.0.10 (de0) - ✅ FULLY OPERATIONAL
  - Compiling bradman.c
  - Generating manpage
  - Encoding with uuencode
  - Logging to EFS
- **PDP-11**: 172.20.0.50 (console) - ✅ OPERATIONAL VIA CONSOLE
  - Receiving via console I/O
  - Decoding with uudecode
  - Validating with nroff
  - Results copied to EFS
- **COURIER** (GitHub Actions): ✅ OPERATIONAL
  - Orchestrating all stages
  - Console transfer automation
  - Log aggregation

---

## Immediate Next Steps (Current Session)

### Phase 1: Improve VAX and PDP-11 Logging (30-45 min)

**Goal**: Get more detailed logs from both machines to understand what they're doing

**Current Issue**:
- VAX logs only show 13 lines (basic build info)
- PDP-11 logs don't exist (validation happens via console commands)
- Build process is opaque - hard to see what's actually happening

**Improvements Needed**:

#### 1.1 Enhanced VAX Logging
- Add compilation output (not just "success/fail")
- Show manpage generation details
- Log file sizes and line counts
- Add timestamps for each step
- Show encoding statistics

#### 1.2 PDP-11 Logging System
- Create PDP-11 logging script (similar to VAX)
- Log decode progress
- Log validation steps
- Capture nroff output samples
- Write to EFS for merging

#### 1.3 COURIER Enhancements
- Log each line during transfer (progress indicator)
- Add transfer statistics (bytes, duration, speed)
- Log console output captures
- Better error diagnostics

**Files to Modify**:
- `scripts/vax-build-and-encode.sh` - Add verbose logging
- `scripts/pdp11-validate.sh` - Create proper logging (not just echo)
- `scripts/console-transfer.py` - Add transfer progress logging
- `scripts/arpanet-log.sh` - Already good, use more extensively

---

### Phase 2: Clarify PDP-11 Role (15-30 min)

**Goal**: Document exactly what the PDP-11 is doing and why

**Questions to Answer**:
- What does uudecode do? (binary-to-text decoding)
- What does nroff do? (manpage rendering)
- Why is PDP-11 validation important? (authentic 1970s-80s toolchain)
- What would break if we skipped PDP-11? (miss historical accuracy)

**Deliverables**:
- Update README with PDP-11 role explanation
- Add comments to validation script
- Create architecture diagram showing data flow
- Document historical context

---

### Phase 3: Make Build Process Transparent (30-45 min)

**Goal**: Show the complete build pipeline on the website

**Ideas**:
- Build timeline visualization (VAX → COURIER → PDP-11 → GitHub)
- Show each machine's output in build widget
- Add "What happened" summary to build logs
- Link to architectural docs from site

**Files to Create/Modify**:
- `scripts/generate-build-summary.py` - Create human-readable summary
- `templates/build-timeline.html` - Visual timeline component
- `site/index.html` - Link to build process explanation

---

## PDP-11 Networking Fix Paths

The following three paths are available to resolve the networking blocker, ordered from fastest to most robust:

### Path 3: Fix netnix Crash - TESTED ❌

**Approach**: Force SIMH vector/CSR settings in pdp11.ini to match 2.11BSD kernel expectations.

**SIMH Configuration Fix** (`arpanet/configs/pdp11.ini`):
```ini
set xq enabled
set xq address=174440
set xq vector=120
attach xq eth0
```

**Test Result**: ❌ FAILED - SIMH version 4.0-0 does not support `set xq address` or `set xq vector` parameters. These cause "Non-existent parameter" errors.

**Conclusion**: Path 3 will not work with current SIMH version.

---

### Path 1: Pre-built Networking Image - TESTED ❌

**Approach**: Download PiDP-11 community's `2.11BSD_rq.dsk` with kernel properly built with networking (qe driver for DEQNA/DELQA).

**Sources Attempted**:
- https://pidp.net/pidp11/systems.tar.gz - ❌ Not accessible (404 or corrupted)
- https://github.com/chasecovello/211bsd-pidp11 - ❌ No releases
- https://www.retro11.de - Only rpeth variant (current one), no rq variant

**Result**: Could not locate working pre-built image with networking.

**Alternative**: May need to find alternative source or build custom image.

---

### netnix Kernel Test

**Boot command**: `xp(0,0,0)netnix`

**Result**: Crashes with "Trap stack push abort" at PC:005320

The netnix kernel crashes immediately when booted, regardless of SIMH configuration.

---

### Path 2: Rebuild Kernel (Last Resort)

**Approach**: If keeping current disk image, rebuild kernel with qe driver enabled.

**Steps**:
1. Boot working kernel (unix)
2. Edit `/usr/src/sys/conf/GENERIC` or create `NET` config
3. Ensure these lines exist:
   ```c
   options INET
   device qe0 at uba? csr 174440 vector qeintr
   pseudo-device pty 4
   pseudo-device loop
   pseudo-device ether
   ```
4. Compile: `./config NET && make && make install`
5. Boot new kernel: `xp(0,0,0)netnix`

**Estimated Time**: 2-4 hours

---

### Tape Transfer Alternative (Already Configured)

If all networking paths fail, the TS11 tape drive is already configured:

**Current Config**:
- Tape device in pdp11.ini: `set ts enabled`
- Transfer file: `/var/log/arpanet/transfer.tap`

**Steps**:
1. Write file from VAX to tape
2. Read file on PDP-11 from tape
3. See: TS11 tape transfer testing in progress

---

## Current Priority Order

### Phase 1: Tape Transfer (IMMEDIATE)
**Goal**: Get TS11 tape transfer working between VAX and PDP-11

**Current Config**:
- PDP-11: TS11 tape device enabled (`set ts enabled` in pdp11.ini)
- VAX: Has TU58 tape (but using EFS for file exchange)
- Transfer method: Shared EFS file at `/mnt/arpanet-logs/` mapped to `/var/log/arpanet/`

**Steps**:
1. Start AWS instances: `./aws-start.sh`
2. SSH to VAX: `ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<vax-ip>`
3. Create test file on VAX:
   ```bash
   echo "Test from VAX $(date)" > /mnt/arpanet-logs/vax/tape-test.txt
   ```
4. SSH to PDP-11: `ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<pdp11-ip>`
5. Check if file is accessible via shared EFS
6. Alternatively, use VAX's tape device to write to EFS-mounted tape file
7. Document results

**Alternative - Direct TS11 on PDP-11**:
- The PDP-11 has TS11 configured: `attach ts /var/log/arpanet/transfer.tap`
- Boot PDP-11 and check `dmesg` for ts0 device
- Use `mt` command to read/write tape

**Status**: ⏸️ Pending - Next session task

---

### Phase 2: Direct Connection (AFTER TAPE)
**Goal**: Get VAX ↔ PDP-11 TCP/IP networking working

**Options** (if networking needed):
- Find working PDP-11 kernel with Ethernet support
- Deploy second VAX as alternative
- Rebuild PDP-11 kernel from source

**Status**: ⏸️ Pending

---

### Phase 3: IMP Network (EVENTUALLY)
**Goal**: Restore ARPANET 1822 protocol demonstration

**Note**: IMPs were archived due to protocol incompatibility but can be restored for historical demonstration purposes.

**Status**: ⏸️ Future enhancement

---

## What Was Done Before Blocker Identified

**What's Done**:
- ✅ CDK stack deployed
- ✅ EFS mounted via NFS4 on both instances
- ✅ Docker images built (PDP-11 custom, VAX pulled)
- ✅ Containers running (VAX + PDP-11)
- ✅ IMPs archived with documentation
- ✅ Management scripts created (`aws-*.sh`)
- ✅ Documentation updated (STATUS.md, COLD-START.md)
- ✅ VAX network and FTP fully operational

**What's Next** (after PDP-11 fix):
- → Configure PDP-11 network interfaces
- → Test connectivity (ping)
- → Test FTP transfers both directions
- → Make configuration persistent
- → Document validation results

---

## Immediate Actions (Next Session)

### Phase 1: Network Configuration (30-45 min)

**Complete guide**: `docs/arpanet/VAX-PDP11-FTP-SETUP.md`

#### 1.1 Configure VAX Network
```bash
# Access VAX console
telnet <vax-ip> 2323

# Login as root
login: root

# Configure network
ifconfig de0 172.20.0.10 netmask 255.255.0.0 up
route add default 172.20.0.1

# Verify
ifconfig de0
netstat -rn
```

**Expected**: de0 shows UP with 172.20.0.10

#### 1.2 Configure PDP-11 Network
```bash
# Access PDP-11 console
telnet <pdp11-ip> 2327

# Login as root
login: root

# Configure network
ifconfig xq0 172.20.0.50 netmask 255.255.0.0 up
route add default 172.20.0.1

# Verify
ifconfig xq0
netstat -rn
```

**Expected**: xq0 shows UP with 172.20.0.50

#### 1.3 Test Connectivity
```bash
# From VAX:
ping 172.20.0.50

# From PDP-11:
ping 172.20.0.10
```

**Expected**: Ping replies from both directions

**If fails**: See troubleshooting section in FTP setup guide

---

### Phase 2: FTP Configuration (15-30 min)

#### 2.1 Enable FTP on VAX
```bash
# Check inetd config
grep ftp /etc/inetd.conf

# Should show ftpd enabled
# If not, add: ftp stream tcp nowait root /usr/libexec/ftpd ftpd -l

# Restart inetd (if changed)
ps aux | grep inetd
kill -HUP <pid>

# Verify listening
netstat -an | grep :21
```

#### 2.2 Enable FTP on PDP-11
```bash
# Same steps as VAX
grep ftp /etc/inetd.conf
# If needed, add ftpd to inetd.conf
kill -HUP <inetd-pid>
netstat -an | grep :21
```

---

### Phase 3: FTP Testing (15-30 min)

#### 3.1 Test VAX → PDP-11
```bash
# On VAX:
echo "Hello from VAX" > /tmp/vax-test.txt
ftp 172.20.0.50
# Login as root
ftp> put /tmp/vax-test.txt
ftp> quit

# On PDP-11, verify:
cat ~root/vax-test.txt
```

#### 3.2 Test PDP-11 → VAX
```bash
# On PDP-11:
echo "Hello from PDP-11" > /tmp/pdp11-test.txt
ftp 172.20.0.10
# Login as root
ftp> put /tmp/pdp11-test.txt
ftp> quit

# On VAX, verify:
cat ~root/pdp11-test.txt
```

#### 3.3 Test Binary Transfer
```bash
# VAX → PDP-11 binary:
ftp 172.20.0.50
ftp> binary
ftp> put /bin/ls /tmp/ls-from-vax
ftp> quit

# PDP-11 → VAX binary:
ftp 172.20.0.10
ftp> binary
ftp> put /bin/ls /tmp/ls-from-vax
ftp> quit
```

**Expected**: All transfers succeed, files verified on target

---

### Phase 4: Make Persistent (15-30 min)

#### 4.1 VAX Persistence
```bash
# Edit /etc/rc.local
vi /etc/rc.local

# Add before exit:
ifconfig de0 172.20.0.10 netmask 255.255.0.0 up
route add default 172.20.0.1

# Test:
docker restart arpanet-vax
# Wait 30 sec, verify config persists
```

#### 4.2 PDP-11 Persistence
```bash
# Edit /etc/rc.local
vi /etc/rc.local

# Add before exit:
ifconfig xq0 172.20.0.50 netmask 255.255.0.0 up
route add default 172.20.0.1

# Test:
docker restart arpanet-pdp11
# Wait 30 sec, verify config persists
```

---

### Phase 5: Validation (15 min)

#### 5.1 Create Validation Report
```bash
# SSH to VAX instance
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<vax-ip>

# Create report in EFS shared logs
cat > /mnt/arpanet-logs/shared/ftp-validation-$(date +%Y%m%d).txt <<'EOF'
FTP Validation Report
=====================
Date: $(date)

Network Configuration:
- VAX: 172.20.0.10 (de0)
- PDP-11: 172.20.0.50 (xq0)

Connectivity Tests:
- VAX → PDP-11 ping: [result]
- PDP-11 → VAX ping: [result]

FTP Tests:
- VAX → PDP-11 text: [result]
- PDP-11 → VAX text: [result]
- VAX → PDP-11 binary: [result]
- PDP-11 → VAX binary: [result]

Persistence:
- VAX network survives restart: [result]
- PDP-11 network survives restart: [result]

Status: [PASS/FAIL]
EOF
```

#### 5.2 Update Documentation
- [ ] Mark FTP setup complete in STATUS.md
- [ ] Update PRODUCTION-STATUS with validation results
- [ ] Archive NEXT-STEPS to dated file
- [ ] Create new NEXT-STEPS for pipeline integration

---

## Success Criteria

✅ **Phase 1-5 Complete When**:
1. Both systems have persistent network configuration
2. Ping works both directions
3. Telnet works both directions
4. FTP text transfer works both directions
5. FTP binary transfer works both directions
6. Configuration survives container restarts
7. Validation report created in EFS logs
8. Documentation updated

**Total Time Estimate**: 1.5-2.5 hours

---

## After FTP Working: Pipeline Integration

### Phase 6: Resume Build Integration (2-3 hours)

**Goal**: Transfer resume artifacts from VAX to PDP-11 via FTP

**Steps**:
1. Generate artifact on VAX (already working)
2. FTP transfer to PDP-11
3. Process on PDP-11 (additional formatting/rendering)
4. Collect results in EFS shared logs
5. Automate with expect scripts

**See**: Will be documented in `docs/arpanet/PIPELINE-INTEGRATION.md`

### Phase 7: GitHub Actions Migration (1-2 hours)

**Goal**: Move from AWS testing to GitHub Actions

**Steps**:
1. Create GitHub Actions workflow
2. Build Docker images in CI
3. Run network/FTP tests
4. Generate artifacts
5. Publish to GitHub Pages
6. Stop AWS instances (keep infrastructure for occasional testing)

### Phase 8: Optional Enhancements

**When stable**:
- [ ] Restore IMPs for demonstration (optional)
- [ ] Add web interface for viewing logs
- [ ] Create historical timeline visualization
- [ ] Document for resume/portfolio

---

## Quick Commands Reference

### Check AWS Status
```bash
./aws-status.sh
```

### Access Systems
```bash
# VAX console
telnet <vax-ip> 2323

# PDP-11 console
telnet <pdp11-ip> 2327

# SSH to instances
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<vax-ip>
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<pdp11-ip>
```

### Manage Containers
```bash
# On either instance:
docker-compose -f docker-compose.production.yml ps
docker-compose -f docker-compose.production.yml logs -f
docker-compose -f docker-compose.production.yml restart vax
docker-compose -f docker-compose.production.yml restart pdp11
```

### Check Logs
```bash
# On either instance:
tail -f /mnt/arpanet-logs/vax/boot.log
tail -f /mnt/arpanet-logs/pdp11/boot.log
du -sh /mnt/arpanet-logs/*
```

### Save Money
```bash
./aws-stop.sh  # Saves ~$15/month, keeps all data
./aws-start.sh # Resume work (new IPs shown)
```

---

## Related Documentation

**Primary**:
- `docs/arpanet/VAX-PDP11-FTP-SETUP.md` - **Complete FTP setup guide** ⭐
- `docs/COLD-START.md` - Cold start orientation
- `STATUS.md` - Overall project status
- `PRODUCTION-DEPLOYMENT.md` - Full deployment guide

**Infrastructure**:
- `docker-compose.production.yml` - Container orchestration
- `README.md` - Current single-host `edcloud` lifecycle model
- `STATUS.md` - Current platform boundary and operations status
- `https://github.com/brfid/edcloud/blob/main/SETUP.md` - Active platform setup guide

**Historical**:
- `docs/arpanet/PRODUCTION-STATUS-2026-02-13.md` - Deployment report
- `arpanet/archived/imp-phase/README.md` - Why IMPs were archived
- `docs/arpanet/PDP11-BOOT-SUCCESS-2026-02-12.md` - PDP-11 automation

---

## Decision History

### 2026-02-13: Archive IMPs, Deploy Production
**Decision**: Remove IMPs, use direct VAX ↔ PDP-11 TCP/IP
**Reason**: Protocol incompatibility (Ethernet/TCP-IP vs ARPANET 1822)
**Result**: Simpler architecture, lower maintenance, same functionality

### 2026-02-12: Choose PDP-11 over PDP-10
**Decision**: Use PDP-11/2.11BSD instead of PDP-10/TOPS-20
**Reason**: Console automation issues common to both, PDP-11 has simpler setup
**Result**: Pre-built disk image works, Ethernet support native

### 2026-02-07: Validate ARPANET Phase 1 & 2
**Decision**: Validate IMP routing with VAX
**Reason**: Prove ARPANET 1822 protocol works
**Result**: ✅ Successful, but not needed for VAX ↔ PDP-11 (archived)

---

## Cost Tracking

**Current monthly cost**: ~$17.90
- 2x t3.micro: $15.00
- 2x 8GB EBS: $1.28
- EFS with IA: $0.73
- S3: $0.02

**When stopped**: ~$2.00/month (storage only)

**Optimization option**: Single t3.micro (~$9.50/month, both containers on one instance)

---

## AWS Instance Info

**VAX**: i-090040c544bb866e8 @ 3.80.32.255
**PDP-11**: i-071ab53e735109c59 @ 3.87.125.203
**EFS**: fs-03cd0abbb728b4ad8
**SSH Key**: ~/.ssh/arpanet-temp.pem
**Region**: us-east-1
**Account**: 972626128180

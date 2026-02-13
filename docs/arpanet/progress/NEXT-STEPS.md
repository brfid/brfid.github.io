# ARPANET Next Steps

**Last updated:** 2026-02-13
**Status**: ✅ **Production infrastructure deployed - Ready for FTP setup**

---

## Current Situation

**Date**: 2026-02-13
**Phase**: Production deployment complete, awaiting network configuration

**Infrastructure**:
- ✅ ArpanetProductionStack deployed to AWS
- ✅ 2x t3.micro instances (VAX + PDP-11)
- ✅ Shared EFS logging at `/mnt/arpanet-logs/`
- ✅ Both containers running without restart loops
- ✅ IMP phase archived (protocol incompatibility)

**Network**:
- VAX: 172.20.0.10 (de0 interface detected)
- PDP-11: 172.20.0.50 (xq0 interface, Ethernet working)
- Docker bridge: 172.20.0.0/16

**AWS Instances**:
- VAX: 3.80.32.255 (i-090040c544bb866e8)
- PDP-11: 3.87.125.203 (i-071ab53e735109c59)
- EFS: fs-03cd0abbb728b4ad8
- Cost: ~$17/month running, ~$2/month stopped

**What's Done**:
- ✅ CDK stack deployed
- ✅ EFS mounted via NFS4 on both instances
- ✅ Docker images built (PDP-11 custom, VAX pulled)
- ✅ Containers running (VAX + PDP-11)
- ✅ IMPs archived with documentation
- ✅ Management scripts created (`aws-*.sh`)
- ✅ Documentation updated (STATUS.md, COLD-START.md)

**What's Next**:
- → Configure network interfaces (assign IPs)
- → Test connectivity (ping)
- → Configure FTP on both systems
- → Test file transfers
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
- `infra/cdk/arpanet_production_stack.py` - CDK stack code
- `docker-compose.production.yml` - Container orchestration
- `infra/cdk/PRODUCTION-README.md` - Infrastructure guide

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

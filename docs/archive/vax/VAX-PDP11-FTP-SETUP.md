# VAX ↔ PDP-11 FTP Setup Guide

**Goal**: Establish working FTP file transfers between VAX (172.20.0.10) and PDP-11 (172.20.0.50).

**Prerequisites**: Both containers running on AWS production infrastructure.

---

## Quick Reference

```bash
# Check AWS status
./aws-status.sh

# Access VAX console
telnet <vax-ip> 2323

# Access PDP-11 console
telnet <pdp11-ip> 2327

# From VAX: Transfer to PDP-11
ftp 172.20.0.50

# From PDP-11: Transfer to VAX
ftp 172.20.0.10
```

---

## Phase 1: Network Configuration (30-45 min)

### Step 1: Configure VAX Network

**Access VAX console**:
```bash
telnet <vax-ip> 2323
```

**At BSD login**:
```
login: root
```

**Configure de0 interface**:
```bash
# Check current network config
ifconfig -a

# Configure IP address
ifconfig de0 172.20.0.10 netmask 255.255.0.0 up

# Add default route
route add default 172.20.0.1

# Verify
ifconfig de0
netstat -rn
```

**Expected output**:
```
de0: flags=63<UP,BROADCAST,RUNNING>
        inet 172.20.0.10 netmask ffffff00 broadcast 172.20.255.255
```

### Step 2: Configure PDP-11 Network

**Access PDP-11 console**:
```bash
telnet <pdp11-ip> 2327
```

**At 2.11BSD login**:
```
login: root
```

**Configure xq0 interface**:
```bash
# Check current network config
ifconfig -a

# Configure IP address
ifconfig xq0 172.20.0.50 netmask 255.255.0.0 up

# Add default route
route add default 172.20.0.1

# Verify
ifconfig xq0
netstat -rn
```

**Expected output**:
```
xq0: flags=63<UP,BROADCAST,RUNNING>
        inet 172.20.0.50 netmask ffffff00 broadcast 172.20.255.255
```

### Step 3: Test Connectivity

**From VAX**:
```bash
ping 172.20.0.50
# Expected: replies from 172.20.0.50

telnet 172.20.0.50
# Expected: Connection to 172.20.0.50
# If successful, type 'quit' to exit
```

**From PDP-11**:
```bash
ping 172.20.0.10
# Expected: replies from 172.20.0.10

telnet 172.20.0.10
# Expected: Connection to 172.20.0.10
# If successful, type 'quit' to exit
```

**Troubleshooting**:
- If ping fails: Check `ifconfig` shows UP and correct IP
- If routing fails: Check `netstat -rn` shows default route
- If Docker network issue: Check `docker network inspect arpanet-production`

---

## Phase 2: FTP Server Configuration (15-30 min)

### Step 4: Enable FTP on VAX (4.3BSD)

FTP server (ftpd) should already be enabled in inetd.

**Check inetd configuration**:
```bash
grep ftp /etc/inetd.conf
# Should see: ftp stream tcp nowait root /usr/libexec/ftpd ftpd -l
```

**If not enabled**:
```bash
echo "ftp stream tcp nowait root /usr/libexec/ftpd ftpd -l" >> /etc/inetd.conf
```

**Restart inetd** (if config changed):
```bash
# Find inetd process
ps aux | grep inetd

# Kill and restart (inetd will auto-restart from /etc/rc)
kill -HUP <pid>
```

**Verify FTP is listening**:
```bash
netstat -an | grep :21
# Should see: *.21 LISTEN
```

### Step 5: Enable FTP on PDP-11 (2.11BSD)

**Check inetd configuration**:
```bash
grep ftp /etc/inetd.conf
# Should see: ftp stream tcp nowait root /usr/libexec/ftpd ftpd -l
```

**If not enabled**:
```bash
echo "ftp stream tcp nowait root /usr/libexec/ftpd ftpd -l" >> /etc/inetd.conf
```

**Restart inetd** (if config changed):
```bash
ps aux | grep inetd
kill -HUP <pid>
```

**Verify FTP is listening**:
```bash
netstat -an | grep :21
# Should see: *.21 LISTEN
```

---

## Phase 3: FTP Testing (15-30 min)

### Step 6: Test VAX → PDP-11 Transfer

**On VAX, create test file**:
```bash
echo "Hello from VAX 4.3BSD" > /tmp/vax-test.txt
cat /tmp/vax-test.txt
```

**Connect to PDP-11 FTP**:
```bash
ftp 172.20.0.50
```

**At FTP prompt**:
```
Name: root
Password: (enter root password)

ftp> pwd
ftp> ls
ftp> put /tmp/vax-test.txt
ftp> ls
ftp> quit
```

**Expected result**: File transferred successfully.

**On PDP-11, verify receipt**:
```bash
ls -la ~root/vax-test.txt
cat ~root/vax-test.txt
# Should show: "Hello from VAX 4.3BSD"
```

### Step 7: Test PDP-11 → VAX Transfer

**On PDP-11, create test file**:
```bash
echo "Hello from PDP-11 2.11BSD" > /tmp/pdp11-test.txt
cat /tmp/pdp11-test.txt
```

**Connect to VAX FTP**:
```bash
ftp 172.20.0.10
```

**At FTP prompt**:
```
Name: root
Password: (enter root password)

ftp> pwd
ftp> ls
ftp> put /tmp/pdp11-test.txt
ftp> ls
ftp> quit
```

**Expected result**: File transferred successfully.

**On VAX, verify receipt**:
```bash
ls -la ~root/pdp11-test.txt
cat ~root/pdp11-test.txt
# Should show: "Hello from PDP-11 2.11BSD"
```

### Step 8: Test Binary Transfer

**On VAX, test binary mode**:
```bash
ftp 172.20.0.50
```

**At FTP prompt**:
```
ftp> binary
ftp> put /bin/ls /tmp/ls-from-vax
ftp> quit
```

**On PDP-11, verify**:
```bash
ls -la /tmp/ls-from-vax
file /tmp/ls-from-vax
# Should show binary executable
```

**Test reverse direction**:
```bash
# On PDP-11:
ftp 172.20.0.10
ftp> binary
ftp> put /bin/ls /tmp/ls-from-pdp11
ftp> quit

# On VAX, verify:
ls -la /tmp/ls-from-pdp11
file /tmp/ls-from-pdp11
```

---

## Phase 4: Make Configuration Persistent (15-30 min)

### Step 9: VAX Network Persistence

**Edit network startup script**:
```bash
vi /etc/rc.local
```

**Add before final exit**:
```bash
# Configure network for ARPANET integration
ifconfig de0 172.20.0.10 netmask 255.255.0.0 up
route add default 172.20.0.1
```

**Create hostname file**:
```bash
echo "vax-host" > /etc/hostname
```

**Verify on reboot**:
```bash
# Restart container and check:
docker restart arpanet-vax
# Wait ~30 seconds, then telnet and check:
ifconfig de0
netstat -rn
```

### Step 10: PDP-11 Network Persistence

**Edit network startup script**:
```bash
vi /etc/rc.local
```

**Add before final exit**:
```bash
# Configure network for ARPANET integration
ifconfig xq0 172.20.0.50 netmask 255.255.0.0 up
route add default 172.20.0.1
```

**Create hostname file**:
```bash
echo "pdp11-host" > /etc/hostname
```

**Verify on reboot**:
```bash
# Restart container and check:
docker restart arpanet-pdp11
# Wait ~30 seconds, then telnet and check:
ifconfig xq0
netstat -rn
```

---

## Phase 5: Documentation and Validation (15 min)

### Step 11: Document Current State

**Create validation report**:
```bash
# SSH to VAX instance
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<vax-ip>

# Capture validation evidence
cat > /mnt/arpanet-logs/shared/ftp-validation.txt <<'EOF'
FTP Validation Report
Date: $(date)

VAX Configuration:
$(docker exec arpanet-vax ifconfig de0)

PDP-11 Configuration:
$(docker exec arpanet-pdp11 ifconfig xq0)

Connectivity Test:
$(docker exec arpanet-vax ping -c 3 172.20.0.50)

FTP Services:
VAX: $(docker exec arpanet-vax netstat -an | grep :21)
PDP-11: $(docker exec arpanet-pdp11 netstat -an | grep :21)
EOF
```

### Step 12: Final Validation Checklist

- [ ] VAX network configured (172.20.0.10)
- [ ] PDP-11 network configured (172.20.0.50)
- [ ] Ping works both directions
- [ ] Telnet works both directions
- [ ] FTP text transfer VAX → PDP-11
- [ ] FTP text transfer PDP-11 → VAX
- [ ] FTP binary transfer VAX → PDP-11
- [ ] FTP binary transfer PDP-11 → VAX
- [ ] Network config persists after container restart
- [ ] FTP services auto-start after reboot
- [ ] Validation report created in EFS logs

---

## Troubleshooting

### Network Issues

**Symptom**: `ifconfig` shows no IP address
```bash
# Re-run configuration:
ifconfig de0 172.20.0.10 netmask 255.255.0.0 up  # VAX
ifconfig xq0 172.20.0.50 netmask 255.255.0.0 up  # PDP-11
```

**Symptom**: Ping times out
```bash
# Check interface is UP:
ifconfig de0    # or xq0
# Should show: flags=63<UP,BROADCAST,RUNNING>

# Check routing:
netstat -rn
# Should show default route to 172.20.0.1

# Check Docker network:
# (from host)
docker network inspect arpanet-production
```

**Symptom**: "Network unreachable"
```bash
# Add default route:
route add default 172.20.0.1
```

### FTP Issues

**Symptom**: "Connection refused" on port 21
```bash
# Check FTP server is listening:
netstat -an | grep :21

# If not listening, check inetd:
ps aux | grep inetd
grep ftp /etc/inetd.conf

# Restart inetd:
kill -HUP <inetd-pid>
```

**Symptom**: "Login incorrect"
```bash
# Make sure you're using root account
# Check /etc/ftpusers doesn't block root:
grep root /etc/ftpusers
# If found, remove that line or use different user
```

**Symptom**: "Permission denied" on file transfer
```bash
# Check file permissions:
ls -la <file>

# Check target directory is writable:
ls -ld ~root/
```

### Persistence Issues

**Symptom**: Network config lost after restart
```bash
# Check /etc/rc.local exists and is executable:
ls -la /etc/rc.local
chmod +x /etc/rc.local

# Verify ifconfig commands are in /etc/rc.local:
grep ifconfig /etc/rc.local

# Check rc.local is being executed:
# (add 'echo "Network configured" > /tmp/rc-ran' to verify)
```

---

## Performance Notes

**Expected transfer speeds**:
- Text files: Near-instant (small size)
- Binary files (1MB): ~2-5 seconds
- Large files (10MB): ~30-60 seconds

These are emulated systems, not real hardware, so speeds will vary based on host CPU.

---

## Security Notes

⚠️ **For testing/demonstration only**:
- Using root account for FTP (not recommended for production)
- No encryption (plain FTP, not FTPS/SFTP)
- No firewall rules (Docker network is isolated)
- Passwords transmitted in clear text

This is acceptable for a closed demonstration environment but should NOT be used for sensitive data.

---

## Next Steps After FTP Working

1. **Integrate with build pipeline**:
   - Transfer resume artifacts from VAX to PDP-11
   - Generate additional artifacts on PDP-11
   - Log transfers to EFS

2. **Automate transfers**:
   - Create expect scripts for unattended FTP
   - Add to resume build pipeline
   - Generate transfer logs

3. **Move to GitHub Actions**:
   - Test infrastructure in CI/CD
   - Generate artifacts on each build
   - Publish to GitHub Pages

4. **Optional enhancements**:
   - Add IMP routing back (if desired for demo)
   - Add additional vintage systems
   - Create web interface for logs

---

## References

- **4.3BSD Network Admin Guide**: /usr/doc/networking (on VAX)
- **2.11BSD Setup Guide**: /usr/doc/setup (on PDP-11)
- **Production deployment**: `PRODUCTION-DEPLOYMENT.md`
- **Docker compose**: `docker-compose.production.yml`
- **AWS management**: `aws-*.sh` scripts

---

## Success Criteria

✅ **Complete when**:
1. Both systems have persistent network configuration
2. FTP works both directions (text and binary)
3. Configuration survives container restarts
4. Validation report created with evidence
5. Next steps documented in NEXT-STEPS.md

**Time estimate**: 1.5-2.5 hours for full setup and validation

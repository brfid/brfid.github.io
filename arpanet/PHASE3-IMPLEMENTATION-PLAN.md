# Phase 3 Implementation Plan: PDP-10 Integration & Build Pipeline

**Created**: 2026-02-08
**Status**: Ready to execute
**Blocker**: TOPS-20 installation (manual, 1-2 hours)
**Platform**: AWS EC2 x86_64 (required for SIMH compatibility)

---

## Executive Summary

Phase 3 completes the ARPANET build integration by:
1. Installing TOPS-20 on PDP-10 container
2. Validating 4-container routing (VAX → IMP1 → IMP2 → PDP-10)
3. Implementing FTP file transfer between VAX and PDP-10
4. Integrating ARPANET into resume build pipeline

**Estimated Timeline**: 2-4 weeks
**Critical Path**: TOPS-20 installation (prerequisite for everything else)

---

## Phase 3.1: PDP-10 TOPS-20 Installation

### Prerequisites

**Infrastructure**:
- AWS EC2 x86_64 instance (t3.medium recommended)
- Docker + Docker Compose installed
- Code synced from GitHub

**Verify readiness**:
```bash
# On AWS instance
cd ~/brfid.github.io
git pull
docker compose -f docker-compose.arpanet.phase2.yml ps
```

### Installation Process

#### Step 1: Build PDP-10 Container (if not already built)

```bash
# Build the PDP-10 container
docker compose -f docker-compose.arpanet.phase2.yml build pdp10

# Expected: Downloads TOPS-20 V4.1 tape, compiles pdp10-ks
# Duration: 5-10 minutes
```

**Success criteria**:
- ✅ Image tagged as `arpanet-pdp10`
- ✅ TOPS-20 tape at `/machines/pdp10/tops20_v41.tap`
- ✅ pdp10-ks binary at `/usr/local/bin/pdp10-ks`

#### Step 2: Start Phase 2 Stack

```bash
# Start all containers
docker compose -f docker-compose.arpanet.phase2.yml up -d

# Verify all 4 containers are running
docker compose -f docker-compose.arpanet.phase2.yml ps

# Expected:
# arpanet-vax    (172.20.0.10:2323)
# arpanet-imp1   (172.20.0.20:2324)
# arpanet-imp2   (172.20.0.30:2325)
# arpanet-pdp10  (172.20.0.40:2326) ← Focus here
```

#### Step 3: Connect to PDP-10 Console

```bash
# Connect to PDP-10 telnet console
telnet localhost 2326

# You should see SIMH banner and TOPS-20 boot messages
```

**Expected output**:
```
PDP-10 simulator V4.0-0 Current        git commit id: ...
PDP-10 TOPS-20 V4.1 starting...
IMP network interface: 172.20.0.40:2000 <-> IMP #2 at 172.20.0.30:2000
Telnet console on port 2323
Installation tape: tops20_v41.tap on TUA0
System disk: /machines/data/tops20.dsk on RPA0

Booting from installation tape...
Connect via: telnet localhost 2326
```

#### Step 4: TOPS-20 Installation Wizard

**⚠️ This is a manual, interactive process (~1-2 hours)**

The PDP-10 will boot from the installation tape and present an installation wizard. You'll need to:

1. **Boot from tape**: Follow SIMH prompts
2. **Create system disk**: Format RP06 disk drive (RPA0)
3. **Install OS**: Copy TOPS-20 from tape to disk
4. **Configure networking**: Set up ARPANET interface
5. **Create users**: At minimum, create `OPERATOR` and `ANONYMOUS`
6. **Enable services**: Start FTP daemon, ARPANET stack
7. **Save configuration**: Ensure system boots from disk next time

**Reference documentation**:
- TOPS-20 V4.1 Installation Guide (if available)
- SIMH PDP-10 documentation: http://simh.trailing-edge.com/pdf/pdp10_doc.pdf
- TOPS-20 Commands Reference: http://bitsavers.org/pdf/dec/pdp10/TOPS20/

**Installation notes to capture**:
```bash
# Create a session log
script pdp10-installation-$(date +%Y%m%d).log

# Then telnet and document:
# - Boot commands used
# - Disk configuration (RPA0 size, format options)
# - Network configuration (ARPANET interface setup)
# - User accounts created
# - Services enabled
# - Final boot command

# Exit log
exit
```

#### Step 5: Post-Installation Validation

After installation completes and TOPS-20 is running:

```bash
# 1. Verify system boots successfully
docker restart arpanet-pdp10
sleep 30
telnet localhost 2326

# 2. Login and check services
@LOGIN OPERATOR
Password: <your_password>

@SYSTAT                    # System status
@DIR                       # Directory listing
@ENABLE                    # Enable privileged mode
@INFORMATION FTP-SERVER    # Check FTP daemon

# 3. Test ARPANET interface
@INFORMATION NET           # Network status
@SHOW CONFIGURATION        # System configuration
```

**Success criteria**:
- ✅ TOPS-20 boots from disk (not tape)
- ✅ Login prompt appears
- ✅ User accounts functional
- ✅ FTP daemon running
- ✅ ARPANET interface configured

### Troubleshooting

**Problem**: Installation tape won't boot
- Check SIMH config: `cat arpanet/configs/phase2/pdp10.ini`
- Verify tape file exists: `docker exec arpanet-pdp10 ls -lh /machines/pdp10/tops20_v41.tap`
- Check SIMH logs: `docker logs arpanet-pdp10`

**Problem**: Disk initialization fails
- Ensure disk file exists: `docker exec arpanet-pdp10 ls -lh /machines/data/tops20.dsk`
- Check disk size (should be large enough for TOPS-20)
- Verify RPA0 configuration in SIMH

**Problem**: Network interface not working
- Check IMP #2 logs: `docker logs arpanet-imp2 | grep HI1`
- Verify UDP connectivity: `docker network inspect arpanet-build`
- Review SIMH IMP attachment: `attach -u imp 2000:172.20.0.30:2000`

---

## Phase 3.2: 4-Container Routing Validation

**Prerequisite**: TOPS-20 installation complete

### Testing 4-Container Routing

Create an extended test script based on `test_phase2.py`:

```bash
# Run Python test script
python arpanet/scripts/test_phase2.py

# Manual validation commands
docker logs arpanet-vax | grep -i network
docker logs arpanet-imp1 | grep -E "HI1|MI1" | tail -20
docker logs arpanet-imp2 | grep -E "HI1|MI1" | tail -20
docker logs arpanet-pdp10 | grep -i network

# Network statistics
docker stats --no-stream arpanet-vax arpanet-imp1 arpanet-imp2 arpanet-pdp10
```

### Expected Results

```
VAX (172.20.0.10):
- HI1 interface to IMP #1 active
- Network stack initialized
- Minimal activity (idle)

IMP #1 (172.20.0.20):
- HI1 to VAX: Active host interface
- MI1 to IMP #2: Active modem link
- Routing VAX ↔ Network

IMP #2 (172.20.0.30):
- MI1 to IMP #1: Active modem link
- HI1 to PDP-10: Active host interface
- Routing Network ↔ PDP-10

PDP-10 (172.20.0.40):
- IMP interface: Connected to IMP #2
- TOPS-20 network stack: Active
- FTP daemon: Listening
```

**Success criteria**:
- ✅ All 4 containers stable (no crash loops)
- ✅ Packet flow visible through both IMPs
- ✅ PDP-10 receives ARPANET protocol messages
- ✅ No routing loops or errors

---

## Phase 3.3: FTP File Transfer (VAX ↔ PDP-10)

**Prerequisite**: 4-container routing validated, FTP daemon running on PDP-10

### Approach: SIMH Native Automation

Based on lessons learned from console automation, use **SIMH's native commands** instead of expect+telnet for 99% reliability.

#### Create FTP Transfer Script

```ini
; arpanet/scripts/simh-automation/ftp-test-vax-pdp10.ini
; Tests file transfer from VAX to PDP-10 via ARPANET FTP

; Boot VAX with custom script
set console telnet=2323
set xu enable
attach xu 172.20.0.10

; Network configuration
SEND "\n"
EXPECT "login:"
SEND "root\n"
EXPECT "#"
SEND "/etc/ifconfig de0 172.20.0.10 netmask 255.255.0.0 up\n"
EXPECT "#"

; Create test file
SEND "echo 'Hello from VAX via ARPANET!' > /tmp/test.txt\n"
EXPECT "#"

; FTP to PDP-10
SEND "ftp 172.20.0.40\n"
EXPECT "Name"
SEND "anonymous\n"
EXPECT "ftp>"
SEND "put /tmp/test.txt\n"
EXPECT "Transfer complete"
SEND "bye\n"
EXPECT "#"

; Report success
SEND "echo 'FTP transfer complete'\n"
GO UNTIL "FTP transfer complete"
EXIT
```

#### Run FTP Test

```bash
# Copy script to container
docker cp arpanet/scripts/simh-automation/ftp-test-vax-pdp10.ini arpanet-vax:/tmp/

# Execute with SIMH
docker exec arpanet-vax /usr/bin/simh-vax /tmp/ftp-test-vax-pdp10.ini

# Verify on PDP-10
telnet localhost 2326
@LOGIN OPERATOR
@DIR
# Should see test.txt
```

### Success Criteria

- ✅ FTP connection established VAX → PDP-10
- ✅ File transfer completes successfully
- ✅ File integrity verified on PDP-10
- ✅ Transfer logged by ARPANET logging system
- ✅ 99%+ success rate (like authentic-ftp achieved)

### Extended Testing

**Bidirectional transfer**:
```bash
# VAX → PDP-10
ftp 172.20.0.40
put bradman
put brad.1

# PDP-10 → VAX
ftp 172.20.0.10
get report.txt
```

**Large files**:
- Test with ~1MB file (bradman binary)
- Verify no corruption
- Measure transfer rate

**Multiple files**:
- Batch transfer
- Directory transfer (if supported)

---

## Phase 3.4: Build Pipeline Integration

**Prerequisite**: FTP transfer working reliably

### Implementation Plan

#### 1. Extend VaxStage for ARPANET

Create `resume_generator/vax_arpanet_stage.py`:

```python
"""VAX stage with ARPANET integration."""

from resume_generator.vax_stage import VaxStage

class VaxArpanetStage(VaxStage):
    """VAX stage that uses ARPANET for artifact distribution."""

    def run(self):
        """Run VAX build with ARPANET transfer."""
        # Existing VAX workflow
        super().run()

        # ARPANET transfer workflow
        self._start_arpanet_network()
        self._transfer_to_pdp10()
        self._verify_on_pdp10()
        self._collect_arpanet_logs()

    def _start_arpanet_network(self):
        """Start Phase 2 ARPANET containers."""
        # docker compose -f docker-compose.arpanet.phase2.yml up -d
        pass

    def _transfer_to_pdp10(self):
        """Transfer artifacts via ARPANET FTP."""
        # Use SIMH automation script
        # arpanet/scripts/simh-automation/build-ftp-transfer.ini
        pass

    def _verify_on_pdp10(self):
        """Verify files arrived on PDP-10."""
        # Telnet to PDP-10, check file sizes, checksums
        pass

    def _collect_arpanet_logs(self):
        """Collect ARPANET transfer logs."""
        # Use arpanet_logging system
        # Copy to site/arpanet-transfer.log
        pass
```

#### 2. Create Build FTP Script

```ini
; arpanet/scripts/simh-automation/build-ftp-transfer.ini
; Transfers bradman and brad.1 from VAX to PDP-10

; [Similar to ftp-test but with actual build artifacts]
; - Connect to FTP
; - Transfer bradman binary
; - Transfer brad.1 manpage
; - Get verification report
; - Exit with status
```

#### 3. Update CLI

```python
# resume_generator/cli.py

@click.option('--with-arpanet', is_flag=True, help='Use ARPANET for transfers')
def build(with_arpanet: bool):
    if with_arpanet:
        stage = VaxArpanetStage(...)
    else:
        stage = VaxStage(...)
    stage.run()
```

#### 4. Update Makefile

```makefile
.PHONY: build-arpanet
build-arpanet:
    .venv/bin/resume-gen build --with-arpanet --vax-mode docker

.PHONY: publish-arpanet
publish-arpanet: build-arpanet
    # Deploy site/ to GitHub Pages
```

### Success Criteria

- ✅ Single command builds with ARPANET: `make build-arpanet`
- ✅ Artifacts transferred via authentic 1970s ARPANET
- ✅ Build includes ARPANET transfer logs
- ✅ Landing page displays network activity
- ✅ Build fails gracefully if ARPANET unavailable

---

## Testing Strategy

### Unit Tests

```python
# tests/test_vax_arpanet_stage.py

def test_arpanet_stage_starts_network():
    """Test ARPANET network startup."""
    pass

def test_arpanet_transfer_detects_failures():
    """Test FTP failure detection."""
    pass

def test_arpanet_logs_collected():
    """Test log collection from all components."""
    pass
```

### Integration Tests

```bash
# End-to-end test
make clean
make build-arpanet
ls -lh site/arpanet-transfer.log
grep "Transfer complete" site/arpanet-transfer.log
```

### Validation Checklist

Before marking Phase 3 complete:

- [ ] TOPS-20 installed and stable
- [ ] 4-container routing validated
- [ ] FTP transfers working (99%+ success)
- [ ] Build pipeline integration complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Landing page includes ARPANET section
- [ ] GitHub Actions workflow updated (if applicable)

---

## Timeline Estimate

| Task | Duration | Dependencies |
|------|----------|--------------|
| TOPS-20 Installation | 1-2 hours | AWS instance |
| 4-Container Routing | 1 hour | TOPS-20 complete |
| FTP Transfer Testing | 2-3 hours | Routing validated |
| SIMH Automation Scripts | 3-4 hours | FTP working |
| Build Pipeline Integration | 1-2 days | FTP reliable |
| Testing & Documentation | 1-2 days | Integration complete |
| **Total** | **2-4 weeks** | Includes debugging time |

**Critical path**: TOPS-20 installation is blocking everything else

---

## Next Session Checklist

**Before starting Phase 3 implementation:**

1. ✅ Review this plan
2. ✅ Provision AWS EC2 x86_64 instance
3. ✅ Sync latest code: `git pull`
4. ✅ Install dependencies in venv
5. ✅ Verify topology generation works: `arpanet-topology phase2`
6. ✅ Read TOPS-20 documentation (at least skim installation guide)
7. ✅ Set aside 2-3 hours for uninterrupted TOPS-20 installation
8. ✅ Prepare to take installation notes (screen capture recommended)

**First commands to run:**

```bash
# On AWS EC2
ssh ubuntu@<instance-ip>
cd ~/brfid.github.io
git pull

# Verify topology generation
source .venv/bin/activate
arpanet-topology phase2

# Build and start Phase 2
docker compose -f docker-compose.arpanet.phase2.yml build pdp10
docker compose -f docker-compose.arpanet.phase2.yml up -d
docker compose -f docker-compose.arpanet.phase2.yml ps

# Connect to PDP-10 and BEGIN INSTALLATION
telnet localhost 2326
```

**Remember**: Take detailed notes during TOPS-20 installation. This is a one-time process and the disk image will be preserved, but documentation helps troubleshooting and future reference.

---

**Status**: Plan complete, ready to execute
**Blocker**: TOPS-20 installation (manual process)
**Confidence**: High (clear path, proven infrastructure)

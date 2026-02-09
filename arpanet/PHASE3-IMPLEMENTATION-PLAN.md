# Phase 3 Implementation Plan: PDP-10 Integration & Build Pipeline

**Created**: 2026-02-08
**Status**: Ready to execute
**Blocker**: PDP-10 ITS runtime restart-loop (boot-time failure at `boot rpa0`)
**Platform**: AWS EC2 x86_64 (required for SIMH compatibility)

---

## Executive Summary

Phase 3 completes the ARPANET build integration by:
1. Stabilizing PDP-10 ITS runtime (container stays `Up`)
2. Validating 4-container routing (VAX → IMP1 → IMP2 → PDP-10)
3. Implementing FTP file transfer between VAX and PDP-10
4. Integrating ARPANET into resume build pipeline

**Estimated Timeline**: 2-4 weeks
**Critical Path**: SIMH capability/config reconciliation (`pdp10-ks` + `pdp10.ini`)

---

## Phase 3.0: PDP-10 ITS Runtime Stabilization (NEW immediate priority)

### Why this is first

Recent AWS validation confirms ITS image build completes, and the initial simulator capability mismatches were fixed (`RPA` device family, no unsupported `2048k` CPU setting). The container still restart-loops, but failure has moved to boot-time:

- `./pdp10.ini-52> boot rpa0`
- `Internal error, PC: 000100`

This indicates command-level compatibility is reconciled; current work is now focused on disk/runtime state at boot.

### Stabilization workflow

1. **Interrogate SIMH in the runtime image (without startup ini):**

```bash
docker compose -f docker-compose.arpanet.phase2.yml run --rm \
  --entrypoint /bin/sh pdp10 -lc "printf 'show version\nshow cpu\nshow devices\nhelp set cpu\nshow rp\nshow rpa\nquit\n' | /usr/local/bin/pdp10-ks -q"
```

Capture and save:
- `show version`
- disk device family names (`RP` vs `RPA` or other)
- accepted `set cpu` parameter syntax

2. **Reconcile `arpanet/configs/phase2/pdp10.ini` with observed capabilities:**
   - Start from minimal safe defaults:
     - keep `set cpu its`
     - disable `set cpu 2048k` unless explicitly accepted by this binary
     - explicitly enable disk controller/unit before attach (`set rp enable`, `set rp0 enable`)
   - If simulator exposes `RPA*` instead of `RP*`, rename disk commands accordingly.

3. **Re-test cleanly:**

```bash
docker compose -f docker-compose.arpanet.phase2.yml build pdp10
docker compose -f docker-compose.arpanet.phase2.yml down -v
docker compose -f docker-compose.arpanet.phase2.yml up -d --force-recreate vax imp1 pdp10 imp2
docker compose -f docker-compose.arpanet.phase2.yml ps
docker logs arpanet-pdp10 --tail 260
```

Success = boot proceeds past `boot rpa0` without internal error and `arpanet-pdp10` remains `Up`.

4. **If still failing, run ini interactively line-by-line:**

```bash
docker compose -f docker-compose.arpanet.phase2.yml run --rm \
  --entrypoint /usr/local/bin/pdp10-ks pdp10 -q
```

Then at `sim>`:
```text
do /machines/pdp10.ini
```

Fix first failing line, repeat until `do` completes and boot command succeeds.

---

## Phase 3.1: PDP-10 Runtime Validation (post-stabilization)

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

#### Step 3: Check container health first

```bash
docker compose -f docker-compose.arpanet.phase2.yml ps
docker logs arpanet-pdp10 --tail 220
```

Expected: `arpanet-pdp10` shows `Up` (not `Restarting`).

#### Step 4: Connect to PDP-10 Console

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

#### Step 5: ITS runtime verification

At this phase the objective is stable ITS boot/runtime, not TOPS-20 installation.

Verify:
1. SIMH starts without `RP0`/CPU parameter hard errors (already achieved)
2. ITS boot path proceeds from disk
3. DZ and console ports remain available (`2326`, `10004`)
4. IMP attach remains active to `172.20.0.30:2000`

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

#### Step 6: Post-stabilization validation

After runtime stabilization completes and ITS is running:

```bash
# 1. Verify system boots successfully
docker restart arpanet-pdp10
sleep 30
telnet localhost 2326

# 2. Login and check services
# Continue with ITS-specific service and network checks used in Phase 3 tests
```

**Success criteria**:
- ✅ TOPS-20 boots from disk (not tape)
- ✅ Login prompt appears
- ✅ User accounts functional
- ✅ FTP daemon running
- ✅ ARPANET interface configured

### Troubleshooting (runtime mismatch class)

**Problem**: `%SIM-ERROR: CPU device: Non-existent parameter - 2048K`
- Remove/comment `set cpu 2048k`
- Re-run `help set cpu` interactively to discover accepted syntax

**Problem**: `%SIM-ERROR: No such Unit: RP0` / `Non-existent device: RP0`
- Validate device names via `show devices`
- If `RP` exists, explicitly enable before attach (`set rp enable`, `set rp0 enable`)
- If only `RPA*` exists, update ini to `rpa` naming consistently

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
- [ ] ITS runtime stable (no restart-loop)
- [ ] `pdp10.ini` reconciled to simulator capability set
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
| ITS runtime stabilization | 1-3 hours | AWS instance |
| 4-Container Routing | 1 hour | TOPS-20 complete |
| FTP Transfer Testing | 2-3 hours | Routing validated |
| SIMH Automation Scripts | 3-4 hours | FTP working |
| Build Pipeline Integration | 1-2 days | FTP reliable |
| Testing & Documentation | 1-2 days | Integration complete |
| **Total** | **2-4 weeks** | Includes debugging time |

**Critical path**: PDP-10 runtime stabilization is blocking everything else

---

## Next Session Checklist

**Before starting Phase 3 implementation:**

1. ✅ Review this plan
2. ✅ Provision AWS EC2 x86_64 instance
3. ✅ Sync latest code: `git pull`
4. ✅ Install dependencies in venv
5. ✅ Verify topology generation works: `arpanet-topology phase2`
6. ✅ Run simulator capability interrogation (`show version`, `show devices`, `help set cpu`)
7. ✅ Set aside 2-3 hours for stabilization/retest loop
8. ✅ Capture logs and exact failing ini lines for iteration

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

# Verify runtime health first
docker compose -f docker-compose.arpanet.phase2.yml ps
docker logs arpanet-pdp10 --tail 220
```

**Remember**: Capture simulator capability output (`show version/devices`) and keep it with session notes. It is the fastest way to align `pdp10.ini` with the actual binary.

---

**Status**: Plan complete, ready to execute
**Blocker**: PDP-10 ITS runtime boot failure (`boot rpa0` → `Internal error, PC: 000100`)
**Confidence**: High (clear path, proven infrastructure)

# ARPANET Integration - Next Steps

**Date**: 2026-02-10
**Status**: Protocol mismatch identified; IMP path retired; pivoting to Chaosnet (CH11) for PDP-10 networking

---

## Recent Achievement: Console Automation ✅

The console automation problem has been **completely solved**:

- **Problem**: External telnet automation unreliable (10% success rate)
- **Solution**: SIMH native automation commands (99% success rate)
- **Status**: Production-ready, 100% historical fidelity maintained

See [CONSOLE-AUTOMATION-SOLUTION.md](../research/CONSOLE-AUTOMATION-SOLUTION.md) for complete details.

---

## Immediate Next Steps (High Priority)

### 0. Protocol Mismatch Resolution — Chaosnet Pivot (Critical)

**Goal**: Transition PDP-10 networking from failed IMP/1822 path to authentic Chaosnet (CH11) path.

**Root cause identified (2026-02-10)**:
- SIMH `pdp10-ks` "IMP" device is **not** an ARPANET 1822 interface
- It is a **modern Ethernet/IP NIC** with MAC addresses, ARP, DHCP/IP/gateway config
- Packet captures show Ethernet frames (`0806 0001 0800 0604` = ARP headers), not 1822 messages
- "Bad magic" values (`feffffff`, `00000219`, `ffffffff`) were Ethernet frame headers misinterpreted by IMP2's HI1 1822 parser
- The `hi1shim` adapter solved envelope syntax but the **payload is still Ethernet, not 1822**
- IMP2 cannot route Ethernet frames through ARPANET routing tables
- **Consequence**: TCP/IP FTP to `172.20.0.40:21` will never work (ITS uses NCP, not TCP/IP; ARPANET uses host/IMP numbers, not IP addresses)

**Decision**: Proceed with Chaosnet (CH11) for PDP-10 networking
- CH11 is natively supported by SIMH KS10 emulator
- ITS has Chaosnet drivers and CFTP (Chaosnet FTP) built-in
- **More historically authentic**: MIT ITS used Chaosnet for inter-machine communication, not ARPANET
- Simpler than protocol translation; eliminates semantic mismatch

**Retired components (for PDP-10 path)**:
- ❌ `hi1shim` (Host-IMP Interface adapter) — syntactic-only fix; semantic dead-end
- ❌ PDP-10 IMP configuration — fundamentally incompatible protocol family
- ❌ IMP2 HI1 → PDP-10 host-link — cannot route Ethernet through 1822 IMP
- ❌ Dual-window HI1 gate tests for PDP-10 — validated wrong layer
- ❌ FTP to `172.20.0.40:21` — wrong protocol (use CFTP instead)

**Preserved infrastructure**:
- ✅ VAX + IMP1 + IMP2 ARPANET routing — fully operational and validated
- ✅ ARPANET 1822 protocol — works correctly for VAX ↔ IMP path
- ✅ Logging and monitoring systems — applicable to both protocols
- ✅ Console automation — applies to all SIMH systems

**Implementation tasks (command-first)**:
```bash
# 1) Verify CH11 device availability in current pdp10-ks build
docker exec arpanet-pdp10 pdp10-ks --help | grep -i "ch\|chaos"
# Or at SIMH prompt: show devices

# 2) Update arpanet/configs/phase2/pdp10.ini to enable CH11
# Add:
#   set ch enabled
#   attach ch listen:4001
# Remove or comment out IMP configuration

# 3) Create Chaosnet bridge/peer container (second ITS instance for testing)
# Update docker-compose.arpanet.phase2.yml with pdp10-peer service
# Create arpanet/configs/phase2/pdp10-peer.ini with:
#   set ch enabled
#   attach ch connect:172.20.0.40:4001

# 4) Rebuild and boot
docker compose -f docker-compose.arpanet.phase2.yml build pdp10
docker compose -f docker-compose.arpanet.phase2.yml up -d

# 5) Verify Chaosnet interface comes up at ITS console
telnet localhost 2326
# At ITS prompt:
:SYSTAT   # System status
:HOSTAT   # Host status - should show Chaosnet hosts

# 6) Test CFTP file transfer between ITS instances
# At primary ITS:
:CFTP target-host
:GET remote-file local-file
:PUT local-file remote-file
```

**Success criteria**:
- [ ] CH11 device verified available in SIMH build
- [ ] Chaosnet interface comes up in ITS (visible in `:SYSTAT` or `:HOSTAT`)
- [ ] Chaosnet connectivity established between two ITS instances
- [ ] CFTP file transfer succeeds
- [ ] VAX + IMP1 + IMP2 infrastructure remains operational (no regression)

**Reference**:
- Handoff document: `docs/arpanet/handoffs/LLM-CHAOSNET-PIVOT-2026-02-10.md`
- MIT AI Memo 628: Chaosnet protocol specification
- SIMH CH11 documentation: `set ch enabled`, `attach ch listen:PORT` / `attach ch connect:HOST:PORT`

---

### 1. Chaosnet File Transfer Validation (Next milestone)

**Goal**: Validate end-to-end file transfer using Chaosnet CFTP between ITS instances.

**Prerequisites**:
- [x] CH11 device verified available
- [ ] Chaosnet interface configured and operational
- [ ] Second ITS instance or bridge configured

**Tasks**:
```bash
# 1) Verify both ITS instances have Chaosnet up
docker logs arpanet-pdp10 --tail 100 | grep -i "ch\|chaos"
docker logs arpanet-pdp10-peer --tail 100 | grep -i "ch\|chaos"

# 2) Connect to primary ITS console
telnet localhost 2326

# 3) At ITS prompt, verify Chaosnet status
:SYSTAT   # Check system status
:HOSTAT   # Check host status - should show Chaosnet hosts

# 4) Test CFTP file transfer
:CFTP target-host
:LIST     # List available files on remote
:GET remote-file local-file
# Verify file received

# 5) Reverse direction test
# From peer instance, connect and transfer back
:PUT local-file remote-file

# 6) Verify file integrity
# Compare checksums or file contents on both sides
```

**Success criteria**:
- [ ] Both ITS instances show Chaosnet interface operational
- [ ] `:HOSTAT` shows peer host visible on Chaosnet
- [ ] CFTP connection established successfully
- [ ] File transfers in both directions (GET and PUT)
- [ ] File integrity maintained (checksums match)
- [ ] Transfer logs captured for documentation

**Blockers**: None - CH11 verification complete (or in progress)

---

### 2. Test SIMH Automation Scripts (15 minutes)

**Goal**: Validate the new automation scripts work in current setup

**Tasks**:
```bash
# Start VAX container
docker-compose -f docker-compose.arpanet.phase1.yml up -d vax

# Test basic login automation
docker exec arpanet-vax /usr/bin/simh-vax \
  /machines/data/simh-automation/test-login.ini

# Test FTP automation
docker exec arpanet-vax /usr/bin/simh-vax \
  /machines/data/simh-automation/authentic-ftp-transfer.ini

# Verify file transferred successfully
docker exec arpanet-vax ls -l /tmp/uploaded.txt
```

**Success Criteria**:
- [ ] test-login.ini completes successfully
- [ ] authentic-ftp-transfer.ini transfers file
- [ ] File integrity verified (diff shows identical)
- [ ] Scripts run reliably (3/3 successful runs)

**Blockers**: None - all prerequisites met

---

### 3. Create Build Artifact Transfer Script (30 minutes)

**Goal**: Create production script for transferring build artifacts via ARPANET FTP

**Create**: `scripts/simh-automation/build-artifact-transfer.ini`

**Template**:
```ini
; Build Artifact Transfer via ARPANET FTP
; Transfers compiled artifacts using BSD 4.3 FTP (1986)

set cpu 64m
set cpu idle
attach dz 2323
attach xu eth0
set xu mac=08:00:2b:aa:bb:cc
boot cpu

; Login
go until "login:"
send delay=1000 "root\r"
go until "#"

; Transfer artifact via FTP
send "ftp localhost\r"
go until "Name"
send "operator\r"
go until "Password:"
send "test123\r"
go until "230"

send "binary\r"
go until "ftp>"

; Upload build artifact (parameterize this path)
send "put /machines/data/resume.pdf /tmp/resume-via-arpanet.pdf\r"
go until "226"

send "quit\r"
go until "#"

; Verify transfer
send "ls -l /tmp/resume-via-arpanet.pdf\r"
go until "#"

send "exit\r"
exit
```

**Success Criteria**:
- [ ] Script transfers arbitrary file
- [ ] File integrity verified (MD5/diff)
- [ ] Works with different file types (PDF, binary, text)
- [ ] Error handling for missing source file

**Next**: Integrate into GitHub Actions workflow

---

### 4. Update Docker Compose for Automation (15 minutes)

**Goal**: Make SIMH automation scripts easily accessible in containers

**Update**: `docker-compose.arpanet.phase1.yml`

```yaml
vax:
  build:
    context: ./vax
    dockerfile: Dockerfile
  ports:
    - "2323:2323"  # Console (for debugging)
    - "21:21"      # FTP
  volumes:
    - ./build/vax:/machines/data
    - ./arpanet/scripts/simh-automation:/machines/automation:ro
  networks:
    - arpanet-build
  # Default: interactive mode
  command: ["/usr/bin/simh-vax", "/machines/vax780.ini"]

  # For automated runs, override with:
  # command: ["/usr/bin/simh-vax", "/machines/automation/authentic-ftp-transfer.ini"]
```

**Test**:
```bash
# Interactive mode (default)
docker-compose -f docker-compose.arpanet.phase1.yml up -d

# Automated mode (override)
docker-compose -f docker-compose.arpanet.phase1.yml run vax \
  /usr/bin/simh-vax /machines/automation/test-login.ini
```

**Success Criteria**:
- [ ] Scripts accessible at `/machines/automation/`
- [ ] Both interactive and automated modes work
- [ ] No need to copy scripts into container

---

## Short-Term Goals (1-2 hours)

### 4. PDP-10 Chaosnet Runtime Validation

**Status**: ITS image build complete, Chaosnet configuration pending

**Goal**: Confirm stable ITS boot/runtime on PDP-10 container with Chaosnet networking

**Tasks**:
1. Update PDP-10 config to use CH11 instead of IMP
2. Boot PDP-10 container and verify stable runtime
3. Confirm Chaosnet interface attachment (CH11 device)
4. Validate Chaosnet service reachability for file transfer tests

**Success Criteria**:
- [ ] ITS boots to prompt with stable runtime
- [ ] CH11 interface configured and attached
- [ ] `:SYSTAT` shows Chaosnet operational
- [ ] `:HOSTAT` shows peer hosts (when peer configured)
- [ ] Can transfer file to/from PDP-10 via CFTP

**Blockers**: None - configuration changes only

**Reference**: Chaosnet pivot handoff (`docs/arpanet/handoffs/LLM-CHAOSNET-PIVOT-2026-02-10.md`)

---

### 5. Multi-Protocol Network Topology (Task #25)

**Goal**: Validate dual-protocol architecture: VAX on ARPANET + PDP-10 on Chaosnet

**Updated Architecture**:
```
ARPANET Side:
  [VAX/BSD 4.3] ↔ [IMP #1] ↔ [IMP #2]
  (1822 protocol, DEC/BSD authentic networking)

Chaosnet Side:
  [PDP-10/ITS] ↔ [PDP-10/ITS peer or bridge]
  (Chaosnet protocol, MIT ITS authentic networking)
```

**Historical Authenticity**: This topology is **more historically accurate** than the original plan:
- MIT ITS machines used Chaosnet for local inter-machine communication
- ARPANET was used for gateway/remote access, not local file transfer
- VAX on ARPANET demonstrates authentic DEC/BSD networking
- PDP-10 on Chaosnet demonstrates authentic MIT ITS networking

**Prerequisites**:
- [x] 2-container ARPANET routing validated (VAX → IMP1)
- [x] 3-container ARPANET routing validated (VAX → IMP1 → IMP2)
- [ ] PDP-10 Chaosnet configuration complete
- [ ] Chaosnet peer or bridge operational

**Test Script**: Update validation scripts to cover both protocols

**Success Criteria**:
- [ ] ARPANET path operational: VAX → IMP1 → IMP2
- [ ] All ARPANET interfaces show activity (HI1 at VAX, MI1 between IMPs)
- [ ] Chaosnet path operational: PDP-10 ↔ peer via CH11
- [ ] Both protocols stable simultaneously (no interference)
- [ ] Logging captures both network activities independently

**Estimated Time**: 30 minutes (after Chaosnet ready)

**Note**: Originally planned as "4-container routing test"; now correctly understood as dual-protocol demonstration rather than single unified network.

---

### 6. Cross-Protocol File Transfer (Task #26)

**Goal**: Transfer files between VAX (ARPANET) and PDP-10 (Chaosnet) networks

**Approach Options**:

**Option A: Gateway Bridge** (if needed for unified pipeline):
- Create ARPANET↔Chaosnet gateway container
- Routes between protocol families
- More complex but allows direct VAX↔PDP-10 transfer

**Option B: Separate Demonstrations** (simpler, recommended initially):
- VAX demonstrates ARPANET FTP (VAX↔VAX or VAX↔IMP)
- PDP-10 demonstrates Chaosnet CFTP (ITS↔ITS)
- Both showcased as parallel authentic historical networking examples

**Prerequisites**:
- [ ] PDP-10 Chaosnet operational
- [ ] VAX ARPANET path validated
- [ ] If Option A: Gateway bridge designed and implemented

**Test Sequence (Option B)**:
1. **ARPANET demonstration**:
   - Transfer file on VAX via BSD FTP
   - Use existing authentic FTP automation
   - Document ARPANET protocol logs

2. **Chaosnet demonstration**:
   - Transfer file between ITS instances via CFTP
   - Document Chaosnet protocol activity
   - Capture ITS console session

3. **Integration narrative**:
   - "Resume built using two authentic 1980s networks"
   - VAX: compilation and ARPANET transfer showcase
   - PDP-10: ITS environment and Chaosnet showcase

**Success Criteria (Option B)**:
- [ ] VAX ARPANET transfer validated independently
- [ ] PDP-10 Chaosnet transfer validated independently
- [ ] Both protocol logs captured
- [ ] File integrity maintained in both demonstrations
- [ ] 100% historical authenticity for each protocol

**Automation**: 
- ARPANET: Use existing `scripts/simh-automation/authentic-ftp-transfer.ini`
- Chaosnet: Create `scripts/simh-automation/its-cftp-transfer.ini`

**Estimated Time**: 1-2 hours for Option B; 4-6 hours for Option A gateway

---

## Medium-Term Goals (1 week)

### 7. Build Pipeline Integration (Task #28)

**Goal**: Integrate ARPANET file transfer into GitHub Actions build pipeline

**Architecture**:
```
GitHub Actions Workflow
├─ Build Stage (modern tools)
│  └─ Compile resume, generate PDF
│
├─ ARPANET Transfer Stage ⭐
│  ├─ Start ARPANET containers (VAX, IMPs, PDP-10)
│  ├─ Transfer artifact via authentic BSD FTP (1986)
│  ├─ Capture ARPANET protocol logs
│  └─ Verify transfer integrity
│
└─ Publish Stage
   └─ Deploy to GitHub Pages
```

**Implementation**:
1. Create GitHub Actions workflow file
2. Add ARPANET startup steps
3. Integrate SIMH automation scripts
4. Add log collection and artifact validation
5. Clean up containers after transfer

**Success Criteria**:
- [ ] Build runs automatically on push
- [ ] ARPANET containers start successfully
- [ ] File transfers via authentic FTP
- [ ] Logs captured and saved as artifacts
- [ ] Build completes in <5 minutes
- [ ] Pipeline is reliable (>95% success rate)

**Estimated Time**: 2-3 hours

---

### 8. Landing Page Integration (Task #29)

**Goal**: Display ARPANET transfer status on project landing page

**Features**:
- Show "Built via ARPANET" badge
- Display recent build logs
- Show ARPANET topology diagram
- Link to protocol analysis
- Historical context (1970s technology)

**Implementation**:
1. Design badge/indicator
2. Create log viewer component
3. Add topology visualization
4. Write historical context section
5. Link to technical documentation

**Estimated Time**: 2 hours

---

### 9. Documentation Completion (Task #30)

**Goal**: Complete Phase 3 documentation

**Documents to Create/Update**:
- [ ] PHASE3-COMPLETION.md - Final validation report
- [ ] BUILD-PIPELINE.md - Complete pipeline documentation
- [ ] HISTORICAL-FIDELITY.md - Authenticity analysis
- [ ] LESSONS-LEARNED.md - Technical insights

**Success Criteria**:
- [ ] All phases fully documented
- [ ] Build pipeline documented end-to-end
- [ ] Historical authenticity explained
- [ ] Future maintainers can understand system

**Estimated Time**: 2-3 hours

---

## Long-Term Improvements (Optional)

### Advanced FTP Features

**Goal**: Enhance FTP automation with production features

**Features**:
- Retry logic for failed transfers
- Progress monitoring
- Multiple file transfers
- Directory operations
- Resumable transfers (if supported)

**Estimated Time**: 2-3 hours

---

### Multi-Host Testing

**Goal**: Test with additional ARPANET hosts

**Options**:
- Add PDP-11 running BSD 2.9
- Add another VAX node
- Test multi-path routing
- Simulate network partitions

**Estimated Time**: 4-6 hours

---

### Performance Optimization

**Goal**: Improve build pipeline speed

**Optimizations**:
- Pre-warmed containers
- Cached SIMH states
- Parallel operations
- Incremental builds

**Estimated Time**: 3-4 hours

---

## Implementation Timeline

### Week 1: Chaosnet Pivot (Current)
- [x] Console automation solved
- [x] SIMH scripts created
- [x] Protocol mismatch identified and documented
- [ ] CH11 device verification (15 min)
- [ ] Update PDP-10 config for Chaosnet (30 min)
- [ ] Create Chaosnet peer/bridge (1 hour)
- [ ] Verify Chaosnet interface operational (30 min)

### Week 2: Chaosnet Integration
- [ ] Test CFTP file transfer (1 hour)
- [ ] Validate dual-protocol topology (30 min)
- [ ] Document Chaosnet configuration (1 hour)
- [ ] Create ITS CFTP automation scripts (1 hour)

### Week 3: Build Pipeline
- [ ] GitHub Actions workflow (2-3 hours)
- [ ] Integrate both ARPANET and Chaosnet demonstrations (2 hours)
- [ ] Landing page integration (2 hours)
- [ ] Documentation completion (2-3 hours)

**Total Estimated Time**: 12-16 hours

**Note**: Timeline adjusted for Chaosnet pivot; overall duration similar to original plan but with cleaner architecture and better historical authenticity.

---

## Success Metrics

### Technical Metrics
- [ ] Console automation: >95% success rate (ACHIEVED: 99%)
- [ ] FTP transfers: 100% file integrity
- [ ] Build pipeline: >95% success rate
- [ ] Full pipeline execution: <5 minutes
- [ ] Historical fidelity: 100% (authentic 1986 software)

### Documentation Metrics
- [ ] All phases documented
- [ ] All scripts have usage guides
- [ ] Build pipeline fully explained
- [ ] Historical context provided
- [ ] Troubleshooting guides complete

### Project Metrics
- [ ] "Quiet technical signal" achieved
- [ ] Demonstrates historical computing expertise
- [ ] Functional build pipeline
- [ ] Maintainable for future updates

---

## Blockers and Dependencies

**Current Blockers**:
1. **CH11/Chaosnet feasibility verification** (CRITICAL)
   - Status: Pending verification that CH11 device is available in current pdp10-ks build
   - Impact: Blocks all Chaosnet implementation work
   - Mitigation: Check early with `docker exec arpanet-pdp10 pdp10-ks --help` or `show devices`
   - Fallback: Use different ITS build or keep ARPANET-only demonstration

**Retired Blockers** (no longer active):
1. **PDP-10 ↔ IMP2 Host-Link Framing Mismatch** (RESOLVED/RETIRED as of 2026-02-10)
   - Root cause: Fundamental protocol incompatibility (Ethernet vs 1822)
   - Not a configuration issue; protocol families are incompatible
   - Resolution: Pivot to Chaosnet (CH11) for PDP-10 networking
   - Historical: See `docs/arpanet/handoffs/LLM-HOST-LINK-BLOCKER-2026-02-09.md`

2. **PDP-10 FTP endpoint readiness** (RESOLVED/RETIRED as of 2026-02-10)
   - Root cause: TCP/IP FTP incompatible with ITS NCP network stack
   - Resolution: Use Chaosnet CFTP instead
   - Historical: See `docs/arpanet/handoffs/LLM-PDP10-FTP-BLOCKER-2026-02-10.md`

**No Longer Applicable**:
- hi1shim operational risk — retired; shim removed from PDP-10 path
- IMP bad-magic regression monitoring — only applies to VAX path now
- PDP-10 service bring-up for TCP:21 — wrong protocol; using Chaosnet instead

### Dependencies
1. **Chaosnet configuration** blocks:
   - Chaosnet file transfer validation (Section 1)
   - PDP-10 runtime validation (Section 4)
   - Multi-protocol topology (Section 5)
   - Cross-protocol file transfer (Section 6)

2. **Multi-protocol topology working** blocks:
   - Build pipeline integration (#28)

3. **Build pipeline working** blocks:
   - Landing page integration (#29)

### Risk Mitigation

**Risk**: CH11 not available in current build
**Mitigation**: 
- Verify early (first task in Section 0)
- Fallback to VAX ARPANET-only demonstration if needed
- Alternative: Use different ITS build with CH11 support

**Risk**: Chaosnet configuration unfamiliar
**Mitigation**: 
- Well-documented in ITS manuals and MIT AI Memos
- Simpler than ARPANET 1822 protocol
- Community resources available (SIMH forums, ITS documentation)

**Risk**: Two protocols more complex to maintain
**Mitigation**: 
- Protocols are independent; no coupling
- Each is authentic and self-contained
- Simpler than protocol translation layer
- Can demonstrate ARPANET first, add Chaosnet later

**Risk**: GitHub Actions timing issues
**Mitigation**: Use SIMH automation (proven 99% reliable) for both protocols

---

## Resources

### Documentation
- [CONSOLE-AUTOMATION-SOLUTION.md](../research/CONSOLE-AUTOMATION-SOLUTION.md) - Complete solution
- [scripts/simh-automation/README.md](../operations/SIMH-AUTOMATION-README.md) - Usage guide
- [PHASE3-PLAN.md](../overview/PHASE3-PLAN.md) - Original phase 3 plan
- Refactoring plan document (historical note in this section; no active local path currently tracked)

### Tools
- SIMH automation commands (SEND, EXPECT, GO UNTIL)
- Docker Compose orchestration
- Python logging infrastructure
- GitHub Actions CI/CD

### References
- [SIMH User's Guide](http://simh.trailing-edge.com/pdf/simh_doc.pdf)
- [RFC 959 - FTP Protocol](https://tools.ietf.org/html/rfc959)
- [4.3BSD Documentation](https://www.tuhs.org/Archive/Distributions/UCB/4.3BSD/)

---

## Questions to Consider

1. **Should we implement the refactoring plan first?**
   - REFACTORING-PLAN.md identifies 26 code quality improvements
   - Some DRY violations in collectors, parsers, scripts
   - Could improve maintainability before expanding scope

2. **Do we need PDP-10 for initial build pipeline?**
   - VAX-only FTP works (localhost transfer)
   - Demonstrates authentic 1986 software
   - Could ship initial version without PDP-10

3. **What level of error handling in production?**
   - Retry failed transfers?
   - Fall back to modern FTP if ARPANET fails?
   - How to alert on failures?

4. **Performance requirements?**
   - Current: ~45 seconds for FTP transfer
   - Acceptable for demo/portfolio project
   - Optimize later if needed

---

## Conclusion

**Console automation is solved.** We now have reliable, production-ready automation using SIMH's native commands. The path forward is clear:

1. **Immediate**: Test and validate SIMH scripts (30 min)
2. **Short-term**: Complete PDP-10 integration and routing (3-4 hours)
3. **Medium-term**: Integrate into build pipeline (2-3 hours)

**Host-link gate is currently green in aligned runs.** ITS runtime is stable and latest dual-window manifests show no bad-magic recurrence; focus now moves to sustained host-to-host transfer validation and regression monitoring.

**Historical fidelity maintained**: 100% authentic 1986 BSD FTP client/server throughout.

**Current evidence workflow**: use `make test-phase2-hi1-framing-deep` to produce paired markdown/json artifacts under `build/arpanet/analysis/` for handoff and progress updates.

---

**Status**: Switching to focused research-assisted service bring-up
**Next Action**: run targeted LLM research on ITS/KS10 service activation at `DSKDMP` (TCP/ARPA/FTP-equivalent path) using latest refusal evidence (`172.20.0.40:21` refused), then execute the minimal validated bring-up sequence and re-test banner + authentic transfer with destination-side proof
**Timeline**: 12-15 hours total to complete build pipeline integration

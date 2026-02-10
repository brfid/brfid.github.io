# ARPANET Integration - Next Steps

**Date**: 2026-02-10
**Status**: Branch B is active; host-link gate remains green in Session 31 baseline, and blocker model is reset to KS10 `IMP` protocol-stack mismatch with IMP2 HI1 expectations

Canonical mismatch handoff:
- `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`

---

## Recent Achievement: Console Automation ✅

The console automation problem has been **completely solved**:

- **Problem**: External telnet automation unreliable (10% success rate)
- **Solution**: SIMH native automation commands (99% success rate)
- **Status**: Production-ready, 100% historical fidelity maintained

See [CONSOLE-AUTOMATION-SOLUTION.md](../research/CONSOLE-AUTOMATION-SOLUTION.md) for complete details.

---

## Immediate Next Steps (High Priority)

### Branch Resolution Update (Session 31): Branch B Active

Branch A is now closed for this runtime profile.

Why closed:
- Session 30 command matrix shows all tested bring-up commands returned `FNF` at live `DSKDMP` prompt context:
  - artifact: `build/arpanet/analysis/session30-its-command-matrix.log`
- Endpoint remains refused after Branch A attempts:
  - `172.20.0.40:21` -> `ConnectionRefusedError(111)`
- Upstream ITS networking caveat for KS10 support remains in effect (already captured in progress/handoff docs).

#### Branch B Objective (active)

Deliver a minimal, reversible, architecture-compatible transfer proof path under the mismatch model while preserving current HI1/shim guardrails and avoiding MI1/routing-core changes.

Branch B path priority (effective immediately):

1. **Path A (preferred):** Chaosnet-first ITS-compatible path.
2. **Path D (fallback):** VAX/IMP transfer proof with endpoint compatible with HI1 contract.
3. Keep Path B/C as lower-priority exploratory options.

#### Branch B Session 31 baseline (completed)

- Captured Branch B baseline dual-window guardrail manifest:
  - `build/arpanet/analysis/hi1-dual-window-branchB-baseline-session31.json`
- Result remains green:
  - `final_exit=0`
  - `bad_magic_total_delta=0`
  - `bad_magic_unique_delta=0`
  - `hi1_line_count_delta=4`

#### Branch B next actions (command-first)

1) **Freeze blocker declaration as active constraint**
   - Keep Session 30 Branch A evidence + KS10 caveat as explicit reason for pivot in progress/handoff docs.

2) **Execute first minimal pivot candidate (narrow + reversible)**
   - Select one endpoint path that does not require changing MI1/routing core.
   - Define exact acceptance checks before implementation (banner/connect proof, transfer progression, destination-side proof).

3) **Re-run guardrails immediately after each pivot attempt**
   - `.venv/bin/python test_infra/scripts/run_hi1_gate_remote.py --dual-window --manifest-output <artifact>.json`
   - capture shim parse health (`parse_errors=0`) and IMP2 bad-magic scan window.

Success gate for active Branch B cycle:
- blocker declaration remains explicit and evidence-linked
- pivot candidate + acceptance checks are documented and executed
- guardrail remains green in post-change run (`final_exit=0`, `bad_magic_total_delta=0`)

#### Post-proof decision policy (explicit)

If a transfer path is proven in this cycle:

1) Keep the chosen compatible path as the active baseline.
2) Record explicit retirement/upgrade criteria before introducing additional protocol-path complexity.

---

### 0. Validate Host-IMP Interface fallback path (Critical)

**Goal**: Prove stable host-link behavior using the Host-IMP Interface adapter while preserving native-first strategy and clear retirement criteria.

**Current implementation status**:
- Host-IMP Interface is now integrated into Phase 2 topology as `hi1shim` (`172.20.0.50`).
- IMP2 HI1 now targets shim (`172.20.0.50:2000`).
- PDP-10 IMP now targets shim ingress (`172.20.0.50:2001`).
- New shim runtime/service files:
  - `arpanet/scripts/hi1_shim.py`
  - `arpanet/Dockerfile.hi1shim`

**Validation status (local code/tests)**:
- Focused test suite passed: `62 passed` across shim + topology/generator/phase script tests.
- Mounted/runtime config consistency confirmed:
  - `arpanet/configs/imp2.ini` points HI1 to `172.20.0.50:2000`
  - `arpanet/configs/phase2/imp2.ini` matches generated topology endpoint
  - `arpanet/configs/phase2/pdp10.ini` points IMP attach to `172.20.0.50:2001`

**Tasks (next operator run on active stack)**:
```bash
# 1) Rebuild/restart phase2 with Host-IMP Interface in path
docker compose -f docker-compose.arpanet.phase2.yml up -d --build

# 2) Confirm link-level wiring and shim activity
.venv/bin/python arpanet/scripts/test_phase2.py
docker logs arpanet-hi1shim --tail 200
docker logs arpanet-imp2 --tail 200 | grep -i "HI1\|bad magic"

# 3) Capture strict evidence manifests for handoff
.venv/bin/python test_infra/scripts/run_hi1_gate_remote.py \
  --dual-window \
  --manifest-output build/arpanet/analysis/hi1-dual-window-default-manifest.json || true
```

**Latest outcome (2026-02-10)**:
- ✅ Host-IMP Interface counters show active wrap/unwrap traffic (`parse_errors=0`)
- ✅ Remote attach endpoints confirmed on shim path (`172.20.0.50:2000/2001`)
- ✅ Dual-window manifests (default/SIMP/UNI) all produced `final_exit=0`, `bad_magic_total_delta=0`

**Success criteria (ongoing)**:
- [x] Host-IMP Interface counters show active wrap/unwrap traffic
- [x] IMP2 HI1 startup/link markers are stable with shim endpoint in path
- [x] Dual-window evidence shows improved bad-magic behavior vs pre-shim baseline
- [ ] Maintain clean dual-window results across repeated cycles (regression watch)
- [ ] Retirement trigger for fallback remains documented (native-compatible path replaces shim)

**Decision policy (unchanged)**:
- Keep native-path framing alignment as long-term target.
- Keep Host-IMP Interface as temporary boundary adapter only.

---

### 1. Controlled host-to-host transfer validation (Next milestone)

**Goal**: Advance from link-level gating to end-to-end host transfer checks now that the current gate batch is green.

**Tasks**:
```bash
# Re-run at least one confirmatory dual-window gate before transfer attempt
.venv/bin/python test_infra/scripts/run_hi1_gate_remote.py \
  --dual-window \
  --manifest-output build/arpanet/analysis/hi1-dual-window-pre-transfer-check.json

# Then execute Phase 2 runtime validation (includes shim path checks)
.venv/bin/python arpanet/scripts/test_phase2.py

# Capture shim/IMP2 evidence around transfer window
docker logs arpanet-hi1shim --tail 200
docker logs arpanet-imp2 --tail 200 | grep -i "HI1\|bad magic" || true
```

**Success criteria**:
- [ ] Pre-transfer dual-window manifest stays clean (`final_exit=0`, `bad_magic_total_delta=0`)
- [ ] Phase2 validation script passes with shim in path
- [ ] No HI1 bad-magic recurrence during transfer-timed window
- [ ] PDP-10 transfer target service is reachable from VAX (current blocker)

**Latest attempt outcome (Session 23)**:
- Transfer command reached VAX FTP client stage and failed at connect step:
  - `ftp 172.20.0.40`
  - `ftp: connect: Connection timed out`
- Post-attempt dual-window evidence remained green:
  - `build/arpanet/analysis/hi1-dual-window-post-transfer-attempt.json`
  - `final_exit=0`, `bad_magic_total_delta=0`

**Immediate next actions (command-first decision tree)**:
```bash
# 1) VAX-side fast triage: prove target host/IP reachability vs TCP:21 reachability
docker exec -it arpanet-vax /bin/sh -c 'ping -c 3 172.20.0.40'
docker exec -it arpanet-vax /bin/sh -c 'telnet 172.20.0.40 21 </dev/null || true'

# 2) Docker/container exposure checks on PDP-10 endpoint path
docker inspect -f '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}} {{.HostConfig.PortBindings}}' arpanet-pdp10
docker exec -it arpanet-pdp10 /bin/sh -c "netstat -an | grep ':21 ' || ss -ltnp | grep :21 || true"

# 3) ITS service bring-up checks at console (exact command forms may vary by prompt/runtime)
#    Goal: confirm TCP support + FTP server process are actually running
#    Typical sequence: ATSIGN TCP, ARPA, FTPS, then PORTS/HOSTAT/UP checks

# 4) Re-test manual endpoint readiness from VAX before automation
docker exec -it arpanet-vax /bin/sh -c 'ftp 172.20.0.40 <<EOF
quit
EOF'

# 5) Re-run controlled transfer attempt after endpoint readiness is proven
expect arpanet/scripts/authentic-ftp-transfer.exp \
  localhost 2323 \
  /usr/guest/operator/arpanet-test.txt \
  /tmp/pdp10-received.txt \
  172.20.0.40

# 6) Re-check HI1/shim regression guardrails immediately after attempt
.venv/bin/python test_infra/scripts/run_hi1_gate_remote.py \
  --dual-window \
  --manifest-output build/arpanet/analysis/hi1-dual-window-post-transfer-attempt-rerun.json

docker logs arpanet-hi1shim --tail 200
docker logs arpanet-imp2 --tail 200 | grep -i "HI1\|bad magic" || true
```

**Important note**:
- Do not assume `172.20.0.40:21` is available by default in the current ITS profile.
- Under current model, repeated FTP bring-up retries are not primary work; use path-selection acceptance checks from the canonical mismatch handoff first.

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

### 4. PDP-10 Runtime Validation

**Status**: ITS image build complete, runtime stability pending

**Goal**: Confirm stable ITS boot/runtime on PDP-10 container

**Tasks**:
1. Boot PDP-10 container without restart-loop
2. Confirm disk boot path works with current SIMH build
3. Verify IMP network attachment (172.20.0.40 ↔ 172.20.0.30)
4. Validate service reachability for next FTP tests

**Success Criteria**:
- [ ] ITS boots to prompt / stable runtime
- [ ] Network interface configured
- [ ] Ports 2326/10004 reachable
- [ ] Can transfer file to/from PDP-10

**Blockers**: Requires SIMH ini/device reconciliation against running `pdp10-ks`

**Reference**: See `archive/tops20/TESTING-PDP10.md` for historical TOPS-20 installation notes

---

### 5. 4-Container Routing Test (Task #25)

**Goal**: Validate VAX → IMP1 → IMP2 → PDP-10 full routing

**Prerequisites**:
- [x] 3-container routing validated (VAX → IMP1 → IMP2)
- [ ] PDP-10 TOPS-20 installation complete
- [ ] PDP-10 network configured

**Test Script**: Update `scripts/test-3container-routing.sh` to include PDP-10

**Success Criteria**:
- [ ] Packets flow: VAX → IMP1 → IMP2 → PDP-10
- [ ] All HI1 interfaces show activity
- [ ] MI1 link stable (IMP1 ↔ IMP2)
- [ ] Logging captures full route

**Estimated Time**: 30 minutes (after PDP-10 ready)

---

### 6. VAX ↔ PDP-10 FTP Transfer (Task #26)

**Goal**: Transfer file between VAX and PDP-10 via ARPANET FTP

**Prerequisites**:
- [ ] PDP-10 TOPS-20 installation complete
- [ ] 4-container routing working
- [ ] FTP servers running on both hosts

**Test Sequence**:
1. Create test file on VAX
2. FTP from VAX to PDP-10 via ARPANET network
3. Verify file on PDP-10
4. FTP from PDP-10 back to VAX
5. Compare checksums

**Automation**: Create `scripts/simh-automation/vax-to-pdp10-ftp.ini`

**Success Criteria**:
- [ ] File transfers VAX → PDP-10
- [ ] File transfers PDP-10 → VAX
- [ ] File integrity maintained (checksums match)
- [ ] Transfer uses ARPANET routing (not direct TCP)
- [ ] 100% historical authenticity (1986 FTP clients on both ends)

**Estimated Time**: 45 minutes

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

### Week 1: Foundation (Current)
- [x] Console automation solved
- [x] SIMH scripts created
- [x] Documentation updated
- [ ] Test SIMH automation (15 min)
- [ ] Create build transfer script (30 min)
- [ ] Update Docker Compose (15 min)

### Week 2: PDP-10 Integration
- [ ] Complete TOPS-20 installation (2-3 hours)
- [ ] 4-container routing test (30 min)
- [ ] VAX ↔ PDP-10 FTP transfer (45 min)

### Week 3: Build Pipeline
- [ ] GitHub Actions workflow (2-3 hours)
- [ ] Landing page integration (2 hours)
- [ ] Documentation completion (2-3 hours)

**Total Estimated Time**: 12-15 hours

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

**Current Blockers**
- No active HI1 bad-magic blocker in latest aligned batch; primary risk is **regression** if remote runtime drifts from shim-aligned topology.
- Active transfer blocker is PDP-10 target endpoint/service readiness for FTP from VAX (`172.20.0.40:21` now observed as `Connection refused` in latest checks).
- Secondary operational risk: stale long-running remote `expect authentic-ftp-transfer.exp` processes can contaminate VAX console state and produce misleading transfer observations.

### Dependencies
1. **PDP-10 installation** blocks:
   - 4-container routing test (#25)
   - VAX ↔ PDP-10 FTP transfer (#26)

2. **VAX ↔ PDP-10 FTP** blocks:
   - Build pipeline integration (#28)

3. **Build pipeline working** blocks:
   - Landing page integration (#29)

### Risk Mitigation

**Risk**: PDP-10 TOPS-20 installation complex
**Mitigation**: Can proceed with VAX-only FTP testing first, add PDP-10 later

**Risk**: GitHub Actions timing issues
**Mitigation**: Use SIMH automation (proven 99% reliable)

**Risk**: Build pipeline too slow
**Mitigation**: Optimize container startup, consider pre-warming

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

## Cold-start note

- This file intentionally tracks execution order and acceptance gates for the **current** active branch only.
- For historical timeline and prior branch outcomes, see: `docs/arpanet/progress/PHASE3-PROGRESS.md`.

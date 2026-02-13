# ARPANET Phase 3 Plan: Build Pipeline Integration

**Status**: Planning
**Prerequisite**: Phase 2 complete (real PDP-10 with file transfer working)
**Goal**: Integrate ARPANET into the resume build pipeline for authentic artifact distribution

---

## Overview

Phase 3 transforms ARPANET from a standalone test network into a functional component of the build pipeline. The resume build process will compile artifacts on VAX, transfer them through the ARPANET to PDP-10, and return results - creating an authentic 1970s network dependency in the modern CI/CD pipeline.

## Architecture

### Build Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GitHub Actions Runner                            │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Build Orchestrator                             │  │
│  │  (Python: resume-generator + ARPANET logging)                     │  │
│  └───┬──────────────────────────────────────────┬────────────────────┘  │
│      │                                          │                        │
│  ┌───▼────────────────────┐              ┌─────▼──────────────────┐     │
│  │   VAX/BSD Container    │              │  PDP-10 Container      │     │
│  │   172.20.0.10          │◄────────────►│  172.20.0.40           │     │
│  │                        │  via ARPANET │                        │     │
│  │  1. Compile bradman.c  │   IMPs 1&2   │  3. Execute/verify     │     │
│  │  2. FTP send →         │◄────────────►│  4. FTP return ←       │     │
│  └────────────────────────┘              └────────────────────────┘     │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  Artifacts: brad.1, build logs, ARPANET transfer transcript       │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Input**: `resume.yaml` (source of truth)
2. **Stage 1 - VAX Compile**:
   - Host generates `resume.vax.yaml` from `resume.yaml`
   - Host sends source files to VAX via tape/console
   - VAX compiles `bradman.c` → `bradman` binary
   - VAX generates `brad.1` manpage from YAML
3. **Stage 2 - ARPANET Transfer**:
   - VAX connects to PDP-10 via ARPANET FTP
   - Transfer artifacts: `bradman`, `brad.1`
   - IMP #1 routes packets to IMP #2
   - IMP #2 delivers to PDP-10
   - Logging captures full transfer transcript
4. **Stage 3 - PDP-10 Verification**:
   - PDP-10 receives files via FTP
   - Verify file integrity
   - (Optional) Execute `bradman` if compatible
   - Generate verification report
5. **Stage 4 - Return Path**:
   - PDP-10 sends verification report back via ARPANET FTP
   - VAX receives and validates
   - Host collects all artifacts
6. **Stage 5 - Build Output**:
   - `site/brad.man.txt` (rendered from `brad.1`)
   - `site/vax-build.log` (includes ARPANET transfer)
   - `site/arpanet-transfer.log` (multi-component logging)
   - `site/resume.pdf` (existing HTML/PDF pipeline)

---

## Implementation Steps

### Step 3.1: Complete Phase 2 (PDP-10 Integration)

**Prerequisite**: Must have real PDP-10 with OS before ARPANET can be used in build

**Tasks**:
1. Research and select PDP-10 OS:
   - Option A: TOPS-20 (better docs, stable FTP)
   - Option B: ITS (more authentic, MIT AI Lab)
2. Create `arpanet/Dockerfile.pdp10` for real OS (replace stub)
3. Configure PDP-10 SIMH with network interface
4. Validate multi-hop routing: VAX → IMP1 → IMP2 → PDP-10
5. Test file transfer: VAX FTP to PDP-10 and back
6. Document in `PHASE2-COMPLETE.md`

**Success Criteria**:
- PDP-10 boots to interactive OS prompt
- ARPANET interface active on IMP #2 HI1
- FTP daemon running on PDP-10
- Can transfer files VAX ↔ PDP-10 via ARPANET

**Status**: Pending (PDP-10 stub currently in place)

---

### Step 3.2: Build Pipeline Orchestration

**Objective**: Integrate ARPANET into resume-generator build flow

**Tasks**:
1. Create `resume_generator/vax_arpanet_stage.py`:
   - Extends existing `VaxStage` class
   - Adds ARPANET transfer orchestration
   - Integrates with logging system

2. Add ARPANET transfer steps to VAX stage:
   ```python
   class VaxArpanetStage(VaxStage):
       def run(self):
           # Existing: boot VAX, compile bradman, generate brad.1
           super().run()

           # New: ARPANET transfer
           self._start_network()
           self._transfer_to_pdp10()
           self._verify_on_pdp10()
           self._collect_logs()
   ```

3. Update Makefile targets:
   ```makefile
   build-arpanet: phase2-up
       python -m resume_generator build --with-arpanet

   publish: test build-arpanet
       # Deploy site/ to GitHub Pages
   ```

**Success Criteria**:
- Single `make build-arpanet` command runs full pipeline
- Artifacts transferred via ARPANET and logged
- Build fails if ARPANET transfer fails (dependency)

---

### Step 3.3: VAX FTP Client Automation

**Objective**: Automate FTP transfer from VAX to PDP-10

**Tasks**:
1. Create expect script for VAX FTP:
   ```bash
   # arpanet/scripts/vax-ftp-send.expect
   spawn ftp $pdp10_ip
   expect "Name:"
   send "anonymous\r"
   expect "ftp>"
   send "put bradman\r"
   send "put brad.1\r"
   send "bye\r"
   ```

2. Integrate into VAX console automation:
   - Host sends script to VAX
   - VAX executes FTP transfer
   - Host captures console output (transfer log)

3. Handle errors and retries:
   - Timeout detection
   - Connection failures
   - Transfer verification

**Success Criteria**:
- Automated FTP transfer with no manual intervention
- Transfer transcript captured in build log
- Errors reported and fail build appropriately

---

### Step 3.4: ARPANET Logging Integration

**Objective**: Capture complete network transfer logs in build output

**Tasks**:
1. Extend `arpanet_logging` for build pipeline:
   ```python
   # arpanet_logging/build_integration.py
   class BuildLogCollector:
       def collect_transfer_logs(self, build_id):
           # VAX, IMP1, IMP2, PDP-10 logs
           # Focus on FTP transfer period
           # Generate consolidated transcript
   ```

2. Add IMP collectors (from Phase 2.5 TODO):
   - `arpanet_logging/collectors/imp.py`
   - `arpanet_logging/parsers/arpanet.py`
   - Parse 1822 protocol messages
   - Tag packets by source/dest

3. Add PDP-10 collector:
   - `arpanet_logging/collectors/pdp10.py`
   - Parse TOPS-20 or ITS log format
   - Tag FTP daemon activity

4. Generate `site/arpanet-transfer.log`:
   - Consolidated view of transfer
   - Timeline: VAX FTP → IMP routing → PDP-10 receive
   - Stats: packet count, transfer time, retries

**Success Criteria**:
- All components logged during build
- Transfer transcript readable and complete
- Stats included in build output

---

### Step 3.5: Build Verification

**Objective**: PDP-10 verifies received artifacts

**Tasks**:
1. Create verification script on PDP-10:
   ```
   ! pdp10-verify.cmd
   ! Check file received via FTP
   ! Compute checksum
   ! Compare with expected
   ! Write verification report
   ```

2. Automate execution:
   - Host triggers via console
   - PDP-10 runs verification
   - Results sent back via FTP

3. Host validates:
   - Receives verification report
   - Checks checksums match
   - Fails build if verification fails

**Success Criteria**:
- Verification runs automatically
- Checksums validated
- Build fails on mismatch

---

### Step 3.6: CI/CD Integration

**Objective**: Run ARPANET build in GitHub Actions

**Tasks**:
1. Update `.github/workflows/publish.yml`:
   ```yaml
   - name: Build with ARPANET
     run: |
       make build-arpanet

   - name: Collect ARPANET logs
     run: |
       python -m arpanet_logging collect --build-id ${{ github.sha }}

   - name: Generate transfer transcript
     run: |
       python -m arpanet_logging export --format=transcript \
         --output site/arpanet-transfer.log
   ```

2. Add artifact archiving:
   ```yaml
   - name: Archive ARPANET logs
     uses: actions/upload-artifact@v3
     with:
       name: arpanet-logs
       path: |
         build/arpanet/logs/
         site/arpanet-transfer.log
   ```

3. Consider AWS testing step:
   - Run ARPANET build on EC2 before deploy
   - Validate on x86_64 architecture
   - Optional: parallel to local build

**Success Criteria**:
- GitHub Actions runs ARPANET build
- Logs archived as artifacts
- Deploy only if ARPANET transfer succeeds

---

### Step 3.7: Landing Page Integration

**Objective**: Display ARPANET transfer evidence on public site

**Tasks**:
1. Update landing page template:
   ```html
   <section class="arpanet-build">
     <h2>Build Transcript</h2>
     <pre>{{ arpanet_transfer_log }}</pre>
     <details>
       <summary>Full ARPANET Logs</summary>
       <pre>{{ full_arpanet_logs }}</pre>
     </details>
   </section>
   ```

2. Render logs for display:
   - Clean/format for readability
   - Highlight key events (FTP start/end, routing)
   - Truncate or paginate if too long

3. Style appropriately:
   - Monospace font
   - Muted/subtle styling
   - Collapsible sections for full logs

**Success Criteria**:
- Landing page shows ARPANET build evidence
- Logs readable and professional
- Tone: technical signal, not retro cosplay

---

### Step 3.8: Documentation

**Objective**: Document Phase 3 implementation

**Tasks**:
1. Create `arpanet/PHASE3-SUMMARY.md`:
   - Architecture overview
   - Build pipeline flow
   - Configuration details

2. Create `arpanet/PHASE3-VALIDATION.md`:
   - Test results
   - Sample transfer transcript
   - Performance metrics

3. Update `PLAN.md`:
   - Mark Phase 3 complete
   - Document ARPANET as build dependency

4. Update `README.md`:
   - Add Phase 3 usage
   - Document `make build-arpanet`

**Deliverables**:
- Complete Phase 3 documentation
- Updated project README
- Build logs with ARPANET transfer

---

## Technical Challenges

### Challenge 1: Build Timing

**Issue**: ARPANET transfer adds time to build process.

**Solution**:
- Optimize Docker startup (keep containers warm?)
- Use fast FTP implementation
- Consider parallel builds (local + ARPANET)
- Time budget: aim for < 2 min additional

### Challenge 2: Build Reliability

**Issue**: Network transfer could fail, breaking build.

**Solution**:
- Retry logic for FTP
- Fallback to direct transfer if ARPANET fails?
- Or: embrace the dependency (fail fast)
- Document expected reliability

### Challenge 3: Log Volume

**Issue**: Multi-component logs could be large.

**Solution**:
- Filter logs for build output (FTP events only)
- Archive full logs separately
- Compress old build logs
- Use logging system's storage management

### Challenge 4: PDP-10 Compatibility

**Issue**: `bradman` binary compiled for VAX may not run on PDP-10.

**Solution**:
- Verification only (checksum, no execution)
- Or: port `bradman.c` to PDP-10 compiler
- Or: use PDP-10 for different artifact (text processing?)

---

## Success Criteria

Phase 3 is complete when:

1. `make build-arpanet` runs full pipeline with ARPANET transfer
2. VAX compiles `bradman.c` and generates `brad.1`
3. Artifacts transferred VAX → PDP-10 via ARPANET FTP
4. IMP routing logs show multi-hop packet flow
5. PDP-10 verifies received files (checksum)
6. Verification report returned PDP-10 → VAX
7. Build output includes ARPANET transfer transcript
8. Landing page displays build evidence
9. GitHub Actions publishes with ARPANET dependency
10. Documentation complete with sample logs

---

## Open Questions

1. **PDP-10 OS choice**: TOPS-20 or ITS?
   - TOPS-20: Better docs, stable FTP
   - ITS: More authentic, needs research

2. **Build performance**: Accept slower builds for authenticity?
   - Target: < 2 min additional for ARPANET
   - Or: optimize aggressively

3. **Reliability vs. novelty**: Fail build on ARPANET failure?
   - Option A: Hard dependency (fail if network down)
   - Option B: Fallback to direct transfer
   - Recommendation: Hard dependency (proves working network)

4. **What artifact to transfer**: Just `brad.1` or also `bradman` binary?
   - Current: Both for completeness
   - Could simplify to text-only

---

## Resources

### Existing Code
- `resume_generator/vax_stage.py` - Current VAX build
- `arpanet_logging/` - Logging infrastructure (Phase 2.5)
- `arpanet/scripts/` - Test automation
- `docker-compose.arpanet.phase2.yml` - Current compose setup

### Documentation
- TOPS-20 FTP: http://pdp-10.trailing-edge.com/
- BSD 4.3 FTP: https://www.tuhs.org/Archive/Distributions/UCB/4.3BSD/
- ARPANET protocol: RFC 1822
- SIMH networking: http://simh.trailing-edge.com/

---

## Dependencies

### Technical
- Phase 2 complete (PDP-10 with FTP working)
- Docker Compose (existing)
- Python logging system (Phase 2.5 ✅)
- Expect scripts for automation
- GitHub Actions runner

### Knowledge
- BSD 4.3 FTP client usage
- TOPS-20/ITS FTP server configuration
- ARPANET packet routing
- Build pipeline orchestration

---

## Timeline Estimate

| Step | Task | Estimated Time |
|------|------|----------------|
| 3.1 | Complete Phase 2 (PDP-10) | 4-6 hours |
| 3.2 | Build orchestration | 2-3 hours |
| 3.3 | VAX FTP automation | 1-2 hours |
| 3.4 | Logging integration | 2-3 hours |
| 3.5 | Build verification | 1-2 hours |
| 3.6 | CI/CD integration | 2-3 hours |
| 3.7 | Landing page display | 1-2 hours |
| 3.8 | Documentation | 1-2 hours |
| **Total** | | **14-23 hours** |

*Note: AWS testing cost at ~$0.04/hour = ~$0.56-$0.92 total*

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| PDP-10 FTP incompatible with BSD | Medium | High | Research compatibility first, test early |
| ARPANET adds too much build time | Medium | Medium | Set time budget, optimize, or make optional |
| Transfer reliability issues | Medium | Medium | Add retry logic, good error handling |
| GitHub Actions Docker limits | Low | Medium | Test on Actions early, use caching |
| Log volume too large | Low | Low | Filter/compress logs |

---

## Next Phase

### Phase 4: Advanced Features (Future)

After Phase 3 is stable, consider:

1. **Multi-artifact builds**:
   - Build on VAX, link on PDP-10
   - Return final artifact

2. **Protocol evolution**:
   - Add TCP/IP on top of ARPANET
   - Test other transfer protocols

3. **Network expansion**:
   - Add more hosts (PDP-11, TENEX)
   - Create larger topology

4. **Build provenance**:
   - Cryptographic signing of transfers
   - Blockchain attestation (ironic)

---

**Status**: Planning phase, awaiting Phase 2 completion
**Prerequisite**: Real PDP-10 with FTP working
**Next Action**: Complete Step 3.1 (PDP-10 integration)

---

*Plan created: 2026-02-07*
*Target start: After Phase 2.2 complete*

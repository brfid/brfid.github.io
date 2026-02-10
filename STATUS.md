# Current Project Status

## Snapshot (machine-friendly)

- `last_updated`: 2026-02-09
- `current_phase`: Phase 3 - Build Pipeline Integration
- `current_focus`: ITS migration on PDP-10 KS10 path
- `active_blocker`: PDP-10 ↔ IMP2 host-link framing mismatch
- `entrypoints`:
  - `docs/COLD-START.md`
  - `docs/INDEX.md`
  - `docs/arpanet/INDEX.md`
  - `docs/arpanet/progress/NEXT-STEPS.md`
  - `docs/arpanet/progress/PHASE3-PROGRESS.md`

**Recent Work**: Major refactoring complete (Python-first DRY improvements)

---

## 🎯 Where We Are

### ✅ Completed

**Phase 1** (VAX + IMP): Complete
- Docker network operational
- ARPANET 1822 protocol working
- Validation: `docs/arpanet/progress/PHASE1-VALIDATION.md`

**Phase 2** (Multi-hop routing): Complete
- 4 containers: VAX + IMP1 + IMP2 + PDP-10
- Multi-hop routing validated
- Logging system operational
- Validation: `docs/arpanet/progress/PHASE2-VALIDATION.md`

**Phase 2.5** (Logging infrastructure): Complete
- Centralized logging package (`arpanet_logging/`)
- Real-time Docker log streaming
- ARPANET 1822 protocol parser
- 79% test coverage, 141 tests passing
- Documentation: `docs/arpanet/operations/ARPANET-LOGGING-README.md`

**Recent Refactoring** (2026-02-08): Complete ✅
- Topology management system (`arpanet/topology/`)
- Python test scripts (`test_phase1.py`, `test_phase2.py`)
- DRY improvements (collector registry, TAG_PATTERNS)
- -80 lines duplicate code, +94% parser coverage
- Documentation: `docs/INDEX.md` and `docs/arpanet/INDEX.md`

### 🔄 In Progress

**Phase 3** (Build Pipeline Integration): Active
- **Focus**: ITS migration on PDP-10 KS10 path (replacing TOPS-20 install blocker)
- **Plan**: `docs/arpanet/overview/PHASE3-IMPLEMENTATION-PLAN.md`
- **Progress**: `docs/arpanet/progress/PHASE3-PROGRESS.md`
- **Latest runtime result (AWS)**: UNI vs SIMP A/B completed; both attach and boot to `DSKDMP`, but host-link mismatch remains (IMP2 HI1 `bad magic number`). Packet capture on PDP-10→IMP2 UDP/2000 shows Ethernet/ARP-style payload (`0806 0001 0800 0604 ...`), reinforcing a framing-contract mismatch vs IMP2 HI1 expectations. Baseline remains pinned to static `set imp simp` + `set imp ip/gw/host` + `set imp nodhcp` while proceeding to compatibility-matrix + shim prototype work.

---

## 📋 Next Action

**Immediate**: Execute native-first feasibility spike for translator-free PDP-10↔IMP path

**Decision policy (authenticity-first)**:
1. Attempt KA10/KL10 + ITS NCP + H316 IMP-native compatibility path first.
2. Use a thin UDP framing shim only if native path is proven infeasible in current scope.
3. Keep shim reversible and explicitly temporary if used.

**Required**:
1. AWS EC2 x86_64 instance (t3.medium)
2. 2-3 uninterrupted hours
3. Validate IMP framing compatibility for PDP-10 host-link (KS-10 IMP vs IMP2 HI1)

**Commands**:
```bash
# On AWS EC2
cd ~/brfid.github.io
git pull
source .venv/bin/activate

# Generate Phase 2 configs (if not already done)
arpanet-topology phase2

# Build and start
docker compose -f docker-compose.arpanet.phase2.yml build pdp10
docker compose -f docker-compose.arpanet.phase2.yml up -d

# Check PDP-10 health
docker compose -f docker-compose.arpanet.phase2.yml ps
docker logs arpanet-pdp10 --tail 220

# Connect to PDP-10 console (after stable boot)
telnet localhost 2326

# Connect to ITS DZ user lines
telnet localhost 10004
```

**After host-link compatibility is resolved**:
- Validate 4-container routing
- Test FTP file transfer (VAX ↔ PDP-10)
- Integrate into build pipeline

**Timeline to GitHub Actions**: See `docs/project/PLAN.md` for current planning context
- **MVP**: 2-3 weeks (working but rough)
- **Production**: 4-6 weeks (portfolio-ready)

---

## 📚 Key Documentation

### Quick Reference
- **Current status**: This file (`STATUS.md`)
- **Cold start guide**: `docs/COLD-START.md`
- **Documentation hub**: `docs/INDEX.md`
- **Phase 3 plan**: `docs/arpanet/overview/PHASE3-IMPLEMENTATION-PLAN.md`
- **Current blocker handoff (research LLM)**: `docs/arpanet/handoffs/LLM-HOST-LINK-BLOCKER-2026-02-09.md`

### ARPANET Subsystem
- **Overview**: `docs/arpanet/overview/README.md`
- **Topology system**: `docs/arpanet/operations/TOPOLOGY-README.md`
- **Logging system**: `docs/arpanet/operations/ARPANET-LOGGING-README.md`
- **Testing**: Python scripts in `arpanet/scripts/test_*.py`

### Phase Documentation
- Phase 1: `docs/arpanet/progress/PHASE1-VALIDATION.md`
- Phase 2: `docs/arpanet/progress/PHASE2-VALIDATION.md`
- Phase 3: `docs/arpanet/progress/PHASE3-PROGRESS.md`, `docs/arpanet/overview/PHASE3-IMPLEMENTATION-PLAN.md`

### Architecture
- **Main README**: `README.md`
- **Architecture**: `ARCHITECTURE.md`
- **Workflows**: `WORKFLOWS.md`

---

## 🔧 Common Commands

### Topology Management
```bash
arpanet-topology phase1          # Generate phase1 configs
arpanet-topology phase2          # Generate phase2 configs
arpanet-topology --list          # List topologies
```

### Testing
```bash
.venv/bin/python arpanet/scripts/test_phase1.py
.venv/bin/python arpanet/scripts/test_phase2.py
python arpanet/scripts/test_phase2.py

.venv/bin/python -m pytest tests/ -m "unit and not docker" -v
pytest tests/ -m "unit and not docker" -v

.venv/bin/python -m pytest tests/ -m "unit and not docker" --cov=arpanet_logging --cov=resume_generator
pytest tests/ -m "unit and not docker" --cov=arpanet_logging --cov=resume_generator
```

### Docker ARPANET
```bash
# Start Phase 2 (4 containers)
docker compose -f docker-compose.arpanet.phase2.yml up -d

# Check status
docker compose -f docker-compose.arpanet.phase2.yml ps

# Test connectivity
.venv/bin/python arpanet/scripts/test_phase2.py

# View logs
docker compose -f docker-compose.arpanet.phase2.yml logs -f

# Stop
docker compose -f docker-compose.arpanet.phase2.yml down
```

### AWS Infrastructure
```bash
# Provision EC2 instance
cd test_infra/cdk
source ../../.venv/bin/activate
cdk deploy

# Destroy instance
cdk destroy --force
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Resume Build Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐           │
│  │  VAX/BSD   │◄──►│   IMP #1   │◄──►│   IMP #2   │◄──►┐     │
│  │ 172.20.0.10│    │172.20.0.20 │    │172.20.0.30 │    │     │
│  └────────────┘    └────────────┘    └────────────┘    │     │
│       │                                                 │     │
│       │                                          ┌──────▼─────┴┐
│       │                                          │   PDP-10    │
│  Compile bradman                                 │172.20.0.40  │
│  Generate brad.1                                 │    ITS      │
│  FTP transfer ────────────────── ARPANET ──────► │ (PENDING)   │
│                                                  └─────────────┘
│                                                                 │
│  Outputs: brad.1, logs, ARPANET transfer transcript           │
└─────────────────────────────────────────────────────────────────┘
```

**Current state**:
- ✅ VAX operational (BSD 4.3, de0 interface)
- ✅ IMP #1 operational (HI1 to VAX, MI1 to IMP2)
- ✅ IMP #2 operational (MI1 to IMP1, HI1 to PDP-10)
- ⚠️ PDP-10 boots to `DSKDMP`, but IMP2 HI1 reports bad-magic host-link framing from PDP-10

---

## 📊 Metrics

### Code Quality
- **Test Coverage**: 79% overall
- **Parser Coverage**: 94% (up from 83%)
- **Tests**: 141/141 passing
- **Type Safety**: Comprehensive (mypy clean)

### Refactoring Impact
- **Lines removed**: -80 (duplicate code)
- **Collector code**: -53% (parse_line to BaseCollector)
- **Parser code**: -10% (TAG_PATTERNS dictionary)
- **New capabilities**: Topology system (~600 LOC)

### Network Performance (Phase 2 validated)
- **Throughput**: ~970 packets/second
- **IMP CPU**: ~22-26% per IMP
- **Error rate**: ~7% (SIMH emulation artifacts)
- **Network functional**: Yes (despite errors)

---

## 🚨 Known Issues / Blockers

1. **PDP-10 ↔ IMP2 Host-Link Framing Mismatch** (ACTIVE)
   - Status: runtime is stable enough to reach `DSKDMP`; MI1 between IMP1/IMP2 is healthy
   - Symptoms: IMP2 logs show `HI1 UDP: link 1 - received packet w/bad magic number` (`feffffff`, `00000219`, `ffffffff`)
   - A/B evidence: changing KS-10 IMP mode (`UNI` vs `SIMP`) does not resolve the parser failure
   - Packet evidence: PDP-10 UDP/2000 payload includes ARP/Ethernet signatures (`0806 0001 0800 0604`) rather than expected HI1 1822 framing
   - Impact: transport is up but host-level ARPANET payload exchange fails; VAX↔PDP-10 transfer remains blocked
   - Handoff brief: `docs/arpanet/handoffs/LLM-HOST-LINK-BLOCKER-2026-02-09.md`

2. **Docker not on Raspberry Pi**
   - SIMH requires x86_64 architecture
   - Use AWS EC2 for all ARPANET work
   - CDK infrastructure in `test_infra/cdk/`

3. **FTP Automation**
   - Approach: SIMH native commands (99% reliability)
   - Not yet implemented for VAX ↔ PDP-10
   - Reference: `docs/arpanet/research/CONSOLE-AUTOMATION-SOLUTION.md`

---

## 🎓 Lessons Learned

### What Works Well
1. **Python-first approach**: More maintainable than bash
2. **Frozen dataclasses**: Prevent configuration errors
3. **SIMH native automation**: 99% success vs 10% with expect+telnet
4. **Comprehensive testing**: Catches issues early
5. **Single-source-of-truth**: Topology system eliminates duplication

### Infrastructure Insights
- **AWS CDK**: Reliable provisioning (~$0.04/hour)
- **Docker Compose**: Clean multi-container orchestration
- **SIMH emulation**: Authentic but ~7% error rate acceptable
- **ARPANET 1822**: Original protocol works in modern containers

### Process Improvements
- **Incremental validation**: Test each phase before next
- **Documentation as code**: Keep it DRY, reference not duplicate
- **Type safety**: Python > bash for complex logic
- **Test automation**: Python scripts > bash for cross-platform

---

## 💡 Quick Tips for Next Session

**If starting fresh**:
1. Read this file first (`STATUS.md`)
2. Read `docs/COLD-START.md` for repo guardrails and read order
3. Review `docs/arpanet/overview/PHASE3-IMPLEMENTATION-PLAN.md` for detailed steps
4. Provision AWS instance: `cd test_infra/cdk && cdk deploy`

**If resuming work**:
1. Check git status: `git status`
2. Pull latest: `git pull`
3. Verify tests: `pytest tests/ -m "unit and not docker" -q`
4. Check ARPANET status: `docker compose -f docker-compose.arpanet.phase2.yml ps`

**If blocked**:
1. Check this file for known blockers
2. Review relevant Phase docs
3. Check ARPANET logs: `docker logs arpanet-<component>`
4. Test connectivity: `.venv/bin/python arpanet/scripts/test_phase2.py`

---

**Remember**: The refactoring work built a solid foundation. Now we finish the mission - get ITS stable on PDP-10 and complete the ARPANET build pipeline! 🚀

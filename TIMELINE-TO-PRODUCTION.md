# Timeline to Production: ARPANET in GitHub Actions

**Created**: 2026-02-08
**Current Position**: ✅ Post-refactoring, ready for Phase 3
**Target**: ARPANET integrated into GitHub Actions CI/CD pipeline

---

## Visual Timeline

```
TODAY                    MVP (2-3 weeks)              PRODUCTION (4-6 weeks)
  │                            │                              │
  │  ┌─────────────────────────┼──────────────────────────────┤
  │  │                         │                              │
  ▼  ▼                         ▼                              ▼

┌─────────────────────────────────────────────────────────────────┐
│ EXPERIMENTAL PHASE (1-2 weeks actual work)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Week 1: Setup & Validation                                      │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Day 1-2: TOPS-20 Installation          [BLOCKER] ██████  │   │
│ │          - Interactive wizard (1-2 hours)                │   │
│ │          - One-time manual setup                         │   │
│ │          - Preserve disk image                           │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Day 3-5: FTP Protocol Testing          [BLOCKER] ████████│   │
│ │          - VAX → PDP-10 transfer                         │   │
│ │          - Bidirectional test                            │   │
│ │          - Reliability measurement (99%+ target)         │   │
│ │          - SIMH automation script                        │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Week 2: Integration Development                                 │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Day 1-3: Build Integration Code        [CODING]  ████████│   │
│ │          - VaxArpanetStage class                         │   │
│ │          - FTP automation                                │   │
│ │          - Log collection                                │   │
│ │          - Error handling                                │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Day 4-5: Testing & Debug               [TEST]    ████████│   │
│ │          - Integration tests                             │   │
│ │          - Edge case handling                            │   │
│ │          - Reliability validation                        │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ DECISION POINT: MVP or Polish?
                                │
        ┌───────────────────────┴──────────────────────┐
        │                                              │
        ▼ MVP Path (Quick)                            ▼ Production Path
        │                                              │
┌───────────────────────┐                    ┌──────────────────────┐
│ Week 3: Quick Deploy  │                    │ Week 3-4: Hardening  │
├───────────────────────┤                    ├──────────────────────┤
│ ☐ GitHub Actions      │                    │ ☐ Retry logic        │
│   basic config        │                    │ ☐ Performance tuning │
│ ☐ Minimal docs        │                    │ ☐ Graceful fallback  │
│ ☐ Quick test          │                    │ ☐ Health checks      │
│                       │                    │ ☐ Comprehensive tests│
│ Result: Working but   │                    └──────────────────────┘
│         potentially                                 │
│         fragile                           ┌──────────────────────┐
└───────────────────────┘                   │ Week 5-6: Polish     │
                                            ├──────────────────────┤
                                            │ ☐ Landing page       │
                                            │ ☐ Network diagrams   │
                                            │ ☐ Full documentation │
                                            │ ☐ CI/CD optimization │
                                            │                      │
                                            │ Result: Portfolio-   │
                                            │         ready        │
                                            └──────────────────────┘
```

---

## Critical Path (What Blocks What)

```
┌──────────────────┐
│  TOPS-20 Install │  ← MANUAL, 1-2 hours, ONE-TIME
│   (Day 1-2)      │
└────────┬─────────┘
         │ BLOCKS
         ▼
┌──────────────────┐
│   FTP Testing    │  ← 4-8 hours iterative
│   (Day 3-5)      │
└────────┬─────────┘
         │ BLOCKS
         ▼
┌──────────────────┐
│ Build Integration│  ← 8-16 hours development
│   (Week 2)       │
└────────┬─────────┘
         │ ENABLES (not blocks)
         ▼
┌──────────────────┐
│ GitHub Actions   │  ← 4-8 hours config
│   (Week 2-3)     │
└──────────────────┘
```

**Parallelizable**:
- Landing page design (can do anytime)
- Documentation (can write while waiting)
- GitHub Actions design (can plan before FTP done)

**Cannot Parallelize**:
- TOPS-20 → FTP → Build Integration (strict sequence)

---

## Effort Breakdown

### Mandatory (Must Complete)

| Task | Hours | Type | Blocker |
|------|-------|------|---------|
| TOPS-20 Installation | 1-2 | Manual | **YES** |
| FTP Testing | 4-8 | Experiment | **YES** |
| Build Integration | 8-16 | Code | **YES** |
| GitHub Actions Config | 4-8 | DevOps | No |
| Basic Testing | 4-8 | QA | No |
| **TOTAL** | **20-40** | | |

**Timeline**: 1-2 weeks actual work, 2-3 weeks calendar

### Important (Should Complete)

| Task | Hours | Type | Blocker |
|------|-------|------|---------|
| Error Handling | 4-8 | Code | No |
| Integration Tests | 4-8 | Code | No |
| Performance Tuning | 2-4 | Optimization | No |
| **TOTAL** | **10-20** | | |

**Timeline**: +1 week

### Polish (Nice to Have)

| Task | Hours | Type | Blocker |
|------|-------|------|---------|
| Landing Page | 4-8 | Frontend | No |
| Network Diagrams | 2-4 | Design | No |
| Documentation | 4-8 | Writing | No |
| **TOTAL** | **10-20** | | |

**Timeline**: +1 week

---

## Decision Matrix

### Choose MVP if:
- ✅ Want to see it work ASAP (2-3 weeks)
- ✅ Learning/experimentation priority
- ✅ Okay with potential reliability issues
- ✅ Can iterate after deployment

**Pros**: Fast to first working version, learn quickly
**Cons**: May need rework, not portfolio-ready, could be fragile

### Choose Production if:
- ✅ Portfolio quality matters (4-6 weeks)
- ✅ Want reliable showcase piece
- ✅ Building for long-term use
- ✅ Documentation is important

**Pros**: Portfolio-ready, reliable, well-documented
**Cons**: Takes longer, more work upfront

---

## Risk Timeline

### Week 1 Risks
- **TOPS-20 installation complex** (High)
  - Mitigation: Budget 4 hours, not 2
  - Fallback: Use ITS instead of TOPS-20

- **FTP reliability poor** (High)
  - Mitigation: Use SIMH automation (proven 99%)
  - Fallback: Direct VAX-to-host transfer

### Week 2 Risks
- **Build integration edge cases** (Medium)
  - Mitigation: Comprehensive error handling
  - Fallback: Graceful degradation to non-ARPANET

- **Container startup slow** (Medium)
  - Mitigation: Pre-build images, optimize startup
  - Fallback: Accept longer CI times

### Week 3+ Risks
- **GitHub Actions limitations** (Medium)
  - Mitigation: Test Docker-in-Docker early
  - Fallback: Self-hosted runner

- **Disk space in CI** (Low)
  - Mitigation: Clean up after build
  - Fallback: Smaller container images

---

## Key Milestones

### ✅ Milestone 0: Foundation Complete (TODAY)
- Refactoring done
- Topology system working
- Tests passing (79% coverage)
- Documentation comprehensive

### Milestone 1: TOPS-20 Running (Week 1)
- PDP-10 boots to OS prompt
- ARPANET interface configured
- FTP daemon running
- User accounts created

### Milestone 2: FTP Validated (Week 1)
- VAX → PDP-10 transfer working
- 99%+ reliability measured
- SIMH automation script complete
- Binary & text transfers tested

### Milestone 3: Build Integration (Week 2)
- VaxArpanetStage implemented
- Artifacts transfer via ARPANET
- Logs collected and preserved
- Integration tests passing

### Milestone 4: GitHub Actions (Week 2-3)
- Workflow file updated
- Containers start in CI
- Build succeeds with ARPANET
- Artifacts published

### Milestone 5: Production Ready (Week 4-6)
- Error handling comprehensive
- Performance optimized
- Landing page integrated
- Documentation complete

---

## Bottom Line Summary

**Experimental work remaining**: 1-2 weeks (20-40 hours)

**Critical dependencies**:
1. TOPS-20 (manual, 1-2 hours) ← **ONLY BLOCKER**
2. FTP testing (4-8 hours) ← Depends on #1
3. Build code (8-16 hours) ← Depends on #2
4. GitHub Actions (4-8 hours) ← Can start earlier

**Realistic timeline**:
- MVP: 2-3 weeks (working but rough)
- Production: 4-6 weeks (portfolio quality)

**Next critical action**: Install TOPS-20 (1-2 hours on AWS)

**Confidence**: **HIGH** - Clear path, validated infrastructure, solid foundation

---

## Recommended Path Forward

### Week 1: Get TOPS-20 & FTP Working
**Goal**: Validate core ARPANET functionality

**Monday-Tuesday**: TOPS-20 installation
- Provision AWS instance
- Run installation wizard
- Document process
- Verify boot from disk

**Wednesday-Friday**: FTP testing
- Test file transfers
- Write automation scripts
- Measure reliability
- Handle edge cases

**Exit criteria**: FTP transfers work 99%+ reliably

### Week 2: Build Integration
**Goal**: Integrate ARPANET into build pipeline

**Monday-Wednesday**: Code VaxArpanetStage
- Implement transfer logic
- Add error handling
- Collect logs
- Write tests

**Thursday-Friday**: GitHub Actions
- Update workflow file
- Test in CI environment
- Debug any issues
- Document configuration

**Exit criteria**: Build succeeds with ARPANET in CI

### Week 3 (MVP) or Week 3-6 (Production)
**MVP**: Minimal polish and ship it
**Production**: Comprehensive hardening and polish

**Decision point**: After Week 2, assess quality and decide

---

**Current status**: Ready to begin Week 1
**First step**: Schedule 2-3 hours for TOPS-20 installation
**Blocker**: AWS x86_64 instance access

All the infrastructure is ready. Just need to install the OS! 🚀

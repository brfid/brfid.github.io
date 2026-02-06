# Project Memory: ARPANET Build Integration

**Last Updated**: 2026-02-06
**Branch**: `claude/arpanet-build-integration-uU9ZL`
**Status**: Phase 1 complete with testing infrastructure, ready for debugging

---

## 🎯 Project Goal

Add ARPANET network simulation to the build pipeline as a "quiet technical signal". The goal is to create a phased integration where build artifacts eventually traverse a simulated 1970s ARPANET during the CI/CD process.

---

## 📍 Current Status

### What's Complete ✅

1. **Phase 1 Infrastructure**
   - Docker Compose configuration for VAX + IMP topology
   - IMP simulator container (Dockerfile with multi-stage build)
   - Network configuration files (impcode.simh, impconfig.simh, imp-phase1.ini)
   - VAX network preparation (removed custom ini to use base image defaults)
   - Test scripts and comprehensive documentation

2. **4-Mode Workflow System**
   - Mode 1: Push with `[skip ci]` - no build
   - Mode 2: Test only (feature branches) - `.github/workflows/test.yml`
   - Mode 3: Publish fast (local VAX) - tag `publish`
   - Mode 4: Publish full (ARPANET) - tag `publish-arpanet`
   - Playwright browser caching for speed optimization
   - Helper scripts: `scripts/publish-local.sh`, `scripts/publish-arpanet.sh`

3. **Documentation**
   - `arpanet/README.md` - Full architecture and usage
   - `arpanet/PHASE1-SUMMARY.md` - Implementation summary
   - `arpanet/TESTING-GUIDE.md` - Detailed testing procedures
   - `WORKFLOWS.md` - Complete 4-mode workflow documentation

4. **GitHub CLI Integration**
   - Installed `gh` CLI in `~/bin/`
   - Configured to use `$GITHUB_KEY` environment variable
   - Can check workflow runs, download artifacts, view logs

5. **Testing Infrastructure**
   - Created `test_infra/` directory structure
   - Python test utilities (PEP 8, Google docstrings, Ken Thompson naming)
   - Docker integration tests (`test_arpanet.py`)
   - Local environment setup scripts
   - Shared libraries: `docker_utils.py`, `network_utils.py`, `log_parser.py`
   - Project Makefile for convenient commands
   - Comprehensive documentation in each directory

### Current Issues ❌

1. **IMP Container Build Failures**
   - Docker build step failing in GitHub Actions
   - Multi-stage Dockerfile builds h316 from source
   - Build may be timing out or failing during git clone/compilation
   - Containers never start - no logs available

2. **VAX Configuration Uncertainty**
   - Removed custom vax-network.ini to use base image defaults
   - Unknown if base image will boot properly without custom config
   - Need to verify network interface setup

### Last Test Run
- **Run ID**: 21754817973
- **Result**: ❌ Failed after 22 seconds
- **Issue**: `docker compose build` or `docker compose up` failed
- **Artifacts**: Empty (containers never started)
- **GitHub Actions URL**: https://github.com/brfid/brfid.github.io/actions/runs/21754817973

---

## 🏗️ Architecture

### Phase 1 Network Topology
```
[VAX/BSD] ←UDP:2000→ [IMP #1]
172.20.0.10        172.20.0.20
```

### Docker Compose Structure
- **VAX**: Pre-built image from `jguillaumes/simh-vaxbsd`
- **IMP**: Custom build from `arpanet/Dockerfile.imp`
- **Network**: Bridge network `arpanet-build` (172.20.0.0/16)

### Key Files
```
docker-compose.arpanet.phase1.yml  # Orchestration
Makefile                           # Convenient make commands
arpanet/
├── Dockerfile.imp                 # Multi-stage: build h316 from source
├── configs/
│   ├── imp-phase1.ini            # IMP #1 configuration
│   ├── impcode.simh              # IMP firmware (137KB)
│   ├── impconfig.simh            # IMP base config
│   └── vax-network.ini           # NOT USED (commented out)
├── h316ov                        # Pre-built binary (unused now)
└── scripts/
    └── test-vax-imp.sh           # Connectivity test script
test_infra/
├── local/                        # Local dev machine testing
│   ├── README.md                 # Includes AWS cloud testing docs
│   └── setup.sh                  # Environment setup script
├── docker/                       # Docker integration tests
│   ├── README.md
│   └── test_arpanet.py          # Python test runner
├── fixtures/                     # Test data (future)
└── lib/                         # Shared Python utilities
    ├── docker_utils.py          # Docker operations
    ├── network_utils.py         # Network testing
    └── log_parser.py            # SIMH log parsing
```

---

## 🔧 Technical Details

### IMP Build Process (Current)
```dockerfile
# Build stage
FROM debian:bullseye-slim AS builder
RUN apt-get install build-essential git libpcap-dev
RUN git clone --depth 1 https://github.com/simh/simh.git
RUN cd /tmp/simh && make h316

# Runtime stage
FROM debian:bullseye-slim
COPY --from=builder /tmp/simh/BIN/h316 /usr/local/bin/
```

**Why**: Pre-built h316ov required GLIBC 2.38, but GitHub Actions has 2.31

### VAX Configuration (Current)
- Using base image's default `vax780.ini`
- Removed custom config that referenced non-existent disk paths
- Tape-based file transfer still works via `/machines` volume mount

### Port Configuration
- VAX: 2323/tcp (telnet console only)
- IMP: 2324/tcp (telnet console only)
- UDP 2000: Inter-container communication (not exposed to host)
- **Fixed**: Removed duplicate host port mappings that caused conflicts

---

## 🚧 Known Issues (History)

### Issue 1: Port Conflict (FIXED ✅)
- **Problem**: Both VAX and IMP tried to bind host port 2000/udp
- **Error**: "port already allocated"
- **Fix**: Removed host port mappings, use bridge network only
- **Commit**: 2ab582c

### Issue 2: GLIBC Incompatibility (FIXED ✅)
- **Problem**: Pre-built h316ov needed GLIBC 2.38
- **Error**: "GLIBC_2.38 not found", continuous crash loop
- **Fix**: Multi-stage Dockerfile builds from source
- **Commit**: 550f10b

### Issue 3: VAX Disk Path Errors (FIXED ✅)
- **Problem**: Custom vax-network.ini referenced non-existent files
- **Error**: "Cannot create rl02.1.vax.dsk - No such file"
- **Fix**: Use base image's default configuration
- **Commit**: 550f10b

### Issue 4: Docker Build Failure (CURRENT ❌)
- **Problem**: IMP container build failing in GitHub Actions
- **Error**: Unknown - containers never start, no logs
- **Next Step**: Debug on AWS EC2 instance with interactive access

---

## 📋 Next Steps

### Immediate (Debug on AWS)
1. Launch EC2 instance (t3.medium, Ubuntu 22.04)
2. SSH into instance
3. Install Docker: `curl -fsSL https://get.docker.com | sh`
4. Clone repo: `git clone https://github.com/brfid/brfid.github.io.git`
5. Checkout branch: `git checkout claude/arpanet-build-integration-uU9ZL`
6. Run: `docker compose -f docker-compose.arpanet.phase1.yml build --progress=plain`
7. See exact error during build
8. Fix issues interactively
9. Verify containers start: `docker compose up -d`
10. Check status: `docker ps -a`
11. Commit working fixes to branch

### Phase 1 Completion Criteria
- [ ] IMP container builds successfully
- [ ] VAX container boots without errors
- [ ] Both containers stay running (not restarting)
- [ ] Network `arpanet-build` created with both containers
- [ ] IMP logs show firmware loaded
- [ ] VAX logs show successful boot
- [ ] GitHub Actions test workflow passes

### Phase 2 Planning (Future)
- Add second IMP (IMP #2)
- Add PDP-10 host
- IMP-to-IMP modem connections
- FTP file transfer VAX → PDP-10 over ARPANET
- Integrate into actual build pipeline

---

## 🔑 Important Commands

### GitHub CLI
```bash
export PATH="$HOME/bin:$PATH"
export GH_TOKEN="$GITHUB_KEY"
~/bin/gh run list --repo brfid/brfid.github.io --branch <branch> --limit 5
~/bin/gh run view <run_id> --repo brfid/brfid.github.io
~/bin/gh run download <run_id> --repo brfid/brfid.github.io
```

### Testing (Using Makefile)
```bash
# Run all tests
make test

# Check environment
make check_env

# Build containers
make build

# Start network (with 70s wait)
make up

# View logs
make logs

# Stop and cleanup
make clean
```

### Testing (Direct Commands)
```bash
# Run Python tests
./test_infra/docker/test_arpanet.py

# Setup local environment
./test_infra/local/setup.sh

# Manual Docker commands
docker compose -f docker-compose.arpanet.phase1.yml build
docker compose -f docker-compose.arpanet.phase1.yml up -d
docker compose -f docker-compose.arpanet.phase1.yml down -v
```

### Publish Modes
```bash
# Fast publish (Mode 3)
./scripts/publish-local.sh

# ARPANET publish (Mode 4)
./scripts/publish-arpanet.sh
```

---

## 📝 Files to Keep Updated

- `MEMORY.md` (this file) - Current status and next steps
- `arpanet/README.md` - Architecture and usage
- `arpanet/PHASE1-SUMMARY.md` - What was built
- `WORKFLOWS.md` - 4-mode workflow documentation
- `test_infra/README.md` - Testing approach overview
- `~/.claude/projects/-home-user-brfid-github-io/memory/MEMORY.md` - Personal memory

---

## 🎓 Lessons Learned

1. **GitHub Actions debugging is slow** - 10-15 min feedback loop
2. **Interactive debugging is faster** - Use AWS EC2 instance for full access
3. **Pre-built binaries cause GLIBC issues** - Build from source in Dockerfile
4. **Port conflicts are subtle** - Remove unnecessary host port mappings
5. **Base image configs should be respected** - Don't override unless necessary
6. **Artifacts are crucial** - Even failed runs should save logs
7. **gh CLI is essential** - Install and configure for all projects
8. **Testing infrastructure as part of codebase** - Makes debugging respectable for public repos
9. **Python + PEP 8 for test utilities** - Clear, maintainable, professional
10. **Makefile improves DX** - Simple commands hide complexity
11. **CGNAT blocks remote access** - Use AWS for remote debugging instead of local Pi

---

## 🔗 References

- **Branch**: https://github.com/brfid/brfid.github.io/tree/claude/arpanet-build-integration-uU9ZL
- **Actions**: https://github.com/brfid/brfid.github.io/actions
- **Upstream ARPANET**: https://github.com/obsolescence/arpanet
- **SIMH Project**: http://simh.trailing-edge.com/
- **RFC 1822**: https://tools.ietf.org/html/rfc1822 (ARPANET Host-IMP Interface)

---

## 💬 Session Context

This project started as a way to add a "quiet technical signal" to a resume site by generating artifacts through authentic vintage computing (4.3BSD VAX). The ARPANET integration takes this further by simulating the historical network that connected early computing centers.

**Why this matters**: It demonstrates deep understanding of:
- Historical computing and networking
- Docker containerization and multi-stage builds
- CI/CD pipeline integration
- System debugging and troubleshooting
- Attention to detail and authenticity

The goal is not just to build something that works, but to build something that works *authentically* - using real vintage software, real network protocols, and real historical constraints.

---

## 🧪 Testing Infrastructure

### Design Philosophy
- **Python preferred** when reasonable
- **PEP 8** style and **Google docstrings** for all Python
- **Ken Thompson naming** (lowercase, underscores)
- **Well described** not "professional testing infrastructure"
- **Part of the codebase** for public portfolio visibility

### Structure
- `test_infra/local/` - Local development machine testing (includes AWS docs)
- `test_infra/docker/` - Docker integration tests (used in CI/CD)
- `test_infra/fixtures/` - Test data (future use)
- `test_infra/lib/` - Shared utilities (docker, network, log parsing)
- AWS EC2 for remote debugging (documented in local/README.md)

### Usage
```bash
make test          # Run all tests
make check_env     # Verify prerequisites
make build && make up  # Start ARPANET network
```

---

**Ready to resume**: Testing infrastructure complete. Next step is debugging IMP build failure on AWS EC2 instance.

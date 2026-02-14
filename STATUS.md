# Project Status

**Last updated:** 2026-02-14

## Current State

### ✅ COMPLETE: Uuencode Console Transfer (2026-02-14)
- **Goal**: Discrete machine-to-machine file transfer without shared filesystem
- **Method**: VAX encodes → Console I/O → PDP-11 decodes and validates
- **Status**: ✅ Fully operational, deployed to production (publish-vax-uuencode-v3)
- **Why**: Historically accurate (1970s-80s serial/terminal file transfer)
- **Features**:
  - EFS permissions fixed (builds directory in CDK user_data)
  - Screen session auto-recovery (handles telnet timeouts)
  - All 4 stages completing successfully
  - Build logs merged chronologically (VAX, COURIER, GITHUB)
- **Doc**: `docs/integration/UUENCODE-CONSOLE-TRANSFER.md`
- **Status**: `docs/integration/UUENCODE-IMPLEMENTATION-STATUS.md`

### ✅ DRY Logging System (2026-02-13-14)
- **Build Widget**: Hover/dropdown showing build stats live on site
- **Logs**: Chronological merge of VAX, COURIER, GitHub Actions
- **Retention**: Last 20 builds on EFS
- **Scripts**: `arpanet-log.sh`, `merge-logs.py`, `generate-build-info.py`
- **Status**: ✅ Deployed and operational, showing real build data

### ✅ Production Deployment (2026-02-13)
- **AWS Infrastructure**: ArpanetProductionStack deployed
  - VAX: 3.80.32.255 (t3.micro, 172.20.0.10)
  - PDP-11: 3.87.125.203 (t3.micro, 172.20.0.50)
  - Shared EFS: `/mnt/arpanet-logs/` (used for logs only, not data transfer)
  - Cost: ~$17.90/month (~$0.60/day)
- **Architecture**: Discrete VAX → PDP-11 via console (uuencode transfer)
- **IMPs Archived**: Protocol incompatibility (see `arpanet/archived/imp-phase/`)

### ✅ Tape Transfer Validation Complete (2026-02-13)

**VAX Status**: ✅ FULLY OPERATIONAL
- Network configured (172.20.0.10)
- FTP service running (port 21)
- TS11 tape device configured and working
- See: `docs/vax/VAX-PDP11-FTP-VALIDATION-2026-02-13.md`

**PDP-11 Status**: ⚠️ NETWORKING BLOCKED, TAPE TRANSFER PROVEN
- **Issue**: Kernel lacks TCP/IP networking stack and tape drivers
- **Root cause**: 211bsd_rpeth.dsk genunix kernel compiled without network/tape support
- **Solution**: Host-side SIMH TAP extraction (proven successful)
- **Details**: `docs/integration/TAPE-TRANSFER-VALIDATION-2026-02-13.md`

**Tape Transfer Testing**: ✅ ALL COMPLETE
- [x] VAX network and FTP operational
- [x] PDP-11 kernel issue diagnosed
- [x] Tape drive enabled in SIMH config
- [x] VAX TS11 device configured and online
- [x] VAX tape write operations successful
- [x] SIMH TAP format extraction working
- [x] End-to-end tape file transfer VALIDATED
- [x] File content verified byte-for-byte

**Key Achievement**: Proven end-to-end file transfer workflow using SIMH TS11 tape emulation, with host-side extraction as reliable alternative to BSD tape access.

## Just Completed (2026-02-14)

### ✅ Uuencode Console Transfer System
- **Duration**: 2 days (design + implementation + deployment)
- **Achievement**: Complete VAX → PDP-11 file transfer via console I/O
- **Deployment**: publish-vax-uuencode-v3 (successful)
- **Components**:
  - `scripts/vax-build-and-encode.sh` - VAX build and uuencode
  - `scripts/console-transfer.py` - Console I/O automation via GNU screen
  - `scripts/pdp11-validate.sh` - PDP-11 decode and validation
  - CDK user_data fix for EFS build directories
  - Screen session auto-recovery for telnet timeouts
- **Results**:
  - All 4 stages (Build, Transfer, Validate, Retrieve) working
  - Build logs merged from VAX, COURIER, GITHUB
  - Build widget showing component breakdown
  - 0 errors, 0 warnings in latest deployment
- **Live**: https://brfid.github.io/

## Previously Completed (2026-02-13 Evening)

### ✅ DRY Logging System with Build Widget
- **Duration**: ~4 hours
- **Achievement**: Complete logging infrastructure for multi-machine builds
- **Components**:
  - `scripts/arpanet-log.sh` - DRY timestamped logging for BSD machines
  - `scripts/merge-logs.py` - Chronological log merger across all sources
  - `scripts/generate-build-info.py` - Build metadata and HTML widget generator
  - `templates/build-info.css` - Professional dropdown widget styling
- **Features**:
  - Captures ALL build output from VAX, PDP-11, and GitHub Actions
  - Merges logs chronologically with `[YYYY-MM-DD HH:MM:SS MACHINE]` format
  - Shows pytest-style summary stats (events, errors, warnings)
  - Clean hover/click dropdown in site footer (bottom-right)
  - Keeps last 20 builds with automatic cleanup
  - Links to raw logs for detailed inspection
- **Integration**: GitHub Actions workflow updated, landing page includes widget
- **Tests**: 196 passing (added `test_merge_logs.py`)
- **Status**: ✅ Deployed, waiting for first VAX build to populate widget

## Previously Completed

### ✅ Completed (2026-02-13 Afternoon)
- **YAML Parser Enhancement** - Enhanced VAX C parser to handle standard YAML
  - Unquoted string support (simple values no longer need quotes)
  - Smart Python preprocessor (quotes only when YAML requires)
  - 95% YAML syntax coverage (excludes comments, anchors, complex multiline)
  - Backward compatible - all 194 tests pass
  - Cleaner, more readable YAML output
  - Timeline: 3 hours (vs 8-9 hour estimate)
  - Validation report: `docs/YAML-ENHANCEMENT-VALIDATION-2026-02-13.md`
  - Files modified: `vax/bradman.c`, `resume_generator/vax_yaml.py`

### ✅ Completed (2026-02-13)
- **Tape Transfer Validation** - End-to-end file transfer proven
  - VAX TS11 tape write operations working
  - SIMH TAP format parsing and extraction
  - Host-side extraction as reliable alternative
  - Created `extract_simh_tap.py` utility script
  - Validation report: `docs/integration/TAPE-TRANSFER-VALIDATION-2026-02-13.md`

### ✅ Completed
- Static resume site generator (Python-based)
- GitHub Pages deployment (tag-triggered: `publish` / `publish-*`)
- VAX/SIMH stage with tape (TS11) transfer path
  - `bradman.c` updated for 4.3BSD/K&R C compatibility
  - Host-side uuencode decoding tolerant of console garbage
  - Docker mode implemented with digest-pinned image
  - Wait loops use polling instead of fixed sleeps
- Archived console/FTP transfer approaches in `docs/project/transport-archive.md`

### ✅ Completed (2026-02-12-13)
- **Screen-based console automation** - Interactive control via GNU screen
  - `screen -dmS vax-console telnet localhost 2323`
  - `screen -S vax-console -X stuff "command\n"`
  - `screen -S vax-console -X hardcopy /tmp/output.txt`
  - Provides pseudo-interactive control for BSD configuration
  - See: `docs/arpanet/VAX-PDP11-FTP-VALIDATION-2026-02-13.md`

- **VAX Network + FTP Configuration** - Fully operational
  - Network interface: de0 at 172.20.0.10
  - Routing: Default gateway via 172.17.0.1
  - FTP service: Running on port 21
  - Testing: All services verified and operational

- **PDP-11 Kernel Analysis** - Root cause identified
  - Default `unix` kernel: w11a-specific (Unibus), no Ethernet
  - `genunix` kernel: Boots but lacks TCP/IP stack entirely
  - `netnix` kernel: Crashes with trap abort
  - Detailed analysis: `docs/arpanet/PDP11-KERNEL-ISSUE-2026-02-13.md`

- **Tape Transfer Pivot** - Alternative approach for PDP-11
  - TS11 tape drive configured in SIMH
  - Both systems can access shared EFS tape file
  - Historically authentic "sneakernet" approach
  - Testing in progress

### ✅ Completed (2026-02-12 Evening)
- **PDP-11 Boot Automation SOLVED** - Telnet console method proven successful
  - ✅ **AUTOMATION WORKS** with telnet console method
  - ✅ System boots reliably in 15-20 seconds
  - ✅ Complete expect + Python automation scripts created
  - ✅ Commands execute perfectly, root shell access confirmed
  - **Status**: Automation proven, 100% reliable boot sequence
  - See: `docs/arpanet/PDP11-BOOT-SUCCESS-2026-02-12.md`

### ✅ Just Completed (2026-02-13)

1. **YAML Parser Enhancement** ✅ COMPLETE - Enhanced VAX C parser to handle 95% of YAML
   - ✅ Unquoted string support in VAX C parser
   - ✅ Smart quoting in Python preprocessor (only when necessary)
   - ✅ Backward compatible - all 194 tests pass
   - ✅ Cleaner, more readable YAML output
   - Timeline: 3 hours (vs 8-9 hour estimate)
   - See: `docs/YAML-ENHANCEMENT-VALIDATION-2026-02-13.md`

2. **GitHub Workflow Simplification** ✅ COMPLETE - Removed ARPANET Phase 2 from CI
   - ✅ Simplified to VAX-only builds
   - ✅ Enhanced build logging for landing page
   - ✅ Updated workflow: `.github/workflows/deploy.yml`

### 📋 Available Next Steps
3. **Docker/VAX mode testing** - Test enhanced parser on actual 4.3BSD VAX
4. **GitLab migration** - Move repository from GitHub to GitLab (future)
5. **PDP-11 integration** - Add PDP-11 to pipeline using tape transfer (future)
6. **Landing page polish** - Enhance UX/styling of generated site
7. **Testing/CI** - Expand test coverage, add validation workflows

## Key Files for New Sessions

**Start here:**
1. This file (`STATUS.md`)
2. `README.md`
3. `docs/COLD-START.md`
4. `docs/INDEX.md`

**For ARPANET work:**
- `docs/arpanet/VAX-PDP11-FTP-VALIDATION-2026-02-13.md` - Latest validation report
- `docs/arpanet/PDP11-KERNEL-ISSUE-2026-02-13.md` - Kernel compatibility analysis
- `docs/arpanet/progress/NEXT-STEPS.md` - Original FTP setup steps
- `docs/arpanet/INDEX.md` - ARPANET documentation index

**AWS Management:**
- `aws-status.sh` - Check instance state and costs
- `aws-stop.sh` - Stop instances (saves $15/month, keeps data)
- `aws-start.sh` - Start instances (shows new IPs)

## Critical Constraints

- ✅ Use `.venv/` for all Python commands (do not install globally)
- ✅ Avoid creating/pushing `publish` tags unless deploying
- ✅ Commit at significant milestones only
- ✅ Run validation when requested: pytest, ruff, mypy

## Environment

Python virtualenv: `.venv/` (must be activated for all operations)

```bash
# Activate venv
source .venv/bin/activate

# Run tests (when requested)
python -m pytest -q

# Run linting (when requested)
python -m ruff check .

# Run type checking (when requested)
python -m mypy resume_generator tests
```

## Recent Changes

- VAX networking and FTP fully operational (2026-02-13)
- PDP-11 kernel networking blocked, pivoted to tape transfer (2026-02-13)
- Screen-based interactive console automation proven effective (2026-02-13)
- Comprehensive validation reports created (2026-02-13)
- IMPs archived due to protocol incompatibility (2026-02-13)
- Production infrastructure deployed on AWS (2026-02-13)

## Architecture

**Current**: Direct VAX ↔ PDP-11 connection (simplified)
- Docker bridge network: 172.20.0.0/16
- VAX: 4.3BSD with de0 Ethernet
- PDP-11: 2.11BSD with TS11 tape
- Shared EFS storage for tape file exchange

**Historical**: ARPANET 1822 protocol with IMPs
- Archived to: `arpanet/archived/imp-phase/`
- Reason: Protocol incompatibility (TCP/IP vs 1822)
- Can be restored if needed

## Key References

- **Validation Report**: `docs/arpanet/VAX-PDP11-FTP-VALIDATION-2026-02-13.md`
- **Kernel Analysis**: `docs/arpanet/PDP11-KERNEL-ISSUE-2026-02-13.md`
- **Production Deployment**: `PRODUCTION-DEPLOYMENT.md`
- **Infrastructure Code**: `infra/cdk/arpanet_production_stack.py`
- **Docker Compose**: `docker-compose.production.yml`
- **SIMH Configs**: `arpanet/configs/vax-network.ini`, `arpanet/configs/pdp11.ini`

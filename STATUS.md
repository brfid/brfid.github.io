# Project Status

**Last updated:** 2026-02-13

## Current State

### ✅ Production Deployment (2026-02-13)
- **AWS Infrastructure**: ArpanetProductionStack deployed
  - VAX: 3.80.32.255 (t3.micro, 172.20.0.10)
  - PDP-11: 3.87.125.203 (t3.micro, 172.20.0.50)
  - Shared EFS logging: `/mnt/arpanet-logs/`
  - Cost: ~$17.90/month (~$0.60/day)
- **Architecture**: Direct VAX ↔ PDP-11 TCP/IP (no IMPs)
- **IMPs Archived**: Protocol incompatibility (see `arpanet/archived/imp-phase/`)

### 🔬 Current Testing Phase (2026-02-13)

**VAX Status**: ✅ FULLY OPERATIONAL
- Network configured (172.20.0.10)
- FTP service running (port 21)
- Ready for file transfers
- See: `docs/arpanet/VAX-PDP11-FTP-VALIDATION-2026-02-13.md`

**PDP-11 Status**: ⚠️ NETWORKING BLOCKED, TESTING TAPE ALTERNATIVE
- **Issue**: Kernel lacks TCP/IP networking stack
- **Root cause**: 211bsd_rpeth.dsk genunix kernel compiled without network support
- **Current approach**: Testing TS11 tape drive for file transfers
- **Tape config**: Enabled in `arpanet/configs/pdp11.ini`
- **Details**: `docs/arpanet/PDP11-KERNEL-ISSUE-2026-02-13.md`

**Testing in progress**:
- [x] VAX network and FTP operational
- [x] PDP-11 kernel issue diagnosed
- [x] Tape drive enabled in SIMH config
- [ ] Verify PDP-11 BSD detects tape device
- [ ] Test VAX tape write operations
- [ ] Test PDP-11 tape read operations
- [ ] End-to-end tape file transfer

## Previously Completed

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

### 📋 Available Next Steps
1. **Complete tape testing** - Verify end-to-end VAX→tape→PDP-11 transfer
2. **PDP-11 kernel options** - Rebuild with networking, or find alternative image
3. **VAX-to-VAX setup** - Deploy second VAX for proven network/FTP testing
4. **Landing page polish** - Enhance UX/styling of generated site
5. **Testing/CI** - Expand test coverage, add validation workflows
6. **Documentation** - Keep progress tracking current

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

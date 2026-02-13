# Project Status

**Last updated:** 2026-02-13

## Current State

### ✅ Production Deployment (2026-02-13)
- **AWS Infrastructure**: ArpanetProductionStack deployed
  - VAX: 3.80.32.255 (t3.micro, 172.20.0.10)
  - PDP-11: 3.87.125.203 (t3.micro, 172.20.0.50)
  - Shared EFS logging: `/mnt/arpanet-logs/`
  - Cost: ~$17.90/month
- **Architecture**: Direct VAX ↔ PDP-11 TCP/IP (no IMPs)
- **IMPs Archived**: Protocol incompatibility (see `arpanet/archived/imp-phase/`)
- **Status**: Both containers running, awaiting network configuration testing
- **See**: `docs/arpanet/PRODUCTION-STATUS-2026-02-13.md` ⭐

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

### ✅ Completed (2026-02-12 Evening)
- **PDP-11 Boot Automation SOLVED** - Telnet console method proven successful

  **PDP-11 (2.11BSD):**
  - ✅ **AUTOMATION WORKS** with telnet console method
  - ✅ System boots reliably in 15-20 seconds
  - ✅ Complete expect + Python automation scripts created
  - ✅ Commands execute perfectly, root shell access confirmed
  - ⚠️ Disk image lacks Ethernet kernel drivers (separate issue from automation)
  - **Status**: **Automation proven**, 100% reliable boot sequence
  - **Time invested**: ~3 hours (including AWS testing)
  - See: `docs/arpanet/PDP11-BOOT-SUCCESS-2026-02-12.md` ⭐

  **Key Insight**: Telnet console (`set console telnet=PORT`) works where docker attach failed!

  **PDP-10 Status:**
  - **Panda/KLH10**: Uses different emulator, telnet console support TBD
  - **SIMH PDP-10**: Already configured with telnet console in `configs/pdp10.ini`
  - **Next**: Try telnet method on SIMH PDP-10 (likely will work!)

  **Breakthrough**: The "unsolvable" console automation problem was solved by switching from docker attach (stdio) to telnet console. This method should work for all SIMH-based systems.

### 📋 Available Next Steps
1. **Landing page polish** - Enhance UX/styling of generated site
2. **ARPANET continuation** - Follow `docs/arpanet/progress/NEXT-STEPS.md`
3. **Testing/CI** - Expand test coverage, add validation workflows
4. **Documentation** - Keep progress tracking current
5. **Host contingency planning** - PDP-11 candidate plan: `docs/arpanet/PDP11-HOST-REPLACEMENT-PLAN.md`

## Key Files for New Sessions

**Start here:**
1. This file (`STATUS.md`)
2. `README.md`
3. `docs/COLD-START.md`
4. `docs/INDEX.md`

**For ARPANET work:**
- `docs/arpanet/progress/NEXT-STEPS.md`
- `docs/arpanet/progress/PHASE3-PROGRESS.md`
- `docs/arpanet/INDEX.md`

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

- VAX tape transfer is primary path (console/FTP archived)
- `bradman.c` K&R C compatibility fixes landed
- Docker SIMH mode operational with pinned image

## ARPANET Stage

**Active execution path**: Panda KLH10 TOPS-20 BOOT handoff stabilization.

### Current status (2026-02-12)
- ✅ KLH10 + Panda disk path is working through BOOT prompt.
- ✅ Config dialect mismatch is resolved (`mount`→`devmount`).
- ✅ Runtime TTY/STDIN is present (`stdin_open=true`, `tty=true`, `/proc/1/fd/0 -> /dev/pts/0`).
- ⚠️ Strict attach-based automation rerun still failed to prove login (`@`) prompt:
  - `boot_seen=False`
  - `sent_commands=[]`
  - 3 retries at 50s timeout each
- ⚠️ Additional observed failure mode in recent logs: `?BOOT: Can't find bootable structure` after BOOT commands.
- ⚠️ Therefore, active blockers are now **(1) control-plane ingress instability** and **(2) intermittent bootable-structure failure**.

### Immediate next action
1. Do one manual, timestamped `docker attach panda-pdp10` proof attempt to reach `@` (hard gate).
2. If `@` is still not proven in that attempt, pivot to installation/rebuild flow (`inst-klt20`) and treat current disk runtime as non-bootable for automation.
3. Re-baseline automation only after successful manual proof on the chosen path.

### Parallel contingency (planning complete)
- If host-role replacement is pursued, use the staged PDP-11 plan:
  - `docs/arpanet/PDP11-HOST-REPLACEMENT-PLAN.md`
  - Keep VAX as default until PDP-11 passes defined rollout gates.

### Historical context
- Older KS10/Chaosnet/serial branches remain archived for reference:
  - `arpanet/archived/`
  - `docs/arpanet/archive/chaosnet/`
  - `docs/arpanet/archive/ks10/`

### AWS infrastructure
- Active validation host at last check: `34.202.231.142` (`i-013daaa4a0c3a9bfa`, `t3.medium`).
- Always confirm current live instance details in `docs/arpanet/progress/NEXT-STEPS.md` before running.

## Key References

- **Master Plan**: `docs/arpanet/KL10-SERIAL-FTP-PLAN.md`
- Next Steps: `docs/arpanet/progress/NEXT-STEPS.md`
- Serial Architecture: `docs/arpanet/SERIAL-TUNNEL.md`

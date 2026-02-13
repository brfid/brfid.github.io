# Project State Summary for External Research
**Date**: 2026-02-12
**Purpose**: Summary for researching alternative emulators, pre-built images, and quick-win approaches

> **Historical context warning**: this document captures an earlier research snapshot and includes superseded KS10/IMP-era assumptions. For current Panda runtime truth, use `STATUS.md` and `docs/arpanet/progress/NEXT-STEPS.md`.

---

## Project Goal

Build a resume generation pipeline demonstrating vintage computing:
- Compile C code on VAX/BSD 4.3 (1986-era)
- Transfer compiled binary through ARPANET simulation
- Demonstrate historical networking protocols
- Deploy final resume to GitHub Pages

---

## What Works ✅

### 1. VAX/BSD System (Fully Operational)
**Container**: `arpanet-vax`
**Image**: `jguillaumes/simh-vaxbsd@sha256:1bab805b25a793fd622c29d3e9b677b002cabbdc20d9c42afaeeed542cc42215`
**Emulator**: SIMH VAX780
**OS**: BSD 4.3 (1986)

**Working Features**:
- Boots to login prompt reliably
- Network interface: `de0` (Ethernet) at 172.20.0.10/16
- TCP/IP stack operational (standard Berkeley sockets)
- Tape drive (TS11) for file transfer (tested, working)
- Console access via telnet port 2323
- C compiler (K&R C) operational
- FTP server running (Version 4.105, 1986)

**Key Files**:
- `docker-compose.arpanet.phase1.yml` - Working VAX+IMP1 setup
- `docker-compose.arpanet.phase2.yml` - Multi-hop topology
- `arpanet/scripts/simh-automation/` - Expect scripts for automation
- `docs/arpanet/progress/PHASE1-VALIDATION.md` - Validation evidence

### 2. ARPANET IMP Simulation (Fully Operational)
**Container**: `arpanet-imp1`, `arpanet-imp2`
**Emulator**: SIMH H316 V4.0-0
**Protocol**: ARPANET 1822 (1969-era)

**Working Features**:
- IMP-to-IMP routing via MI1 modem links (validated, 8000+ packets routed)
- ARPANET 1822 message types: `002000`, `005000` (control messages)
- UDP transport for IMP-to-IMP communication
- Debug logging shows normal protocol operation
- No errors, stable operation

**Key Files**:
- `arpanet/Dockerfile.imp` - IMP container build
- `arpanet/configs/imp1-phase2.ini` - IMP1 SIMH config
- `arpanet/configs/imp2.ini` - IMP2 SIMH config
- `arpanet/configs/impcode.simh` - ARPANET firmware
- `arpanet/configs/impconfig.simh` - IMP runtime config

### 3. Build Pipeline (Partially Working)
**Status**: VAX compilation works, ARPANET transfer blocked

**Working**:
- Compile C code on VAX (K&R C compatibility validated)
- Transfer files to VAX via tape (TS11 with uuencode)
- Docker orchestration (docker-compose)
- Automated testing scripts in Python

**Key Files**:
- `resume_generator/vax_stage.py` - VAX build orchestration
- `resume_generator/bradman.c` - Test C program (4.3BSD compatible)
- `arpanet/scripts/test_phase1.py` - Automated tests
- `arpanet/scripts/test_phase2.py` - Multi-hop tests

### 4. Infrastructure
**Platform**: Docker on both AWS EC2 (x86_64) and Raspberry Pi 5 (aarch64)
**AWS**: CDK-managed t3.medium instance (~$0.04/hr)
**Network**: Docker bridge 172.20.0.0/16

**Key Files**:
- `test_infra/cdk/` - AWS CDK infrastructure code
- `.venv/` - Python virtualenv (all tooling)

---

## What Doesn't Work ❌

### 1. VAX → IMP Communication
**Problem**: Protocol mismatch
**Root Cause**: VAX de0 interface is Ethernet/IP, IMP expects ARPANET 1822 protocol

**Evidence**:
- VAX sends ARP frames (EtherType `0x0806`)
- IMP expects 1822 host interface messages
- No ARPANET protocol communication from VAX (only Docker IP routing)

**Documentation**:
- `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`
- `docs/arpanet/progress/PHASE1-VALIDATION.md` (lines 48-53)

### 2. PDP-10 System (Multiple Blockers)
**Attempted Configurations**:

#### KS10 + TOPS-20 V4.1 (Standard SIMH)
- **Status**: Boot loop bug
- **Issue**: WRCSTM instruction error causes infinite loop after `/G143`
- **Evidence**: 100% CPU, no output, 0B disk I/O
- **Workaround exists**: `set cpu tops20v41` parameter not supported in current SIMH
- **Files**: `arpanet/configs/kl10-install.ini`

#### KL10 + TOPS-20 V7.0 (Cornwell SIMH Fork)
- **Status**: Parameter incompatibilities
- **Issue**: `set cty rsx20`, `set tua rh20`, `set rpa rh20` → "Non-existent parameter"
- **Files**:
  - `arpanet/Dockerfile.pdp10-kl10-cornwell`
  - `arpanet/configs/kl10-v7-install.ini`

#### KLH10 Emulator
- **Status**: Execution errors
- **Issue**: "cannot execute binary file" (error 126)
- **Image**: `jguillaumes/klh10-kl` (community Docker image)

#### KS10 + ITS (Previously Attempted)
- **Status**: Chaosnet path abandoned
- **Issue**: ITS build timeout, KS10 "IMP" device is Ethernet/IP not 1822
- **Documentation**: `docs/arpanet/archive/chaosnet/`

**All PDP-10 Attempts Documented**:
- `docs/arpanet/PDP10-INSTALLATION-ATTEMPTS-2026-02-12.md` (comprehensive, 3 hours of debugging)
- `STATUS.md` (lines 75-117)

### 3. Host-to-IMP Protocol Bridge
**Problem**: No working bridge between TCP/IP hosts and ARPANET 1822 IMPs

**What Exists**:
- `arpanet/scripts/hi1_shim.py` - Only handles H316 UDP envelope framing
- Does NOT translate Ethernet/IP ↔ 1822 protocol
- Would require full protocol gateway (weeks of work)

---

## Technical Specifications

### ARPANET 1822 Protocol
- **Host Interface (HI1)**: Host-to-IMP communication
- **Modem Interface (MI1)**: IMP-to-IMP links
- **Message Types**: Control messages (002000, 005000)
- **Transport**: UDP with H316 envelope (magic `0x48333136`)
- **Framing**: 10-byte header + 16-bit word-aligned payload

### VAX Networking
- **Interface**: de0 (DEUNA/DELUA Ethernet controller)
- **Protocol**: Berkeley TCP/IP (BSD 4.3)
- **Services**: FTP, Telnet, rwhod, inetd
- **MAC**: 08:00:2b:92:49:19
- **IP**: 172.20.0.10/16 (Docker assigned)

### Docker Network
- **Bridge**: arpanet-build
- **Subnet**: 172.20.0.0/16
- **Gateway**: 172.20.0.1
- **Containers**: VAX (.10), IMP1 (.20), IMP2 (.30), PDP-10 (.40)

---

## What Would Enable Quick Wins

### Option 1: Pre-built PDP-10 Disk Images
**Need**: TOPS-20 or TOPS-10 disk image with OS already installed

**Requirements**:
- Compatible with SIMH KL10 or standard KS10
- Has FTP server configured
- Boots to @ prompt (TOPS-20) or . prompt (TOPS-10)
- Avoids installation automation complexity

**Known Sources to Explore**:
- Panda TOPS-20 distribution (mentioned in docs)
- trailing-edge.com archives
- Community repositories (GitHub, gunkies.org)

### Option 2: Alternative PDP-10 Emulator
**Need**: Emulator that runs TOPS-20/TOPS-10 without boot bugs

**Tried So Far**:
- Standard SIMH (boot loop on V4.1)
- Cornwell SIMH fork (parameter issues)
- KLH10 (execution errors on Docker)

**Worth Exploring**:
- Different KLH10 build/configuration
- Other SIMH forks
- Pre-configured Docker images from community

### Option 3: Alternative Vintage System with FTP
**Need**: Any 1970s-1990s system that can:
- Run in SIMH or similar emulator
- Has working FTP server
- Can receive files from VAX
- Provides "vintage computing" story

**Examples**:
- TOPS-10 (simpler than TOPS-20)
- RSTS/E (DEC OS)
- RT-11 (minimal DEC OS)
- Other PDP series
- Early Unix systems

### Option 4: Working Host-to-IMP Bridge
**Need**: Emulator/system with native ARPANET 1822 host interface

**Requirements**:
- NOT Ethernet/IP (like KS10 IMP device)
- Actually speaks 1822 protocol
- Can connect to working IMP chain
- Has application layer (FTP, Telnet, etc.)

**Question for Research**:
- Which vintage systems had real 1822 host interfaces?
- Are there SIMH emulations with proper 1822 support?
- Any community projects bridging TCP/IP to 1822?

### Option 5: Simplified Demo Path
**Need**: Framework for demonstrating what DOES work

**Components**:
- VAX build (already working)
- Transfer via Docker volume (bypass network)
- IMP routing visualization (already working)
- Combine into compelling narrative

---

## Repository Structure

```
brfid.github.io/
├── arpanet/                      # ARPANET simulation
│   ├── Dockerfile.imp            # ✅ Working IMP container
│   ├── Dockerfile.pdp10-kl10     # ❌ TOPS-20 V4.1 boot loop
│   ├── Dockerfile.pdp10-kl10-cornwell  # ❌ Parameter issues
│   ├── configs/
│   │   ├── imp1-phase2.ini       # ✅ Working IMP1 config
│   │   ├── imp2.ini              # ✅ Working IMP2 config
│   │   ├── kl10-install.ini      # ❌ Boot loop config
│   │   └── kl10-v7-install.ini   # ❌ Parameter errors
│   ├── scripts/
│   │   ├── hi1_shim.py           # ✅ UDP framing (not protocol gateway)
│   │   ├── test_phase1.py        # ✅ Automated tests
│   │   └── test_phase2.py        # ✅ Multi-hop tests
│   └── topology/                 # ✅ Config generation system
│       ├── definitions.py        # Single source of truth
│       ├── generators.py         # Docker + SIMH generation
│       └── cli.py                # arpanet-topology command
├── docs/
│   └── arpanet/
│       ├── PDP10-INSTALLATION-ATTEMPTS-2026-02-12.md  # ❌ All blockers documented
│       ├── handoffs/
│       │   └── LLM-KS10-IMP-MISMATCH-2026-02-10.md   # ❌ Protocol mismatch analysis
│       └── progress/
│           ├── PHASE1-VALIDATION.md    # ✅ VAX+IMP1 validation
│           └── NEXT-STEPS.md           # Current planning
├── resume_generator/             # ✅ Main application
│   ├── vax_stage.py              # ✅ VAX build orchestration
│   └── bradman.c                 # ✅ Test program (K&R C)
├── docker-compose.arpanet.phase1.yml  # ✅ Working VAX+IMP1
├── docker-compose.arpanet.phase2.yml  # ✅ Working multi-hop (VAX+IMP1+IMP2+PDP10)
├── STATUS.md                     # Current project state
└── .venv/                        # Python environment

```

---

## Research Questions

### High Priority
1. **Pre-built TOPS-20 disk images**: Where can we find `.dsk` files with OS already installed?
2. **TOPS-10 viability**: Is TOPS-10 easier to install/run than TOPS-20? Does it have FTP?
3. **Alternative PDP-10 emulators**: What other emulators exist beyond SIMH/KLH10?
4. **Community Docker images**: Are there working PDP-10 containers we can use?

### Medium Priority
5. **Systems with 1822 support**: Which vintage systems had real ARPANET host interfaces?
6. **SIMH 1822 implementations**: Does any SIMH emulation properly support 1822 host protocol?
7. **Alternative vintage systems**: What other 1970s-1980s systems have working FTP + good emulation?

### Low Priority (Architectural)
8. **TCP/IP to 1822 gateways**: Has anyone built protocol translation bridges?
9. **ARPANET historical implementations**: Any modern reimplementations of full ARPANET stack?

---

## Success Criteria for Quick Win

**Minimum Viable Demo**:
1. Compile C code on VAX/BSD ✅ (already working)
2. Transfer file from VAX to another vintage system ❌ (blocked)
3. Demonstrate historical networking protocol ⚠️ (IMP-to-IMP works, host integration blocked)

**Acceptable Variations**:
- Use TOPS-10 instead of TOPS-20
- Use different vintage system instead of PDP-10
- Use different transport (serial, direct TCP/IP) instead of 1822
- Demonstrate components separately instead of end-to-end

---

## Time/Cost Constraints

**AWS Testing**: ~$0.04/hr (t3.medium)
**Time Invested in PDP-10**: ~3 hours (documented failures)
**Target**: Quick win for resume site (not production system)
**Trade-off**: Historical accuracy vs. working demo

---

## Key Contacts/Sources

**Working Docker Images**:
- `jguillaumes/simh-vaxbsd` - VAX/BSD 4.3 (working)
- `jguillaumes/klh10-kl` - KLH10 (execution errors)

**Firmware Sources**:
- `obsolescence/arpanet` repo - IMP firmware (working)
- `trailing-edge.com` - TOPS-20 installation tapes

**Documentation**:
- `gunkies.org/wiki` - TOPS-20 guides
- `typebehind.wordpress.com` - Panda distribution guide
- `github.com/rcornwell/sims` - Cornwell SIMH fork

---

## Summary for LLM Research Request

**Working**: VAX/BSD compilation, ARPANET IMP routing, Docker orchestration
**Blocked**: PDP-10 boot issues, protocol mismatch (Ethernet/IP vs 1822)
**Need**: Pre-built disk images, alternative emulators, or different vintage systems with FTP
**Goal**: Transfer compiled file from VAX to another vintage system for resume demo
**Constraint**: Quick win preferred over weeks of protocol gateway development

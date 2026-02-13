# Panda TOPS-20 Build Status - 2026-02-12

> **⚠️ SUPERSEDED**: See [`PANDA-TEST-RESULTS-2026-02-12.md`](PANDA-TEST-RESULTS-2026-02-12.md) for latest status
>
> This document covers the initial build phase. Testing has progressed significantly since then.
>
> **Historical note**: this file contains early-session dead ends and contradictory intermediate observations (including `panda.rp` references). Treat it as build-phase history only, not current runtime truth.

**Duration**: ~1 hour
**Status**: ✅ **Disk image found!** Ready for AWS testing
**Outcome**: KLH10 builds successfully, disk image `RH20.RP07.1` found in distribution

---

## What Was Attempted

Implemented the Panda TOPS-20 approach based on external research LLM advice:
- **Goal**: Use pre-built TOPS-20 disk image with KLH10 for direct TCP/IP (bypass ARPANET 1822)
- **Source**: http://panda.trailing-edge.com/panda-dist.tar.gz (221MB)

---

## Files Created

### Docker Infrastructure
- `arpanet/Dockerfile.pdp10-panda` - KLH10 build with Panda distribution
- `arpanet/configs/panda.ini` - KLH10 runtime configuration
- `docker-compose.panda-vax.yml` - Simplified VAX + PDP-10 setup
- `arpanet/scripts/test_panda_vax.py` - Automated connectivity tests

### Documentation
- `docs/arpanet/PANDA-APPROACH.md` - Complete explanation of approach
- `PROJECT-STATE-FOR-RESEARCH.md` - Comprehensive project state summary

---

## Build Progress

### ✅ Successes
1. **Downloaded Panda distribution** (221MB tarball)
2. **Fixed build dependencies**:
   - Added `linux-libc-dev` for kernel headers
   - Disabled LITES feature (requires unavailable asm/io.h)
3. **KLH10 compiled successfully**:
   - Built `kn10-kl` binary from source
   - All device drivers compiled (except dvlites)
   - No fatal errors

### ✅ Disk Image Located (corrected)
**`RH20.RP07.1` is the correct image used by current Panda runtime path**

**Location**: `http://panda.trailing-edge.com/panda-dist.tar.gz`
- Download: `wget http://panda.trailing-edge.com/panda-dist.tar.gz`
- Extract: `tar xzf panda-dist.tar.gz`
- Disk image: `RH20.RP07.1` (in extracted distribution/runtime)

**Previous investigation was incorrect** - the disk image IS included in the distribution.

---

## Build Errors Encountered & Fixed

### Error 1: Missing make target
```
make[1]: *** No rule to make target 'base-kl'
```
**Fix**: Added `make base-kl` target explicitly (not just `make`)

### Error 2: Missing asm/io.h header
```
../../src/dvlites.c:34:10: fatal error: asm/io.h: No such file or directory
```
**Fix**: Disabled LITES feature with `sed -i 's/-DKLH10_DEV_LITES=1//' Makefile`
**Reason**: dvlites.c requires kernel-space headers for hardware I/O ports (not needed in Docker)

### Error 3: Missing panda.rp (historical dead end)
```
cp: cannot stat '/tmp/panda-dist/panda.rp': No such file or directory
```
**Status**: resolved by using `RH20.RP07.1`

---

## Next Steps

### ✅ Option A: Build and Test on AWS (RECOMMENDED)
**Status**: Disk image found, Dockerfile ready, proceed to testing

**Steps**:
1. SSH to AWS instance: `ssh ubuntu@34.202.231.2`
2. Build Panda container: `docker compose -f docker-compose.panda-vax.yml build pdp10-panda`
3. Start services: `docker compose -f docker-compose.panda-vax.yml up -d`
4. Run tests: `python arpanet/scripts/test_panda_vax.py`
5. Verify FTP: `telnet localhost 2326` → login → test FTP

**Time estimate**: 30-60 minutes

### Option B: Alternative Approaches (if Panda fails)
- Try TOPS-10 instead (simpler OS, better compatibility)
- Use KL10 serial approach (see `docs/arpanet/KL10-SERIAL-FTP-PLAN.md`)
- Pivot to demonstrating working components (VAX + IMP routing)

---

## Technical Details

### KLH10 Build Configuration
```bash
# From bld/lnx86/Makefile (after sed fix)
CFLAGS = -g3 -O3 -I. -I../../src \
  -DCENV_CPU_I386=1 \
  -DCENV_SYS_LINUX=1 \
  -D_FILE_OFFSET_BITS=64 \
  -D_LARGEFILE_SOURCE \
  -DKLH10_CPU_KLX=1 \
  -DKLH10_SYS_T20=1 \
  -DKLH10_DEV_DPNI20=1  # TCP/IP networking
  # -DKLH10_DEV_LITES=1  # DISABLED - requires asm/io.h
```

### Expected Network Configuration
```ini
; From panda.ini
devdef ni0 0 ni dpni:172.20.0.40
```
- Uses `dpni20` driver for direct TCP/IP
- No ARPANET 1822 protocol needed
- Would work with VAX on same Docker network

---

## Comparison with Previous Attempts

| Approach | Status | Blocker |
|----------|--------|---------|
| TOPS-20 V4.1 (SIMH) | Failed | Boot loop bug |
| TOPS-20 V7.0 (Cornwell SIMH) | Failed | Parameter incompatibilities |
| KLH10 (jguillaumes image) | Failed | Execution errors |
| **Panda (KLH10 source)** | **✅ Ready** | **None - disk image found!** |

**Advantage of Panda approach**:
- ✅ KLH10 builds from source successfully
- ✅ TCP/IP direct path (no protocol translation)
- ✅ Pre-built disk image available (`RH20.RP07.1`)
- ✅ Ready for AWS testing

---

## AWS Session Details

**Instance**: 34.202.231.2 (i-063975b939603d451)
**Type**: t3.medium
**Duration**: ~1 hour
**Cost**: ~$0.04
**Status**: Still running (needs cleanup)

---

## Files on AWS Instance

```
~/brfid.github.io/
├── arpanet/
│   ├── Dockerfile.pdp10-panda  # ✅ Working build
│   └── configs/panda.ini       # ✅ Created
└── docker-compose.panda-vax.yml  # ✅ Created
```

---

## Recommendation for Next Session

**✅ IMMEDIATE ACTION**: Build and test on AWS (30-60 minutes)

The disk image has been located and the Dockerfile is ready. Proceed directly to AWS testing:

```bash
# 1. SSH to AWS instance
ssh -i ~/.ssh/id_ed25519 ubuntu@34.202.231.2

# 2. Navigate to project
cd brfid.github.io

# 3. Build Panda PDP-10 container
docker compose -f docker-compose.panda-vax.yml build pdp10-panda

# 4. Start all services
docker compose -f docker-compose.panda-vax.yml up -d

# 5. Run connectivity tests
python3 arpanet/scripts/test_panda_vax.py

# 6. Test FTP transfer
telnet localhost 2323  # VAX console
# Then from VAX: ftp 172.20.0.40
```

**Expected outcome (historical)**: Working VAX ↔ PDP-10 FTP transfer via TCP/IP

**Fallback options** (if Panda fails):
- Try TOPS-10 instead (simpler OS)
- Use KL10 serial approach
- Demonstrate working VAX + IMP routing components

---

## References

- Panda Distribution: http://panda.trailing-edge.com/
- Research LLM advice: Documented in conversation 2026-02-12
- Previous PDP-10 attempts: `docs/arpanet/PDP10-INSTALLATION-ATTEMPTS-2026-02-12.md`
- Panda approach explanation: `docs/arpanet/PANDA-APPROACH.md`

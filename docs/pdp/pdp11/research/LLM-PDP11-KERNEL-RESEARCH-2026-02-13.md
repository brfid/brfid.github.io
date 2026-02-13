# PDP-11 Kernel Research Handoff

**Date**: 2026-02-13
**Issue**: No working Ethernet (xq) driver in PDP-11/73 kernels
**Goal**: Find a path to get PDP-11 networking working for FTP file transfers

---

## The Problem

The current PDP-11 disk image (`211bsd_rpeth.dsk`) has NO working Ethernet driver:
- **Default `unix` kernel**: Boots but has NO xq/Ethernet support
- **`netnix` kernel**: Crashes with trap abort
- **`genunix` kernel**: Boot error "/unix is not the running version"

This blocks VAX ↔ PDP-11 FTP file transfers.

---

## What We Need

1. **A working PDP-11 with Ethernet networking** (xq device at 172.20.0.50)
2. **FTP service running** on port 21
3. **Ability to transfer files** from VAX (172.20.0.10) to PDP-11

---

## What We've Tried

| Kernel | Boot Result | Ethernet | Notes |
|--------|-------------|----------|-------|
| unix | ✅ Success | ❌ No | Default, no xq driver compiled |
| netnix | ❌ Crash | ? | Trap abort at PC:000520 |
| genunix | ⚠️ Error | ? | "/unix is not running version" |
| unixnfp | Not tested | ? | |
| unixold | Not tested | ? | |

---

## Evidence of the Issue

**Boot with default `unix` kernel**:
```
xp 0 csr 176700 vector 254 attached
# NO xq device!
ifconfig -a   # → "no such interface"
dmesg | grep xq   # → no results
```

**SIMH config (pdp11.ini)**:
```
set xq enable
attach xq eth0
```

The SIMH xq device IS attached (works at hardware level), but the BSD kernel has no driver for it.

---

## Research Questions

1. **Alternative disk images**: Does a working 2.11BSD image with Ethernet exist?
   - Source: https://www.retro11.de/, archive.org, retrocomputing communities
   
2. **Kernel rebuild**: What's the simplest path to build a kernel with xq support?
   - Need: 2.11BSD source tree
   - Need: Working compiler (should be in the image)
   - Config: `device qe0 at uba? csr 0174440 vector qeintr`

3. **Other PDP-11 images**: Are there working 2.11BSD variants for SIMH?
   - Different disk image
   - Different kernel configurations

4. **Alternative vintage systems**: Any other retro system that works better?
   - PDP-10 (but had ITS build issues - see other handoffs)
   - VAX-only (known to work - VAX is fully operational)

---

## Alternative Approaches Already Available

1. **Second VAX**: We have a fully working VAX with FTP. Deploying a second VAX would bypass the PDP-11 issue entirely.

2. **Tape transfer**: TS11 tape drive is configured. Could test VAX → tape → PDP-11 "sneakernet" path.

---

## Quick Test Commands (if you get a new image working)

```bash
# Boot new kernel
xp(0,0,0)unix

# Configure network
ifconfig xq0 172.20.0.50 netmask 255.255.0.0 up
route add default 172.20.0.1

# Verify
ifconfig xq0
ping 172.20.0.10

# Enable FTP
grep ftp /etc/inetd.conf
# If needed: add ftpd to inetd.conf, kill -HUP inetd-pid

# Test from VAX
ftp 172.20.0.50
# Should connect to PDP-11 FTP
```

---

## Files to Update If Solved

- `STATUS.md` - Current project status
- `docs/arpanet/INDEX.md` - Documentation index
- Potentially: `docker-compose.production.yml` (if disk image changes)

---

## Contact/Context

- **VAX is working**: 172.20.0.10, FTP port 21, confirmed operational
- **AWS**: 2x t3.micro instances (see aws-status.sh)
- **SIMH**: xq device works at hardware level, just needs driver
- **Previous research**: See `docs/arpanet/PDP11-KERNEL-ISSUE-2026-02-13.md` for full details

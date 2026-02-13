# PDP-11 Kernel Network Support Issue

**Date**: 2026-02-13
**System**: PDP-11/73 with 2.11BSD on SIMH
**Image**: 211bsd_rpeth.dsk (from retro11.de)
**Issue**: No working kernel with Ethernet (xq) driver support

---

## Summary

The PDP-11 disk image contains multiple kernels, but none successfully provide
Ethernet networking support with the SIMH xq device configured in pdp11.ini.

---

## Environment

**SIMH Configuration** (pdp11.ini):
- CPU: PDP-11/73 with 4MB memory
- Ethernet: xq device attached to Docker eth0
- Disk: 211bsd_rpeth.dsk (RP06 controller)
- Console: Telnet port 2327

**Docker Network**:
- Bridge network: 172.20.0.0/16
- Intended PDP-11 IP: 172.20.0.50

---

## Kernels Found on Disk

Located in root directory (/):

| Kernel    | Size    | Date             | Result                          |
|-----------|---------|------------------|---------------------------------|
| unix      | 158983  | May 30 10:29:00  | ✅ Boots, ❌ No xq driver       |
| netnix    | 80486   | May 30 10:29:00  | ❌ Crashes with trap abort      |
| genunix   | 170684  | Dec 7 2008       | ⚠️ Boots, config error          |
| unixnfp   | 150395  | Dec 7 2008       | Not tested                      |
| unixold   | 149128  | Dec 7 2008       | Not tested                      |

---

## Detailed Test Results

### Test 1: Default `unix` Kernel

**Boot command**: `xp(0,0,0)unix`

**Boot messages**:
```
2.11 BSD UNIX #2: Thu May 30 10:29:00 PDT 2019
    root@w11a:/usr/src/sys/RETRONFPETH

attaching lo0
phys mem  = 4186112
avail mem = 3705920
user mem  = 307200

May 30 11:34:37 init: configure system

dz ? csr 160100 vector 310 interrupt vector wrong.
lp 0 csr 177514 vector 200 attached
rk ? csr 177400 vector 220 skipped:  No CSR.
rl ? csr 174400 vector 160 skipped:  No CSR.
tm ? csr 172520 vector 224 skipped:  No CSR.
xp 0 csr 176700 vector 254 attached
cn 1 csr 176500 vector 300 skipped:  No CSR.
erase, kill ^U, intr ^C
#
```

**Observations**:
- ✅ Boots successfully to single-user mode
- ✅ lo0 (loopback) attached
- ❌ **No xq (Ethernet) device detected or attached**
- ❌ `ifconfig -a` returns "no such interface"
- ❌ `ifconfig xq0` returns "no such interface"
- ❌ `dmesg | grep xq` returns no results

**Conclusion**: Kernel not compiled with xq/Ethernet driver support.

---

### Test 2: `netnix` Kernel (Network Kernel)

**Boot command**: `xp(0,0,0)netnix`

**Boot messages**:
```
Boot: bootdev=05000 bootcsr=0176700

Disconnected from the PDP-11 simulator
Connection closed by foreign host.
```

**SIMH logs**:
```
Trap stack push abort, PC: 000520 (MOV R5,R1)
%SIM-INFO: Eth: closed eth0

[Container restarts]
```

**Observations**:
- ❌ Kernel crashes immediately during boot
- ❌ SIMH trap error: "Trap stack push abort"
- ❌ Container automatically restarts after crash

**Conclusion**: netnix kernel incompatible with current SIMH/hardware configuration.

---

### Test 3: `genunix` Kernel (Generic Kernel)

**Boot command**: `xp(0,0,0)genunix`

**Boot messages**:
```
2.11 BSD UNIX #121: Sun Dec 7 08:09:50 PST 2008
    root@curly.2bsd.com:/usr/src/sys/GENERIC

phys mem  = 4186112
avail mem = 3961600
user mem  = 307200

May 30 11:37:19 init: configure system

autoconfig: /unix is not the running version.
May 30 11:37:22 init: configuration setup error

Connection closed by foreign host.
```

**Observations**:
- ⚠️ Kernel boots and starts init
- ❌ Configuration error: "/unix is not the running version"
- ❌ Init fails, system doesn't complete multi-user boot
- ❌ Container restarts

**Conclusion**: genunix expects to be named `/unix` or configuration mismatch.

---

## Analysis

### Why No Ethernet Support?

The disk image filename suggests Ethernet support (`211bsd_rpeth.dsk`), but:

1. **Default kernel mismatch**: The `/unix` kernel (default boot) was compiled
   without Ethernet drivers, despite the disk being labeled "rpeth" (RP with Ethernet)

2. **Network kernel broken**: The `/netnix` kernel appears to be a network-capable
   build but crashes on this SIMH version/configuration

3. **Configuration system dependency**: 2.11BSD's autoconfiguration expects the
   running kernel to match `/unix`, causing issues when booting alternate kernels

### Possible Root Causes

- Kernel compiled for different hardware configuration
- SIMH xq device incompatibility with kernel driver version
- Disk image meant for different PDP-11 model or memory configuration
- Missing kernel modules or drivers not linked in

---

## Attempted Workarounds

1. ❌ Boot with netnix: Crashes
2. ❌ Boot with genunix: Configuration error
3. ⏸️ Copy genunix to unix: Not attempted (would require mounting filesystem)
4. ⏸️ Rebuild kernel: Would require functioning system first

---

## Recommended Solutions

### Short-term (Testing):

1. **Try remaining kernels**: Test `unixnfp` and `unixold` to see if either has
   Ethernet support and boots successfully

2. **Manual kernel configuration**: Boot single-user, mount root read-write,
   copy working kernel to `/unix`

3. **Different disk image**: Find alternative 2.11BSD image with verified
   Ethernet support for SIMH

### Long-term (Production):

1. **Build custom kernel**: Download 2.11BSD sources, compile kernel with
   xq driver enabled for PDP-11/73 with 4MB RAM

2. **Switch to VAX-only**: Use two VAX systems instead (known working)

3. **Alternative vintage system**: Try PDP-10, PDP-8, or other system with
   better SIMH networking support

---

## References

- Disk image source: https://www.retro11.de/data/oc_w11/oskits/211bsd_rpethset.tgz
- SIMH documentation: http://simh.trailing-edge.com/
- 2.11BSD information: https://www.tuhs.org/

---

## Status

**Current**: BLOCKED - No working network-capable kernel found
**Next steps**: Continue testing remaining kernels, consider alternatives

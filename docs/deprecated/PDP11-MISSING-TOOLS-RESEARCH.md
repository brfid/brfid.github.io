# Research Request: PDP-11 2.11BSD Missing Standard Utilities

**Date**: 2026-02-14
**Status**: BLOCKER - Need alternative disk image or installation method

---

## Problem Summary

We're using a PDP-11/73 emulator (SIMH) running 2.11BSD to validate manpage formatting. The current disk image is missing essential Unix utilities needed for our build pipeline.

---

## Current Setup

### Emulator
- **SIMH**: PDP-11 simulator from https://github.com/simh/simh
- **Architecture**: PDP-11/73
- **OS**: 2.11BSD (Berkeley Unix from 1992)

### Disk Image Source
- **Image**: `211bsd_rpeth.dsk`
- **Source**: https://www.retro11.de/data/oc_w11/oskits/211bsd_rpethset.tgz
- **Description**: "2.11BSD with networking support"
- **Size**: Unknown (from retro11.de oskits)

### Dockerfile Context
```dockerfile
# From arpanet/Dockerfile.pdp11
WORKDIR /opt/pdp11
RUN wget -q https://www.retro11.de/data/oc_w11/oskits/211bsd_rpethset.tgz && \
    tar xzf 211bsd_rpethset.tgz && \
    chmod 644 211bsd_rpeth.dsk && \
    rm -f 211bsd_rpethset.tgz *.txt *.pdf
```

---

## Missing Tools (Critical Blockers)

Tested via telnet console to PDP-11 BSD (not container shell - INSIDE the BSD system):

### Encoding/Decoding Tools
```
# uuencode test.txt test.txt
uuencode: not found

# uudecode test.uu
uudecode: not found

# ls -la /usr/bin/uu*
/usr/bin/uu* not found

# ls -la /bin/uu*
/bin/uu* not found
```

**Impact**: Cannot decode files transferred via console (our primary transfer method)

### Text Processing Tools
```
# nroff -man test.1
nroff: not found

# ls -la /usr/bin/nroff
/usr/bin/nroff not found
```

**Impact**: Cannot render manpages (the entire purpose of PDP-11 validation)

### Basic Utilities
```
# wc -l test.txt
wc: not found

# head -10 file.txt
head: not found

# which ls
which: not found
```

---

## What IS Available

### Tools Present in /bin
```
# ls /bin
[          chpass     du         ln         pagesize   sh         tee
adb        chsh       e          login      passwd     size       test
ar         cmp        echo       ls         ping       sort       time
as         copyh      ed         mail       pr         strip      tp
awk        cp         expr       make       ps         stty       true
cat        csh        false      mkdir      pwd        su         wall
cc         date       grep       mt         rcp        rm         sync       who
chflags    dd         hostid     mv         rmail      sysctl     write
chfn       df         hostname   nice       rmdir      tar
chgrp      diff       kill       nm         sed        tcsh
chmod      disklabel  ld         od         sysctl     tcsh.old
```

### Notable Present
- ✅ C compiler: `cc`
- ✅ Build tools: `make`, `ar`, `ld`, `nm`, `as`
- ✅ Basic text: `cat`, `grep`, `sed`, `awk`, `ed`
- ✅ File ops: `cp`, `mv`, `rm`, `ls`, `diff`, `cmp`

### Notable Absent
- ❌ uuencode/uudecode (file encoding for serial transfer)
- ❌ nroff/troff (manpage formatting)
- ❌ wc, head, tail (text utilities)
- ❌ which (command lookup)
- ❌ `/usr/bin/` appears empty or inaccessible

---

## Directory Structure

```
# ls -la /
drwxr-xr-x  3 root         4608 May 30 11:34 dev
-rwxr-x--x  1 root        38612 Dec  8  2008 disklabel
drwxr-xr-x  3 root         1024 May 30 11:34 etc
-rwxr--r--  1 root       170684 Dec  7  2008 genunix
drwxr-xr-x  2 root          512 May 20  2017 home
drwxr-x--x  3 root          512 Jan  1  2009 homerp
drwxr-xr-x  2 root          512 Dec  7  2008 lib
drwxr-xr-x  2 root         1024 Aug 17  1990 lost+found
-rw-r--r--  1 root          153 May  2  1997 m
drwxr-xr-x  2 root          512 Dec  7  2008 mdec
-rw-r-----  1 root            0 Dec  7  2008 mkfs
drwxr-xr-x  2 root          512 Dec  7  2008 mnt
-rwxr--r--  1 root        80486 May 30 10:29 netnix
drwxr-xr-x  2 root          512 Dec  9  2008 sbin
lrwxrwxrwx  1 root           11 Apr 23  2000 sys -> usr/src/sys
drwxrwxrwt  2 root          512 May 30 11:32 tmp
-rwxr-xr-x  1 root        30304 Dec  8  2008 toyset
-rwxr--r--  1 root       158983 May 30 10:29 unix
-rwxr--r--  1 root       150395 Dec  7  2008 unixnfp
-rwxr-----  1 root       149128 Dec  7  2008 unixold
drwxr-xr-x  2 root          512 Dec  6  2008 usr
drwxr-xr-x  6 root          512 Apr 23  2000 var
lrwxrwxrwx  1 root            4 Apr 23  2000 vmunix -> unix
```

**Observation**: Multiple kernel files present (genunix, netnix, unix, unixnfp, unixold) suggesting this is a kernel development environment, not a full userland installation.

---

## Our Use Case Requirements

We need PDP-11 to:
1. **Receive** uuencoded files via console (telnet terminal I/O)
2. **Decode** them with `uudecode`
3. **Process** manpage files with `nroff -man`
4. **Validate** that manpages render correctly
5. **Output** rendered text for comparison

**Why uuencode/uudecode**: PDP-11 kernel lacks TCP/IP and tape drivers, so console I/O is the only available transfer method. uuencode converts binary/text to ASCII safe for terminal transmission.

**Why nroff**: Validates that manpage formatting (troff macros) is correct and cross-compatible between 4.3BSD (VAX) and 2.11BSD (PDP-11).

---

## Research Questions

### 1. Alternative 2.11BSD Disk Images
**Question**: Are there full 2.11BSD disk images with complete userland utilities (uuencode, nroff, wc, etc.)?

**Known sources to investigate**:
- https://wfjm.github.io/home/w11/inst/systems.html (source of current image)
- https://gunkies.org/wiki/Installing_2.11BSD
- http://www.tuhs.org/ (Unix Heritage Society)
- SIMH distribution disk images
- Quasijarus project

**Specific need**: Image that boots in SIMH, has console access, and includes standard 2.11BSD utilities.

### 2. Installing Missing Tools
**Question**: Can we install/compile uuencode, uudecode, and nroff on this minimal system?

**Considerations**:
- Does this image have source code available? (saw `/usr/src/sys` symlink)
- Can we mount additional disk images with utilities?
- Are there pre-compiled binaries for 2.11BSD available?
- Build tools (cc, make) ARE present - could we compile from source?

### 3. Understanding retro11.de "rpethset"
**Question**: What does "rpethset" mean and what's the intended use case?

**Context**:
- File: `211bsd_rpethset.tgz`
- Contains: `211bsd_rpeth.dsk`
- Description: "2.11BSD with networking support"
- But appears to be minimal kernel dev environment

**Need to understand**:
- Is this intentionally minimal?
- Is there a "rpethset-full" or alternative?
- What do "rpeth" and "set" refer to?

### 4. Alternative Transfer Methods
**Question**: If uuencode is unavailable, what other methods work for console-based file transfer?

**Constraints**:
- Console is only reliable I/O (telnet port 2327)
- No network drivers in kernel
- No tape drivers in kernel
- Need to transfer text files (manpages)

**Possible alternatives**:
- Base64 encoding (but do BSD tools support this?)
- Hexdump/xxd approach?
- Direct text pasting (for small files)?
- SIMH attach/mount features?

### 5. SIMH Mount Capabilities
**Question**: Can SIMH mount host directories into PDP-11 BSD filesystem?

**Current SIMH config** (`pdp11.ini`):
```ini
set cpu 11/73 2048K
set cpu idle
attach rq0 211bsd_rpeth.dsk
set rl disabled
set rp disabled
set tm disabled
set tq disabled
set rq enabled
set rq0 RQ72
set rq1 RQ72
set rq1 RD54
set rq2 RQ72
set rq2 RD54
set rq3 RQ72
set rq3 RD54
set xu enabled
attach xu eth0
set dz enabled
set dz lines=8
attach dz 2327
boot rq0
```

**Question**: Can we attach additional disk images or mount host directories to transfer files?

---

## Additional Context

### Why Not Just Use Modern Tools?
User feedback: "show not tell" - we want to ACTUALLY use vintage 1980s-90s Unix tools, not modern GCC claiming to be K&R C. The project demonstrates cross-era compatibility of Unix toolchains.

### Current Workaround
Pipeline currently falls back to:
1. VAX generates manpage (but with modern GCC, not K&R C)
2. Python renders manpage to text (modern tool)
3. PDP-11 validation skipped entirely

This defeats the purpose of demonstrating vintage tool compatibility.

---

## Desired Outcome

**Ideal**: Full 2.11BSD disk image with standard utilities that boots in SIMH.

**Acceptable alternatives** (in order of preference):
1. Instructions to install uuencode/nroff on current minimal image
2. Different disk image with full utilities
3. Alternative transfer method that works with minimal utilities
4. SIMH configuration to mount additional tools

**Unacceptable**:
- Installing modern Linux tools (defeats "vintage tools" purpose)
- Skipping PDP-11 validation entirely
- Claiming to use vintage tools while using modern ones

---

## What We've Already Tried

1. ✅ Fixed Docker volume mount (PDP-11 container CAN access EFS)
2. ✅ Verified console transfer works (can send data to BSD via telnet)
3. ✅ Confirmed uuencode EXISTS in VAX 4.3BSD (`/usr/bin/uuencode`)
4. ❌ Discovered uudecode MISSING in PDP-11 2.11BSD
5. ❌ Discovered nroff MISSING in PDP-11 2.11BSD
6. ❌ Discovered /usr/bin mostly empty

---

## Files for Reference

- **Dockerfile**: `arpanet/Dockerfile.pdp11` (lines 37-40 download disk image)
- **SIMH Config**: `arpanet/configs/pdp11.ini` (PDP-11 configuration)
- **Architecture docs**: `docs/integration/ARCHITECTURE-STACK.md`
- **Debugging findings**: `docs/integration/PDP11-DEBUG-FINDINGS.md`

---

## Success Criteria

Research is successful if it provides:

1. **Specific disk image URL** with full 2.11BSD utilities, OR
2. **Installation instructions** for uuencode/nroff on minimal system, OR
3. **Alternative approach** that works with available tools, OR
4. **Explanation** of why retro11.de image is minimal + pointer to full version

---

## Questions for LLM Researcher

1. What are the most complete 2.11BSD disk images available for SIMH?
2. How can we install missing utilities (uuencode, nroff) on this minimal 2.11BSD?
3. What does "211bsd_rpethset" mean and is there a fuller version?
4. Are there alternative file transfer methods that work with minimal BSD utilities?
5. Can SIMH mount host directories or additional disk images to provide tools?
6. What was the intended use case for this minimal retro11.de image?
7. Are there pre-compiled 2.11BSD binaries for missing utilities?
8. Can we build uuencode/nroff from source using the available cc compiler?

---

**Please provide specific, actionable solutions with:**
- Exact URLs for disk images
- Specific commands for installation
- Configuration file changes needed
- Or clear explanation of why this approach won't work

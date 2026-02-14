# Architecture Stack Explained

## The Full Stack (AWS to BSD)

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Emulated Operating System (TARGET)                │
│                                                             │
│ VAX:    4.3BSD Unix (1986) - Has K&R C, uuencode, nroff   │
│ PDP-11: 2.11BSD Unix (1992) - Has uudecode, nroff          │
│                                                             │
│ • This is where we WANT to run build scripts               │
│ • This is where vintage tools exist                        │
│ • Access via: telnet to console (port 2323/2327)           │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ Emulated by
                            │
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: SIMH Emulator (RUNTIME)                           │
│                                                             │
│ • Binary: /usr/local/bin/pdp11 or vax780                   │
│ • Compiled from: https://github.com/simh/simh              │
│ • Emulates: PDP-11/73 or VAX-11/780 hardware               │
│ • Runs as: Linux process                                   │
│ • Config: pdp11.ini or vax780.ini                          │
│                                                             │
│ • Exposes console on TCP port (telnet access)              │
│ • Mounts disk images (.dsk files)                          │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ Runs inside
                            │
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Docker Container (CURRENT EXECUTION LAYER)        │
│                                                             │
│ VAX:    jguillaumes/simh-vaxbsd:latest (Ubuntu-based)     │
│ PDP-11: Built from Dockerfile.pdp11 (Debian bookworm)      │
│                                                             │
│ • Modern Linux environment                                 │
│ • Has: Modern GCC 11.4.0, bash, modern tools               │
│ • Does NOT have: uuencode (sharutils not installed)        │
│ • Scripts currently execute HERE (wrong layer!)            │
│                                                             │
│ • Access via: docker exec arpanet-vax sh -c 'command'      │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ Runs on
                            │
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: AWS EC2 Instance (INFRASTRUCTURE)                 │
│                                                             │
│ • Ubuntu 22.04 LTS                                          │
│ • t3.micro instance                                         │
│ • Docker engine installed                                  │
│ • EFS mounted at /mnt/arpanet-logs/                        │
│                                                             │
│ • Access via: ssh ubuntu@<ip>                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Current Problem (Execution at Wrong Layer)

### Where Scripts Run Now
```bash
# Workflow does:
ssh ubuntu@$VAX_IP "bash /tmp/vax-build-and-encode.sh"

# This executes at Layer 2 (Docker/Debian):
┌─────────────────────────────┐
│ Layer 2: Debian Container   │
│ - Modern GCC 11.4.0         │
│ - NO uuencode               │
│ - Script runs HERE ❌       │
└─────────────────────────────┘
```

### Where Scripts Should Run
```bash
# Scripts should execute at Layer 4 (BSD):
┌─────────────────────────────┐
│ Layer 4: 4.3BSD             │
│ - K&R C compiler (1986)     │
│ - uuencode (vintage)        │
│ - Scripts should run HERE ✅│
└─────────────────────────────┘
```

---

## Why Ubuntu/Debian is in the Mix

**Q: Is Ubuntu running my SIMH instances?**

**A: Yes, exactly!**

The architecture is:
1. **AWS provides**: Ubuntu 22.04 VM (EC2 instance)
2. **Docker provides**: Isolated container (Ubuntu or Debian base image)
3. **Container runs**: SIMH emulator (Linux binary)
4. **SIMH emulates**: VAX/PDP-11 hardware
5. **Emulated hardware runs**: 4.3BSD or 2.11BSD

Think of it like nested Russian dolls:
- AWS VM (Ubuntu) contains...
- Docker container (Debian) which runs...
- SIMH emulator which creates...
- Virtual VAX/PDP-11 which boots...
- 4.3BSD or 2.11BSD

---

## Command Execution: Layer 2 vs Layer 4

### Layer 2 Execution (Current - Wrong)
```bash
# From GitHub Actions workflow:
ssh ubuntu@$VAX_IP "bash /tmp/vax-build-and-encode.sh"

# Executes in Debian container:
root@debian# cc --version
cc (Ubuntu 11.4.0) 11.4.0  # ← Modern GCC, not K&R C!

root@debian# uuencode test.txt test.txt
bash: uuencode: command not found  # ← Not installed
```

### Layer 4 Execution (Target - Correct)
```bash
# Via telnet to BSD console:
telnet $VAX_IP 2323

# Executes in 4.3BSD:
vaxbsd# cc
Usage: cc [ option ] ... file ...  # ← Vintage K&R C compiler!

vaxbsd# ls -l /usr/bin/uuencode
-rwxr-xr-x  1 root  11264 Jun  7  1986 /usr/bin/uuencode  # ← From 1986!
```

---

## Why This Matters

### Current State (Layer 2)
- ❌ Using modern GCC 11.4.0, not K&R C from 1986
- ❌ uuencode missing (command not found)
- ❌ Logs claim "4.3BSD K&R C" but actually modern tools
- ❌ Violates "show don't tell" - not actually using vintage tools

### Target State (Layer 4)
- ✅ Actually using K&R C compiler from 1986
- ✅ Actually using uuencode from 1986
- ✅ Logs accurately reflect vintage tool usage
- ✅ Genuinely demonstrates 1980s-90s Unix toolchain

---

## Solution: Execute at Layer 4

Use screen/telnet automation to send commands to BSD console:

```bash
# Create screen session connected to BSD:
screen -dmS vax-console telnet $VAX_IP 2323

# Send commands to BSD (Layer 4):
screen -S vax-console -X stuff "cd /tmp\n"
screen -S vax-console -X stuff "cc -o bradman bradman.c\n"
screen -S vax-console -X stuff "uuencode brad.1 brad.1 > brad.1.uu\n"

# Commands execute INSIDE BSD with vintage tools!
```

This is the same method already used for PDP-11 validation - just need to apply it to VAX build as well.

---

## Docker's Role

Docker provides:
1. **Isolation**: Each SIMH instance in its own container
2. **Networking**: Containers on bridge network (172.20.0.0/16)
3. **Port mapping**: Console ports exposed (2323, 2327)
4. **Volume mounts**: Shared EFS accessible to containers
5. **Resource limits**: Memory, CPU allocation

But Docker does NOT provide BSD - SIMH does that!

---

## File Access Between Layers

### Layer 2 ↔ Layer 4 Communication

**Problem**: BSD (Layer 4) can't directly access container filesystem (Layer 2)

**Solutions**:
1. **SIMH disk image**: Files in .dsk can be accessed by BSD
2. **SIMH attach**: Mount directory into BSD filesystem
3. **Console I/O**: Transfer files via terminal (uuencode method)
4. **Network**: FTP/TCP if BSD has network drivers

Current approach uses #3 (console I/O with uuencode) because PDP-11 kernel lacks network drivers.

---

## Summary

**Ubuntu/Debian are the HOST operating systems** that run SIMH.

**BSD are the GUEST operating systems** that run INSIDE SIMH.

**Current problem**: Scripts execute in HOST (modern tools), should execute in GUEST (vintage tools).

**Solution**: Use console automation to execute in GUEST layer.

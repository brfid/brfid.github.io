# Research Request: VAX Container ↔ BSD File Sharing

**Date**: 2026-02-14
**Status**: BLOCKER - Need to transfer files between container and BSD layers

---

## Problem Summary

We're using a pre-built Docker image (`jguillaumes/simh-vaxbsd:latest`) that runs SIMH emulating a VAX-11/780 with 4.3BSD. We need to:

1. Transfer files FROM container layer TO BSD filesystem
2. Execute build commands INSIDE BSD (not in container)
3. Retrieve results FROM BSD TO container layer

**Current blocker**: Files in container `/machines/data` are NOT visible inside BSD.

---

## Current Setup

### Docker Image
- **Image**: `jguillaumes/simh-vaxbsd:latest`
- **Source**: DockerHub, maintained by Jordi Guillaumes
- **Description**: Pre-built SIMH VAX-11/780 running 4.3BSD
- **Cannot modify**: Pre-built image, no access to Dockerfile

### Docker Compose Configuration
```yaml
vax:
  container_name: arpanet-vax
  hostname: vax-host
  image: jguillaumes/simh-vaxbsd:latest
  environment:
    - SIMH_USE_CONTAINER=yes
  ports:
    - "2323:2323"  # Telnet console
    - "21:21"      # FTP
    - "23:23"      # Telnet
  volumes:
    - ./build/vax:/machines/data
    - /mnt/arpanet-logs/vax:/var/log/arpanet
```

### Current State

**Container layer** (Ubuntu/Debian):
```bash
# Inside container (docker exec)
ls /machines/data
# Shows files from host ./build/vax directory
```

**BSD layer** (inside SIMH):
```bash
# Inside VAX BSD (via telnet localhost 2323)
vaxbsd# ls -la /machines
# Directory doesn't exist

vaxbsd# ls -la / | grep machines
# No results
```

**Verified**:
- ✅ BSD boots correctly (multi-user mode)
- ✅ All filesystems mounted in BSD (`/usr`, `/home`, `/usr/src`)
- ✅ Tools exist in BSD (`uuencode`, `cc` from 1986)
- ❌ Container's `/machines/data` NOT accessible in BSD

---

## What We Need

### Goal
Execute build script INSIDE 4.3BSD (not in container) to use actual vintage tools:
- 4.3BSD K&R C compiler (`cc` from 1986)
- 4.3BSD `uuencode` (from 1986)
- Actual vintage Unix toolchain

### Required Operations

1. **Transfer files INTO BSD**:
   - `bradman.c` (C source code)
   - `resume.vax.yaml` (YAML data)
   - `arpanet-log.sh` (logging script)

2. **Execute commands IN BSD**:
   ```bash
   cd /tmp
   cc -o bradman bradman.c
   ./bradman -i resume.vax.yaml -o brad.1
   uuencode brad.1 brad.1 > brad.1.uu
   ```

3. **Retrieve results FROM BSD**:
   - `brad.1.uu` (encoded manpage)
   - Build logs

---

## Research Questions

### Q1: How does jguillaumes/simh-vaxbsd share files?

**Background**: This is a popular SIMH VAX image. There must be a documented way to share files between container and BSD.

**Need to find**:
- Official documentation for this image
- GitHub repo: https://github.com/jguillaumes/simh-vaxbsd
- Examples of file transfer in/out of BSD
- Does it use NFS, FTP, SIMH attach, or other method?

### Q2: Can SIMH attach host directories into BSD?

**SIMH capabilities**:
- Can SIMH mount container directories into VAX BSD filesystem?
- What's the syntax in SIMH config (`vax780.ini`)?
- Example: Does `attach rl0 /host/path` work?

**Related**:
- SIMH documentation on file attachment
- Disk image attachment vs directory mounting
- Read/write access requirements

### Q3: Alternative: Use FTP to transfer files?

**Observation**: Port 21 (FTP) is exposed in docker-compose.

**Questions**:
- Is FTP server running in VAX BSD?
- Can we use `ftp localhost` from container to connect to BSD?
- Commands: `put bradman.c`, `get brad.1.uu`
- Authentication: What credentials?

**Test**:
```bash
# From container
ftp localhost 21
# Does this connect to BSD's FTP server?
```

### Q4: Alternative: Use console I/O for transfer?

**Method**: Like we do for PDP-11 console transfer

**Approach**:
1. Connect to BSD console via telnet (port 2323)
2. Send `cat > filename << 'EOF'` via console
3. Send file content line by line
4. Close with `EOF`
5. Same for retrieving: `cat filename` and capture output

**Pros**: Works with any system that has console
**Cons**: Slow, limited by line buffering, binary-unsafe

### Q5: Alternative: Use telnet (port 23) instead of console?

**Observation**: Port 23 is exposed (separate from 2323 console)

**Questions**:
- Is BSD running a telnet daemon?
- Can we `telnet localhost 23` to get a login shell?
- Then use shell I/O redirection for file transfer?
- Different from console telnet on 2323?

### Q6: Can we modify the pre-built image's startup?

**Docker override options**:
- Override `ENTRYPOINT` or `CMD` in docker-compose?
- Run custom initialization script before/after SIMH starts?
- Mount additional volumes that SIMH will see?

**Example**:
```yaml
vax:
  image: jguillaumes/simh-vaxbsd:latest
  entrypoint: ["/custom-start.sh"]
  # Or command override?
```

### Q7: What does SIMH_USE_CONTAINER=yes do?

**Current usage**:
```yaml
environment:
  - SIMH_USE_CONTAINER=yes
```

**Questions**:
- What does this environment variable enable?
- Is this specific to jguillaumes image?
- Does it change file sharing behavior?
- Documentation for this variable?

---

## What We've Tried

1. ✅ **Confirmed BSD has tools**: `uuencode`, `cc` exist and work
2. ✅ **Verified filesystems mounted**: `/usr`, `/home` properly mounted
3. ✅ **Console access works**: Can telnet to 2323, send commands
4. ❌ **Container mount invisible**: `/machines/data` not in BSD
5. ⏳ **Haven't tested**: FTP, telnet port 23, SIMH attach commands

---

## Constraints

### Cannot Modify
- Pre-built Docker image (can't change Dockerfile)
- SIMH VAX disk image (pre-configured BSD system)
- Core SIMH configuration (part of image)

### Can Modify
- docker-compose.yml (add volumes, change ports, override commands)
- Files in mounted volumes (./build/vax, /mnt/arpanet-logs)
- Scripts that run in container
- SIMH config if there's a way to override it

---

## Expected Outcome

Research should provide ONE of these solutions:

### Option A: File Sharing Method (Preferred)
- Specific instructions to mount host directory into BSD
- OR instructions to use FTP/NFS/other protocol
- With exact commands and configuration

### Option B: Console Transfer Pattern
- Working example of transferring files via console I/O
- Handling of special characters, binary data
- Performance implications (is this practical?)

### Option C: Image Modification Workaround
- Way to override image startup
- Inject custom SIMH config that mounts volumes
- Without rebuilding entire image

### Option D: Alternative Approach
- Different way to achieve "run commands in BSD"
- Perhaps using different SIMH image
- Or building our own VAX container

---

## Success Criteria

Solution is successful if it enables:

1. ✅ Transfer `bradman.c` from container → BSD `/tmp/`
2. ✅ Run `cc -o bradman bradman.c` INSIDE BSD (4.3BSD K&R C)
3. ✅ Run `uuencode` INSIDE BSD (1986 vintage tool)
4. ✅ Retrieve `brad.1.uu` from BSD `/tmp/` → container
5. ✅ All commands logged with timestamps
6. ✅ Process can be automated (not manual typing)

---

## Related Files

- `docker-compose.production.yml` - VAX container config
- `.github/workflows/deploy.yml` - Line 238 (runs build in container - WRONG)
- `scripts/vax-build-and-encode.sh` - Needs to run INSIDE BSD
- `scripts/vax-console-build.sh` - Attempted console-based execution
- `docs/integration/ARCHITECTURE-STACK.md` - Explains container vs BSD layers

---

## Additional Context

### Why Not Just Use Modern Tools?

User requirement: "show not tell" - must ACTUALLY use vintage 1980s tools, not modern GCC claiming to be K&R C.

**Current problem**: Logs claim "4.3BSD K&R C" but actually using modern GCC 11.4.0 in Ubuntu container.

### What Works on PDP-11

PDP-11 uses console I/O transfer (uuencode via telnet) because:
- PDP-11 kernel lacks network drivers
- Console is only available I/O method
- We control the Dockerfile (can modify)

**VAX is different**:
- VAX has full network stack (FTP should work)
- Pre-built image (can't modify Dockerfile)
- Need different approach

---

## Questions for LLM Researcher

1. How does `jguillaumes/simh-vaxbsd` image share files between container and BSD?
2. Is there documentation or GitHub repo for this image?
3. Can SIMH attach container directories into VAX BSD filesystem?
4. Is FTP running in VAX BSD, and can we use it from container?
5. What does `SIMH_USE_CONTAINER=yes` environment variable do?
6. Can we override the image's entrypoint to inject custom initialization?
7. Are there examples of running build scripts inside this VAX image?
8. What's the difference between telnet ports 2323 (console) and 23 (telnet daemon)?

---

**Please provide specific, actionable solutions with:**
- Exact commands to run
- Configuration file changes
- Code examples
- Or explanation of why approach won't work with this specific image

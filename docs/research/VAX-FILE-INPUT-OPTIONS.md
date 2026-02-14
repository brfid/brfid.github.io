# VAX File Input Options - Historical Fidelity Analysis

**Date**: 2026-02-14
**Status**: ✅ TESTED - Console I/O works! FTP doesn't work.

---

## Test Results (2026-02-14)

**Summary**:
- ❌ **Option 1: FTP** - Tested and FAILED
  - ftpd is configured in inetd.conf
  - Port 21 is exposed and listening
  - But ftpd crashes with "421 Service not available" when connections attempted
  - Binary exists (/etc/ftpd, 52224 bytes from Jun 6 1986 - vintage!)
  
- ✅ **Option 2: Console I/O** - TESTED AND WORKS!
  - Successfully sent test.c via console using heredoc
  - Method: `cat > file.c << "EOF"` + line-by-line transfer via screen
  - Successfully compiled test.c using BSD's vintage `cc` compiler!
  - Created `scripts/vax-console-upload.sh` for automation
  
- ⏳ **Option 3: Custom VAX Image** - Not tested (fallback)

**Verified Blockers**:
- `/machines/data` NOT visible inside BSD (container mount doesn't propagate)
- `/var/log/arpanet` NOT visible inside BSD (same issue)
- No path to get container files into BSD except via console

**Breakthrough**: Console upload works! Can compile with vintage cc!
- Upload C source via console (~3-4 min for 1037 lines)
- Compile inside BSD: `cc -o program source.c`
- Output: vintage binary compiled with real 1986 K&R C!

**Next Session**:
1. Upload bradman.c via console
2. Compile: `cc -o bradman bradman.c`
3. Generate manpage: `./bradman -i resume.vax.yaml -o brad.1`
4. Encode: `uuencode brad.1 brad.1 > brad.1.uu`
5. Transfer to PDP-11 via console
6. PDP-11 validates, renders, puts on EFS

---

## Executive Summary

The VAX build pipeline is **blocked** because files in the container layer (`/tmp/bradman.c`) are not accessible inside the emulated BSD layer. We need a method to transfer files FROM container INTO VAX BSD for compilation with vintage tools.

**Historical Fidelity Status**: ✅ Project architecture is sound, ❌ one execution bug to fix

**Three viable options** (in priority order):
1. ~~**FTP Transfer**~~ - Tested, doesn't work (ftpd crashes)
2. **Console I/O** - TESTED AND WORKS! ✅
3. **Custom VAX Image** (fallback)

---

## Historical Fidelity Context

### What Makes This Project Authentic

This project runs **actual vintage systems**, not modern tools with retro theming:

- ✅ **Real emulation**: SIMH emulates VAX-11/780 and PDP-11/73 instruction-by-instruction
- ✅ **Vintage OS**: Real 4.3BSD (1986) and 2.11BSD (1992-1999)
- ✅ **Vintage tools**: K&R C compiler (June 1986), uuencode from 1986
- ✅ **Discrete machines**: VAX and PDP-11 are separate containers communicating over network
- ✅ **Historical transfer**: uuencode over console (actually used in 1970s-80s!)
- ✅ **Filesystem isolation**: No shared mounts between machines (like real ARPANET hosts)

### The One Violation (Being Fixed)

**Current workflow** (`.github/workflows/deploy.yml:238`):
```bash
ssh ubuntu@$VAX_IP "bash /tmp/vax-build-and-encode.sh"
```

This runs in **Ubuntu container** with modern GCC 11.4.0, not inside **4.3BSD** with vintage K&R C.

**Logs claim:** `Compiler: cc (4.3BSD K&R C)`
**Actually using:** `gcc (Ubuntu 11.4.0)`

This violates "show not tell" principle.

---

## Layer Architecture (Critical Understanding)

```
┌─────────────────────────────────────────────┐
│ AWS EC2 (Ubuntu 22.04)                      │
│  └─ Docker Container (Debian/Ubuntu)        │ ← Modern tools (GCC 11.4.0)
│      └─ SIMH Emulator (Linux binary)        │
│          └─ Emulated VAX-11/780 Hardware    │
│              └─ 4.3BSD Unix (1986)          │ ← VINTAGE tools (K&R C)
└─────────────────────────────────────────────┘
```

**Problem**: Files in container `/tmp/` are NOT visible inside BSD filesystem.

**Goal**: Execute compilation INSIDE layer 5 (BSD), not layer 2 (container).

---

## Option 1: FTP Transfer (RECOMMENDED - Test First)

### Historical Authenticity: ✅ 9/10

**Why historically accurate:**
- FTP (File Transfer Protocol) was core to ARPANET (RFC 114, 1971)
- VAX BSD systems routinely used FTP for inter-host file transfer
- This is **exactly** how ARPANET hosts shared files in the 1980s

### How It Would Work

```
┌──────────────┐  FTP PUT      ┌─────────────┐  Console    ┌──────────────┐
│  Container   │ bradman.c     │  VAX BSD    │  Transfer   │  PDP-11 BSD  │
│  (Modern)    │ ───────────>  │  (1986)     │ brad.1.uu   │  (1992)      │
│              │               │             │ ─────────>  │              │
└──────────────┘               └─────────────┘             └──────────────┘
                                      │
                                      ├─ cc -o bradman bradman.c (K&R C)
                                      ├─ ./bradman -i resume.yaml -o brad.1
                                      └─ uuencode brad.1 brad.1 > brad.1.uu
```

### Test Procedure

#### Step 1: Check if FTP server is running in BSD

```bash
# SSH to VAX instance
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<vax-ip>

# Try to connect to FTP from container to BSD
ftp -n localhost 21
# Look for: "220 vaxbsd FTP server" or similar
```

#### Step 2: Test login and file transfer

```bash
# If FTP prompt appears, try logging in
ftp> user root
# Password: (try empty, or 'root', or check BSD default)

ftp> pwd
# Should show BSD filesystem path

ftp> put /tmp/test.txt
# Test upload

# Inside BSD (telnet localhost 2323):
vaxbsd# ls -la /tmp/test.txt
# Verify file arrived
```

#### Step 3: Implement in workflow

**Update `.github/workflows/deploy.yml` Stage 1:**

```yaml
- name: Stage 1 - VAX Build (FTP Method)
  run: |
    # Create FTP batch script
    cat > /tmp/ftp-upload.txt <<'EOF'
    user root
    binary
    cd /tmp
    put bradman.c
    put resume.vax.yaml
    put arpanet-log.sh
    bye
    EOF

    # Upload files via FTP
    ftp -n $VAX_IP 21 < /tmp/ftp-upload.txt

    # Execute build via console (vax-console-build.sh)
    # Commands run INSIDE BSD with vintage tools
    ./scripts/vax-console-build.sh "$BUILD_ID" "$VAX_IP"

    # Retrieve encoded result via FTP
    cat > /tmp/ftp-download.txt <<'EOF'
    user root
    binary
    cd /tmp
    get brad.1.uu
    bye
    EOF

    ftp -n $VAX_IP 21 < /tmp/ftp-download.txt
```

### Pros
- ✅ Fast and reliable
- ✅ Most historically appropriate for ARPANET
- ✅ Minimal code changes
- ✅ Bidirectional (upload + download)

### Cons
- ❓ Unknown if FTP daemon is configured in `jguillaumes/simh-vaxbsd` image
- ❓ Unknown default credentials
- ❓ Needs testing to verify

### Success Criteria
- [ ] FTP server responds on port 21 from container
- [ ] Can authenticate (root user)
- [ ] Files uploaded appear in BSD `/tmp/`
- [ ] Can download files from BSD `/tmp/`

---

## Option 2: Console I/O Transfer (Maximum Authenticity)

### Historical Authenticity: ✅ 10/10

**Why historically accurate:**
- Serial terminal file transfer via uuencode was standard practice (1970s-80s)
- Used for modem connections, terminal-to-terminal, dial-up systems
- Predates widespread FTP usage
- **This is exactly how files were transferred before networking!**

### How It Would Work

```
┌──────────────┐  Console I/O  ┌─────────────┐  Console    ┌──────────────┐
│  Container   │  cat > file   │  VAX BSD    │  Transfer   │  PDP-11 BSD  │
│  (Modern)    │ ───────────>  │  (1986)     │ brad.1.uu   │  (1992)      │
│              │  line-by-line │             │ ─────────>  │              │
└──────────────┘               └─────────────┘             └──────────────┘
                                      │
                                      ├─ cc -o bradman bradman.c (K&R C)
                                      ├─ ./bradman -i resume.yaml -o brad.1
                                      └─ uuencode brad.1 brad.1 > brad.1.uu
```

### Implementation (Expand Existing Script)

**Update `scripts/vax-console-build.sh`** to send source files via console:

```bash
#!/bin/bash
# VAX console-based build with file upload
# Sends source files + build commands to VAX BSD console

set -e

BUILD_ID="$1"
VAX_IP="$2"

SESSION="vax-build-$$"

echo "[VAX-CONSOLE] Creating screen session..."
screen -dmS "$SESSION" telnet "$VAX_IP" 2323
sleep 3

# Helper to send commands
send_cmd() {
    screen -S "$SESSION" -X stuff "$1\n"
    sleep "${2:-1}"
}

# Login as root
send_cmd "" 0.5
send_cmd "root" 2

# Change to /tmp
send_cmd "cd /tmp" 1

# === UPLOAD FILES VIA CONSOLE ===

echo "[VAX-CONSOLE] Uploading bradman.c via console..."
send_cmd "cat > /tmp/bradman.c <<'BRADMAN_EOF'" 0.5

# Send source file line-by-line
while IFS= read -r line; do
    # Escape special characters if needed
    screen -S "$SESSION" -X stuff "$line\n"
    sleep 0.1  # Rate limit to prevent buffer overflow
done < vax/bradman.c

send_cmd "BRADMAN_EOF" 1

echo "[VAX-CONSOLE] Uploading resume.vax.yaml via console..."
send_cmd "cat > /tmp/resume.vax.yaml <<'YAML_EOF'" 0.5

while IFS= read -r line; do
    screen -S "$SESSION" -X stuff "$line\n"
    sleep 0.1
done < vax/resume.vax.yaml

send_cmd "YAML_EOF" 1

echo "[VAX-CONSOLE] Uploading arpanet-log.sh via console..."
send_cmd "cat > /tmp/arpanet-log.sh <<'LOG_EOF'" 0.5

while IFS= read -r line; do
    screen -S "$SESSION" -X stuff "$line\n"
    sleep 0.1
done < scripts/arpanet-log.sh

send_cmd "LOG_EOF" 1
send_cmd "chmod +x /tmp/arpanet-log.sh" 1

# === RUN BUILD COMMANDS ===

echo "[VAX-CONSOLE] Executing build inside BSD..."

# Compile (runs inside 4.3BSD with K&R C)
send_cmd "cd /tmp" 1
send_cmd "cc -o bradman bradman.c 2>&1 | tee compile.log" 3
send_cmd "ls -la bradman" 1

# Generate manpage
send_cmd "./bradman -i resume.vax.yaml -o brad.1 2>&1 | tee bradman.log" 2
send_cmd "ls -la brad.1" 1

# Encode for transfer
send_cmd "uuencode brad.1 brad.1 > brad.1.uu" 1
send_cmd "ls -la brad.1.uu" 1

# Log completion
send_cmd "echo 'VAX build complete' | /tmp/arpanet-log.sh VAX $BUILD_ID" 1

echo "[VAX-CONSOLE] Build complete, waiting for output..."
sleep 5

# Capture console output
screen -S "$SESSION" -X hardcopy "/tmp/vax-console-$BUILD_ID.txt"

# === RETRIEVE ENCODED FILE ===

echo "[VAX-CONSOLE] Retrieving brad.1.uu via console..."
send_cmd "cat brad.1.uu" 1
sleep 2

# Capture output to file
screen -S "$SESSION" -X hardcopy "/tmp/brad.1.uu.raw"

# Clean up screen session
screen -S "$SESSION" -X quit 2>/dev/null || true

# Extract actual uuencoded content (remove console prompts)
grep -E '^(begin |M|end)' /tmp/brad.1.uu.raw > /tmp/brad.1.uu

echo "[VAX-CONSOLE] Build and transfer complete"
exit 0
```

### Pros
- ✅ Maximum historical authenticity (pure terminal workflow)
- ✅ No dependency on configured services (FTP, NFS, etc.)
- ✅ Works with any SIMH image (only needs console)
- ✅ Proven method (PDP-11 already works this way)
- ✅ Self-contained (no external dependencies)

### Cons
- ⏱️ Slower than FTP (line-by-line transfer)
- 🔧 More complex (need careful console I/O handling)
- 📝 Requires escaping special characters
- 🐛 Risk of console buffer overflow if too fast

### Success Criteria
- [ ] Source files appear in BSD `/tmp/` after console upload
- [ ] `cc` compilation runs inside BSD (not container)
- [ ] `uuencode` runs inside BSD
- [ ] Encoded output retrieved via console
- [ ] Logs show vintage tool versions

---

## Option 3: Build Custom VAX Image (Fallback)

### Historical Authenticity: ✅ 8/10

**Why still authentic:**
- End result uses vintage tools (4.3BSD, K&R C)
- Custom build process doesn't affect runtime behavior
- Similar to `Dockerfile.pdp11` (which works)

**Why slightly less authentic:**
- Custom image build is modern tooling
- Not using "stock" SIMH VAX distribution
- More maintenance overhead

### How It Would Work

Create `arpanet/Dockerfile.vax` similar to `Dockerfile.pdp11`:

```dockerfile
FROM debian:bookworm-slim

# Install SIMH dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpcap-dev \
    wget \
    git \
    telnet \
    && rm -rf /var/lib/apt/lists/*

# Build SIMH VAX from source
WORKDIR /tmp
RUN git clone --depth 1 https://github.com/simh/simh.git && \
    cd simh && \
    make vax780 && \
    cp BIN/vax780 /usr/local/bin/ && \
    cd .. && \
    rm -rf simh

# Download 4.3BSD disk image
# (Need to find source - check obsolescence/arpanet repo)
WORKDIR /opt/vax
RUN wget [4.3BSD disk image URL] && \
    tar xzf [...] && \
    chmod 644 *.dsk

# Create data directory accessible to both container and BSD
RUN mkdir -p /machines/data

# Copy SIMH config that mounts /machines/data
COPY configs/vax780.ini /opt/vax/vax780.ini

# Expose ports
EXPOSE 2323 21 23

# Start SIMH
CMD ["vax780", "vax780.ini"]
```

**Update `configs/vax780.ini`** to mount container directory into BSD:

```ini
; VAX 11/780 Configuration
set cpu 64M

; Attach disk images
attach rq0 4.3bsd.dsk

; Attach shared directory (if SIMH supports it)
; attach rl1 /machines/data

; Network
attach xu eth0

; Console
set console telnet=2323

boot cpu
```

### Research Needed
- [ ] Find 4.3BSD disk image source (check obsolescence/arpanet)
- [ ] Verify SIMH can mount host directories into BSD
- [ ] Test disk attachment syntax
- [ ] Ensure BSD sees mounted directory

### Pros
- ✅ Full control over configuration
- ✅ Proven approach (PDP-11 works)
- ✅ Can ensure file access
- ✅ Reproducible builds

### Cons
- 🔨 Most work to implement
- 📦 Larger image (need to include disk image)
- 🔧 More maintenance (can't use pre-built image updates)
- ❓ Unknown if SIMH supports host directory mounting

### Success Criteria
- [ ] Custom VAX image builds successfully
- [ ] 4.3BSD boots in custom image
- [ ] Files in `/machines/data` accessible from both layers
- [ ] All vintage tools working
- [ ] Network configuration correct

---

## Research LLM Feedback (With Caveats)

An LLM researcher analyzed the VAX blocker and provided recommendations. **Critical review:**

### Claim 1: `SIMH_USE_CONTAINER=yes` Causes File Sharing Issues

**Research LLM says:**
> "This variable tells the container to use its internal volume for the disk images, effectively ignoring your host mount at `/machines`"

**Project memory says:**
> "Environment variable `SIMH_USE_CONTAINER=yes` required for external volume mounting - Without it, container will restart with volume mount error"

**VERDICT**: ⚠️ **CONTRADICTORY** - Need to test which is correct.

**Action**: Test by toggling variable and observing behavior.

### Claim 2: FTP is Available

**Research LLM says:**
> "Switch to the FTP method I identified"

**Problem**: The research doc asked "Is FTP running in BSD?" as an **open question**. The LLM assumed FTP works without verification.

**VERDICT**: ⚠️ **UNVERIFIED ASSUMPTION** - Need to test.

**Action**: Test FTP connectivity (Option 1 procedure above).

### Useful Feedback

**Docker network suggestion:**
> "Create a custom Docker network rather than relying on default bridge"

**Response**: ✅ Already implemented (`arpanet-production` network in `docker-compose.production.yml`)

---

## Decision Matrix

| Criterion | FTP | Console I/O | Custom Image |
|-----------|-----|-------------|--------------|
| **Historical Authenticity** | ⭐⭐⭐⭐⭐ 9/10 | ⭐⭐⭐⭐⭐ 10/10 | ⭐⭐⭐⭐ 8/10 |
| **Implementation Speed** | ⚡ Fast (if works) | ⏱️ Medium | 🔨 Slow |
| **Reliability** | ✅ High (if configured) | ⚠️ Medium (console timing) | ✅ High |
| **Maintenance** | 🎯 Low | 🎯 Low | 🔧 High |
| **Testing Required** | ❓ FTP availability | ✅ Proven method | ❓ Disk image sourcing |
| **Risk** | 🟢 Low (if FTP works) | 🟡 Medium (timing) | 🔴 High (disk config) |

---

## Recommended Action Plan

### Phase 1: Quick Tests (30 minutes)

1. **Test FTP availability** (Option 1)
   ```bash
   ssh ubuntu@$VAX_IP "ftp -n localhost 21"
   ```
   - If connects → Proceed with FTP implementation
   - If fails → Move to Phase 2

2. **Test `SIMH_USE_CONTAINER` behavior**
   ```bash
   # Try without variable, observe if container restarts
   ```

### Phase 2: Console Implementation (2 hours)

If FTP not available:

1. **Enhance `vax-console-build.sh`** with file upload
2. **Test source file transfer** via console
3. **Verify compilation** runs inside BSD
4. **Update workflow** to use console method

### Phase 3: Custom Image (Fallback, 4 hours)

If both above fail:

1. **Research 4.3BSD disk image sources**
2. **Create `Dockerfile.vax`**
3. **Test disk mounting configuration**
4. **Migrate to custom image**

---

## Success Validation

Once implemented, verify historical fidelity:

### Required Checks
- [ ] `cc --version` inside BSD shows "4.3BSD" or 1986 date
- [ ] `which cc` shows `/bin/cc` (BSD), not `/usr/bin/gcc` (modern)
- [ ] Compilation happens inside emulated VAX (check logs)
- [ ] `uuencode` version is vintage (from 1986)
- [ ] Logs accurately report tool usage (no false claims)

### Smoke Test
```bash
# SSH to VAX
ssh ubuntu@$VAX_IP

# Connect to BSD console
telnet localhost 2323

# Login as root
vaxbsd# which cc
/bin/cc

vaxbsd# cc -V
# Should show 4.3BSD or error (not modern GCC version)

vaxbsd# file /bin/cc
# Should show PDP-11 or VAX binary, not x86_64

vaxbsd# ls -la /tmp/bradman.c
# Should exist if file transfer worked
```

---

## Related Documentation

- **Current blocker**: `docs/research/VAX-CONTAINER-BSD-FILE-SHARING.md`
- **Architecture**: `STATUS.md` (layer stack explanation)
- **PDP-11 solution**: `docs/integration/PDP11-USR-MOUNT-FIX.md` (working example)
- **Console transfer**: `docs/integration/UUENCODE-CONSOLE-TRANSFER.md`
- **Workflow**: `.github/workflows/deploy.yml:238` (line to fix)

---

## Cold Start Instructions

**If starting fresh on this blocker:**

1. Read this document completely
2. Read `STATUS.md` for current state
3. Check VAX is running: `./aws-status.sh`
4. Test FTP: Follow Option 1 test procedure
5. If FTP works: Implement Option 1
6. If FTP fails: Implement Option 2 (console I/O)
7. If both fail: Research Option 3 (custom image)

**Goal**: Execute `cc` and `uuencode` INSIDE 4.3BSD, not in container.

**Success**: Logs truthfully show vintage tool usage, not modern GCC.

---

**Last updated**: 2026-02-14
**Next step**: Choose option and begin testing

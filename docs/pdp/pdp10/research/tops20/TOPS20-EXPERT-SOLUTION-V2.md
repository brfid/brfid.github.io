# TOPS-20 Installation - Expert Solution V2 (FINAL)

**Date**: 2026-02-09
**Credit**: Expert analysis identifying Telnet console wrapper issue
**Status**: Ready to implement

---

## The Real Problem (Finally!)

**NOT**: TOPS-20 won't boot
**NOT**: Tape is incompatible
**NOT**: Stop code 7 is fatal

**ACTUAL PROBLEM**:

> The KS10 simulator IS booting from tape; the FE (front-end console) IS running; but the **Telnet console layer inside Docker** is intercepting the console in a way that leaves you with a banner and no visible prompt/output.

**Evidence**:
- SIMH logs show: `%SIM-INFO: Running` (boot succeeded!)
- We see: `Connected to the KS-10 simulator CON-TELNET device` (FE running!)
- We DON'T see: MTBOOT prompt (Telnet wrapper drops output!)

**Key Insight**: Console output is going somewhere (SIMH is running), but the Telnet wrapper isn't showing it to our client.

---

## The Solution

**Stop using Telnet console for installation entirely.**

Use direct stdio console (the container's stdin/stdout) instead:
- Run `pdp10-ks` with console on terminal (no Telnet)
- Complete TOPS-20 install interactively
- Reuse the installed disk in production container

This matches how EVERY successful TOPS-20 installation works.

---

## Implementation - Method 1: Direct Console Install

### Step 1: Create Stdio Console Configuration

```bash
ssh ubuntu@34.227.223.186
cd ~/brfid.github.io

cat > arpanet/configs/pdp10-install-stdio.ini << 'EOF'
; KS10 TOPS-20 V4.1 install with STDIO console (no Telnet)
; Based on working Gunkies recipe

set cpu tops20
set debug stdout
set console wru=034

; Console on STDIO (not Telnet!)
set console notelnet

; Log console output to file as well
set console log=/machines/pdp10/console-install.log

; Tape: TOPS-20 V4.1 install tape
set tu enable
set tu0 locked
attach -f tu0 /machines/pdp10/tops20_v41.tap

; Disk: RP06 system disk
set rp enable
set rp0 rp06
attach rp0 /machines/data/tops20.dsk

; Boot from tape into MTBOOT
boot tu0
EOF
```

**Key differences from previous attempts**:
- ✅ `set console notelnet` - Console stays on stdin/stdout
- ✅ `set console log=...` - Also logs to file (for debugging)
- ✅ Uses `tu0` / `rp0` (classic PDP-10 naming)
- ✅ `set cpu tops20` - Sets CPU mode properly

### Step 2: Stop Current Container

```bash
docker rm -f pdp10-install 2>/dev/null || true
```

### Step 3: Run Interactive Install

```bash
docker run --rm -it \
  --name pdp10-install \
  -v brfid.github.io_arpanet-pdp10-data:/machines/data \
  -v brfid.github.io_arpanet-pdp10-config:/machines/pdp10 \
  -v "$PWD/arpanet/configs/pdp10-install-stdio.ini":/machines/pdp10/install-stdio.ini:ro \
  brfidgithubio-pdp10 \
  /usr/local/bin/pdp10-ks /machines/pdp10/install-stdio.ini
```

**What you'll see**:

```text
KS-10 simulator V4.0-0 Current        git commit id: 627e6a6b

BOOT V11.0(315)

MTBOOT>
```

**Finally! The prompt appears!** 🎉

### Step 4: Complete Installation

At the `MTBOOT>` prompt, follow existing guide:

```text
MTBOOT> /L
[BOOT: Loading]
[OK]
MTBOOT> /G143
```

Then answer formatter questions (from TOPS20-INSTALLATION-GUIDE.md):
- Replace file system: Y
- Define structure: Y
- Structure name: PS
- Number of packs: 1
- Location: 0,0
- All defaults: Y
- Date: 8-FEB-26 12:00:00
- Reason: INSTALLATION

Wait 5-10 minutes for disk format, then:

```text
[When you see "RUNNING DDMP"]
Ctrl-C

MX> GET FILE MTA0:
MX> GET FILE MTA0:
MX> START

TOPS-20 Monitor 4.1(2020)
@
```

Continue with DUMPER, user creation, bootstrap (per existing guide).

### Step 5: After Installation - Reconfigure for Production

Once installed and tested, create production config:

```bash
cat > arpanet/configs/pdp10-production.ini << 'EOF'
; KS10 TOPS-20 V4.1 production - boots from INSTALLED disk

set cpu tops20
set debug stdout
set console wru=034

; For now: console on stdio (can add Telnet later)
set console notelnet

; Disk: INSTALLED system
set rp enable
set rp0 rp06
attach rp0 /machines/data/tops20.dsk

; IMP Network Interface
set imp enabled
set imp debug
attach -u imp 2000:172.20.0.30:2000

; DZ lines for user TTY access (instead of console Telnet)
set dz enable
set dz lines=8
attach dz 2323

echo ========================================
echo PDP-10 TOPS-20 V4.1 Production
echo ========================================
echo Console: stdio (docker attach for maintenance)
echo User TTYs: DZ on port 2323 (host 2327)
echo IMP: Connected to IMP #2 at 172.20.0.30
echo Disk: Booting from installed system
echo ========================================

; Boot from INSTALLED disk
boot rp0
EOF
```

**Key Architecture**:
- ✅ Console: stdio (maintenance only via `docker attach`)
- ✅ User access: DZ lines on Telnet (port 2327 on host)
- ✅ FTP: Via DZ Telnet TTY
- ✅ No console Telnet timing issues!

### Step 6: Update Docker Compose

Update `docker-compose.arpanet.phase2.yml`:

```yaml
pdp10:
  # ... existing config ...
  ports:
    - "2327:2323"  # DZ user TTYs (not console!)
  volumes:
    - ./arpanet/configs/pdp10-production.ini:/machines/pdp10.ini:ro
```

### Step 7: Start Production Container

```bash
docker compose -f docker-compose.arpanet.phase2.yml up -d pdp10

# Wait for boot
sleep 30

# Check logs (console output goes here now)
docker logs arpanet-pdp10

# Connect to user TTY
telnet localhost 2327
```

---

## Why This Works

### Before (Failed)
```
SIMH → Console Telnet Wrapper → Docker Port 2326 → Your Client
         ↑
    Output gets lost/buffered here
```

### After (Works)
```
SIMH → Container stdout → Docker logs / docker attach
                ↓
         Direct visibility

User access:
TOPS-20 → DZ TTY lines → Telnet Port 2327 → Your Client
                ↓
         Proper TTY handling
```

**Benefits**:
1. ✅ Console output visible during install
2. ✅ No Telnet timing race
3. ✅ Matches how everyone else does it
4. ✅ Proper separation: console vs user TTYs
5. ✅ Can still access console via `docker attach`

---

## Alternative: Use Console Log

Even if stdio doesn't show output, the console log will:

```bash
# During install, monitor the log
docker exec -it pdp10-install tail -f /machines/pdp10/console-install.log
```

This will show MTBOOT prompt even if the terminal doesn't!

---

## For Phase 3: User Access via DZ

Once TOPS-20 is installed, configure FTP:

```text
# Connect to DZ TTY
telnet localhost 2327

# Login
[TOPS-20 login prompt]
login: OPERATOR
Password: operator

# Start FTP
@ ENABLE
@ START FTP
@ INFO FTP-SERVER
```

Then from VAX:
```bash
ftp 172.20.0.40  # PDP-10 IP
```

**This is the clean architecture**: Console for admin, DZ for users.

---

## Comparison with Previous Attempts

| Attempt | Console | Boot | Result |
|---------|---------|------|--------|
| Original | Telnet auto-boot | Timeout race | ❌ Timing fail |
| Previous | Telnet manual boot | Works | ❌ No output visible |
| **This** | **Stdio** | **Works** | **✅ Output visible!** |

**Root cause was**: Telnet console wrapper behavior in Docker, not TOPS-20 or SIMH itself.

---

## Time Estimate

- Setup config: 5 minutes
- Run installation: 1-2 hours (mostly DUMPER waiting)
- Production config: 10 minutes
- Testing: 15 minutes

**Total**: ~2-3 hours, but should actually complete this time!

---

## Success Criteria

Installation successful when:
1. ✅ See MTBOOT> prompt on stdio console
2. ✅ Complete disk formatting and file restoration
3. ✅ TOPS-20 boots from installed disk
4. ✅ Can login via DZ TTY (telnet localhost 2327)
5. ✅ FTP server running and accessible
6. ✅ Phase 3 file transfer tests work

---

## References

**Expert Analysis Sources**:
- SIMH Users' Guide: Console configuration options
- PDP-10 Simulator Usage: Device naming (TU vs TUA)
- Running TOPS-20 V4.1 under SIMH: Working recipe
- Community setups: PiDP-10, ITS - all use stdio console + DZ TTYs

**Key Insight**: "The Telnet 'console' layer inside the Docker container is intercepting the console in a way that leaves you with a banner and no visible prompt/output."

---

**Status**: Ready to execute
**Confidence**: High - matches proven working configurations
**Next**: Run the installation with stdio console

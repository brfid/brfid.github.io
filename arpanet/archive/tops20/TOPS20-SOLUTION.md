# TOPS-20 Installation Solution - Interactive Console Approach

**Date**: 2026-02-08
**Status**: Implementing expert-recommended solution
**Credit**: Solution based on analysis of published TOPS-20-on-SIMH recipes

---

## Root Cause Identified

**The Problem Was NOT**: TOPS-20 refusing to boot
**The Problem WAS**: Installation attempted through telnet console with auto-boot from ini

**Why This Fails:**
- Every published TOPS-20-on-SIMH recipe runs install from an **interactive simulator console** on the host TTY
- NOT from a telnet-only console that auto-boots from ini file
- Telnet+auto-boot creates timing race that's nearly impossible to win in headless Docker

**Evidence:**
- [Gunkies Recipe](https://gunkies.org/wiki/Running_TOPS-20_V4.1_under_SIMH): Interactive console, manual boot
- [Supnik's alt.sys.pdp10 Post](https://groups.google.com/g/alt.sys.pdp10/c/og-_kNunWHo): Interactive console, manual boot
- PiDP-10 setups: Console on local TTY, telnet only for DZ user lines

---

## The Solution

### Core Strategy

**One-Off Interactive Installation:**
1. Run pdp10-ks interactively with Docker TTY (no telnet)
2. Use same volumes as production container
3. Complete full TOPS-20 install through direct console
4. Leave behind populated `tops20.dsk` in volume

**Then Reconfigure Production:**
1. Change ini to boot from installed disk (not tape)
2. Optionally re-enable telnet console for day-to-day use
3. System boots directly to TOPS-20 login prompt

**Result:** Installation complexity isolated to one-time interactive session, production container just boots installed system.

---

## Implementation Steps

### Step 1: Stop Production Container

```bash
ssh ubuntu@34.227.223.186
cd ~/brfid.github.io
docker compose -f docker-compose.arpanet.phase2.yml stop pdp10
```

**Why:** Prevent two SIMH instances from writing same disk simultaneously.

---

### Step 2: Create Interactive Install Configuration

**Create `/machines/pdp10/install.ini` in config volume:**

```bash
docker run --rm -it \
  -v brfid.github.io_arpanet-pdp10-config:/machines/pdp10 \
  ubuntu:22.04 bash

# Inside helper container:
cat >/machines/pdp10/install.ini << 'EOF'
; TOPS-20 V4.1 Interactive Installation Configuration
; Based on Gunkies recipe - NO TELNET, manual boot
; https://gunkies.org/wiki/Running_TOPS-20_V4.1_under_SIMH

set debug stdout

; CPU configuration for TOPS-20
set cpu tops-20
set wru 006           ; WRU = ^E (as per Supnik's example)

; Disable unused devices
set dz disabled
set lp20 disabled

; Tape drive with installation tape
set tua enable
set tua0 locked
attach tua0 /machines/pdp10/tops20_v41.tap

; RP06 system disk
set rpa enable
set rpa0 rp06
attach rpa0 /machines/data/tops20.dsk

; Note: IMP disabled for installation - will add back to production config

echo ========================================
echo TOPS-20 V4.1 Interactive Installation
echo ========================================
echo Console: Direct TTY (no telnet)
echo Tape: tops20_v41.tap on TUA0
echo Disk: tops20.dsk on RPA0 (will be formatted)
echo ========================================
echo Ready for manual boot
echo Type: boot tua0
echo ========================================
EOF

exit
```

**Key Differences from Production Config:**
- ✅ No `SET CONSOLE TELNET` (uses Docker TTY)
- ✅ No auto-boot command (manual at sim> prompt)
- ✅ No IMP attachment (not needed for install)
- ✅ Console stays on controlling terminal

---

### Step 3: Run Interactive Installation Session

**Start pdp10-ks interactively:**

```bash
docker run --rm -it \
  --name pdp10-install \
  -v brfid.github.io_arpanet-pdp10-data:/machines/data \
  -v brfid.github.io_arpanet-pdp10-config:/machines/pdp10 \
  brfidgithubio-pdp10 \
  /usr/local/bin/pdp10-ks /machines/pdp10/install.ini
```

**What You'll See:**

```text
KS-10 simulator V4.0-0 Current        git commit id: 627e6a6b
========================================
TOPS-20 V4.1 Interactive Installation
========================================
Console: Direct TTY (no telnet)
Tape: tops20_v41.tap on TUA0
Disk: tops20.dsk on RPA0 (will be formatted)
========================================
Ready for manual boot
Type: boot tua0
========================================

sim>
```

**You now have direct console access!**

---

### Step 4: Boot from Installation Tape

At the `sim>` prompt:

```text
sim> boot tua0
```

**Expected Output:**

```text
BOOT V11.0(315)

MTBOOT>
```

**If you see "BOOT V11.0(315)" but no prompt**, hit Enter once to repaint.

---

### Step 5: Load Disk Formatter

At the `MTBOOT>` prompt:

```text
MTBOOT> /L
[BOOT: Loading]
[OK]
MTBOOT> /G143
```

**This starts the disk formatter.**

---

### Step 6: Answer Formatter Questions

Follow the sequence from TOPS20-INSTALLATION-GUIDE.md:

```text
DO YOU WANT TO REPLACE THE FILE SYSTEM ON THE DISK?
Y

DO YOU WANT TO DEFINE A PUBLIC STRUCTURE?
Y

STRUCTURE NAME:
PS

NUMBER OF PACKS IN THIS STRUCTURE:
1

LOGICAL PACK LOCATION:
0,0

DO YOU WANT THE DEFAULT SIZE SWAPPING SPACE?
Y

DO YOU WANT THE DEFAULT SIZE FRONT-END FILE SYSTEM?
Y

DO YOU WANT THE DEFAULT SIZE BOOTSTRAP AREA?
Y

DO YOU WANT TO WRITE PROTOTYPE BAT BLOCKS?
Y

DO YOU WANT TO ENABLE PASSWORD ENCRYPTION FOR THE SYSTEM STRUCTURE?
N

DATE AND TIME (DD-MMM-YY HH:MM:SS):
8-FEB-26 12:00:00

IS THIS CORRECT?
Y

REASON FOR RELOAD:
INSTALLATION
```

**Wait 5-10 minutes for disk formatting.**

---

### Step 7: Load Monitor and Restore Files

When you see `RUNNING DDMP`, press **Ctrl-C**:

```text
MX> GET FILE MTA0:
MX> GET FILE MTA0:
MX> START
```

**You should reach:**

```text
TOPS-20 Monitor 4.1(2020)
@
```

**Enable privileged mode and run DUMPER:**

```text
@ ENABLE
@ RUN DUMPER
DUMPER> TAPE MTA0:
DUMPER> REWIND
DUMPER> SKIP 2
DUMPER> RESTORE <*>*.*.*
```

**This will take 30-60 minutes.** TOPS-20 is copying all system files from tape to disk.

**Progress indicators:**
```text
RESTORING: PS:<SYSTEM>EXEC.EXE.1
RESTORING: PS:<SYSTEM>DUMPER.EXE.1
...
```

**When complete:**

```text
DUMPER> EXIT
@
```

---

### Step 8: Create User Accounts

```text
@ ENABLE
@ RUN DLUSER
* ADD OPERATOR 1,2
  Password: operator
  Re-enter password: operator
* EXIT
@
```

**Optional:** Add ANONYMOUS account for FTP:

```text
@ RUN DLUSER
* ADD ANONYMOUS 2,2
  Password: [leave blank or use simple password]
* EXIT
```

---

### Step 9: Write Bootstrap to Disk

```text
@ RUN SMFILE
* WRITE /BOOTSTRAP
* EXIT
@
```

**This makes the disk bootable.**

---

### Step 10: Shutdown and Test

```text
@ ENABLE
@ SHUTDOWN
Reason for shutdown: Installation complete
Estimated uptime: 0
Shutdown in how many minutes: 0

@ CEASE NOW
```

**System will halt. You'll return to:**

```text
sim>
```

**Test boot from disk:**

```text
sim> boot rpa0
```

**Should see:**

```text
TOPS-20 Monitor 4.1(2020)
@
```

**Login to verify:**

```text
@ LOGIN OPERATOR
Password: operator

@ SYSTAT
@ DIR
@ INFO FTP-SERVER
```

**If everything works, exit:**

```text
@ LOGOUT
[disconnected]

sim> exit
```

**Installation complete!** The `tops20.dsk` file in your volume is now a fully installed system.

---

## Step 11: Reconfigure Production Container

### Update Production Configuration

Edit the production `pdp10.ini` to boot from installed disk:

```bash
docker run --rm -it \
  -v brfid.github.io_arpanet-pdp10-config:/machines/pdp10 \
  ubuntu:22.04 bash

cat >/machines/pdp10/pdp10.ini << 'EOF'
; SIMH PDP-10 KS Configuration - TOPS-20 V4.1 Production
; Boots from INSTALLED disk (not installation tape)

set debug stdout
set console wru=034

; Disable unused devices
set dz disabled
set lp20 disabled

; Tape drive (available but not used for boot)
set tua enable
set tua0 locked
attach tua0 /machines/pdp10/tops20_v41.tap

; System disk (INSTALLED)
set rpa enable
set rpa0 rp06
attach rpa0 /machines/data/tops20.dsk

; IMP Network Interface for ARPANET
set imp enabled
set imp debug
attach -u imp 2000:172.20.0.30:2000

; Telnet console for remote access
set console telnet=2323

echo ========================================
echo PDP-10 TOPS-20 V4.1 Production
echo ========================================
echo Console: telnet on port 2323 (host 2326)
echo Disk: Booting from INSTALLED system
echo IMP: Connected to IMP #2 at 172.20.0.30
echo ========================================

; Boot from INSTALLED disk (not tape)
boot rpa0
EOF

exit
```

**Key Changes:**
- ✅ `boot rpa0` instead of `boot tua0` (boots from disk, not tape)
- ✅ Telnet console re-enabled for remote access
- ✅ IMP interface restored
- ✅ System boots directly to TOPS-20 login

---

### Start Production Container

```bash
cd ~/brfid.github.io
docker compose -f docker-compose.arpanet.phase2.yml up -d pdp10
```

**Wait 30 seconds for boot:**

```bash
sleep 30
docker logs arpanet-pdp10 | tail -20
```

**Expected:**

```text
========================================
PDP-10 TOPS-20 V4.1 Production
========================================
...
boot rpa0
%SIM-INFO: Running
```

---

### Connect and Verify

```bash
telnet localhost 2326
```

**You should see TOPS-20 login prompt over telnet!**

```text
Connected to localhost.
Escape character is '^]'.

TOPS-20 Monitor 4.1(2020)
@
```

**Login:**

```text
@ LOGIN OPERATOR
Password: operator

@ SYSTAT
@ INFO FTP-SERVER
@ INFO NET
@ DIR
```

**Success!** TOPS-20 is now running and accessible via telnet.

---

## Verification Checklist

- [ ] System boots from disk without errors
- [ ] Can connect via telnet to console
- [ ] Can login as OPERATOR
- [ ] SYSTAT shows system running
- [ ] FTP server is active
- [ ] Can create/list files
- [ ] IMP interface shows connected (check logs)

---

## Why This Works

### Before (Failed Approach)
```
Container Start → ini executes → boot tua0 → wait for telnet (timeout race)
                                        ↓
                        MTBOOT output before connection
                                        ↓
                              Connection too late → missed prompt
```

### After (Working Approach)
```
Interactive Session → sim> prompt → manual boot tua0 → see MTBOOT directly
                                          ↓
                              Complete installation through TTY
                                          ↓
                              Disk saved in volume

Production Container → ini executes → boot rpa0 → TOPS-20 login
                                                        ↓
                                              Telnet works because OS
                                              handles console properly
```

**Key Insight:** Installation requires console interaction BEFORE OS is configured. Production operation works with telnet because TOPS-20 itself manages the console.

---

## Troubleshooting

### Problem: Can't see sim> prompt in interactive session

**Solution:** Hit Enter once. SIMH may be waiting silently.

### Problem: MTBOOT doesn't appear after boot tua0

**Solution:**
- Check logs: `docker logs pdp10-install`
- Verify tape attached: Should see "TUA0: Tape Image scanned"
- Try: `show tua0` at sim> prompt

### Problem: Disk format fails

**Solution:**
- Ensure disk file is writable in volume
- Check disk size (RP06 = ~176 MB)
- Verify: `show rpa0` at sim> prompt

### Problem: DUMPER restoration hangs

**Solution:**
- This is normal! Can take 30-60+ minutes
- Watch for "RESTORING:" messages
- Be patient - go get coffee

### Problem: Production container won't boot from disk

**Solution:**
- Check ini: Verify `boot rpa0` (not tua0)
- Check logs: Look for boot errors
- Test interactively:
  ```bash
  docker exec -it arpanet-pdp10 /usr/local/bin/pdp10-ks
  sim> att rpa0 /machines/data/tops20.dsk
  sim> boot rpa0
  ```

---

## Next Steps After Installation

### 1. Configure Network Services

Inside TOPS-20:

```text
@ ENABLE
@ EDIT SYSTEM:4-1-CONFIG.CMD
[Configure networking, printers, etc.]
^Z

@ TAKE SYSTEM:4-1-CONFIG.CMD
```

### 2. Start FTP Daemon

```text
@ ENABLE
@ START FTP
@ INFO FTP-SERVER
```

### 3. Test ARPANET Connectivity

Check IMP interface:

```bash
docker logs arpanet-pdp10 | grep "IMP"
docker logs arpanet-imp2 | grep "HI1"
```

### 4. Proceed with Phase 3

Now that TOPS-20 is installed:
- Run 4-container routing tests
- Test FTP file transfer VAX ↔ PDP-10
- Integrate into build pipeline

---

## Alternative: If Installation Still Fails

### Option A: TOPS-10 Instead

TOPS-10 has pre-built images available:
- [Steuben Technologies TOPS-10](https://steubentech.com/~talon/pdp10/)
- Simpler installation process
- Still has FTP and networking

### Option B: Simplified Test Service

Create minimal echo/test service:
- Skip full OS installation
- Validate 4-container routing
- Complete Phase 3 with basic functionality
- Add TOPS-20 as Phase 3.5 enhancement

### Option C: KLH10 + Panda TOPS-20

Use different emulator:
- KLH10 instead of SIMH
- Panda distribution has pre-built disk
- Requires new container setup

---

## References

**Primary Sources:**
- [Running TOPS-20 V4.1 under SIMH - Gunkies](https://gunkies.org/wiki/Running_TOPS-20_V4.1_under_SIMH)
- [Getting TOPS-20 up and running in SIMH - Supnik](https://groups.google.com/g/alt.sys.pdp10/c/og-_kNunWHo)
- [SIMH Documentation](https://simh.trailing-edge.com/pdf/pdp10_doc.pdf)

**Console Configuration:**
- [SIMH Console Options](https://tangentsoft.com/pidp8i/uv/doc/simh/main.pdf)
- [PiDP-10 Manual](https://obsolescence.dev/pidp10-sw/PiDP-10_Manual.pdf)

**TOPS-20 Resources:**
- [TOPS-20 Commands Reference](http://www.bourguet.org/v2/pdp10/cmds/front)
- [Bitsavers TOPS-20 Documentation](http://www.bitsavers.org/pdf/dec/pdp10/TOPS20/)

---

**Document Version**: 1.0
**Date**: 2026-02-08
**Status**: Ready for implementation
**Estimated Time**: 2-3 hours (1 hour setup + 1-2 hours install/restore)

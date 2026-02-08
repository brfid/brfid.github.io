# TOPS-20 V4.1 Installation Guide for PDP-10 KS10

**Created**: 2026-02-08
**Target**: arpanet-pdp10 container on AWS EC2
**Duration**: 1-2 hours (manual, interactive)
**Status**: Ready to execute

---

## Quick Start

```bash
# On your local machine (Raspberry Pi)
ssh ubuntu@34.227.223.186

# On AWS instance
cd ~/brfid.github.io
docker compose -f docker-compose.arpanet.phase2.yml ps  # Verify running

# Connect to PDP-10 console
telnet localhost 2326

# You'll see SIMH prompt - installation begins from here
```

---

## Pre-Installation Checklist

**Verify these before starting:**

```bash
# 1. Container is running
docker ps | grep pdp10
# Should show: arpanet-pdp10 (Up X hours)

# 2. TOPS-20 tape is loaded
docker exec arpanet-pdp10 ls -lh /machines/pdp10/tops20_v41.tap
# Should show: 21M file

# 3. Disk file exists
docker exec arpanet-pdp10 ls -lh /machines/data/tops20.dsk
# Should exist (may be empty/new)

# 4. Check current state
docker logs arpanet-pdp10 | tail -20
# Should show: "Waiting for console Telnet connection"
```

---

## Installation Overview

The installation process has these phases:

1. **Boot from tape** - Boot TOPS-20 installer from installation tape
2. **Initialize disk** - Format RP06 disk and create file structure
3. **Copy system** - Transfer TOPS-20 from tape to disk
4. **Configure system** - Set up hostname, accounts, networking
5. **Enable services** - Start FTP daemon and ARPANET interface
6. **Validate boot** - Ensure system boots from disk on restart

**Important**: Take detailed notes during installation. This is a one-time process and documentation will help troubleshooting.

---

## Phase 1: Boot from Installation Tape

### Step 1.1: Connect to Console

```bash
# SSH to AWS instance
ssh ubuntu@34.227.223.186

# Start screen session (recommended - allows reconnection if SSH drops)
screen -S tops20-install

# Connect to PDP-10 console
telnet localhost 2326
```

**Expected output:**
```
Connected to localhost.
Escape character is '^]'.

KS-10 simulator V4.0-0 Current
PDP-10 TOPS-20 V4.1 starting...

sim>
```

### Step 1.2: Boot from Tape

At the `sim>` prompt, the simulator should auto-boot from the tape. If not, type:

```
boot tua0
```

**Expected**: The TOPS-20 installer will start loading from the installation tape.

You should see messages like:
```
MTBOOT V11.0(315)

Type ? for help

MTBOOT>
```

---

## Phase 2: Disk Initialization

### Step 2.1: Start Disk Formatter

At the `MTBOOT>` prompt:

```
/L          (Load formatter)
/G143       (Go to address 143 - start formatter)
```

**Alternative**: Some versions may just need `/G` or simply pressing RETURN.

### Step 2.2: Answer Formatter Questions

The disk formatter will ask a series of questions. Here are recommended answers:

**Q: "DO YOU WANT TO REPLACE THE FILE SYSTEM ON THE DISK?"**
**A:** `Y` (Yes - this is a new installation)

**Q: "DO YOU WANT TO DEFINE A PUBLIC STRUCTURE?"**
**A:** `Y` (Yes)

**Q: "STRUCTURE NAME:"**
**A:** `PS` (Standard name for "Public Structure")

**Q: "NUMBER OF PACKS IN THIS STRUCTURE:"**
**A:** `1` (We have one RP06 disk)

**Q: "LOGICAL PACK LOCATION:"**
**A:** `0,0` (Unit 0, Controller 0)

**Q: "DO YOU WANT THE DEFAULT SIZE SWAPPING SPACE?"**
**A:** `Y` (Yes - default is fine)

**Q: "DO YOU WANT THE DEFAULT SIZE FRONT-END FILE SYSTEM?"**
**A:** `Y` (Yes)

**Q: "DO YOU WANT THE DEFAULT SIZE BOOTSTRAP AREA?"**
**A:** `Y` (Yes)

**Q: "DO YOU WANT TO WRITE PROTOTYPE BAT BLOCKS?"**
**A:** `Y` (Yes - BAT = Bad Block Allocation Table)

**Q: "DO YOU WANT TO ENABLE PASSWORD ENCRYPTION FOR THE SYSTEM STRUCTURE?"**
**A:** `N` (No - simpler for testing, can enable later)

**Q: "DATE AND TIME (DD-MMM-YY HH:MM:SS):"**
**A:** `8-FEB-26 12:00:00` (Current date/time)

**Q: "IS THIS CORRECT?"**
**A:** `Y` (Yes)

**Q: "REASON FOR RELOAD:"**
**A:** `INSTALLATION` (or `NEW INSTALLATION`)

### Step 2.3: Wait for Formatting

You'll see messages like:
```
WRITING DISK STRUCTURE...
FORMATTING COMPLETE
RUNNING DDMP
```

**Note**: When you see "RUNNING DDMP", the disk is being initialized. This may take a few minutes.

---

## Phase 3: System Installation

### Step 3.1: Interrupt to Monitor

When you see "RUNNING DDMP", press:

```
Ctrl-C
```

This interrupts the formatter and brings you to the monitor prompt:

```
MX>
```

### Step 3.2: Load Monitor from Tape

At the `MX>` prompt:

```
GET FILE MTA0:
```

**Note**: You may need to type this command **twice** if the first attempt doesn't respond.

Then start the monitor:

```
START
```

### Step 3.3: Reach System Prompt

After the monitor starts, you should see:

```
TOPS-20 Monitor 4.1(2020)
@
```

The `@` is the TOPS-20 command prompt. You're now in the system!

---

## Phase 4: Restore System Files

### Step 4.1: Enable Privileged Commands

```
@ENABLE
```

**Note**: On a fresh installation, you may not need a password, or try blank password.

### Step 4.2: Run DUMPER to Restore Files

```
@RUN DUMPER
```

At the `DUMPER>` prompt:

```
DUMPER> TAPE MTA0:
DUMPER> REWIND
DUMPER> SKIP 2          (Skip past installation files to savesets)
DUMPER> RESTORE <*>*.*.*
```

**Warning**: This restoration process can take **30 minutes to several hours** depending on tape contents. Be patient!

You'll see messages like:
```
RESTORING: PS:<SYSTEM>EXEC.EXE.1
RESTORING: PS:<SYSTEM>DUMPER.EXE.1
...
```

### Step 4.3: Complete Restoration

When DUMPER finishes, you'll return to the `DUMPER>` prompt.

```
DUMPER> EXIT
```

---

## Phase 5: System Configuration

### Step 5.1: Create User Accounts

```
@ENABLE
@RUN DLUSER

*ADD OPERATOR 1,2
 Password: <type_password>
 Re-enter password: <type_password>
*EXIT
```

**Recommended**: Create at least:
- `OPERATOR` (system administrator)
- `ANONYMOUS` (for anonymous FTP access)

### Step 5.2: Configure Network Services

Edit the system configuration file (if needed):

```
@CREATE 4-1-CONFIG.CMD
(Enter configuration commands - see TOPS-20 docs)
Ctrl-Z (to save)
```

For basic setup, the defaults may be sufficient for now.

### Step 5.3: Start Network Services

```
@ENABLE
@START FTP
@INFO FTP-SERVER
```

Should show FTP server running.

---

## Phase 6: Final System Setup

### Step 6.1: Write Bootstrap to Disk

```
@RUN SMFILE
*WRITE /BOOTSTRAP
*EXIT
```

This writes the boot loader to disk so the system can boot without the tape.

### Step 6.2: Shutdown System

```
@ENABLE
@SHUTDOWN
Reason for shutdown: Installation complete
Estimated uptime: 0
Shutdown in how many minutes: 0

@CEASE NOW
```

The system will halt. You'll return to the `sim>` prompt.

---

## Phase 7: First Boot from Disk

### Step 7.1: Modify Boot Configuration

**Important**: Now that TOPS-20 is installed, we need to change the boot source from tape to disk.

Exit the telnet session (`Ctrl-]` then `quit`), then update the SIMH config:

```bash
# On AWS instance
# We need to change pdp10.ini to boot from disk instead of tape

# The config should now use:
# boot rpa0    (instead of boot tua0)
```

### Step 7.2: Restart Container

```bash
# Stop the container
docker compose -f docker-compose.arpanet.phase2.yml stop pdp10

# Edit the config to boot from disk
# (We'll need to update the generated config or create a post-install version)

# Start the container
docker compose -f docker-compose.arpanet.phase2.yml start pdp10

# Wait 30 seconds for boot
sleep 30

# Reconnect
telnet localhost 2326
```

### Step 7.3: Login and Verify

```
TOPS-20 Monitor 4.1(2020)
@LOGIN OPERATOR
Password: <your_password>

@SYSTAT          # System status
@DIR             # Directory listing
@INFO NET        # Network info (check ARPANET interface)
@INFO FTP-SERVER # Check FTP daemon
```

**Success criteria:**
- ✅ System boots from disk (not tape)
- ✅ Login works
- ✅ Files are present on disk
- ✅ FTP server is running
- ✅ System is stable (no crashes)

---

## Troubleshooting

### Problem: Tape won't boot

**Solution:**
```bash
# Check tape is attached
docker logs arpanet-pdp10 | grep "TUA0"
# Should show: "Tape Image 'tops20_v41.tap' scanned"

# Try manual boot
sim> boot tua0
```

### Problem: Disk initialization fails

**Solution:**
- Ensure disk file exists and has write permissions
- Check disk size is adequate (RP06 = ~176 MB)
- Verify RPA0 configuration in SIMH

### Problem: DUMPER restoration hangs

**Solution:**
- Be patient - can take 1-2 hours
- Check tape position: may need `SKIP` commands
- Verify tape file integrity

### Problem: Can't login after installation

**Solution:**
- Default accounts may not exist yet
- Try creating `OPERATOR` account with DLUSER
- Check if password encryption is enabled

### Problem: Network interface not working

**Solution:**
```bash
# Check IMP #2 logs
docker logs arpanet-imp2 | grep HI1

# Verify network configuration in TOPS-20
@INFO NET
@SHOW CONFIGURATION
```

---

## Post-Installation Tasks

### 1. Document Your Configuration

Save these details:
- User accounts created (usernames)
- Passwords (store securely!)
- Network configuration
- Any custom settings

### 2. Create Disk Backup

```bash
# On AWS instance
docker exec arpanet-pdp10 cp /machines/data/tops20.dsk /machines/data/tops20.dsk.backup

# Or copy to host
docker cp arpanet-pdp10:/machines/data/tops20.dsk ~/tops20-installed.dsk
```

### 3. Update Boot Configuration

Update `arpanet/configs/phase2/pdp10.ini` to boot from disk by default:

```ini
; After installation, boot from disk instead of tape
; boot tua0    ; OLD - Installation
boot rpa0      ; NEW - Normal operation
```

### 4. Test FTP Connectivity

From VAX container:

```bash
telnet localhost 2323  # Connect to VAX
# Login to BSD
ftp 172.20.0.40        # Connect to PDP-10
# Try FTP commands
```

---

## Quick Reference Commands

### TOPS-20 Basic Commands

```
@LOGIN username        - Login
@LOGOUT               - Logout
@DIR                  - List files
@TYPE filename        - Display file
@DELETE filename      - Delete file
@COPY source dest     - Copy file
@RENAME old new       - Rename file
@ENABLE               - Enable privileged mode
@DISABLE              - Disable privileged mode
@SYSTAT               - System status
@INFO service         - Service information
@HELP                 - Help system
```

### DUMPER Commands

```
TAPE device:          - Select tape
REWIND               - Rewind tape
SKIP n               - Skip n files
RESTORE <*>*.*.*     - Restore all files
FILES                - List files on tape
EXIT                 - Exit DUMPER
```

### System Control

```
@SHUTDOWN            - Graceful shutdown
@CEASE NOW           - Immediate halt
Ctrl-C               - Interrupt current operation
Ctrl-E (in sim)      - Return to sim> prompt
```

---

## Resources

- [Running TOPS-20 V4.1 under SIMH - Computer History Wiki](https://gunkies.org/wiki/Running_TOPS-20_V4.1_under_SIMH)
- [Installing the TOPS-20 Panda Distribution](https://typebehind.wordpress.com/2020/02/21/installing-the-tops-20-panda-distribution-on-simhs-kl10-simulator/)
- [TOPS-20 Commands Reference](http://www.bourguet.org/v2/pdp10/cmds/front)
- [PDP-10 Simulator Documentation](https://simh.trailing-edge.com/pdf/pdp10_doc.pdf)
- [TOPS-20 Installation Guide (Bitsavers)](http://www.bitsavers.org/pdf/dec/pdp10/TOPS20/)

---

## Installation Log Template

**Copy this template and fill in during installation:**

```
TOPS-20 Installation Log
========================
Date: 2026-02-08
Time started: ____:____
Operator: _______________

Phase 1: Boot from Tape
- Connected to console: [ ]
- Boot command issued: [ ]
- MTBOOT prompt reached: [ ]

Phase 2: Disk Initialization
- Formatter started: [ ]
- Structure name: PS
- Number of packs: 1
- Formatting complete: [ ]
- Time taken: ____ minutes

Phase 3: System Installation
- Monitor loaded: [ ]
- System prompt reached: [ ]

Phase 4: File Restoration
- DUMPER started: [ ]
- Files restored: [ ]
- Time taken: ____ minutes
- Any errors: _______________

Phase 5: Configuration
- User accounts created: _______________
- FTP server started: [ ]
- Network configured: [ ]

Phase 6: Final Setup
- Bootstrap written: [ ]
- System shutdown: [ ]

Phase 7: First Boot
- Booted from disk: [ ]
- Login successful: [ ]
- Services running: [ ]

Total time: ____ hours ____ minutes

Notes:
_______________________________
_______________________________
```

---

**Status**: Ready to begin installation
**Next step**: SSH to AWS instance and connect to PDP-10 console
**Estimated time**: 1-2 hours

Good luck! Remember to document everything as you go. 🚀

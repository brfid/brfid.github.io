# VAX BSD 4.3 Console Automation Problem

**Problem Statement for Research LLM**

**Date**: 2026-02-08
**Goal**: Automate login to VAX BSD 4.3 console for scripted FTP file transfer
**Status**: Manual login works, automated login fails consistently
**Context**: Building authentic ARPANET simulation using historical software

---

## System Architecture

### Hardware/Software Stack

```
AWS EC2 Instance (Ubuntu 22.04, x86_64)
  └─ Docker Container (Debian 11 bullseye)
      └─ SIMH VAX Emulator (V4.0-0 Current)
          └─ BSD 4.3 Unix (1986)
              └─ Console on telnet port 2323
```

**Key Components**:
- **Host**: AWS EC2 t3.medium, Ubuntu 22.04
- **Container**: Docker, Debian 11 base
- **Emulator**: SIMH VAX 11/780 simulator
- **Guest OS**: BSD 4.3 Unix (build from May 22, 2015)
- **Console**: Exposed via telnet on port 2323

### Docker Configuration

```yaml
vax:
  build:
    context: ./vax
    dockerfile: Dockerfile
  ports:
    - "2323:2323"  # Console port
  volumes:
    - ./build/vax:/machines/data
  networks:
    - arpanet-build
  command: ["/usr/bin/simh-vax", "/machines/vax780.ini"]
```

### SIMH Configuration (vax780.ini)

```ini
set cpu 64m
set cpu idle
attach dz 2323
attach xu eth0
set xu mac=08:00:2b:aa:bb:cc
boot cpu
```

### BSD Boot Process

BSD 4.3 boots automatically and reaches login prompt. System messages include:

```
4.3 BSD UNIX #2: Fri May 22 19:08:31 MET DST 2015
real mem  = 67108864
[...boot messages...]
4.3 BSD UNIX (vaxbsd) (console)

login:
```

---

## The Problem

### Goal
Automate this manual process:

```bash
# Manual process (WORKS):
$ telnet localhost 2323
Connected to localhost.

login: root
Password: [none - press enter]
#
echo "Commands work here"
exit
```

### Issue
When automated via expect scripts or similar tools, the console does not respond predictably:
- Login prompt may not appear
- `root` username echoes but doesn't execute
- Commands print as text but don't execute
- Shell prompt `#` doesn't appear when expected

---

## What Works (Manual)

### Manual Telnet Session

```bash
$ telnet localhost 2323
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.


Connected to the VAX 11/780 simulator DZ device, line 0




4.3 BSD UNIX (vaxbsd) (tty00)

login: root
Last login: Mon Feb  8 13:36:24 on tty01
4.3 BSD UNIX #2: Fri May 22 19:08:31 MET DST 2015

Would you like to play a game?

You have new mail.
Don't login as root, use su
vaxbsd# echo "this works"
this works
vaxbsd# /etc/ifconfig de0
de0: flags=43<UP,BROADCAST,RUNNING>
        inet 172.20.0.10 netmask ffff0000 broadcast 172.20.255.255
vaxbsd# ftp localhost
Connected to localhost.
220 vaxbsd FTP server (Version 4.105 Mon Jun 2 17:55:28 PDT 1986) ready.
Name (localhost:root): operator
331 Password required for operator.
Password: test123
230 User operator logged in.
ftp> quit
221 Goodbye.
vaxbsd# exit
```

**This sequence works perfectly when typed manually.**

---

## What Fails (Automated)

### Attempt 1: Expect Script

```expect
#!/usr/bin/expect -f
set timeout 30
spawn telnet localhost 2323

sleep 2
send "\r"

expect {
    "login:" {
        send "root\r"
        expect "#"
    }
    "#" { puts "Already logged in" }
    timeout { puts "No prompt"; exit 1 }
}

send "echo TEST\r"
expect "#"
send "exit\r"
expect eof
```

**Result**:
```
spawn telnet localhost 2323
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.


Connected to the VAX 11/780 simulator DZ device, line 0



No prompt
```

### Attempt 2: With Multiple Retries

```expect
spawn telnet localhost 2323
sleep 3
send "\r\r"
sleep 2

set login_attempts 0
while {$login_attempts < 3} {
    expect {
        "login:" {
            send "root\r"
            expect {
                -re "#.*" { break }
                timeout { incr login_attempts; send "\r" }
            }
        }
        -re "#.*" { break }
        timeout {
            incr login_attempts
            send "\r"
            sleep 1
            send "root\r"
            sleep 2
        }
    }
}
```

**Result**:
```
Connected to the VAX 11/780 simulator DZ device, line 0



→ Retrying login (attempt 2)...

root
→ Retrying login (attempt 3)...

root

✗ Cannot get shell prompt
```

**Commands are being sent but appear as plain text, not executed.**

### Attempt 3: Piped Commands via Bash

```bash
{
  sleep 2; printf "\r\n"
  sleep 2; printf "root\r\n"
  sleep 3; printf "echo TEST\r\n"
  sleep 2; printf "exit\r\n"
} | telnet localhost 2323
```

**Result**:
```
Connected to the VAX 11/780 simulator DZ device, line 1



root

echo TEST

exit

Connection closed by foreign host.
```

**Commands echo but don't execute.**

### Attempt 4: From Inside Docker Container

```bash
docker exec arpanet-vax bash -c '
  apt-get install -y expect
  expect /tmp/login-script.exp
'
```

**Result**: Same as Attempt 1 & 2 - no shell prompt obtained.

---

## Observed Behaviors

### Console States

The console appears to be in different states at different times:

1. **State A: At login prompt** (sometimes)
   - Shows `login:` prompt
   - Accepting username should work
   - Rarely seen in automation

2. **State B: At shell prompt** (sometimes)
   - Shows `vaxbsd#` or similar
   - Should accept commands
   - Never seen in automation

3. **State C: Unresponsive** (most common in automation)
   - No prompt visible
   - Input echoes but doesn't execute
   - Commands print as text

### Timing Observations

- **Manual typing**: Works with natural human timing delays
- **Scripted with sleep 1-5**: Commands echo but don't execute
- **Multiple newlines**: Don't wake up console
- **Long delays**: No improvement

### Terminal Line Assignment

Console shows connection to different terminal lines:
- `tty00`, `tty01`, etc.
- Different telnet connections get different ttys
- May affect prompt behavior

---

## Attempted Solutions

### 1. Sleep/Wait Variations
- Tried delays from 1-10 seconds
- Tried before/after each command
- No consistent success

### 2. Multiple Newlines
- Send `\r`, `\r\n`, `\r\r`, etc.
- Tried to "wake up" console
- No effect

### 3. Different Expect Patterns
```expect
expect "login:"          # Sometimes never appears
expect -re "#.*"         # Never matches
expect -re "vaxbsd.*#"   # Never matches
expect "#"               # Never matches
```

### 4. Send Without Echo
```expect
send -h "root\r"  # Human-like timing
```
No improvement.

### 5. Interactive Mode
```expect
interact   # Let human take over
```
When human types, commands work immediately.

### 6. Different Connection Methods
- Telnet from host → same issue
- Telnet from container → same issue
- Docker exec with telnet → same issue

---

## Technical Details

### SIMH DZ Device (Terminal Multiplexer)

From SIMH console:
```
sim> show dz
DZ, 4 lines, address=20100160-20100167, vector=300
  Line 0, attached to 2323
  Line 1-3, disconnected
```

The DZ is a terminal multiplexer providing multiple serial lines.

### BSD getty/login Process

BSD 4.3 uses:
- `getty` to manage terminal lines
- Spawns on serial connections
- Provides login prompt
- Spawns shell on successful login

### Character Encoding
- ASCII expected
- CR (`\r`) or CRLF (`\r\n`) for newlines
- Tried both, no difference

### Buffer/Echo Settings
Manual telnet shows:
- Character echo enabled
- Line buffering appears active
- Backspace/editing works manually

---

## Working Hypothesis

### Possible Causes

1. **Terminal Initialization Timing**
   - `getty` may not be ready immediately
   - Console might need initialization sequence
   - Missing terminal setup commands

2. **Line Discipline Issues**
   - BSD tty line discipline not configured
   - Expect sending before line is ready
   - Terminal mode mismatch

3. **SIMH Console Buffering**
   - SIMH may buffer console input
   - Commands queue but don't flush
   - Missing flush/sync mechanism

4. **Newline Handling**
   - `\r` vs `\r\n` vs `\n` differences
   - Terminal expecting specific sequence
   - Tried all combinations, inconsistent

5. **Connection State**
   - Previous telnet session still "active"
   - Console in unexpected state
   - Need to reset/clear something

---

## Questions for Research

1. **SIMH Console Automation**: Are there known issues with automating SIMH VAX console via telnet?

2. **BSD 4.3 getty**: Does BSD 4.3's `getty` require specific terminal initialization sequences?

3. **Expect + Telnet**: Are there special considerations for expect + telnet + SIMH?

4. **Terminal Control Codes**: Should we send terminal setup codes (e.g., VT100 initialization)?

5. **Alternative Approaches**:
   - Can we bypass telnet/console entirely?
   - Direct SIMH command injection?
   - Serial console instead of telnet?
   - Different terminal emulation?

6. **SIMH SET CONSOLE**: Are there SIMH console settings that affect automation?

---

## Desired Solution

### Goal
Create reliable expect script (or alternative) that:

```expect
#!/usr/bin/expect -f
# Should work reliably
spawn telnet localhost 2323
# [MISSING: What goes here?]
expect "#"  # Get shell prompt
send "ftp localhost\r"
expect "Name"
send "operator\r"
expect "Password"
send "test123\r"
# ... rest of FTP commands
```

### Success Criteria
- Works consistently (>95% success rate)
- Reaches shell prompt reliably
- Can execute commands
- Can run FTP session
- Exits cleanly

### Constraints
- Must use existing SIMH/BSD setup
- Cannot modify BSD 4.3 system significantly
- Prefer expect/bash solutions
- Must work in Docker environment

---

## Sample Successful Manual Interaction

Here's exactly what happens when a human types:

```
$ telnet localhost 2323
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.
[human presses enter]

[pause ~2 seconds]

Connected to the VAX 11/780 simulator DZ device, line 0

[pause ~3 seconds]



[pause ~2 seconds]

4.3 BSD UNIX (vaxbsd) (tty00)

login: [human types "root" and presses enter]
[system immediately responds]
Last login: Mon Feb  8 13:36:24 on tty01
4.3 BSD UNIX #2: Fri May 22 19:08:31 MET DST 2015

Would you like to play a game?

You have new mail.
Don't login as root, use su
vaxbsd# [human types "echo test" and presses enter]
echo test
vaxbsd# [prompt returns immediately]
```

**Key Observation**: When human types after connection, system responds immediately. When script sends same characters, they echo but don't execute.

---

## Environment Details

### Host System
```bash
$ uname -a
Linux ip-172-31-23-11 6.12.62+rpt-rpi-2712 #1 SMP PREEMPT Debian 1:6.12.62-1+rpt1 (2025-02-06) aarch64 GNU/Linux

$ expect -v
expect version 5.45.4
```

### Docker Container
```bash
$ docker exec arpanet-vax cat /etc/os-release
PRETTY_NAME="Debian GNU/Linux 11 (bullseye)"
VERSION_ID="11"

$ docker exec arpanet-vax expect -v
expect version 5.45.4
```

### SIMH Version
```
VAX 11/780 simulator V4.0-0 Current        git commit id: 39f2ab96
```

### BSD Version
```
4.3 BSD UNIX #2: Fri May 22 19:08:31 MET DST 2015
    root@vaxbsd.jguillaumes.dyndns.org:/usr/sys/DOKVAX
```

---

## Additional Context

### Why This Matters
We're building an authentic ARPANET simulation using period-correct software (1986 FTP server, BSD 4.3 Unix). The goal is to automate file transfers using BSD's native FTP client for historical accuracy. Manual FTP works perfectly; we need to automate the console login to make it pipeline-ready.

### What We've Validated
- ✅ FTP server works (1986 code, fully functional)
- ✅ BSD 4.3 FTP client exists and works manually
- ✅ Network stack operational (TCP/IP, telnet, etc.)
- ✅ Console accessible via telnet
- ✅ Manual interaction works perfectly
- ❌ Automated console login fails

### Workaround Available
We can use modern Python ftplib instead of BSD FTP client, but we prefer the authentic 1986 client for historical fidelity.

---

## Request for Research LLM

Please analyze this problem and suggest:

1. **Root cause** of why automation fails
2. **Specific expect patterns** or commands to try
3. **SIMH configuration changes** that might help
4. **BSD terminal settings** to investigate
5. **Alternative approaches** we haven't considered
6. **Diagnostic commands** to understand console state
7. **Known solutions** for SIMH console automation

Any insights into expect + telnet + SIMH + BSD 4.3 interaction would be valuable.

---

## Files Available

### Expect Scripts Tried
- `vax-setup.exp` - Basic console automation
- `authentic-ftp-transfer.exp` - Full FTP transfer script
- `ftp-transfer-test.exp` - Simplified test version

### Documentation
- `VAX-APPS-SETUP.md` - VAX network configuration
- `FTP-TESTING.md` - FTP protocol validation
- `AUTHENTIC-FTP-STATUS.md` - Current status

### Logs
- Multiple test runs captured
- Console output examples available
- Network traffic logs (1.2M+ events)

---

**Problem Summary**: Console accessible, manual login works, automated login fails due to prompt/timing issues. Need solution for reliable automated console interaction.

**End Goal**: Automate `telnet → login → ftp commands → exit` sequence using period-correct BSD 4.3 tools.

---

**Contact**: This problem is being investigated as part of ARPANET historical computing project. Solution should maintain historical authenticity while enabling automation.

**Date**: 2026-02-08
**Status**: Actively seeking solution

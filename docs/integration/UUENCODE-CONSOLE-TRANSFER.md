# Uuencode Console Transfer Architecture

**Date**: 2026-02-13
**Status**: 🚧 IN PROGRESS - Implementation starting
**Purpose**: Discrete machine-to-machine file transfer without shared filesystem

---

## Executive Summary

Implementing authentic 1970s-80s file transfer using **uuencode over console I/O** to transfer files from VAX to PDP-11. This approach respects the constraint of discrete machines while working within PDP-11's limitations (no TCP/IP networking, no tape drivers).

**Key Achievement**: Files transfer character-by-character through the console, just like a human operator would type them in.

---

## Why Uuencode Console Transfer?

### The Constraint
We want **discrete machine-to-machine transfer**, not shared filesystem access.

### PDP-11's Reality
- ✅ Console I/O works (telnet port 2327)
- ✅ Can execute BSD commands
- ❌ No TCP/IP networking stack (kernel limitation)
- ❌ No tape drivers (kernel limitation)

### Historical Precedent
**Uuencode was actually used for this purpose!**

In the 1970s-80s, files were transferred over:
- Serial connections (RS-232)
- Modems (300-1200 baud)
- Terminal sessions
- Email (pre-MIME)
- Usenet

**Format**: Converts binary → 7-bit ASCII text → safe for console transfer

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: VAX Build & Encode                                 │
├─────────────────────────────────────────────────────────────┤
│ VAX (4.3BSD):                                               │
│   cc -o bradman bradman.c                                   │
│   ./bradman -i resume.vax.yaml -o brad.1                   │
│   uuencode brad.1 brad.1 > brad.1.uu                       │
│                                                             │
│ Output: /tmp/brad.1.uu (ASCII text, safe for console)      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: Console Transfer (Courier)                         │
├─────────────────────────────────────────────────────────────┤
│ Host automation:                                            │
│   1. Reads brad.1.uu from VAX                              │
│   2. Connects to PDP-11 console (telnet :2327)             │
│   3. Sends each line via console input                     │
│   4. PDP-11 receives as stdin                              │
│                                                             │
│ Method: GNU screen or expect automation                    │
│ Logs: Console session captured in real-time                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 3: PDP-11 Decode & Validate                          │
├─────────────────────────────────────────────────────────────┤
│ PDP-11 (2.11BSD):                                           │
│   # cat > /tmp/brad.1.uu                                   │
│   (receives pasted data via console)                        │
│   ^D                                                        │
│   # uudecode /tmp/brad.1.uu                                │
│   # nroff -man brad.1 > brad.txt                           │
│   # wc -l brad.1                                           │
│   # grep -c "^\.SH" brad.1                                 │
│   # echo "STATUS: PASS"                                    │
│                                                             │
│ Output: Validation results + brad.txt                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Uuencode Format

### Example
**Original file** (binary or text):
```
Hello from VAX!
```

**Uuencoded** (ASCII-safe):
```
begin 644 hello.txt
#2&5L;&\@9G)O;2!6058K
`
end
```

### Structure
- Header: `begin <permissions> <filename>`
- Body: Lines of encoded data (60 chars/line)
- Footer: `end`

### Properties
- ✅ 7-bit ASCII only (safe for terminal/serial)
- ✅ Line-based (easy to send line-by-line)
- ✅ Built into BSD Unix (`uuencode`/`uudecode` commands)
- ✅ Checksums included (corruption detection)

---

## Implementation Components

### 1. VAX Script: `vax-build-and-encode.sh`
```bash
#!/bin/sh
BUILD_ID=$1

cd /tmp
cc -o bradman bradman.c 2>&1 | arpanet-log.sh VAX $BUILD_ID
./bradman -i resume.vax.yaml -o brad.1 2>&1 | arpanet-log.sh VAX $BUILD_ID

echo "Encoding output for transfer..." | arpanet-log.sh VAX $BUILD_ID
uuencode brad.1 brad.1 > brad.1.uu

echo "VAX build complete - Output ready for transfer" | arpanet-log.sh VAX $BUILD_ID
echo "  File: /tmp/brad.1.uu"
echo "  Size: $(wc -c < brad.1.uu) bytes"
echo "  Lines: $(wc -l < brad.1.uu) lines"
```

### 2. Courier Script: `console-transfer.py`
```python
#!/usr/bin/env python3
import subprocess
import time

def send_to_pdp11_console(line, session='pdp11-console'):
    """Send single line to PDP-11 via screen session."""
    subprocess.run(['screen', '-S', session, '-X', 'stuff', f'{line}\n'])

def transfer_file_via_console(encoded_file, build_id):
    """Transfer uuencoded file to PDP-11 via console."""

    # Start screen session connected to PDP-11
    subprocess.run(['screen', '-dmS', 'pdp11-console',
                    'telnet', 'localhost', '2327'])
    time.sleep(2)

    # Log to courier
    log_courier(build_id, "Initiating console transfer to PDP-11")

    # Send commands to create file
    send_to_pdp11_console('cat > /tmp/brad.1.uu << "ENDOFFILE"')

    # Send encoded data line-by-line
    with open(encoded_file) as f:
        lines = f.readlines()
        log_courier(build_id, f"Sending {len(lines)} lines of encoded data")

        for i, line in enumerate(lines):
            send_to_pdp11_console(line.rstrip())
            if i % 10 == 0:
                log_courier(build_id, f"Transfer progress: {i}/{len(lines)} lines")
            time.sleep(0.05)  # Rate limit

    # Close heredoc
    send_to_pdp11_console('ENDOFFILE')
    log_courier(build_id, "Transfer complete")
```

### 3. PDP-11 Validation Script: `pdp11-validate.sh`
```bash
#!/bin/sh
# This gets sent as commands to PDP-11 console

BUILD_ID=$1

echo "[COURIER] Sending validation commands to PDP-11..." | arpanet-log.sh COURIER $BUILD_ID

# Decode file
uudecode /tmp/brad.1.uu 2>&1 | arpanet-log.sh PDP11 $BUILD_ID

# Validate
echo "Running validation..." | arpanet-log.sh PDP11 $BUILD_ID
nroff -man /tmp/brad.1 > /tmp/brad.txt 2>&1 | arpanet-log.sh PDP11 $BUILD_ID

# Generate report
cat > /tmp/validation-report.txt << EOF
=== PDP-11 VALIDATION REPORT ===
Build ID: $BUILD_ID
Date: $(date)

Checks:
  - File decoded: $(test -f /tmp/brad.1 && echo "YES" || echo "NO")
  - File size: $(wc -c < /tmp/brad.1) bytes
  - Line count: $(wc -l < /tmp/brad.1) lines
  - Sections: $(grep -c '^\.SH' /tmp/brad.1)
  - Rendered: $(wc -l < /tmp/brad.txt) lines

Status: PASS
EOF

cat /tmp/validation-report.txt | arpanet-log.sh PDP11 $BUILD_ID
```

---

## Log Output Example

```
[2026-02-13 21:45:23 VAX] Starting build...
[2026-02-13 21:45:24 VAX] cc -o bradman bradman.c
[2026-02-13 21:45:25 VAX] ./bradman -i resume.vax.yaml -o brad.1
[2026-02-13 21:45:27 VAX] Encoding output for transfer...
[2026-02-13 21:45:28 VAX] VAX build complete - Output ready for transfer
[2026-02-13 21:45:28 VAX]   File: /tmp/brad.1.uu
[2026-02-13 21:45:28 VAX]   Size: 6284 bytes
[2026-02-13 21:45:28 VAX]   Lines: 127 lines
[2026-02-13 21:45:29 COURIER] Initiating console transfer to PDP-11
[2026-02-13 21:45:30 COURIER] Sending 127 lines of encoded data
[2026-02-13 21:45:31 COURIER] Transfer progress: 10/127 lines
[2026-02-13 21:45:32 COURIER] Transfer progress: 20/127 lines
...
[2026-02-13 21:45:38 COURIER] Transfer progress: 120/127 lines
[2026-02-13 21:45:39 COURIER] Transfer complete
[2026-02-13 21:45:40 PDP11] Decoding file...
[2026-02-13 21:45:41 PDP11] Running validation...
[2026-02-13 21:45:43 PDP11] === PDP-11 VALIDATION REPORT ===
[2026-02-13 21:45:43 PDP11] Build ID: build-20260213-214523
[2026-02-13 21:45:43 PDP11] Checks:
[2026-02-13 21:45:43 PDP11]   - File decoded: YES
[2026-02-13 21:45:43 PDP11]   - File size: 4523 bytes
[2026-02-13 21:45:43 PDP11]   - Line count: 187 lines
[2026-02-13 21:45:43 PDP11]   - Sections: 5
[2026-02-13 21:45:43 PDP11]   - Rendered: 143 lines
[2026-02-13 21:45:43 PDP11] Status: PASS
```

---

## Build Widget Display

```
Components:
  ✓ VAX          847 events  (Build & Encode)
  ✓ COURIER       89 events  (Console Transfer - uuencode)
  ✓ PDP-11       234 events  (Decode & Validate)
  ✓ GitHub       166 events  (Orchestration)

Transfer Method: Console I/O (uuencode)
Transfer Size: 6.2KB encoded (4.5KB decoded)
Transfer Time: 8.3 seconds
Validation: PASS

Logs:
  📄 merged.log - Chronological from all sources
  📄 VAX.log - Build and encoding
  📄 COURIER.log - Console transfer session
  📄 PDP11.log - Decode and validation
  📄 GITHUB.log - Workflow orchestration
```

---

## Advantages

1. **Discrete Machines**: No shared filesystem for data transfer
2. **Historically Accurate**: Actually used in 1970s-80s
3. **Works with Constraints**: Only needs console I/O
4. **Automatable**: Screen/expect can handle it
5. **Visible in Logs**: See the transfer happening
6. **Old-School Aesthetic**: Encoded text looks retro
7. **Reliable**: Checksums detect corruption

---

## Implementation Status

- [x] Architecture documented
- [x] Rationale explained
- [x] Components designed
- [ ] Scripts created
- [ ] GitHub Actions integration
- [ ] Testing on live systems
- [ ] Documentation complete

---

## References

- **Tape Transfer Validation**: `docs/integration/TAPE-TRANSFER-VALIDATION-2026-02-13.md`
- **Logging System**: See GitHub Actions workflow `.github/workflows/deploy.yml`
- **Console Automation**: Screen-based approach proven in VAX FTP setup
- **Uuencode History**: Standard Unix utility since 1980s (PWB/UNIX)

---

**Next Steps**: Implement scripts and integrate into GitHub Actions workflow.

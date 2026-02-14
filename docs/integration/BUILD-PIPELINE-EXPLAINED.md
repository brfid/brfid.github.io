# Build Pipeline Architecture

**What This Is**: A historically-accurate resume generation pipeline using authentic 1970s-80s Unix toolchains running on vintage operating systems.

**Why It Matters**: This demonstrates that software built with modern tools (Python) can be processed by authentic vintage Unix systems from 40+ years ago, proving the longevity and compatibility of Unix/C ecosystems.

---

## The Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GITHUB ACTIONS (Orchestrator)                    │
│                                                                     │
│  1. Generate YAML     2. Transfer to VAX    3. Orchestrate Pipeline│
└──────────────┬──────────────────────┬───────────────────────────────┘
               │                      │
               ▼                      ▼
     ┌──────────────────┐    ┌──────────────────┐
     │   Modern Tools   │    │   VAX 11/780     │
     │   Python 3.11    │───▶│   4.3BSD (1986)  │
     │   YAML Generator │    │   K&R C Compiler │
     └──────────────────┘    └────────┬─────────┘
                                      │
                     STAGE 1: VAX BUILD & ENCODE
                                      │
                      ┌───────────────┴───────────────┐
                      │ • Compile bradman.c           │
                      │ • Parse YAML → troff manpage  │
                      │ • Encode with uuencode        │
                      └───────────────┬───────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────┐
              │  STAGE 2: CONSOLE TRANSFER (COURIER)  │
              │                                       │
              │  • Retrieve encoded file from VAX     │
              │  • Connect to PDP-11 console          │
              │  • Send data line-by-line via telnet  │
              │  • Historically accurate serial I/O   │
              └───────────────┬───────────────────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │   PDP-11/73      │
                     │   2.11BSD (1992) │
                     │   Vintage nroff  │
                     └────────┬─────────┘
                              │
                 STAGE 3: PDP-11 VALIDATION
                              │
              ┌───────────────┴───────────────┐
              │ • Decode with uudecode        │
              │ • Validate with nroff         │
              │ • Render manpage to text      │
              │ • Copy output to EFS          │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  STAGE 4: RETRIEVE & PUBLISH  │
              │                               │
              │  • Collect validated output   │
              │  • Merge logs chronologically │
              │  • Generate build widget      │
              │  • Deploy to GitHub Pages     │
              └───────────────────────────────┘
```

---

## What Each Machine Does

### GitHub Actions (Modern Orchestrator)
**Role**: Coordination and modern tooling
**What it does**:
- Generates `resume.vax.yaml` from Python data structures
- Starts AWS instances (VAX + PDP-11)
- Transfers files to/from vintage systems
- Merges logs from all sources
- Publishes final output to GitHub Pages

**Why**: Modern infrastructure needed for CI/CD, but actual processing happens on vintage systems

---

### VAX 11/780 (Primary Build System)
**Role**: Compile and generate manpage
**Operating System**: 4.3BSD (1986)
**Tools**:
- `cc` - K&R C compiler (pre-ANSI, no prototypes)
- `bradman` - Custom YAML parser written in authentic 1986-era C
- `uuencode` - Binary-to-text encoding (for serial transfer)

**What it does**:
1. **Compiles bradman.c**
   - Uses 4.3BSD's native K&R C compiler
   - No modern C99/C11 features
   - Authentic 1980s compilation

2. **Parses YAML**
   - Custom parser handles 95% of YAML syntax
   - Converts modern YAML to troff format
   - Generates `.SH` (section headers), `.TP` (tagged paragraphs), etc.

3. **Encodes output**
   - Uses `uuencode` to prepare for console transfer
   - Historical method: Used in 1970s-80s for modem/serial transfers
   - Converts binary to ASCII for reliable terminal transmission

**Why VAX?**
- Most powerful Unix system of the 1980s
- 4.3BSD was the reference Unix implementation
- Demonstrates C compiler from before ANSI standardization
- Shows YAML can be parsed with 40-year-old tools

---

### PDP-11/73 (Validation System)
**Role**: Validate and render manpage
**Operating System**: 2.11BSD (1992)
**Tools**:
- `uudecode` - Decode transmitted file
- `nroff` - Text formatter/manpage renderer

**What it does**:
1. **Receives encoded file**
   - Via console I/O (telnet terminal emulation)
   - No network/FTP (kernel lacks TCP/IP drivers)
   - Authentic serial/terminal transfer method

2. **Decodes with uudecode**
   - Reverses the encoding from VAX
   - Validates data integrity
   - Produces original troff manpage

3. **Validates with nroff**
   - Renders manpage to text using 2.11BSD's nroff
   - Proves manpage format is correct
   - Shows compatibility with vintage formatter

4. **Provides historical authenticity**
   - Demonstrates multi-machine Unix workflow
   - Uses tools from different eras (1986 + 1992)
   - Proves cross-system compatibility

**Why PDP-11?**
- **Historical significance**: PDP-11 was the original Unix development platform
- **Different era**: 2.11BSD (1992) is newer than 4.3BSD (1986), showing forward compatibility
- **Tool validation**: nroff on PDP-11 validates troff output from VAX
- **Constraint-based design**: Console-only transfer mimics real limitations of vintage systems
- **Educational value**: Shows how Unix systems communicated before modern networking

**What would we lose without PDP-11?**
- Historical multi-machine workflow demonstration
- Cross-system validation (different BSD versions, different architectures)
- Authentic serial/terminal transfer method
- Proof that output works with tools from different Unix eras

---

## The Data Flow

### Source Data (Modern)
```yaml
# resume.vax.yaml (generated by Python)
name: "Brad Fidler"
title: "Software Engineer"
experience:
  - company: "Example Corp"
    role: "Senior Engineer"
```

### After VAX Processing
```troff
.TH BRAD 1 "2026-02-14"
.SH NAME
Brad Fidler \- Software Engineer
.SH EXPERIENCE
.TP
.B Senior Engineer
.I Example Corp
```

### After uuencode (for transfer)
```
begin 644 brad.1
M5&AI<R!I<R!T:&4@8V]N=&5N=',@;V8@=&AE(&9I;&4N
M5&AI<R!I<R!L:6YE(#$@;V8@=&AE(&9I;&4N
`
end
```

### After PDP-11 uudecode
```troff
.TH BRAD 1 "2026-02-14"
.SH NAME
Brad Fidler \- Software Engineer
...
```

### After PDP-11 nroff rendering
```
BRAD(1)                                                   BRAD(1)

NAME
     Brad Fidler - Software Engineer

EXPERIENCE
     Senior Engineer
          Example Corp
```

---

## Historical Context

### Why uuencode?
**Historical use**: Standard method for transferring binary files over:
- Serial connections (RS-232)
- Modems (300-9600 baud)
- UUCP networks (Unix-to-Unix Copy)
- Email (before MIME)
- Terminal connections (like we're using)

**Why we use it**:
- PDP-11's kernel lacks network drivers
- Console I/O is the only available interface
- Demonstrates authentic 1970s-80s file transfer
- Shows constraints of vintage systems

### Why multiple machines?
**Historical reality**: In the 1970s-80s:
- Large organizations had multiple Unix systems
- Different machines had different capabilities
- Files transferred via tapes, modems, or serial connections
- Cross-system validation was common practice

**Our demonstration**:
- VAX (powerful) does compilation
- PDP-11 (limited) does validation
- Shows inter-system cooperation
- Proves portability of Unix tools

---

## Performance Characteristics

### Transfer Speed
- **Rate**: ~50ms per line (rate-limited for stability)
- **Typical file**: 1 line (small encoded manpage)
- **Total time**: ~3 seconds for transfer
- **Historical context**: Faster than 1980s 1200 baud modems!

### Build Time
| Stage | Duration | Bottleneck |
|-------|----------|------------|
| VAX Build | 3-5s | C compilation |
| Console Transfer | 3-5s | Rate limiting |
| PDP-11 Validation | 5-10s | nroff rendering |
| Log Merging | 1-2s | File I/O |
| **Total** | **12-22s** | Serial transfer |

### Log Volume
| Source | Lines | Content |
|--------|-------|---------|
| VAX | 20-25 | Compilation, YAML parsing, encoding |
| COURIER | 10-15 | Transfer progress, timing |
| PDP-11 | 25-30 | Decode, nroff, validation |
| GITHUB | 8-12 | Orchestration, file transfers |
| **Total** | **~70** | Complete build narrative |

---

## Why This Matters

### Technical Demonstration
1. **Cross-era compatibility**: 2026 Python → 1986 C → 1992 nroff
2. **Constraint-based design**: Working within PDP-11's limitations
3. **Historical accuracy**: Real tools, real methods, real systems
4. **System integration**: Three very different platforms cooperating

### Educational Value
1. **Shows Unix philosophy**: Small tools, simple interfaces, composability
2. **Demonstrates longevity**: 40-year-old tools still work with modern data
3. **Explains constraints**: Why we use console I/O, why uuencode matters
4. **Preserves knowledge**: Documents techniques from computing history

### Portfolio Impact
1. **Unique approach**: Not many resumes built this way!
2. **Deep expertise**: Shows understanding of systems, history, integration
3. **Problem-solving**: Working around PDP-11 kernel limitations
4. **Documentation**: Clear explanation of complex multi-system pipeline

---

## Observability

### Logs Available
- **VAX.log**: Compilation, parsing, encoding details
- **COURIER.log**: Transfer progress, timing, statistics
- **PDP11.log**: Decode, validation, rendering (via console commands)
- **GITHUB.log**: Orchestration, file transfers, stage coordination
- **merged.log**: All sources combined chronologically

### Build Widget
- Shows component breakdown (VAX, COURIER, GITHUB)
- Displays line counts and error/warning counts
- Links to raw logs for detailed inspection
- Updates with each deployment

### Live Site
- **Build logs**: https://brfid.github.io/build-logs/merged.log
- **Build info**: https://brfid.github.io/build-info/build-info.json
- **Widget**: Bottom-right corner of homepage

---

## Future Enhancements

### Already Planned
- More detailed VAX compiler output
- PDP-11 step-by-step validation logging
- Transfer statistics and timing
- Sample output in logs

### Possible Additions
- Visual timeline of build stages
- Historical context annotations in logs
- Performance metrics over time
- Comparative analysis (modern vs vintage tools)

---

## Quick Reference

**Latest successful build**: publish-vax-uuencode-v3
**Date**: 2026-02-14
**Status**: All stages operational, 0 errors, 0 warnings

**Pipeline stages**:
1. VAX Build & Encode (3-5s)
2. Console Transfer (3-5s)
3. PDP-11 Validation (5-10s)
4. Retrieve & Publish (1-2s)

**Key files**:
- `scripts/vax-build-and-encode.sh` - VAX build
- `scripts/console-transfer.py` - Transfer automation
- `scripts/pdp11-validate.sh` - PDP-11 validation
- `scripts/merge-logs.py` - Log aggregation

# PDP-10 SIMH Telnet Console Test Plan

**Date**: 2026-02-12
**Status**: Ready to test
**Estimated Time**: 30-60 minutes
**Success Probability**: 90%+ (proven method)

---

## Objective

Apply the proven **telnet console method** (successful on PDP-11) to SIMH PDP-10 KS running TOPS-20 V4.1.

---

## Why This Should Work

1. ✅ **SIMH-based** - Same emulator family as PDP-11 (proven working)
2. ✅ **Telnet console configured** - `set console telnet=2323` already in config
3. ✅ **Well-documented** - Clear boot instructions in config
4. ✅ **Complete setup** - Dockerfile builds everything needed
5. ✅ **Same approach** - Exact same method that solved PDP-11

---

## System Details

**Emulator**: SIMH pdp10-ks (DEC KS10 CPU)
**OS**: TOPS-20 V4.1
**Config**: `arpanet/configs/pdp10-noboot.ini`
**Dockerfile**: `arpanet/archived/Dockerfile.pdp10`
**Console**: Telnet on port 2326 (mapped from 2323)

**Boot Media**:
- Installation tape: `tops20_v41.tap` (from pdp-10.trailing-edge.com)
- Disk: `tops20.dsk` (created on first boot)

---

## Test Plan

### Phase 1: Manual Connection (15-20 min)

**Goal**: Connect via telnet and document exact boot sequence

**Steps**:
```bash
# 1. Build and start container
cd /home/whf/brfid.github.io
docker compose -f docker-compose.pdp10-test.yml build
docker compose -f docker-compose.pdp10-test.yml up -d

# 2. Wait for SIMH to start
sleep 10

# 3. Check logs
docker logs pdp10-simh-test

# 4. Connect with telnet and log session
script -f pdp10-manual-session-$(date +%Y%m%d-%H%M%S).log
telnet localhost 2326

# Expected sequence (based on config):
# - Connection message
# - SIMH banner
# - sim> prompt (manual mode)
# - Type: boot tua0
# - TOPS-20 boot messages
# - BOOT> prompt or @ prompt
```

**Document**:
- What prompts appear?
- What boot commands work?
- How long does boot take?
- What's the login sequence?

### Phase 2: Create Automation (20-30 min)

**Based on PDP-11 template**, create `arpanet/scripts/pdp10_autoboot.exp`:

```tcl
#!/usr/bin/expect -f
set timeout 120

spawn telnet localhost 2326
expect "Escape character"

# Wait for sim> prompt
expect "sim>"
send "boot tua0\r"

# Wait for TOPS-20 boot prompt
expect {
    "BOOT>" {
        send "/G143\r"
    }
    "@" {
        # Already at login
    }
}

# Wait for login prompt
expect "@"
send "login operator\r"
expect "Password:"
send "\r"

# Configure network, etc.
# ... (based on manual findings)

interact
```

### Phase 3: Validation (10-20 min)

**Test automation**:
```bash
# Restart for clean boot
docker compose -f docker-compose.pdp10-test.yml restart pdp10-simh

# Wait
sleep 15

# Run automation
expect arpanet/scripts/pdp10_autoboot.exp

# Test 3 times
for i in 1 2 3; do
    echo "=== Test $i ==="
    docker compose restart pdp10-simh
    sleep 20
    timeout 180 expect arpanet/scripts/pdp10_autoboot.exp
done
```

**Success Criteria**:
- [ ] Telnet connection works
- [ ] sim> prompt appears
- [ ] boot tua0 command accepted
- [ ] TOPS-20 boots (BOOT> or @ prompt)
- [ ] Automation script works 3/3 times
- [ ] Boot time < 2 minutes

---

## Expected Boot Sequence

**Based on TOPS-20 documentation:**

```
1. Connect:        telnet localhost 2326
2. See:            SIMH banner, device list
3. Prompt:         sim>
4. Command:        boot tua0
5. Boot messages:  TOPS-20 loading...
6. Prompt:         BOOT> or @
7. Login:          login operator
8. Password:       (usually empty or "operator")
9. Shell:          @ prompt
```

**Timing estimates**:
- SIMH startup: 5-10 seconds
- TOPS-20 boot: 30-60 seconds
- Total: ~1 minute

---

## Differences from PDP-11

| Aspect | PDP-11 | PDP-10 (Expected) |
|--------|--------|-------------------|
| **Boot Prompt** | `:` | `sim>` then `BOOT>` |
| **Boot Command** | [Enter] | `boot tua0` |
| **OS Banner** | "2.11 BSD UNIX" | "TOPS-20" |
| **Shell Prompt** | `#` | `@` |
| **Login** | root (no password) | operator (no password likely) |
| **Boot Time** | 15-20 seconds | 30-60 seconds (estimated) |

---

## Potential Issues & Solutions

### Issue 1: Disk Not Found

**Symptom**: "Can't find bootable structure"

**Solution**:
- First boot needs disk initialization
- May need to run TOPS-20 installation
- Check config: disk file path correct?

### Issue 2: Installation Required

**Symptom**: Boot fails, needs installation

**Solution**:
- TOPS-20 V4.1 may need full installation process
- Follow installation prompts
- May take 30-60 minutes for initial setup
- After installation, save disk image
- Subsequent boots should be fast

### Issue 3: Different Prompts

**Symptom**: Prompts don't match expectations

**Solution**:
- Document actual prompts
- Update expect script patterns
- Use regex: `-re "(BOOT>|@|sim>)"`

---

## Automation Script Template

**File**: `arpanet/scripts/pdp10_autoboot.exp`

```tcl
#!/usr/bin/expect -f
# PDP-10 TOPS-20 V4.1 Automated Boot
# Based on successful PDP-11 telnet console method

set timeout 120
log_user 1

puts "\n=========================================="
puts "PDP-10 TOPS-20 Automated Boot"
puts "Timestamp: [clock format [clock seconds]]"
puts "==========================================\n"

# Connect to SIMH telnet console
puts "→ Connecting to console (localhost:2326)..."
spawn telnet localhost 2326
expect {
    "Escape character" {
        puts "✓ Connected to SIMH console\n"
    }
    timeout {
        puts "✗ ERROR: Failed to connect"
        exit 1
    }
}

# Wait for sim> prompt (SIMH command prompt)
puts "→ Waiting for SIMH prompt..."
expect {
    "sim>" {
        puts "✓ SIMH ready\n"
        puts "→ Sending boot command: boot tua0"
        send "boot tua0\r"
    }
    timeout {
        puts "✗ ERROR: No SIMH prompt"
        exit 1
    }
}

# Wait for TOPS-20 to boot
puts "\n→ Waiting for TOPS-20 to boot (30-60 seconds)..."
expect {
    "TOPS-20" {
        puts "✓ TOPS-20 loaded\n"
    }
    timeout {
        puts "⚠ Didn't see TOPS-20 banner (continuing...)"
    }
}

# Wait for prompt (BOOT> or @)
puts "→ Waiting for prompt..."
expect {
    "BOOT>" {
        puts "✓ BOOT prompt found"
        puts "→ Sending /G143 to boot..."
        send "/G143\r"
        expect "@"
        puts "✓ Login prompt ready\n"
    }
    "@" {
        puts "✓ Login prompt ready (direct boot)\n"
    }
    timeout {
        puts "✗ ERROR: No boot prompt"
        exit 1
    }
}

puts "=========================================="
puts "✅ BOOT COMPLETE"
puts "=========================================="

# Login (if needed)
puts "\n→ Attempting login..."
send "login operator\r"
expect {
    "Password:" {
        send "\r"
        expect "@"
        puts "✓ Logged in\n"
    }
    "@" {
        puts "✓ Already at command prompt\n"
    }
}

# Execute test command
puts "→ Testing commands..."
send "dir\r"
expect "@"

send "systat\r"
expect "@"

puts "\n=========================================="
puts "✅ AUTOMATION COMPLETE"
puts "Timestamp: [clock format [clock seconds]]"
puts "=========================================="

puts "\nConsole session active."
puts "Press Ctrl-C to exit or continue interactive session below.\n"

interact
```

---

## Success Documentation

**If successful**, create:
- `docs/arpanet/PDP10-BOOT-SUCCESS-2026-02-12.md`
- Update `STATUS.md` with success
- Update `TELNET-CONSOLE-METHOD.md` with PDP-10 confirmation
- Commit automation script

**Template**:
```markdown
# PDP-10 SIMH Boot Success

✅ Telnet console method confirmed working on PDP-10!

**Boot Time**: XX seconds
**Success Rate**: X/X tests
**Method**: Same as PDP-11 (telnet console)

This proves the telnet console method is universal for SIMH systems.
```

---

## Cleanup

```bash
# Stop and remove
docker compose -f docker-compose.pdp10-test.yml down

# Remove volumes if needed
docker volume prune

# Or keep for future tests
```

---

## Next Steps After Success

1. ✅ Document findings
2. ✅ Create final automation script
3. ✅ Update STATUS.md
4. ✅ Commit all files
5. → Try on other SIMH systems (VAX, PDP-8, etc.)
6. → Create automation library

---

## Estimated Timeline

- **Setup**: 5 minutes (docker build)
- **Manual test**: 15-20 minutes
- **Automation**: 20-30 minutes
- **Validation**: 10-20 minutes
- **Documentation**: 15-20 minutes
- **Total**: 60-90 minutes

**If installation required**: Add 30-60 minutes for initial TOPS-20 setup

---

## References

- **PDP-11 Success**: docs/arpanet/PDP11-BOOT-SUCCESS-2026-02-12.md
- **Telnet Method**: docs/arpanet/TELNET-CONSOLE-METHOD.md
- **TOPS-20 Docs**: http://pdp-10.trailing-edge.com/
- **SIMH PDP-10**: http://simh.trailing-edge.com/pdf/pdp10_doc.pdf

---

**Status**: ✅ Ready to test
**Success Probability**: 90%+
**Recommendation**: **Try this immediately!**

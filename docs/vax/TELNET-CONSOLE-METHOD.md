# Telnet Console Method - Universal SIMH Boot Automation

**Date**: 2026-02-12
**Status**: Historical reference; partially applicable
**Scope**:
- VAX↔PDP-11 console-session discipline remains relevant
- PDP-10/ARPANET sections in this document are retained history, not active pipeline guidance
**Use for current work**:
- Primary runbook: `../integration/operations/VAX-PDP11-COLD-START-DIAGNOSTICS.md`
- Active integration index: `../integration/INDEX.md`
- Retired/blocked paths: `../archive/DEAD-ENDS.md`

---

## The Problem This Solves

### What Failed: Docker Attach (stdio console)

```bash
# The old approach that didn't work:
docker attach pdp11-host
# Issues:
# - Only shows NEW output after attach
# - Can't see boot prompt that already appeared
# - Timing issues with input
# - Container restart on detach
# Result: Hours of debugging, no reliable solution
```

### What Works: Telnet Console

```bash
# The new approach that works:
telnet localhost 2327
# Benefits:
# - SIMH waits for connection before proceeding
# - All output visible after connection
# - Stable, standard protocol
# - Works with expect, pexpect, any automation
# Result: 100% reliable, solved in 1 hour
```

---

## How It Works

### 1. Configure SIMH for Telnet Console

**In your `.ini` file:**
```ini
; Instead of stdio (default)
set console telnet=2327

; Then boot command
boot rp0
```

**What happens:**
1. SIMH starts and listens on port 2327
2. SIMH WAITS for telnet connection
3. When you connect, boot messages appear
4. You can send commands and see responses
5. Connection is stable throughout boot

### 2. Automate with Expect

```tcl
#!/usr/bin/expect -f
set timeout 120

spawn telnet localhost 2327
expect "Escape character"

# Boot sequence
expect ":"
send "\r"
expect "BSD UNIX"
expect "#"

# Execute commands
send "ifconfig xq0 inet 172.20.0.50 netmask 255.255.0.0 up\r"
expect "#"

interact
```

### 3. Or Use Python (pexpect)

```python
import pexpect

child = pexpect.spawn('telnet localhost 2327')
child.expect('Escape character')
child.expect(':')
child.sendline('')  # Boot
child.expect('BSD UNIX', timeout=30)
child.expect('#')

# Execute commands
child.sendline('ifconfig xq0 inet 172.20.0.50 netmask 255.255.0.0 up')
child.expect('#')

child.interact()
```

---

## Applying to Previous Failed Attempts

### PDP-10 (SIMH-based) - HIGH SUCCESS PROBABILITY

**Systems this applies to:**
- `arpanet/configs/pdp10.ini` - Already has telnet console configured!
- `arpanet/configs/kl10-runtime.ini` - Has telnet console
- Any SIMH PDP-10 configuration

**Current config (pdp10.ini line 35):**
```ini
set console telnet=2323
```

**Boot sequence (expected):**
```
spawn telnet localhost 2323
expect "Escape character"

# Wait for TOPS-20 boot prompt
expect "BOOT>"
send "/G143\r"

# Wait for @ prompt
expect "@"

# Configure network, run commands
send "login operator\r"
expect "Password:"
send "\r"
expect "@"

# ... more commands ...
```

**To test:**
1. Use existing Dockerfile (`Dockerfile.pdp10stub` or similar)
2. Start container with `docker-compose`
3. Run: `telnet localhost 2323`
4. Document exact boot sequence
5. Create expect script
6. Profit! 🎉

### PDP-10 (KLH10/Panda) - UNKNOWN

**System:** `arpanet/Dockerfile.pdp10-panda`

**Issue:** KLH10 uses different syntax than SIMH
- No `set console telnet` command
- Uses TTY/PTY directly
- May need different approach

**Options:**
1. Check KLH10 documentation for telnet console support
2. Use socat to create telnet bridge to TTY
3. Stick with SIMH PDP-10 instead

### VAX (Already Working) - CAN BE IMPROVED

**Current:** Uses jguillaumes/simh-vaxbsd image
**Could:** Configure telnet console for better automation

**Config file** (`arpanet/configs/vax-network.ini`):
```ini
set console telnet=2323
```

Already present! VAX should work with this method too.

---

## Step-by-Step: Convert Any SIMH System

### 1. Update SIMH Config

**Find your `.ini` file** and add:
```ini
set console telnet=PORT
```

**Choose unique ports:**
- PDP-11: 2327
- PDP-10: 2326
- VAX: 2323
- Others: 2328, 2329, etc.

### 2. Update Docker Compose

**Expose the telnet port:**
```yaml
services:
  pdp10:
    ports:
      - "2326:2326"  # Telnet console
```

**Mount the config:**
```yaml
    volumes:
      - ./arpanet/configs/pdp10.ini:/opt/pdp10/pdp10.ini:ro
```

### 3. Create Expect Script

**Template:**
```tcl
#!/usr/bin/expect -f
set timeout 120

# Connect
spawn telnet localhost PORT
expect "Escape character"

# Wait for boot prompt (system-specific)
expect "BOOT_PROMPT"
send "BOOT_COMMAND\r"

# Wait for login (system-specific)
expect "LOGIN_PROMPT"
send "USERNAME\r"
expect "PASSWORD_PROMPT"
send "PASSWORD\r"

# Wait for shell
expect "SHELL_PROMPT"

# Execute commands
send "your commands here\r"
expect "SHELL_PROMPT"

interact
```

### 4. Test Manually First

```bash
# Start container
docker compose up -d system

# Connect manually
telnet localhost PORT

# Document EXACT prompts and responses:
# - What do you see first?
# - What prompts appear?
# - What commands work?
# - How long does boot take?

# Save transcript
script -f boot-transcript.log
telnet localhost PORT
# ... do the boot ...
exit
```

### 5. Codify in Automation

**Update expect script with:**
- Exact prompt patterns
- Correct command sequences
- Appropriate timeouts
- Network configuration
- Verification steps

### 6. Validate

```bash
# Test 3 times in a row
for i in 1 2 3; do
    echo "=== Test $i ==="
    docker compose restart system
    sleep 20
    expect autoboot.exp
    echo "Exit code: $?"
done

# Success: All 3 boots work
# Failure: Debug and adjust
```

---

## Comparison Matrix

| System | Stdio Console | Telnet Console | Status |
|--------|---------------|----------------|--------|
| **PDP-11 2.11BSD** | ❌ Failed | ✅ **Working** | Proven |
| **PDP-10 SIMH** | ❌ Failed (likely) | ⚠️ Untested | Should work |
| **PDP-10 KLH10** | ❌ Failed | ❓ Unknown | Research needed |
| **VAX SIMH** | ✅ Working | ✅ Should work | Already stable |
| **PDP-8** | ❓ Unknown | ⚠️ Untested | Should work |
| **Any SIMH** | Variable | ✅ Likely works | Test it! |

---

## Troubleshooting

### Connection Closes Immediately

**Symptom:** `telnet localhost PORT` connects then closes

**Causes:**
1. SIMH not configured for telnet: Add `set console telnet=PORT`
2. SIMH crashed/restarted: Check `docker logs CONTAINER`
3. Port not exposed: Check docker-compose ports section

**Fix:** Verify config and restart container

### Boot Prompt Not Appearing

**Symptom:** Connection works but no prompt

**Causes:**
1. SIMH hasn't started boot yet
2. Boot already completed before you connected
3. System is waiting for something else

**Fix:**
- Wait longer (30-60 seconds)
- Check docker logs to see current state
- Restart container and connect immediately

### Commands Not Executing

**Symptom:** Type commands, nothing happens

**Causes:**
1. Not at a prompt (still booting)
2. Wrong prompt expectation
3. System crashed

**Fix:**
- Wait for actual prompt
- Check logs for errors
- Verify system is healthy

---

## Best Practices

### 1. Always Test Manually First

```bash
# Don't write automation blind
# Connect manually and document EVERYTHING

script -f manual-session.log
telnet localhost PORT
# ... complete full boot sequence ...
exit

# Now you have the exact sequence to automate
```

### 2. Use Generous Timeouts

```tcl
# Boots can be slow, especially first time
set timeout 120  # 2 minutes

# For specific operations
expect {
    "prompt" { ... }
    timeout {
        puts "Still waiting, check logs"
        exit 1
    }
}
```

### 3. Add Logging

```tcl
#!/usr/bin/expect -f
log_file boot-automation.log
log_user 1  # Show output to terminal too
```

### 4. Handle Edge Cases

```tcl
expect {
    "login:" {
        send "root\r"
    }
    "Login:" {
        send "root\r"
    }
    -re "(login|Login):" {
        send "root\r"
    }
    timeout {
        puts "No login prompt"
        exit 1
    }
}
```

### 5. Verify Success

```tcl
# Don't just assume it worked
send "echo SUCCESS\r"
expect "SUCCESS"
expect "#"

# Or check network
send "ping -c 1 172.20.0.1\r"
expect {
    "1 packets transmitted" {
        puts "Network working"
    }
    timeout {
        puts "Network not ready"
    }
}
```

---

## Next Steps

### Immediate (High Priority)

1. **Test SIMH PDP-10** with telnet console
   - Use existing `configs/pdp10.ini` (already has telnet)
   - Create expect script based on PDP-11 template
   - Document boot sequence
   - Should take 30-60 minutes

2. **Create automation library**
   - `arpanet/scripts/autoboot_pdp11.exp` ✅ Done
   - `arpanet/scripts/autoboot_pdp10.exp` ← Create this
   - `arpanet/scripts/autoboot_vax.exp` ← Create this

3. **Update docker configs**
   - Ensure all use telnet console
   - Document ports in docker-compose

### Future Work

1. **Research KLH10 telnet support**
   - Check KLH10 documentation
   - Ask in vintage computing forums
   - Consider socat bridge if needed

2. **Test other SIMH systems**
   - PDP-8
   - PDP-15
   - Nova
   - Etc.

3. **GitHub Actions integration**
   - Use telnet method in CI/CD
   - Automated testing
   - Build pipeline validation

---

## Success Metrics

### PDP-11 (Proven)
- ✅ 100% boot success rate (5/5 tests)
- ✅ 15-20 second boot time
- ✅ Commands execute reliably
- ✅ Automation scripts created
- ✅ Can run unattended

### PDP-10 (Expected)
- Should achieve similar success rate
- Boot time: ~30-60 seconds (estimated)
- TOPS-20 @ prompt automation
- Network configuration possible
- FTP server setup viable

### General (All SIMH Systems)
- Telnet console: Reliable, standard approach
- Expect automation: Well-understood, proven
- Python pexpect: Alternative for those who prefer Python
- CI/CD ready: Can run in GitHub Actions

---

## Conclusion

The **telnet console method** transforms SIMH boot automation from "impossible" to "straightforward". What took hours of debugging with stdio/docker-attach now works reliably in minutes with telnet.

**Key insight:** SIMH's design of "wait for telnet connection" before proceeding is perfect for automation - it ensures we never miss the boot prompt.

**Applicability:**
- ✅ Works on PDP-11 (proven)
- ⚠️ Should work on SIMH PDP-10 (config already present)
- ⚠️ Should work on VAX (config already present)
- ⚠️ Should work on any SIMH system (untested but likely)

**Recommendation:** Apply this method to ALL SIMH-based systems immediately.

---

## References

- **PDP-11 Success**: docs/arpanet/PDP11-BOOT-SUCCESS-2026-02-12.md
- **Expect Documentation**: https://core.tcl-lang.org/expect/
- **SIMH Documentation**: http://simh.trailing-edge.com/
- **Pexpect (Python)**: https://pexpect.readthedocs.io/

---

**Method Status**: ✅ **PROVEN AND RECOMMENDED**
**Next Application**: **PDP-10 SIMH (30-60 min effort)**

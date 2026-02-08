# SIMH Automation Scripts

This directory contains SIMH automation scripts that use native SIMH commands (`SEND`, `EXPECT`, `GO UNTIL`) for reliable console automation.

## Background

These scripts solve the console automation problem documented in [CONSOLE-AUTOMATION-PROBLEM.md](../../CONSOLE-AUTOMATION-PROBLEM.md). Instead of using external tools like `expect + telnet` (which are unreliable due to timing issues), these scripts use SIMH's built-in automation commands that inject input directly into the console device.

**Success Rate**: 99% (vs 10% with expect+telnet)

See [CONSOLE-AUTOMATION-SOLUTION.md](../../CONSOLE-AUTOMATION-SOLUTION.md) for complete technical details.

## Available Scripts

### test-login.ini
Tests basic console login automation.

**Usage**:
```bash
docker exec arpanet-vax /usr/bin/simh-vax /machines/data/test-login.ini
```

**What it does**:
- Boots BSD 4.3
- Logs in as root
- Executes test commands
- Verifies console automation works

**Time**: ~30 seconds

---

### authentic-ftp-transfer.ini
Automates file transfer using BSD 4.3's native FTP client (1986).

**Usage**:
```bash
# 1. Copy source file to VAX volume
cp myfile.txt ./build/vax/source.txt

# 2. Run automated transfer
docker exec arpanet-vax /usr/bin/simh-vax /machines/data/authentic-ftp-transfer.ini

# 3. Check destination
docker exec arpanet-vax cat /tmp/uploaded.txt
```

**What it does**:
- Logs into VAX console
- Creates test file
- Starts FTP session to localhost
- Authenticates as operator user
- Transfers file in binary mode
- Verifies file integrity with diff

**Time**: ~45 seconds

**Historical Authenticity**: 100%
- Real 1986 FTP client (`/usr/bin/ftp`)
- Real 1986 FTP server (Version 4.105)
- RFC 959 protocol (October 1985)

---

### configure-network.ini
Configures VAX network interface automatically.

**Usage**:
```bash
docker exec arpanet-vax /usr/bin/simh-vax /machines/data/configure-network.ini
```

**What it does**:
- Configures de0 interface (172.20.0.10/16)
- Verifies configuration with ifconfig
- Tests connectivity with ping
- Shows routing table

**Time**: ~35 seconds

---

## How to Use These Scripts

### Method 1: Mount as Volume (Recommended)

In `docker-compose.arpanet.phase1.yml`:

```yaml
vax:
  volumes:
    - ./build/vax:/machines/data
    - ./arpanet/scripts/simh-automation:/machines/automation
  command: ["/usr/bin/simh-vax", "/machines/automation/test-login.ini"]
```

Then run:
```bash
docker-compose -f docker-compose.arpanet.phase1.yml up
```

### Method 2: Copy to Running Container

```bash
# Start VAX
docker-compose -f docker-compose.arpanet.phase1.yml up -d vax

# Copy script
docker cp arpanet/scripts/simh-automation/test-login.ini arpanet-vax:/tmp/test.ini

# Run script
docker exec arpanet-vax /usr/bin/simh-vax /tmp/test.ini
```

### Method 3: Direct Execution

```bash
# If script is in mounted volume:
docker exec arpanet-vax /usr/bin/simh-vax /machines/data/test-login.ini
```

---

## Creating Custom Scripts

### Basic Template

```ini
; Your script description
set cpu 64m
set cpu idle
attach dz 2323
attach xu eth0
set xu mac=08:00:2b:aa:bb:cc

; Boot BSD
boot cpu

; Login
go until "login:"
send delay=1000 "root\r"
go until "#"

; Your commands here
send "your_command\r"
go until "#"

; Exit
send "exit\r"
exit
```

### Key Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `go until "pattern"` | Run until text appears | `go until "login:"` |
| `send "text"` | Inject text into console | `send "root\r"` |
| `send delay=N "text"` | Send with typing delay | `send delay=1000 "root\r"` |
| `expect "pattern"` | Wait for pattern | `expect "#"` |
| `exit` | Exit SIMH | `exit` |

### Best Practices

1. **Use `go until` instead of `expect`**
   - More reliable for long operations
   - Processes output continuously

2. **Add delays for login prompts**
   ```ini
   send delay=1000 "root\r"  ; 1 second delay simulates human typing
   ```

3. **Wait for specific codes, not generic prompts**
   ```ini
   go until "230"  ; FTP login success
   go until "226"  ; FTP transfer complete
   ```

4. **Test incrementally**
   - Start with simple login
   - Add one command at a time
   - Verify each step

5. **Always use `\r` for newlines**
   ```ini
   send "command\r"  ; Correct
   send "command\n"  ; Wrong - use \r
   ```

---

## Integration with Build Pipeline

### GitHub Actions Example

```yaml
name: Build with ARPANET FTP

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Start ARPANET
        run: docker-compose -f docker-compose.arpanet.phase1.yml up -d

      - name: Wait for boot
        run: sleep 30

      - name: Transfer via authentic FTP
        run: |
          cp build/resume.pdf ./build/vax/resume.pdf
          docker exec arpanet-vax /usr/bin/simh-vax \
            /machines/data/authentic-ftp-transfer.ini

      - name: Verify transfer
        run: |
          docker exec arpanet-vax ls -l /tmp/uploaded.txt

      - name: Cleanup
        run: docker-compose -f docker-compose.arpanet.phase1.yml down
```

---

## Troubleshooting

### Script hangs at login prompt
**Symptom**: Script waits forever at "login:"

**Solution**: Increase delay in send command
```ini
send delay=2000 "root\r"  ; Try 2 seconds instead of 1
```

### Commands don't execute
**Symptom**: Commands appear but don't run

**Fix**: Make sure you're waiting for prompt before sending next command
```ini
send "command1\r"
go until "#"           ; Wait for prompt!
send "command2\r"
```

### FTP transfer fails
**Symptom**: FTP connection refused

**Fix**: Make sure FTP server is running
```bash
# Check inetd is running
docker exec arpanet-vax ps aux | grep inetd

# Check FTP service configured
docker exec arpanet-vax grep ftp /etc/inetd.conf
```

### File not found errors
**Symptom**: Can't find source file

**Fix**: Verify file is in mounted volume
```bash
# List files in VAX volume
docker exec arpanet-vax ls -l /machines/data/

# Copy file if missing
docker cp myfile.txt arpanet-vax:/machines/data/
```

---

## Performance Notes

| Script | Boot Time | Execution Time | Total |
|--------|-----------|----------------|-------|
| test-login.ini | ~25s | ~5s | ~30s |
| authentic-ftp-transfer.ini | ~25s | ~20s | ~45s |
| configure-network.ini | ~25s | ~10s | ~35s |

**Note**: Boot time is consistent across all scripts (~25 seconds for BSD 4.3 to reach login prompt).

---

## Further Reading

- [CONSOLE-AUTOMATION-SOLUTION.md](../../CONSOLE-AUTOMATION-SOLUTION.md) - Complete technical solution
- [CONSOLE-AUTOMATION-PROBLEM.md](../../CONSOLE-AUTOMATION-PROBLEM.md) - Original problem statement
- [AUTHENTIC-FTP-STATUS.md](../../AUTHENTIC-FTP-STATUS.md) - FTP testing results
- [SIMH User's Guide](http://simh.trailing-edge.com/pdf/simh_doc.pdf) - Official SIMH documentation

---

**Status**: Production ready
**Reliability**: 99% success rate
**Historical Fidelity**: 100% (authentic 1986 BSD FTP client/server)

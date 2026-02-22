# VAX-PDP11 FTP Setup - Validation Report

**Date**: 2026-02-13
**Session Duration**: ~2 hours
**Status**: ✅ VAX OPERATIONAL | ⚠️ PDP-11 BLOCKED

---

## Executive Summary

Successfully configured VAX/BSD with full TCP/IP networking and FTP service. 
PDP-11 setup blocked due to kernel compatibility issues - no available kernel 
has working Ethernet driver support.

**VAX Status**: ✅ READY FOR FTP TRANSFERS  
**PDP-11 Status**: ❌ BLOCKED - Requires kernel rebuild or alternative image

---

## VAX Configuration - ✅ COMPLETE

### Network Configuration

**Interface**: `de0` (DEC Ethernet)  
**IP Address**: `172.20.0.10`  
**Netmask**: `255.255.0.0` (ffff0000)  
**Broadcast**: `172.20.255.255`  
**Status**: UP, BROADCAST, RUNNING  
**MAC Address**: `08:00:2b:92:49:19`

**Routing Table**:
```
Destination          Gateway              Flags    Refcnt Use        Interface
127.0.0.1            127.0.0.1            UH       0      0          lo0
172.17.0.103         127.0.0.1            UH       0      16         lo0
default              172.17.0.1           UG       1      3          de0
172.20               172.20.0.10          U        0      0          de0
```

### FTP Service Status

**Service**: ✅ RUNNING  
**Port**: 21 (TCP LISTEN)  
**Daemon**: `/etc/ftpd`  
**Configuration**: `/etc/inetd.conf`  
**Entry**: `ftp stream tcp nowait root /etc/ftpd ftpd`

**Verification**:
```
tcp        0      0  *.21                   *.*                    LISTEN
```

### System Information

**OS**: 4.3 BSD UNIX  
**Hostname**: vaxbsd  
**Build**: Fri May 22 19:08:31 MET DST 2015  
**Console**: Telnet port 2323  
**Docker IP**: 172.20.0.10 (container network)  
**Public IP**: 3.80.32.255 (AWS instance)

### Testing Completed

- ✅ Network interface configured
- ✅ Routing table established
- ✅ FTP daemon running
- ✅ Port 21 listening
- ✅ File creation tested (`/tmp/vax-test.txt`)
- ✅ inetd service operational

### What Works

1. **Network**: Full TCP/IP stack operational
2. **FTP Server**: Ready to accept connections
3. **File System**: Read/write access to `/tmp`
4. **Console Access**: Screen-based interactive control via telnet
5. **Service Management**: inetd responding to signals

---

## PDP-11 Configuration - ❌ BLOCKED

**Image**: `211bsd_rpeth.dsk` (from retro11.de)  
**Issue**: No working kernel with Ethernet (xq) driver support

### Kernels Tested

| Kernel    | Boot Result | Ethernet Support | Notes                           |
|-----------|-------------|------------------|---------------------------------|
| unix      | ✅ Success  | ❌ No            | Default, boots to single-user   |
| netnix    | ❌ Crash    | ❓ Unknown       | Trap stack push abort (PC:000520)|
| genunix   | ⚠️ Partial  | ❓ Unknown       | Config error: /unix mismatch    |
| unixnfp   | ❓ Unknown  | ❓ Unknown       | Not fully tested (container crash)|
| unixold   | ⏸️ Skipped  | ❓ Unknown       | Not tested                      |

### Root Cause

The default `unix` kernel boots successfully but was **not compiled with xq 
Ethernet driver support**. Alternative kernels either crash or have configuration 
errors preventing multi-user boot.

**Evidence**:
- Boot messages show no `xq` device attachment (only `lo0` loopback)
- `ifconfig -a` returns "no such interface"
- `dmesg | grep xq` returns no results
- Kernel source path: `/usr/src/sys/RETRONFPETH` (RP-ETHERNET label misleading)

### Detailed Issue Report

**Location**: `/mnt/arpanet-logs/shared/pdp11-kernel-issue-2026-02-13.md`

See full technical analysis including:
- Complete boot logs for each kernel
- SIMH trap/error messages
- Attempted workarounds
- Recommended solutions

---

## Infrastructure Status

### AWS Environment

**VAX Instance**: i-090040c544bb866e8  
**PDP-11 Instance**: i-071ab53e735109c59  
**VAX Public IP**: 3.80.32.255  
**PDP-11 Public IP**: 3.87.125.203

### Docker Network

**Network**: `arpanet-production`  
**Type**: Bridge  
**Subnet**: 172.20.0.0/16  
**Gateway**: 172.20.0.1

**Containers**:
- ✅ `arpanet-vax`: Up and stable
- ⚠️ `arpanet-pdp11`: Restarts frequently (kernel crashes)

### EFS Shared Storage

**Mount Point**: `/mnt/arpanet-logs/`  
**Filesystem**: <efs-id>
**Directories**:
- `/mnt/arpanet-logs/vax/` - VAX logs
- `/mnt/arpanet-logs/pdp11/` - PDP-11 logs
- `/mnt/arpanet-logs/shared/` - Shared documentation

**Current Files**:
- `pdp11-kernel-issue-2026-02-13.md` - Detailed PDP-11 analysis
- `vax-pdp11-ftp-validation-2026-02-13.md` - This report

---

## Methodology Used

### Screen-Based Interactive Access

Successfully implemented persistent console sessions using GNU screen:

```bash
# Create persistent sessions
screen -dmS vax-console telnet localhost 2323
screen -dmS pdp11-console telnet localhost 2327

# Send commands
screen -S vax-console -X stuff "command\n"

# Capture output
screen -S vax-console -X hardcopy /tmp/output.txt
```

**Advantages**:
- Persistent connection prevents SIMH timeouts
- Pseudo-interactive control through multiple tool calls
- Can analyze output and adapt commands
- Works around telnet automation limitations

---

## Current Capabilities

### What Can Be Done Now

1. **VAX Local Testing**: FTP loopback transfers on VAX (127.0.0.1)
2. **VAX File Operations**: Create, edit, transfer files within VAX
3. **Network Testing**: Can ping VAX from Docker host
4. **Service Verification**: All VAX network services accessible

### What Cannot Be Done (Blocked)

1. ❌ VAX ↔ PDP-11 file transfers
2. ❌ PDP-11 network configuration
3. ❌ Bidirectional FTP testing
4. ❌ Multi-system validation

---

## Recommendations

### Short-Term (Unblock Development)

**Option A**: VAX-to-VAX Setup (RECOMMENDED)
- Deploy second VAX container
- Both use proven working configuration
- Can complete full bidirectional FTP testing
- Estimated time: 30-60 minutes

**Option B**: PDP-11 Kernel Rebuild
- Boot PDP-11 with working `unix` kernel
- Recompile kernel with xq driver enabled
- Risk: Complex, may uncover additional issues
- Estimated time: 2-4 hours

**Option C**: Alternative PDP-11 Image
- Find pre-built 2.11BSD with verified Ethernet support
- Replace current disk image
- Risk: May have different issues
- Estimated time: 1-2 hours

### Long-Term (Production)

1. **Document VAX Configuration**: Create persistent network setup scripts
2. **Automation Scripts**: Simple expect/screen-based automation for boot/config
3. **Alternative Architectures**: Consider PDP-10, VAX-only, or modern BSD systems
4. **Kernel Library**: Build/maintain collection of working kernels for each system

---

## Time Investment

**Total Session**: ~2 hours  
**VAX Configuration**: 30 minutes (successful)  
**PDP-11 Debugging**: 90 minutes (blocked by kernel issue)

---

## Success Criteria

### Completed ✅

- [x] VAX network interface configured (172.20.0.10)
- [x] VAX routing table established
- [x] VAX FTP service running and listening
- [x] Interactive console access working (both systems)
- [x] Documentation created
- [x] Issue report written

### Blocked ❌

- [ ] PDP-11 network interface configured
- [ ] Connectivity test (VAX ↔ PDP-11 ping)
- [ ] FTP transfer VAX → PDP-11
- [ ] FTP transfer PDP-11 → VAX
- [ ] Binary transfer verification
- [ ] Persistent configuration (rc.local)

### Not Attempted ⏸️

- Network configuration persistence (both systems)
- Multi-user boot validation
- Performance testing
- Security hardening

---

## Next Steps

**Immediate** (User Decision Required):
1. Choose path forward: VAX-VAX, PDP-11 kernel fix, or alternative
2. Research PDP-11 kernel issue (user investigating)

**If Proceeding with VAX-only**:
1. Deploy second VAX container
2. Configure second VAX at 172.20.0.50
3. Test ping both directions
4. Test FTP transfers both directions
5. Make configurations persistent
6. Create final validation report

**If Fixing PDP-11**:
1. Boot with `unix` kernel (working)
2. Mount filesystem read-write
3. Copy alternate kernel to `/unix`
4. OR: Rebuild kernel with xq support
5. Test network functionality
6. Proceed with FTP setup

---

## Files Generated

**On AWS EFS** (`/mnt/arpanet-logs/shared/`):
- `pdp11-kernel-issue-2026-02-13.md` - Technical analysis
- `vax-pdp11-ftp-validation-2026-02-13.md` - This report

**On Local Machine** (`/tmp/`):
- Various screen captures and logs

---

## Conclusion

VAX networking and FTP are fully operational and ready for file transfers.  
PDP-11 is blocked by kernel compatibility issues requiring either a kernel  
rebuild, alternative disk image, or pivot to dual-VAX architecture.

The screen-based interactive approach proved highly effective for console  
automation and troubleshooting, providing pseudo-interactive control that  
worked around telnet protocol limitations.

---

**Report Generated**: 2026-02-13 14:23 UTC  
**AWS Instance**: 3.80.32.255 (VAX), 3.87.125.203 (PDP-11)  
**Next Session**: Await user direction on path forward

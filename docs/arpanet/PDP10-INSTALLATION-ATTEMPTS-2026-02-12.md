# PDP-10 Installation Attempts - 2026-02-12
**Duration**: ~3 hours
**Status**: Multiple approaches attempted, all blocked by compatibility issues
**Result**: Automation method proven, manual installation recommended

## Summary

Attempted to automate TOPS-20 installation on PDP-10/KL10 emulator. Successfully solved SIMH configuration errors and developed working automation method (screen + command injection), but hit insurmountable compatibility bugs in multiple approaches.

## What Worked ✅

1. **SIMH Configuration Syntax** - Fixed unit number requirements
   - Changed `set tu enable` → `set tu0 locked`
   - Changed `set rp rp06` → `set rp0 rp06`
   - Fixed tape filename path

2. **Automation Method** - Screen session + command stuffing
   - `screen -dmS pdp10` - Create detached session
   - `screen -S pdp10 -X stuff 'command\n'` - Send commands
   - Successfully delivered `/L` and `/G143` to MTBOOT> prompt

3. **Container Build** - All Dockerfiles build successfully
   - Standard SIMH with V4.1
   - Cornwell SIMH fork with V7.0
   - KLH10 image pulled

## What Failed ❌

### Attempt 1: TOPS-20 V4.1 on Standard SIMH
**Problem**: Boot loop after `/G143`
- System runs at 100% CPU indefinitely
- No console output after boot commands
- 0B disk I/O (no actual installation)
- **Root cause**: Known WRCSTM instruction bug in V4.1
- **Workaround exists**: `set cpu tops20v41` parameter
- **Issue**: Current SIMH version doesn't support that parameter

**Evidence**:
```
MTBOOT>/L
         /G143
[... 100% CPU, no further output ...]
```

### Attempt 2: TOPS-20 V7.0 on Cornwell SIMH Fork
**Problem**: Parameter incompatibilities
- Cornwell fork supports KL10 (standard SIMH is KS-10 only)
- Downloaded V7.0 tape successfully
- Config parameters from documentation don't work:
  - `set cty rsx20` → "Non-existent parameter"
  - `set tua rh20` → "Non-existent parameter"
  - `set rpa rh20` → "Non-existent parameter"
- Boot process doesn't reach MTBOOT> prompt
- Shows 22.6MB disk I/O (promising vs V4.1's 0B)

**Evidence**:
```
%SIM-ERROR: CTY device: Non-existent parameter - RSX20
%SIM-ERROR: TUA device: Non-existent parameter - RH20
%SIM-ERROR: RPA device: Non-existent parameter - RH20
%SIM-INFO: TUA0: Tape Image scanned as E11 format
Booting from tape...
[... no MTBOOT> prompt appears ...]
```

### Attempt 3: KLH10 Pre-built Docker Image
**Problem**: Execution errors
- Found community Docker image: `jguillaumes/klh10-kl`
- Image pulls successfully (amd64 architecture)
- Cannot execute binaries inside container
- Error 126: "cannot execute binary file"

## Technical Discoveries

### SIMH Version Differences
- **Standard SIMH**: KS-10 only, limited to TOPS-20 V4.x
- **Cornwell SIMH**: Full KL10 support, can run V2-V7
- **Parameter naming**: Varies between versions (no standardization)
- **CPU options**: `TOPS-20`, `TOPS10`, `ITS` (case-sensitive, uppercase)

### TOPS-20 Installation Process
1. Boot from tape (`boot tu` or `boot tua`)
2. MTBOOT> prompt appears
3. Type `/L` to load monitor from tape
4. Type `/G143` to start at address 143 (begins formatting)
5. Interactive prompts for filesystem configuration
6. Tape restoration process
7. System configuration
8. Reboot to @ prompt

### Automation Challenges
- Docker detached mode blocks all stdin methods
- `docker attach` with piped input → doesn't work
- `telnet` console mode → connection drops
- `expect` scripts → pattern matching fails
- **Solution**: `screen` session with command stuffing works!

## Files Created/Modified

### New Dockerfiles
- `arpanet/Dockerfile.pdp10-kl10-cornwell` - Cornwell SIMH fork with KL10

### Configuration Files
- `arpanet/configs/kl10-install.ini` - Fixed unit syntax for V4.1
- `arpanet/configs/kl10-install-auto.ini` - Auto-boot version
- `arpanet/configs/kl10-install-interactive.ini` - Telnet console version
- `arpanet/configs/kl10-runtime.ini` - Post-installation runtime
- `arpanet/configs/kl10-v7-install.ini` - V7.0 installation (parameter issues)
- `arpanet/configs/kl10-v7-runtime.ini` - V7.0 runtime
- `arpanet/configs/kl10-v7-simple.ini` - Simplified V7.0 config

### Documentation
- `docs/arpanet/KL10-BOOT-PROGRESS-2026-02-12.md` - Initial boot fix progress
- `docs/arpanet/PDP10-INSTALLATION-ATTEMPTS-2026-02-12.md` - This file

## Lessons Learned

1. **Vintage software compatibility is fragile**
   - Multiple emulators with different quirks
   - Documentation often outdated
   - Parameters change between versions

2. **Automation is possible but time-consuming**
   - Screen method works reliably
   - Each approach requires custom workarounds
   - ROI questionable vs manual installation (15-30 min)

3. **Manual installation is pragmatic**
   - User can complete interactively in 15-30 minutes
   - Avoids all automation complexity
   - Creates reusable disk image for future

## Recommendations

### For Immediate Progress
**Manual installation** on local machine or AWS:
1. Start container interactively
2. Type `/L` and `/G143` at prompts
3. Answer installation questions
4. Save resulting disk image
5. Use disk image in future containers

### For Future Automation
**Use pre-built disk images**:
1. Find community-shared TOPS-20 disk images
2. Skip installation entirely
3. Boot directly to @ prompt
4. Panda distribution may have these

### Alternative Approaches
**Use TOPS-10 instead**:
- Simpler than TOPS-20
- Better SIMH compatibility
- Has FTP support
- Easier installation process

## References

- [Gunkies TOPS-20 V4.1 Guide](https://gunkies.org/wiki/Running_TOPS-20_V4.1_under_SIMH)
- [Installing TOPS-20 Panda Distribution](https://typebehind.wordpress.com/2020/02/21/installing-the-tops-20-panda-distribution-on-simhs-kl10-simulator/)
- [Richard Cornwell's SIMH Fork](https://github.com/rcornwell/sims)
- [PDP-10/klh10 on GitHub](https://github.com/PDP-10/klh10)
- [TOPS-20 Tapes at trailing-edge.com](http://pdp-10.trailing-edge.com/)

## Time Breakdown

- Initial config debugging: 30 min
- Automation attempts: 60 min
- TOPS-20 V7.0 setup: 45 min
- KLH10 investigation: 15 min
- Documentation: 30 min
- **Total**: ~3 hours

## AWS Costs

- Instance: t3.medium (~$0.04/hr)
- Runtime: ~3 hours
- **Total cost**: ~$0.12

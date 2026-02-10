# TOPS-20 Installation Quick Start

**Ready to install TOPS-20?** This is your 5-minute guide to get started.

---

## TL;DR - Just Get Me Started!

```bash
# 1. SSH to AWS
ssh ubuntu@34.227.223.186

# 2. Run helper script
cd ~/brfid.github.io
bash arpanet/scripts/tops20-install-helper.sh

# 3. Choose option 1 (pre-flight check)
# 4. Choose option 6 (connect to console)
# 5. Follow the prompts in the installation guide
```

---

## What You're About to Do

You're installing **TOPS-20 V4.1** (a 1980s operating system from DEC) on a **PDP-10 KS10** emulator. This is the final blocker preventing Phase 3 completion.

**Time required**: 1-2 hours (mostly waiting for file restoration)

**What to expect**:
1. Boot from installation tape
2. Answer configuration questions
3. Wait for files to copy (~30-60 minutes)
4. Create user accounts
5. Verify system boots from disk

---

## Before You Start

### ✅ What's Already Done

- ✅ AWS EC2 instance running (34.227.223.186)
- ✅ PDP-10 container built and running
- ✅ TOPS-20 V4.1 tape loaded (21MB)
- ✅ Disk file ready
- ✅ Network configured

### 📋 What You Need

- **Time**: 1-2 hours uninterrupted
- **Access**: SSH to AWS instance
- **Patience**: File restoration is slow
- **Documentation**: Have the guide open

**Recommended**: Use `screen` or `tmux` so you can disconnect SSH without interrupting installation.

---

## Installation Steps (Ultra-Quick)

### 1. Connect to AWS

```bash
ssh ubuntu@34.227.223.186
cd ~/brfid.github.io
```

### 2. Pre-Flight Check

```bash
bash arpanet/scripts/tops20-install-helper.sh check
```

Should see all ✅ green checkmarks.

### 3. Start Logging (Optional but Recommended)

```bash
screen -S tops20
script tops20-install-$(date +%Y%m%d-%H%M%S).log
```

### 4. Connect to Console

```bash
telnet localhost 2326
```

### 5. Follow Installation Prompts

**Boot from tape:**
- System should auto-boot, or type: `boot tua0`
- At `MTBOOT>` prompt: `/L` then `/G143`

**Answer questions:**
- Replace file system? `Y`
- Define public structure? `Y`
- Structure name: `PS`
- Number of packs: `1`
- All defaults? `Y` to everything else
- Date/time: `8-FEB-26 12:00:00` (current date)
- Reason: `INSTALLATION`

**Load monitor:**
- When you see "RUNNING DDMP", press `Ctrl-C`
- At `MX>` prompt: `GET FILE MTA0:` (type twice if needed)
- Then: `START`

**Restore files:**
- At `@` prompt: `@ENABLE`
- Then: `@RUN DUMPER`
- Commands:
  ```
  TAPE MTA0:
  REWIND
  SKIP 2
  RESTORE <*>*.*.*
  ```
- **Wait 30-60 minutes** for restoration
- When done: `EXIT`

**Create accounts:**
```
@ENABLE
@RUN DLUSER
*ADD OPERATOR 1,2
 Password: <pick_a_password>
*EXIT
```

**Write bootstrap:**
```
@RUN SMFILE
*WRITE /BOOTSTRAP
*EXIT
```

**Shutdown:**
```
@SHUTDOWN
Reason: Installation complete
Minutes: 0
@CEASE NOW
```

### 6. Update Config to Boot from Disk

```bash
# Exit telnet (Ctrl-] then 'quit')
# TODO: Need to update pdp10.ini to boot from rpa0 instead of tua0
# This will be automated in topology generator
```

### 7. Test Boot

```bash
docker compose -f docker-compose.arpanet.phase2.yml restart pdp10
sleep 30
telnet localhost 2326

# Should see TOPS-20 boot and login prompt
@LOGIN OPERATOR
Password: <your_password>
@SYSTAT
```

---

## Troubleshooting

### "Connection refused" on telnet

```bash
# Check container is running
docker ps | grep pdp10

# Check logs
docker logs arpanet-pdp10 | tail -20

# Restart if needed
docker compose -f docker-compose.arpanet.phase2.yml restart pdp10
```

### DUMPER restoration takes forever

**This is normal!** TOPS-20 restoration can take 30-60 minutes or more. Go get coffee.

### Lost connection during installation

If using `screen` or `tmux`, reconnect:

```bash
ssh ubuntu@34.227.223.186
screen -r tops20    # Reconnect to screen session
```

### Something went wrong, need to start over

```bash
# Remove disk file and restart
docker exec arpanet-pdp10 rm /machines/data/tops20.dsk
docker compose -f docker-compose.arpanet.phase2.yml restart pdp10
# Then try again
```

---

## What Happens After Installation

Once TOPS-20 is installed and running:

1. **✅ Unblocks Phase 3** - Can proceed with remaining tasks
2. **Next**: Test 4-container routing (VAX → IMP1 → IMP2 → PDP-10)
3. **Then**: Implement FTP file transfer
4. **Finally**: Integrate into build pipeline

**Timeline**: 1-2 weeks to Phase 3 completion after TOPS-20 is ready.

---

## Getting Help

### During Installation

- **Full guide**: `less arpanet/TOPS20-INSTALLATION-GUIDE.md`
- **Helper script**: `bash arpanet/scripts/tops20-install-helper.sh`
- **Container logs**: `docker logs arpanet-pdp10`

### Resources

- [TOPS-20 Installation Guide (Detailed)](./TOPS20-INSTALLATION-GUIDE.md)
- [Computer History Wiki - Running TOPS-20](https://gunkies.org/wiki/Running_TOPS-20_V4.1_under_SIMH)
- [TOPS-20 Commands Reference](http://www.bourguet.org/v2/pdp10/cmds/front)
- [PDP-10 Simulator Docs](https://simh.trailing-edge.com/pdf/pdp10_doc.pdf)

---

## Ready?

```bash
ssh ubuntu@34.227.223.186
cd ~/brfid.github.io
bash arpanet/scripts/tops20-install-helper.sh
```

**Good luck!** 🚀

Remember: Document everything. Take screenshots. This is a one-time process and your notes will be valuable for troubleshooting and future reference.

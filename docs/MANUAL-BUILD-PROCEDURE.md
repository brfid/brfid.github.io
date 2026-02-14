# Manual Build Procedure

How to manually trigger a build on AWS instances to generate logs with enhanced vintage tool evidence.

## Prerequisites

- AWS instances running: `./aws-start.sh`
- SSH key: `~/.ssh/arpanet-temp.pem`
- Get IPs: `./aws-status.sh`

## Method 1: GitHub Actions (Recommended)

```bash
# Trigger automated build via workflow
git tag publish-vax-test-$(date +%Y%m%d)
git push origin publish-vax-test-$(date +%Y%m%d)
```

**Workflow handles:**
1. Start AWS instances
2. Upload files via console to BSD
3. Execute build inside BSD (vintage tools)
4. Extract logs from console captures
5. Merge logs chronologically
6. Deploy to GitHub Pages

**Monitor**: GitHub Actions tab
**Logs**: `/mnt/arpanet-logs/builds/<build-id>/` on AWS

---

## Method 2: Manual Console Execution

### Current Logs Available

**From build-20260214-121649** (in `site/build-logs/`):
- VAX.log - Real K&R C compilation
- COURIER.log - Console transfer
- GITHUB.log - Orchestration
- merged.log - Complete timeline

**Note**: Pre-enhanced logging. Missing compiler dates/binary timestamps.

### Console Automation Status

**What Works:**
- ✅ Console access via screen + telnet
- ✅ File upload via heredoc
- ✅ BSD command execution
- ✅ Vintage cc compiler accessible

**Needs Work:**
- ⚠️ Timing synchronization
- ⚠️ Log capture completeness
- ⚠️ Build execution verification

### Manual Procedure (Reference)

**From `docs/integration/VAX-PDP11-VALIDATION-2026-02-14.md`:**

```bash
# On AWS VAX host
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<vax-ip>

# Interactive console session
screen -S vax-console telnet localhost 2323
# Login as root
# Upload files via heredoc manually
# Execute: /tmp/vax-build-and-encode.sh <build-id>
# Logs write to /mnt/arpanet-logs/builds/<build-id>/
```

---

## Expected Enhanced Log Output

**Target format from updated scripts:**

```log
[2026-02-14 HH:MM:SS VAX] System Information:
[2026-02-14 HH:MM:SS VAX]   OS: 4.3 BSD UNIX #1: Fri Jun  6 19:55:29 PDT 1986
[2026-02-14 HH:MM:SS VAX]   Compiler: cc: Berkeley C compiler, version 4.3 BSD, 7 June 1986
[2026-02-14 HH:MM:SS VAX]   Compiler binary: /bin/cc (45056 bytes, dated Jun  7  1986)
[2026-02-14 HH:MM:SS VAX]   Tool: uuencode (6366 bytes, dated Jun  7  1986)
...
[2026-02-14 HH:MM:SS PDP11]   OS: 2.11 BSD UNIX #1: Sun Nov  7 22:40:28 PST 1999
[2026-02-14 HH:MM:SS PDP11]   Tool: uudecode (16716 bytes, dated Nov  7  1999)
[2026-02-14 HH:MM:SS PDP11]   Tool: nroff -man (44940 bytes, dated Nov  7  1999)
```

**Proves**: Authentic 1986/1999 vintage binaries used.

---

## Troubleshooting

**No logs generated:**
- Check EFS: `df -h /mnt/arpanet-logs` on AWS
- Check fallback: `/tmp/arpanet-logs-<build-id>/` inside BSD
- Console capture: `/tmp/vax-build-console.txt` on AWS host

**docker exec shows wrong files:**
- Container `/tmp` ≠ BSD `/tmp` (different layers)
- Must check via console session, not docker exec

---

## Task #7: Enhanced Logging Build

**Status**: In progress - console automation needs refinement

**For now**: Use existing logs for webpage design
**Next**: GitHub Actions workflow or refined console automation

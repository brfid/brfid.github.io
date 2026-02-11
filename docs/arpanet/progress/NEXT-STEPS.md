# ARPANET Next Steps

**Active path**: Direct transfer (VAX/4.3BSD ↔ PDP-11/2.11BSD, two t3.micro VMs)
**PDP-10/ITS**: Dropped — replaced with PDP-11/2.11BSD
**IMP chain**: Archived in `arpanet/archived/` (blocked on HI1 framing mismatch)

---

## Architecture: VAX + PDP-11 on Separate VMs

Two different architectures, two different BSDs, connected over a VPC private
subnet. The PDP-11 running 2.11BSD is the last BSD for that architecture and
has working TCP/IP networking under SIMH.

```
┌─────────────────────┐              ┌─────────────────────┐
│  t3.micro           │              │  t3.micro           │
│  VAX (builder)      │◄────────────►│  PDP-11 (receiver)  │
│  SIMH + 4.3BSD      │   TCP/IP     │  SIMH + 2.11BSD     │
│  Compiles bradman.c │   over VPC   │  Receives brad.1    │
│  ~$0.01/hr          │   private    │  ~$0.01/hr          │
└─────────────────────┘   subnet     └─────────────────────┘
```

### Why PDP-11/2.11BSD

- Different architecture from VAX (better technical signal)
- SIMH PDP-11 is the most mature emulator in SIMH (rock solid)
- 2.11BSD has TCP/IP networking (FTP, rcp work out of the box)
- Pre-built disk images available (`simh.trailing-edge.com`)
- Runs comfortably on t3.micro (PDP-11 emulation is very lightweight)
- No ITS/KLH10/Chaosnet complexity

### Transfer options (pick one during implementation)

| Method | Historically authentic | Complexity | Fun factor |
|--------|----------------------|------------|------------|
| FTP (TCP/IP) | ⭐⭐ | Low | Standard |
| rcp (TCP/IP) | ⭐⭐ | Low | Standard |
| Serial link (DL11 ↔ TCP) | ⭐⭐⭐ | Medium | High — real inter-machine serial |
| UUCP over serial | ⭐⭐⭐ | Medium | Very period-accurate |

Serial/UUCP would be the most interesting signal. FTP is the fastest to get working.

---

## Step 0: Tear Down Old Infrastructure

```bash
# Stop IMP containers on existing t3.medium
ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186 \
  "cd brfid.github.io && docker compose -f arpanet/archived/docker-compose.arpanet.phase2.yml down 2>/dev/null; true"
```

Terminate old t3.medium after new VMs are confirmed working.

---

## Step 1: Provision Two t3.micro Instances

Both need:
- Ubuntu 22.04 AMI
- Docker installed
- SSH key: `~/.ssh/id_ed25519`
- Same VPC/subnet (private IP connectivity)
- Security group: SSH from your IP + all traffic between instances

Name tags: `arpanet-vax`, `arpanet-pdp11`

---

## Step 2: VAX Instance

Already proven — same setup as current project:

- Docker image: `jguillaumes/simh-vaxbsd` (pinned by digest)
- Console on port 2323
- 4.3BSD boots to login prompt
- bradman.c compiles and runs

---

## Step 3: PDP-11 Instance

- [ ] Find or build 2.11BSD SIMH disk image with networking
- [ ] Create `arpanet/Dockerfile.pdp11` (SIMH PDP-11 + 2.11BSD)
- [ ] Create SIMH config for PDP-11 with DELQA Ethernet or DL11 serial
- [ ] Verify 2.11BSD boots and network/serial is reachable
- [ ] Port `bradman.c` to 2.11BSD if needed (K&R C — should work as-is
      since it's already 4.3BSD/K&R compatible, but 2.11BSD has a smaller
      libc — test compilation)

### 2.11BSD disk images

Available from:
- `simh.trailing-edge.com` — pre-built images
- `github.com/AaronJackson/2.11BSD` — build from source
- The SIMH distribution itself often includes sample configs

### bradman.c on 2.11BSD

`bradman.c` already targets K&R C with pre-ANSI fallbacks (varargs, no
stdlib.h, etc.). 2.11BSD's `cc` is a K&R compiler. The code should compile
with zero or minimal changes. Test:

```
cc -o bradman bradman.c
```

If `roff_escape_line` or string functions cause issues, they'll be minor
(2.11BSD has `malloc`, `free`, `strlen`, `strcmp`, `fprintf` — all used
by bradman.c).

---

## Step 4: Network Transfer

### Option A: FTP (fastest to implement)
```
# On PDP-11: start ftpd (2.11BSD has it)
# On VAX: ftp <pdp11-private-ip>
# put brad.1
```

### Option B: Serial link (most interesting)
- SIMH PDP-11 DL11 serial → TCP socket → SIMH VAX DZ serial
- Use `tip` or `cu` on each end
- Transfer via XMODEM, ZMODEM, or raw `cat > file`
- Or UUCP over serial (very period-accurate for PDP-11)

### Option C: rcp (simplest)
```
# Configure .rhosts on PDP-11
# On VAX: rcp brad.1 pdp11:/tmp/brad.1
```

---

## Step 5: Validation

- [ ] Transfer brad.1 from VAX to PDP-11
- [ ] Verify file integrity (diff, checksum, or `man brad` on PDP-11)
- [ ] Capture evidence artifacts
- [ ] Document in results file

---

## Deferred: IMP Chain (Return Later)

Archived in `arpanet/archived/`. Blocked on KS10 HI1 framing mismatch.
See `arpanet/archived/README.md`.

---

## References

- Archived IMP topology: `arpanet/archived/README.md`
- IMP blocker: `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`
- Progress timeline: `docs/arpanet/progress/PHASE3-PROGRESS.md`

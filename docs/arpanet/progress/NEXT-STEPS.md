# ARPANET Next Steps

**Active path**: Chaosnet-direct (VAX ↔ PDP-10/ITS, separate VMs)  
**IMP chain**: Archived in `arpanet/archived/` (blocked on HI1 framing mismatch)

---

## Architecture: Two t3.micro Instances

Each emulator runs on its own VM, connected over a VPC private subnet.
This is historically accurate (Chaosnet was a LAN connecting separate machines)
and cheaper than the current single t3.medium ($0.02/hr vs $0.04/hr).

```
┌─────────────────────┐         ┌─────────────────────┐
│  t3.micro (VAX)     │         │  t3.micro (PDP-10)  │
│  SIMH 4.3BSD        │◄───────►│  ITS (KLH10/SIMH)   │
│  172.31.x.x         │  VPC    │  172.31.x.y         │
│  ~$0.01/hr           │ private │  ~$0.01/hr           │
└─────────────────────┘  subnet └─────────────────────┘
                    Chaosnet over UDP
```

### Why t3.micro

- SIMH/KLH10 are single-threaded, use ~50-100MB RAM
- 1GB RAM is sufficient (Docker + emulator)
- 2 vCPU handles emulator + OS overhead
- $0.0104/hr each ($0.50/day for both if left running, $0 when stopped)
- t3.nano (512MB) is too tight after Docker overhead

---

## Immediate: Tear Down Old Infrastructure

### Step 0: Stop IMP containers and downsize

```bash
# Tear down IMP topology on existing t3.medium
ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186 \
  "cd brfid.github.io && docker compose -f arpanet/archived/docker-compose.arpanet.phase2.yml down 2>/dev/null; true"

# Stop the t3.medium (don't terminate yet — reuse as VAX host or terminate after new VMs are up)
```

---

## Step 1: Provision Two t3.micro Instances

Options:
- **Manual (console)**: Launch two t3.micro in same VPC/subnet, same security group, same key
- **CDK** (existing `test_infra/`): Modify to provision two instances instead of one

Both instances need:
- Ubuntu 22.04 AMI
- Docker installed
- Same SSH key (`~/.ssh/id_ed25519`)  
- Same VPC private subnet (so they can reach each other on private IPs)
- Security group allowing:
  - SSH (22) from your IP
  - All traffic between the two instances (same SG, self-referencing rule)

### Name tags
- `arpanet-vax` — runs VAX/4.3BSD under SIMH
- `arpanet-pdp10` — runs PDP-10/ITS under KLH10 or SIMH

---

## Step 2: PDP-10/ITS Runtime

This is the key unknown. Research needed:

- [ ] Can SIMH KS10 boot ITS? (The ITS project primarily targets KLH10)
- [ ] If not, can KLH10 compile on x86_64 Ubuntu? (It should — it's the native target)
- [ ] Pre-built ITS disk images available? Check `github.com/PDP-10/its` releases
- [ ] If ITS build is needed: build on Mac x86 Docker, scp disk image to t3.micro

**Fallback**: If ITS won't run on the t3.micro, build the disk image on the Mac
(x86_64 Docker via Rosetta) and copy it over. The t3.micro only needs to *run* 
the emulator, not build ITS from source.

---

## Step 3: Chaosnet Connectivity

Once both VMs are running:

- [ ] Configure Chaosnet shim (or direct UDP) between VMs using private IPs
- [ ] Verify PDP-10/ITS Chaosnet responds to packets from VAX VM
- [ ] Test file transfer

The Chaosnet "shim" may simplify to just UDP port forwarding between the two
VMs, since they're on a real network. Chaosnet packets can be encapsulated
in UDP between the two emulator instances.

---

## Step 4: Transfer Test

- [ ] Run `arpanet/scripts/test_chaosnet_transfer.py` (adapted for two-VM topology)
- [ ] Capture evidence artifacts
- [ ] Document in `docs/arpanet/progress/PATH-A-CHAOSNET-RESULTS.md`

---

## Deferred: IMP Chain (Return Later)

Archived in `arpanet/archived/`. Blocked on KS10 HI1 framing mismatch.
See `arpanet/archived/README.md`.

---

## References

- Chaosnet plan: `docs/arpanet/progress/PATH-A-CHAOSNET-PLAN.md`
- IMP blocker: `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`
- Archived IMP topology: `arpanet/archived/README.md`
- Progress timeline: `docs/arpanet/progress/PHASE3-PROGRESS.md`

# ARPANET Next Steps

**Active path**: VAX ↔ PDP-10 Serial Tunnel (Phase 1: serial-over-TCP)
**IMP chain**: Archived in `arpanet/archived/` (blocked on HI1 framing mismatch)
**PDP-11 path**: Superseded by PDP-10 serial tunnel

---

## Architecture: VAX + PDP-10 Serial Tunnel

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  VAX/4.3BSD     │  TCP    │  Serial-TCP    │  TCP    │  PDP-10/ITS     │
│  SIMH DZ11      │◄───────►│  Tunnel        │◄───────►│  SIMH DL11      │
│  :2323 (console)│  :9000  │  (socat)       │  :9001  │  :2326 (console)│
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

### Why PDP-10/ITS

- Native Chaosnet support (interesting technical signal)
- TOPS-20 via SIMH KS10
- Serial tunnel is simplest path to connectivity
- No IMP complexity needed

### Current AWS Status

| VM | Role | Status |
|----|------|--------|
| `arpanet-vax` | VAX/4.3BSD | ✅ Running (t3.medium) |
| `arpanet-pdp10` | PDP-10/TOPS-20 | ✅ Running |

**Connection**:
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186
```

**Serial tunnel ports**:
- `localhost:9000` → VAX console (2323)
- `localhost:9001` → PDP-10 console (2326)

---

## Phase 1: Serial-over-TCP Tunnel (Complete)

✅ Infrastructure created:
- `docker-compose.vax-pdp10-serial.yml`
- `arpanet/scripts/serial-tunnel.sh`
- `arpanet/configs/pdp10-serial.ini`
- `docs/arpanet/SERIAL-TUNNEL.md`

✅ VAX tested:
```
Connected to the VAX 11/780 simulator DZ device, line 0
login: root
```

### Test Serial Tunnel

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186

# Start tunnel (use tmux for persistence):
tmux
socat TCP-LISTEN:9000,bind=127.0.0.1,fork TCP:localhost:2323 &
socat TCP-LISTEN:9001,bind=127.0.0.1,fork TCP:localhost:2326 &
socat TCP:127.0.0.1:9000 TCP:127.0.0.1:9001 &
# Detach: Ctrl+B D

# Test:
telnet localhost 9000  # VAX console
telnet localhost 9001  # PDP-10 console
```

---

## Phase 2: Chaosnet-on-Serial (Next)

After serial tunnel is proven working:
- Implement Chaosnet protocol on both ends
- Shim translates serial ↔ Chaosnet NCP
- VAX runs simple Chaosnet client
- PDP-10 uses native ITS Chaosnet

See `docs/arpanet/SERIAL-TUNNEL.md` for full architecture.

---

## Deferred: IMP Chain (Return Later)

Archived in `arpanet/archived/`. Blocked on KS10 HI1 framing mismatch.
See `arpanet/archived/README.md`.

---

## References

- Serial tunnel architecture: `docs/arpanet/SERIAL-TUNNEL.md`
- Archived IMP topology: `arpanet/archived/README.md`
- IMP blocker: `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`
- Progress timeline: `docs/arpanet/progress/PHASE3-PROGRESS.md`

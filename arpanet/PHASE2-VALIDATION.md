# ARPANET Phase 2 Validation (Steps 2.1 + 2.2 bootstrap)

**Date**: 2026-02-07  
**Environment**: AWS EC2 Ubuntu 22.04 (x86_64)  
**Scope**: Phase 2 topology with host-link bootstrap (VAX + IMP1 + IMP2 + PDP10 host stub)

---

## Topology Under Test

```
[VAX/BSD] <-> [IMP #1] <-> [IMP #2] <-> [PDP10 host stub]
   HI1          MI1 modem link      HI1
```

- `arpanet-vax` @ `172.20.0.10`
- `arpanet-imp1` @ `172.20.0.20`
- `arpanet-imp2` @ `172.20.0.30`
- `arpanet-pdp10` @ `172.20.0.40`

---

## Validation Commands

```bash
docker compose -f docker-compose.arpanet.phase2.yml build
docker compose -f docker-compose.arpanet.phase2.yml up -d
bash arpanet/scripts/test-phase2-imp-link.sh
```

Follow-up measurement command:

```bash
docker compose -f docker-compose.arpanet.phase2.yml ps
docker logs arpanet-imp1 | grep -c "MI1 UDP: link 0 - packet sent"
docker logs arpanet-imp1 | grep -c "MI1 UDP: link 0 - packet received"
docker logs arpanet-imp2 | grep -c "MI1 UDP: link 0 - packet sent"
docker logs arpanet-imp2 | grep -c "MI1 UDP: link 0 - packet received"
```

---

## Significant Findings

1. **Phase 2 test script passes with Step 2.2 bootstrap topology**
   - `arpanet/scripts/test-phase2-imp-link.sh` completed successfully.
   - Script confirmed all four containers running and MI1 markers present in both IMP logs.

2. **Sustained MI1 traffic observed in both directions**
   - IMP1: `MI1 sent=8802`, `MI1 recv=8836`
   - IMP2: `MI1 sent=8861`, `MI1 recv=8878`
   - Counts indicate active, ongoing bidirectional packet flow beyond initial startup.

3. **Container stability during run window**
   - `arpanet-vax`, `arpanet-imp1`, `arpanet-imp2`, and `arpanet-pdp10` remained `Up` through validation sampling.

4. **Non-blocking compose warning**
   - Compose warns that top-level `version` is obsolete in Compose v2.
   - Functional impact: none observed.

5. **IMP2 HI1 host-link bootstrap validated (Step 2.2 bootstrap)**
   - IMP2 was updated to attach HI1 to `172.20.0.40:2000`.
   - Logs show HI1 transmit activity from IMP2 (example markers):
     - `HI1 IO: ... transmit packet`
     - `HI1 UDP: link 1 - packet sent`
   - This confirms a live host endpoint is attached for next-stage host testing.

---

## Conclusion

Phase 2 **Step 2.1 and Step 2.2 bootstrap are validated** on AWS x86_64 for the current scope:

- IMP-to-IMP modem link is up
- MI1 packets are continuously exchanged in both directions
- IMP2 HI1 is attached to a live host stub endpoint
- No immediate instability observed during the test window

---

## Next Testing Target (after Step 2.2 bootstrap)

Replace the host stub with a real PDP-10/TOPS-20 (or ITS) guest and validate:

1. host attach/boot stability,
2. host traffic crossing IMP1↔IMP2,
3. multi-hop end-to-end message flow prior to file-transfer testing.

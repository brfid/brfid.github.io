# Analysis Handoff: KS10 `IMP` Mismatch with H316 IMP HI1 Path

**Date**: 2026-02-10  
**Repo**: `brfid.github.io`  
**Purpose**: reset cold-start assumptions for the PDP-10 path using current evidence.

---

## Core Misidentification

The SIMH `pdp10-ks` `IMP` device used in this project (`set imp enabled`, `set imp simp|uni`, `attach imp udp:...`) is **not** a native ARPANET 1822 host interface.

In this runtime profile it behaves as an Ethernet/IP-style NIC (MAC/ARP/IP semantics), while IMP2 HI1 expects 1822 host-interface framing/semantics.

Representative capture evidence already recorded in-repo:

```text
0x0030: ffff ffff ffff 0000 0219 9e8f 0806 0001
0x0040: 0800 0604 0001 0000 0219 9e8f ac14 0028
```

`0806` is Ethernet ARP EtherType, confirming Ethernet-family payloads were being sent where HI1 expected a different contract.

---

## Why Green HI1 Shim Gates Were Necessary but Insufficient

`hi1_shim.py` wraps payload bytes in an H316 UDP envelope (`MAGIC='H316'`) so IMP2 no longer reports bad magic:

- `final_exit=0`
- `bad_magic_total_delta=0`

This validates envelope compatibility at the immediate ingress boundary, but it does **not** prove end-to-end PDP-10 application reachability when inner payload semantics remain mismatched.

Interpretation for operators:

1. Green dual-window gates = transport/framing guardrail health under the shimmed path.
2. They are **not alone** proof that PDP-10 is a valid ARPANET 1822 host endpoint for FTP in this KS10 profile.

---

## Why `ftp 172.20.0.40` Fails in Current Model

Timeout/refusal on `172.20.0.40:21` should no longer be treated as only a service-bring-up issue. It is consistent with a deeper protocol-stack mismatch between expected ARPANET host semantics and KS10 NIC semantics in this path.

---

## Ranked Next Paths

### Path A (recommended): Chaosnet track for ITS authenticity

- Use KS10/ITS networking along Chaosnet-native expectations.
- Reframe architecture as ARPANET + Chaosnet bridge story where appropriate.
- Avoid forcing KS10 NIC into an 1822 host role it does not natively satisfy here.

### Path D (fast delivery fallback): VAX/IMP transfer proof with non-ITS endpoint on IMP2 side

- Keep already-validated ARPANET routing evidence (VAX↔IMP1↔IMP2).
- Prove transfer with an endpoint that matches the host-interface contract.
- Keep PDP-10 ITS as historical/runtime artifact if needed, without claiming unsupported FTP endpoint semantics.

### Lower-priority exploratory paths

- Path B: direct Docker-network IP path if ITS stack/service support is proven.
- Path C: reverse transfer direction only if protocol compatibility is demonstrated.

---

## Operational Policy Update

For next cold starts:

1. Treat **KS10 IMP mismatch** as the primary Branch B constraint.
2. Do not run repeated blind ITS FTP bring-up retries as primary strategy.
3. Keep dual-window HI1 + shim parse checks as regression guardrails.
4. Advance through a path decision (A first, D fallback) with explicit acceptance criteria.

---

## References

- `docs/arpanet/handoffs/LLM-HOST-LINK-BLOCKER-2026-02-09.md`
- `docs/arpanet/handoffs/LLM-PDP10-FTP-BLOCKER-2026-02-10.md`
- `docs/arpanet/progress/PHASE3-PROGRESS.md`
- `docs/arpanet/progress/NEXT-STEPS.md`
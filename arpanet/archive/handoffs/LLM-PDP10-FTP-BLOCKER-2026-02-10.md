# Research Handoff: PDP-10 FTP Reachability Blocker (Post HI1 Stabilization)

**Date**: 2026-02-10  
**Repo**: `brfid.github.io`  
**Primary Goal**: complete first reliable end-to-end VAX → PDP-10 host-to-host transfer over the current Phase 2 topology.  
**Current Blocker**: VAX FTP client cannot connect to PDP-10 target (`172.20.0.40:21`) despite green HI1/dual-window link gates.

---

## 1) Cold-Start Executive Summary

We resolved earlier host-link framing failures by introducing a temporary Host-IMP Interface boundary adapter (`hi1shim`) between PDP-10 and IMP2. After remote stack alignment, dual-window HI1 gates are consistently green (`final_exit=0`, `bad_magic_total_delta=0`) including a post-transfer-attempt regression run.

However, the first controlled host-to-host transfer attempt fails at **application/service reachability**:

```text
ftp 172.20.0.40
ftp: connect: Connection timed out
```

This means the current critical path is no longer HI1 framing; it is **PDP-10 service readiness/exposure for the transfer endpoint** (or a design mismatch in expected transfer method for ITS runtime).

---

## 2) Known-Good vs Known-Bad

## Known-Good

1. **Host-link gate (HI1)** is clean under strict dual-window acceptance:
   - post-alignment default/SIMP/UNI runs: `final_exit=0`, zero bad-magic deltas.
   - post-transfer-attempt run also green:
     - artifact: `build/arpanet/analysis/hi1-dual-window-post-transfer-attempt.json`
     - `final_exit=0`
     - `bad_magic_total_delta=0`

2. `hi1shim` traffic/counters active and parse-clean:
   - `parse_errors=0`
   - counters for wrapped/unwrapped movement present and increasing in active windows.

3. PDP-10 runtime reaches ITS/DSKDMP state; IMP attach and ARP activity visible in logs.

## Known-Bad

1. Controlled transfer attempt failed from VAX side before FTP login to target:
   - command path used:

```bash
expect arpanet/scripts/authentic-ftp-transfer.exp \
  localhost 2323 \
  /usr/guest/operator/arpanet-test.txt \
  /tmp/pdp10-received.txt \
  172.20.0.40
```

2. Failure signature in transfer log:

```text
ftp 172.20.0.40
ftp: connect: Connection timed out
```

3. No evidence yet that PDP-10 runtime is exposing an FTP listener compatible with this workflow.

---

## 3) Current Architecture Context

Phase 2 topology (active path):

- `arpanet-vax` (BSD 4.3)
- `arpanet-imp1`
- `arpanet-imp2`
- `arpanet-pdp10` (ITS runtime)
- `arpanet-hi1shim` (boundary adapter)

Key host-link wiring now in effect:

- IMP2 HI1 endpoint → `172.20.0.50:2000` (shim)
- PDP10 IMP endpoint → `172.20.0.50:2001` (shim)

Reference implementation/config files:

- `docker-compose.arpanet.phase2.yml`
- `arpanet/scripts/hi1_shim.py`
- `arpanet/configs/imp2.ini`
- `arpanet/configs/phase2/imp2.ini`
- `arpanet/configs/phase2/pdp10.ini`
- `test_infra/scripts/run_hi1_gate_remote.py`

---

## 4) Most Relevant Artifacts

Primary evidence artifacts (local workspace):

- `build/arpanet/analysis/hi1-dual-window-pre-transfer-check.json`
- `build/arpanet/analysis/hi1-dual-window-post-transfer-attempt.json`

Operational log references:

- remote transfer log (AWS workspace):
  - `build/arpanet/analysis/host-to-host-transfer-attempt.log`
- session/state docs:
  - `arpanet/PHASE3-PROGRESS.md` (Session 23)
  - `arpanet/NEXT-STEPS.md`

Historical blocker context:

- `arpanet/LLM-HOST-LINK-BLOCKER-2026-02-09.md` (older HI1 bad-magic phase, now largely mitigated under shim-aligned runtime)

---

## 5) Precise Problem Statement for Research LLM

Given a KS-10/ITS container in this topology, where HI1 framing/regression gates are green via shim but VAX-side FTP connect to PDP-10 (`172.20.0.40:21`) times out, determine:

1. What is the historically/technically correct way to achieve **host-to-host file transfer** in this exact runtime state?
2. Is FTP on port 21 expected at all on this PDP-10 ITS setup, or is another service/protocol path required first?
3. What minimal, concrete steps are needed to bring the PDP-10 endpoint to “transfer-ready” without regressing link-layer stability?

---

## 6) Candidate Hypotheses (Prioritized)

1. **No FTP service is running on PDP-10 ITS** (most likely).
2. FTP-equivalent service exists but is not bound/reachable on expected interface.
3. Service exists but requires ITS-specific bring-up/login/bootstrap sequence before external connections.
4. Transfer method expectation is wrong for this host state (e.g., NCP/TCP stack mismatch or different canonical service path).
5. Network path/routing to 172.20.0.40:21 is blocked despite IMP-level activity (less likely given other green evidence, but must be disproven explicitly).

---

## 7) What We Need Back from Research (Concrete Output Format)

Please return:

1. **Decision tree** (fast triage) for “FTP timeout to PDP-10 ITS in this topology”.
2. **Exact in-container verification commands** (PDP-10 side and VAX side) to prove/disprove each branch.
3. **Minimal enablement sequence** to make the target transfer endpoint reachable.
4. **Recommended transfer validation command** using existing automation assets where possible.
5. **Regression guardrails** (what to rerun after changes): dual-window gate + runtime evidence checks.

Preferred response style: high signal, command-first, no broad historical exposition.

---

## 8) Constraints / Non-Goals

- Do **not** undo shim path right now; keep current link-layer stability intact.
- Avoid broad topology redesign unless required.
- Maintain evidence-driven acceptance:
  - post-change dual-window manifest should remain green (`final_exit=0`, `bad_magic_total_delta=0`).

---

## 9) Reproduction Checklist (Current State)

1. Attempt transfer (expected fail currently):

```bash
expect arpanet/scripts/authentic-ftp-transfer.exp \
  localhost 2323 \
  /usr/guest/operator/arpanet-test.txt \
  /tmp/pdp10-received.txt \
  172.20.0.40
```

2. Confirm failure signature in log:

```text
ftp: connect: Connection timed out
```

3. Re-run regression gate (expected green currently):

```bash
.venv/bin/python test_infra/scripts/run_hi1_gate_remote.py \
  --dual-window \
  --manifest-output build/arpanet/analysis/hi1-dual-window-post-transfer-attempt.json
```

---

## 10) Handoff Bottom Line

The project is no longer blocked on HI1 bad-magic under the aligned shim runtime. The unresolved issue is **PDP-10 transfer endpoint readiness** for VAX-initiated host-to-host file transfer. We need a focused ITS/PDP-10 service bring-up path (or corrected transfer mechanism) that preserves current green link-layer gate behavior.

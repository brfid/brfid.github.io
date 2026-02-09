# TOPS-20 Boot-from-Tape: Issues, Attempts, and Current Status

**Last updated:** 2026-02-09  
**Scope:** PDP-10/TOPS-20 tape boot troubleshooting in Stage 3 ARPANET work

---

## Executive summary

We resolved one major infrastructure blocker (PDP-10 IMP attach syntax), but the core TOPS-20 tape-boot path is still blocked. The KS10 simulator consistently halts immediately when booting the TOPS-20 V4.1 installation tape.

Current blocking signature:

```text
Unknown KS-10 simulator stop code 7, PC: 000100
```

No attempt has yet reached `MTBOOT>`.

---

## Environment and artifacts used

- Emulator: **SIMH KS-10** (`pdp10-ks`, V4.0-0, commit 627e6a6b)
- Tape image: `tops20_v41.tap` (from `bb-d867e-bm_tops20_v41_2020_instl.tap`)
- Disk target: RP06 image (`tops20.dsk`)
- Deployment context: Dockerized multi-container ARPANET topology on AWS

Key troubleshooting docs previously created:

- `arpanet/TOPS20-INSTALLATION-PROBLEM.md`
- `arpanet/TOPS20-TAPE-BOOT-FAILURE.md`
- `arpanet/TOPS20-STATUS-FINAL.md`

---

## Confirmed issues encountered

1. **Console interaction/timing problems (initially):**
   - Telnet console mode made it difficult to reliably capture boot interaction.
   - Prompt visibility and connection timing were inconsistent.

2. **Invalid/unsupported KS10 config usage discovered during iterations:**
   - `set cpu tops20` was rejected by this KS10 build.

3. **IMP attach syntax bug in PDP-10 configs (now fixed):**
   - Broken form: `attach -u imp 2000:172.20.0.30:2000`
   - Working form: `attach imp udp:2000:172.20.0.30:2000`
   - This removed `File open error` and allowed IMP UDP device open/traffic.

4. **Persistent tape boot failure (current blocker):**
   - `boot tua0` halts immediately at PC `000100` with stop code `7`.
   - MTBOOT never appears.

---

## Attempt history (condensed)

### A) Auto-boot + telnet automation
- Used expect-based scripts to connect and wait for `MTBOOT>`.
- Result: connection established but no usable boot interaction; no MTBOOT.

### B) Manual-boot configuration variants
- Removed/changed auto-boot behavior to try entering commands manually.
- Result: still no successful path to MTBOOT.

### C) Python telnet and direct timing experiments
- Tried multiple connect/send/read timing patterns.
- Result: no stable prompt flow for successful tape bootstrap interaction.

### D) Process cleanup / restart cycles
- Cleared stale telnet/expect sessions and retried from clean starts.
- Result: reduced noise, but did not fix tape boot failure.

### E) Console mode refinement
- Moved toward stdio-style console handling to remove telnet wrapper ambiguity.
- Result: console visibility improved, but boot failure remained unchanged.

### F) Tape boot command execution on KS10
- Repeated `boot tua0` under cleaned-up config and environment.
- Result: deterministic halt (`stop code 7`, `PC: 000100`) every time.

### G) IMP network attach correction (important parallel fix)
- Updated PDP-10 config files, generator code, and production reconfigure script.
- Result: IMP interface now opens correctly and participates in UDP bridge traffic.
- Impact: solved network attach blocker, but **not** the TOPS-20 tape boot blocker.

---

## Files changed during this troubleshooting cycle

- `arpanet/configs/pdp10.ini`
- `arpanet/configs/phase2/pdp10.ini`
- `arpanet/configs/pdp10-noboot.ini`
- `arpanet/configs/pdp10-install-stdio.ini` (removed invalid `set cpu tops20`)
- `arpanet/topology/generators.py` (generated IMP attach syntax updated)
- `arpanet/scripts/reconfigure-production.sh` (generated config attach syntax updated)

---

## Current status

- **Resolved:** PDP-10 IMP attach syntax/runtime network interface issue.
- **Unresolved / blocking:** TOPS-20 V4.1 tape bootstrap on KS10.

Working/observable log behavior now includes correct IMP UDP device open, but tape boot still halts at `PC: 000100` before installer control is reached.

---

## Most likely root cause (current working theory)

The installed TOPS-20 tape path appears incompatible with this KS10 setup/build (or requires emulator/CPU mode behavior not available in this current KS10 invocation). Prior art and community recipes often rely on KL10/KLH10 workflows for successful TOPS-20 install/boot.

---

## Practical next options

1. **Authentic full TOPS-20 path:** switch PDP-10 emulator path to KL10/KLH10-oriented setup.
2. **Alternative authentic PDP operation:** use TOPS-10 or ITS path where available/known-good.
3. **Project milestone path:** complete Stage 3 on ARPANET routing/logging criteria while treating full TOPS-20 install as a follow-on enhancement.

---

## Bottom line

We have good evidence that the current KS10 + TOPS-20 V4.1 tape combination is the hard blocker, not networking. Network attach and IMP traffic issues were corrected, but tape bootstrap still fails deterministically with stop code 7.

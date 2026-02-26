# Dead Ends and Retired Paths

Purpose: explicitly mark archived approaches that are not part of the current
VAX↔PDP-11 pipeline so active work stays focused.

Current active path:
- `docs/integration/INDEX.md`
- `docs/integration/operations/VAX-PDP11-COLD-START-DIAGNOSTICS.md`
- `scripts/edcloud-vintage-runner.sh`

---

## Dead Ends (for this repo's active pipeline)

| Path | Status | Why retired / blocked | Historical evidence |
|------|--------|------------------------|---------------------|
| ARPANET IMP chain (VAX→IMP→IMP→PDP-10) | Retired / not shipped | Emulator host-link framing mismatch (`bad magic`) and scope pivot to Hugo + VAX↔PDP-11 artifact path | `docs/archive/arpanet/README.md`, `docs/archive/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md` |
| Chaosnet "Path A" for ITS | Retired / not shipped | Did not clear blocker chain to become a stable pipeline dependency | `docs/archive/arpanet/chaosnet/README.md` |
| PDP-10 KS10/TOPS-20 transfer path | Retired / not shipped | Runtime and compatibility blockers; does not serve current VAX↔PDP-11 objective | `docs/archive/pdp-10/INDEX.md`, `docs/archive/pdp-10/ks10/README.md` |
| VAX↔PDP-11 FTP transfer | Retired | Unreliable guest/container networking in this runtime; superseded by console transfer | `docs/archive/pipeline-planning/transport-archive.md`, `docs/archive/pipeline-planning/DEBUGGING-SUMMARY-2026-02-14.md` |
| TS11 tape as primary transport | Retired for active path | Technically validated, but not selected for current production path; added complexity and host-side extraction constraints | `docs/archive/pipeline-planning/TAPE-TRANSFER-VALIDATION-2026-02-13.md` |

---

## Still Useful Historical Context (Not Dead Ends)

These records are old but still high-signal when debugging current console flow:
- `docs/archive/pipeline-planning/VAX-PDP11-VALIDATION-2026-02-14.md` — practical Stage 1→3 checkpoints and evidence patterns
- `docs/archive/pipeline-planning/DEBUGGING-SUMMARY-2026-02-14.md` — why commands must execute inside guest OS environments
- `docs/archive/vax/VAX-CONTAINER-BSD-FILE-SHARING.md` — host/container-vs-guest boundary issues that caused earlier false-positive conclusions

---

## Archive Navigation Note

Many archived files preserve original path names from earlier repo layouts
(for historical fidelity). Use this file, `docs/archive/README.md`, and
`docs/integration/INDEX.md` as the navigation authority.

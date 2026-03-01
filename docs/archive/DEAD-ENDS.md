# Dead Ends and Retired Paths

Purpose: explicitly mark archived approaches that are not part of the current pipeline
so active work stays focused.

Current active path:
- `docs/integration/INDEX.md`
- `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md`
- `scripts/edcloud-vintage-runner.sh`

---

## Dead Ends

| Path | Status | Why retired |
|------|--------|-------------|
| screen + telnet + sleep orchestration | Retired | Timing-based heredoc injection with no handshake; inherently fragile. VAX login prompt unreliable after multiple rapid connections. Replaced by pexpect. Scripts deleted from `scripts/`. |
| docker-compose.production.yml | Retired | Pre-pexpect compose file exposing telnet console ports. Replaced by `docker build`/`docker run` in `edcloud-vintage-runner.sh`. File removed from repo root. |
| FTP (VAX guest → external FTP server) | Retired | VAX guest could not reliably reach the FTP server/container. Networking and routing inside the SIMH container were the issue. |
| FTP (VAX → PDP-11 directly) | Not viable | PDP-11 2.11BSD `unix` kernel has no working Ethernet. `netnix` kernel crashes on `xq` init. Console-based (uuencode or pexpect heredoc) is the only viable file transfer path to PDP-11. |
| uuencode/uudecode console transfer (screen/telnet era) | Retired | Screen/telnet implementation was unreliable. Revisited with pexpect and is now the active UUCP framing mechanism: VAX uuencodes `brad.1`; host captures `brad.1.uu`; PDP-11 `uudecode`s to recover `brad.1`. Not a dead end — this path is validated and in production. |
| TS11 tape as primary transport | Retired | Technically validated, not selected; adds complexity and host-side extraction constraints. |
| ARPANET IMP chain (VAX→IMP→IMP→PDP-10) | Retired | Emulator host-link framing mismatch (`bad magic`) and scope pivot to VAX↔PDP-11 artifact path. |
| Chaosnet / ITS path | Retired | Did not clear blocker chain; not a pipeline dependency. |
| PDP-10 KS10/TOPS-20 transfer path | Retired | Runtime and compatibility blockers; does not serve VAX↔PDP-11 objective. |

---

## Archive navigation

Historical experiment notes are in `docs/archive/` organized by host type.
Use this file and `docs/integration/INDEX.md` as the navigation authority.

# Retired pipeline approaches

Use [the active pipeline guide](../integration/INDEX.md) and `scripts/vintage-runner.sh` for current work.

| Approach | Status | Current constraint or replacement |
|---|---|---|
| GNU screen, telnet, and fixed-delay console control | Retired | `pexpect` drives SIMH through standard input and output and waits for explicit markers. |
| `docker-compose.production.yml` | Retired | The runner uses direct `docker pull`, `docker build`, and `docker run` commands. |
| VAX guest to external FTP server | Retired | The host captures the VAX-generated UUE spool from the console. |
| Direct VAX to PDP-11 FTP | Unavailable | The PDP-11 `unix` kernel has no working Ethernet; `netnix` crashes during `xq` initialization. |
| TS11 tape transfer | Retired | The host transfers the UUE spool between guest consoles. |
| ARPANET IMP chain | Retired | The KS10 SIMH IMP device emits raw Ethernet-style frames, while the H316 simulator expects BBN 1822 leaders. |
| Chaosnet and ITS path | Retired | The incomplete responder and topology do not provide a production transport. |
| PDP-10 KS10 and TOPS-20 path | Retired | The active artifact path uses VAX 4.3BSD and PDP-11 2.11BSD. |

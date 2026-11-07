---
title: "ARPANET Redux"
date: 2026-09-13
draft: false
description: "Connecting Network UNIX and ITS through simulated ARPANET switches."
tags: ["arpanet", "computer-history", "emulation"]
---

[ARPANET Redux](https://github.com/brfid/arpanet-redux) connects simulated PDP-11/Network UNIX V6 and PDP-10/ITS systems through recovered 1973 ARPANET switching software.

## Setup

The switches are simulated Honeywell 316 computers running Interface Message Processor (IMP) software. Each host runs its own Network Control Program (NCP), connected to an IMP through a simulated 1822 host interface.

Traffic follows these routes:

```
Direct:     Network UNIX → IMP 62 → IMP 6 → ITS
After cut:  Network UNIX → IMP 62 → IMP 7 → IMP 6 → ITS
```

Modern tools start and stop the simulators, reconstruct Network UNIX disks from pinned public inputs, and retain guest files between sessions. A modern passive console receives IMP trouble and throughput reports and displays network state.

## A TELNET connection

A native TELNET session connects Network UNIX to ITS. In the [link-cut test](https://github.com/brfid/arpanet-redux/blob/881d703b05c7a8cfe10e45eb51c6d70aefe50e96/docs/experiments/2026-09-01-ncc-pdp11-its-application-failover.md), ITS returns a time command's response before and after the IMP 62–IMP 6 link is cut. The same connection remains open while the IMPs reroute traffic through IMP 7.

## Historical context

TELNET was in use for remote connections by summer 1971. On [July 20](https://www.rfc-editor.org/rfc/rfc198.html), Rand reported testing Lincoln Laboratory's user and server TELNET, login procedure, and access to CMS, all working according to current specifications. This was roughly three years after the Network Working Group's first host-software discussions in [summer 1968](https://www.rfc-editor.org/rfc/rfc1.html).

The modern Network Control Center (NCC) console represents a mid-1970s operations center, approximately 1975–76. Its [documented profile](https://github.com/brfid/arpanet-redux/blob/881d703b05c7a8cfe10e45eb51c6d70aefe50e96/docs/ncc.md#console-profile) combines 1973 IMP reports, 1974–75 operating practices, and the banked light-panel controls described in BBN TIR 90's 1976 revision.

## Sources

| Source | Contribution |
| --- | --- |
| [ARPANET in a Box](https://github.com/obsolescence/arpanet) | Initial IMP software, simulator configurations, and ITS disks. |
| [H316 SIMH](https://github.com/larsbrinkhoff/simh), [KA10 SIMH](https://github.com/larsbrinkhoff/ka10-simh), [Open SIMH](https://github.com/open-simh/simh) | Machine simulators. |
| [linux-ncp](https://github.com/larsbrinkhoff/linux-ncp) | NCP software used to test network behavior. |
| [PDP-10/ITS](https://github.com/PDP-10/its), [SRI/NOSC Network UNIX V6](https://github.com/pdp11/network-unix-v6) | Preserved operating systems, network software, and build inputs. |
| TUHS: [Ken Wellsch V6 distribution](https://www.tuhs.org/Archive/Distributions/Research/Ken_Wellsch_v6/), [Tim Shoppa V6 image](https://www.tuhs.org/Archive/Distributions/Research/Tim_Shoppa_v6/) | V6 root filesystem and RL disk boot block, respectively. |
| [Walden's IMP-code collection](https://www.walden-family.com/impcode/), [DEC IMP11-A manual](https://bitsavers.org/pdf/dec/unibus/IMP11-A_PDP-11_Host_to_IMP_Interface_Feb1975.pdf), BBN Report 1822 | Recovered listings, provenance, and host-interface documentation. |
| [1972 NCC paper](https://www.walden-family.com/impcode/1972-nmc.pdf), BBN TIR 90 in Walden's collection | Network reports and operator displays used as references for the console. |

## Problems encountered

- **Simulator interface:** the PDP-11 IMP device had to be added. Incorrect byte order and truncated incoming messages prevented TELNET from working. A temporary daemon workaround was removed after traces established correct acknowledgement handling in the preserved code. [Investigation](https://github.com/brfid/arpanet-redux/blob/881d703b05c7a8cfe10e45eb51c6d70aefe50e96/docs/research/imp11a-device.md).
- **Source files:** `telnet.c` was zero-filled; an intact `telnet.c.org` supplied the source for the guest build. [Finding](https://github.com/brfid/arpanet-redux/commit/d16b5d95dc0e082d4d18e07c684d3dfade747211).
- **TELNET client:** a missing `break` produced a false protocol-error message. The repair applies only to a staged build copy. The archive does not establish when the defect was introduced. [Repair](https://github.com/brfid/arpanet-redux/commit/45175f265b03909a097c77e2c6ed343092e7157d).

# VAX stage (Stage B)

The VAX (4.3BSD on SIMH) is Stage B of the vintage pipeline. It compiles `bradman.c`
and runs the resulting binary to transform `resume.vintage.yaml` into `brad.1`
(troff man page source), which Stage A (PDP-11 nroff) then renders.

## Why a YAML subset?

Full YAML is too complex to parse reliably with a portable C program on older Unix systems.
The intended workflow is:

1. Host converts `resume.yaml` → `build/vintage/resume.vintage.yaml` (flattened, quoted, versioned).
2. VAX guest compiles and runs `bradman` to produce `brad.1`.
3. PDP-11 guest runs `nroff -man brad.1` to produce `brad.man.txt`.

## Build (on 4.3BSD VAX)

```sh
cc -O -o bradman bradman.c
./bradman -i resume.vintage.yaml -o brad.1
```

Source: `vintage/machines/vax/bradman.c`

## Orchestration

Stage B is driven by pexpect connecting to the SIMH VAX via stdin/stdout.
The pexpect script injects `bradman.c` and `resume.vintage.yaml` via heredoc
(with prompt detection), compiles, runs, and reads back `brad.1`.

See `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md` for the implementation spec.

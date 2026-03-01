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
./bradman -i resume.vintage.yaml -mode bio -o brad.bio.txt
uuencode brad.1 brad.1 > brad.1.uu
```

Source: `vintage/machines/vax/bradman.c`

Stage B produces two output artifacts:
- `brad.1.uu` — UUE-encoded troff source (UUCP spool for PDP-11 delivery)
- `brad.bio.txt` — plain-text bio excerpt (bio mode)

The host captures both from the pexpect session. `brad.1.uu` is delivered to the PDP-11
for `uudecode` + `nroff` rendering. `brad.bio.txt` is parsed into `hugo/data/bio.yaml`
by `resume_generator/bio_yaml.py`.

## Orchestration

Stage B is driven by pexpect connecting to the SIMH VAX via stdin/stdout.
The pexpect script (`scripts/vax_pexpect.py`) injects `bradman.c` via plain heredoc and
`resume.vintage.yaml` via UUE batched heredoc (lines exceed CANBSIZ=256), compiles,
runs both modes, UUE-encodes the output, and captures both artifacts.

See `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md` for implementation details.

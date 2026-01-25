# VAX manpage generator (proof-of-concept)

This folder contains a small, VAX-friendly C program that reads a constrained YAML
subset (`resume.vax.yaml`) and emits a `man(7)` roff source file (`brad.1`).

## Why a YAML subset?

Full YAML is too complex to parse reliably with a tiny, portable C program on older
Unix systems. The intended workflow is:

1. Host converts `resume.yaml` → `resume.vax.yaml` (flattened, quoted, versioned).
2. Guest compiles and runs `bradman` to produce `brad.1`.
3. Guest runs `nroff -man brad.1` (or `man`) to produce the rendered text.

## Build (typical BSD)

```sh
cc -O -o bradman bradman.c
./bradman -i resume.vax.example.yaml -o brad.1
nroff -man brad.1 > brad.txt
```

## Input schema (v1)

See `resume.vax.example.yaml` for an example.


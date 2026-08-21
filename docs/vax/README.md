# VAX stage (Stage B)

The VAX (4.3BSD on SIMH) is Stage B of the vintage pipeline. It compiles `bradman.c` and runs the binary to transform `bio.vintage.yaml` into `brad.bio.roff` (troff), then uuencodes it into `brad.bio.uu` for delivery to the PDP-11. For the end-to-end data flow see [`../integration/INDEX.md`](../integration/INDEX.md); for the as-built gotchas see [`../integration/operations/PEXPECT-PIPELINE-SPEC.md`](../integration/operations/PEXPECT-PIPELINE-SPEC.md).

## Why a YAML subset?

Full YAML is too complex to parse reliably with a portable C program on a 4.3BSD VAX. The host (`resume_generator/vintage_yaml.py`) flattens `site.yaml` into `build/vintage/bio.vintage.yaml`: a small, single-line-scalar, ASCII-only, versioned subset that `bradman.c` can parse with a hand-written scanner.

## Build and run (on the 4.3BSD VAX)

```sh
cc -O -o bradman bradman.c
./bradman -i bio.vintage.yaml -o brad.bio.roff
uuencode brad.bio.roff brad.bio.roff > brad.bio.uu
```

Source: `vintage/machines/vax/bradman.c`.

## bradman contract

Input keys (all from `site.yaml`, via `bio.vintage.yaml`): `schemaVersion`, `buildDate`, `bioName`, `bioHeadline`, `bioProfile`. `bioProfile` is required.

Output (`brad.bio.roff`): a troff document that sets the measure (`.ll 60n`), disables the page offset (`.po 0`) and hyphenation (`.nh`), prints the name and headline verbatim (`.nf`/`.fi`), and fills-and-justifies the blurb (`.ad b`). The build date is emitted only as a `.\"` comment, which nroff strips — so the rendered bio carries no date, and its bytes change only when the copy changes.

## Orchestration

`scripts/vax_pexpect.py` drives the SIMH VAX via stdin/stdout: it injects `bradman.c` via a plain heredoc and `bio.vintage.yaml` via a UUE batched heredoc (the blurb line can exceed the 256-byte CANBSIZ tty limit), compiles, runs `bradman`, uuencodes the output, and captures `brad.bio.uu`.

# VAX stage B

Stage B runs `bradman.c` on a SIMH VAX with 4.3BSD. It converts the public bio input to troff, encodes the troff as a UUCP spool, and returns the spool to the host.

For the complete flow and operator commands, see [the pipeline operations guide](../integration/INDEX.md). For console behavior, see [the pexpect implementation reference](../integration/operations/PEXPECT-PIPELINE-SPEC.md).

## Guest input contract

`resume_generator/vintage_yaml.py` writes `build/vintage/bio.vintage.yaml` with these keys in order:

1. `schemaVersion`
2. `buildDate`
3. `bioName`
4. `bioHeadline`
5. `bioProfile`

Every value is a required, quoted, single-line, printable ASCII string. `bioName` and `bioHeadline` come from `site.yaml`; `bioProfile` comes from `resume.yaml` `basics.summary`.

The generated mapping contains exactly these five keys. The host rejects missing, empty, multiline, nonprintable, or non-ASCII required values before starting SIMH.

## Run the guest commands

With `bradman.c` and `bio.vintage.yaml` in the current guest directory, run:

```sh
cc -O -o bradman bradman.c
./bradman -i bio.vintage.yaml -o brad.bio.roff
uuencode brad.bio.roff brad.bio.roff > brad.bio.uu
```

The host normally performs these commands through `scripts/vax_pexpect.py` and validates each artifact-producing command's exit status.

## Output contract

`brad.bio.roff` sets a 60-column measure, removes the page offset, disables hyphenation, writes the name and headline without fill, and fills and justifies the summary. It records the build date in a troff comment that `nroff` removes.

`brad.bio.uu` is the text spool delivered to the PDP-11. The spool header names the decoded file `brad.bio.roff`.

Source: [`vintage/machines/vax/bradman.c`](../../vintage/machines/vax/bradman.c).

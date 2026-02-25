# VAX manpage generator (proof-of-concept)

This folder contains a small, VAX-friendly C program that reads a constrained YAML
subset (`resume.vintage.yaml`) and emits a `man(7)` roff source file (`brad.1`).

## Why a YAML subset?

Full YAML is too complex to parse reliably with a tiny, portable C program on older
Unix systems. The intended workflow is:

1. Host converts `resume.yaml` → `resume.vintage.yaml` (flattened, quoted, versioned).
2. Guest compiles and runs `bradman` to produce `brad.1`.
3. Guest runs `nroff -man brad.1` (or `man`) to produce the rendered text.

## Build (typical BSD)

```sh
cc -O -o bradman bradman.c
./bradman -i ../../vintage/machines/vax/resume.vax.example.yaml -o brad.1
nroff -man brad.1 > brad.txt
```

## Input schema (v1)

See `../../vintage/machines/vax/resume.vax.example.yaml` for an example.
(The example filename is historical; active pipeline input is `resume.vintage.yaml`.)

## Future Enhancement: Direct YAML Parsing

The current design uses Python to preprocess `resume.yaml` into a simplified subset
(`resume.vintage.yaml`) before the VAX-side parser processes it. An alternative approach
would be to enhance the C parser to handle more of the original YAML directly.

See `../archive/pipeline-planning/vax-yaml-parser-enhancement.md` for a detailed proposal on:
- Eliminating the Python preprocessing step
- Adding bare string, multi-line, and single-quote support (~85 lines)
- Comparison with JSON parser alternatives
- Implementation strategy and code examples

Reference materials in `../archive/vax/examples/`:
- `yaml_parser_analysis.md` - Feature-by-feature analysis
- `parsing_examples.txt` - Side-by-side format comparisons
- `minimal_json_parser.c` - JSON parser complexity demonstration

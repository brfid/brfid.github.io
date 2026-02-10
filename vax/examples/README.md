# VAX Parser Examples and Analysis

This directory contains reference materials exploring alternative parser implementations
for the VAX resume generator.

## Files

### `yaml_parser_analysis.md`
Detailed analysis of extending the current YAML parser to handle more of the original
`resume.yaml` format. Breaks down each feature needed (bare strings, multi-line strings,
single quotes, inline lists) with complexity estimates and code size.

### `parsing_examples.txt`
Side-by-side comparisons showing the differences between:
- Original `resume.yaml` format (what we have)
- Current VAX-YAML subset (what the parser requires today)
- What would need to be added to parse the original directly

Includes visual examples of each YAML feature and why they matter.

### `minimal_json_parser.c`
Skeleton demonstration of what a JSON parser implementation would look like. Shows
the data structures and functions needed (not a working implementation). Useful for
understanding why JSON would be ~500 lines vs YAML enhancement at ~285 lines.

## Context

These files were created during exploration of replacing the Python preprocessing step
(`resume_generator/vax_yaml.py`) with a more capable C parser that could handle the
original YAML directly.

The main proposal document is at: `../../docs/vax-yaml-parser-enhancement.md`

## Key Findings

- **Enhanced YAML parser**: ~285 lines total (+85 from current)
- **JSON parser alternative**: ~500 lines (more work, requires conversion)
- **Full YAML 1.2 parser**: 5000+ lines (overkill for this use case)

**Recommendation**: Enhanced YAML parser is most practical if eliminating Python
preprocessing is desired. Current Python approach is also perfectly valid.

## Learning Value

These examples demonstrate:
- Parser design trade-offs (generality vs simplicity)
- String parsing techniques (quoted, bare, multi-line)
- State machine design
- C memory management patterns
- Legacy system constraints (pre-ANSI C, VAX BSD)

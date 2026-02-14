# YAML Parser Enhancement Plan

**Date**: 2026-02-13  
**Goal**: Enhance VAX C parser to handle 95% of YAML syntax used in `resume.yaml`

---

## Current State Analysis

### YAML Features Actually Used in `resume.yaml`

Based on analysis of the current resume file:

**✓ Currently Used** (MUST support):
- Unquoted strings (130 instances)
- Quoted strings (some instances)
- Lists (with `-` prefix)
- Nested maps/dictionaries
- Long strings (14 over 100 chars)
- Short strings (130 under 100 chars)

**✗ NOT Used** (can skip for 95% coverage):
- Comments (`#`)
- Multiline literals (`|`) or folded (`>`)
- Anchors (`&ref`) and aliases (`*ref`)
- Flow style (`[1, 2, 3]` or `{a: b}`)
- Booleans, numbers, null (currently all strings)

---

## Current C Parser Limitations

The existing `bradman.c` parser (`parse_resume_vax_yaml` function) only handles:
- **Double-quoted strings only**: `"value"`
- **Single-line strings**: No newlines allowed
- **Escaped quotes/backslashes**: `\"` and `\\`
- **Simple maps and lists**: Basic structure only

**Python preprocessor** (`vax_yaml.py`) currently:
- Converts full YAML → constrained subset
- Quotes all strings
- Flattens whitespace
- Escapes special characters

---

## Enhancement Approach

### Option A: Enhance C Parser (RECOMMENDED)

**Pros**:
- Authentic 1980s C programming
- No Python preprocessing needed
- Smaller dependency chain
- Educational value

**Cons**:
- More C code to write/maintain
- K&R C constraints (no ANSI features)
- Manual memory management

**Implementation**:
1. Add unquoted string parsing
2. Add number/boolean detection (optional)
3. Improve string handling for long values
4. Keep existing quoted string support
5. Maintain K&R C compatibility

### Option B: Use libyaml Library

**Pros**:
- Full YAML 1.1 support
- Well-tested code
- Less code to write

**Cons**:
- External dependency
- May not compile on 4.3BSD
- Loses "authentic build" appeal
- Overkill for simple resume

**Verdict**: ❌ Not recommended for this project

---

## Detailed Implementation Plan

### Phase 1: Extend C Parser for Unquoted Strings

**Target File**: `vax/bradman.c`

**Changes Needed**:

1. **String Token Recognition**
```c
/* Current: only handles "quoted" */
static char *parse_quoted_string(FILE *in);

/* Add: handles both quoted and unquoted */
static char *parse_string_value(FILE *in);
static int is_yaml_special_char(int c);
```

2. **Unquoted String Rules**
- Stop at: `:`, `#`, `[`, `]`, `{`, `}`, `,`, newline
- Trim trailing whitespace
- Handle leading/trailing spaces correctly

3. **Number/Boolean Detection** (optional)
```c
static int is_number(const char *s);
static int is_boolean(const char *s);  /* true, false, yes, no */
```

### Phase 2: Improve List/Map Parsing

**Current**: Simple list/map parsing  
**Enhanced**: Handle nested structures better

1. **List Item Parsing**
- Support unquoted values after `-`
- Handle empty lines
- Better error messages

2. **Map Value Parsing**
- Support unquoted values after `:`
- Handle long strings (>100 chars)
- Preserve whitespace in values

### Phase 3: Remove Python Preprocessor

**Target File**: `resume_generator/vax_yaml.py`

**Changes**:
1. Mark `build_vax_resume_v1()` as deprecated
2. Add `build_vax_resume_v2()` that outputs standard YAML
3. Update `vax_stage.py` to use v2
4. Eventually remove v1 entirely

---

## Testing Strategy

### Test Cases for C Parser

1. **Unquoted Strings**
```yaml
name: Bradley Fidler
label: Technical Writer
```

2. **Quoted Strings** (still supported)
```yaml
name: "Bradley Fidler"
summary: "Technical Writer: docs platforms"
```

3. **Lists**
```yaml
work:
- name: DomainTools
  position: Senior Technical Writer
```

4. **Long Strings**
```yaml
summary: Senior Technical Writer specializing in API documentation and docs-as-code...
```

5. **Nested Maps**
```yaml
basics:
  name: Bradley Fidler
  location:
    city: Warwick
    region: New York
```

### Validation

- [ ] Parse `resume.yaml` successfully
- [ ] Generate same output as current parser
- [ ] Handle malformed YAML gracefully
- [ ] Memory leak testing (`valgrind` if available)
- [ ] Compare against Python PyYAML output

---

## Timeline Estimate

| Phase | Task | Time | Complexity |
|-------|------|------|------------|
| 1 | Analyze current parser | 30 min | Low |
| 2 | Add unquoted string support | 2 hrs | Medium |
| 3 | Test unquoted strings | 1 hr | Low |
| 4 | Improve list/map parsing | 2 hrs | Medium |
| 5 | Integration testing | 1 hr | Low |
| 6 | Update Python preprocessor | 1 hr | Low |
| 7 | End-to-end validation | 1 hr | Low |
| **Total** | | **8-9 hrs** | |

---

## Success Criteria

- [x] Parse current `resume.yaml` without preprocessing
- [ ] Handle unquoted strings
- [ ] Handle quoted strings (existing)
- [ ] Handle lists with both quoted/unquoted items
- [ ] Handle nested maps 3+ levels deep
- [ ] No memory leaks
- [ ] Compile cleanly on 4.3BSD VAX
- [ ] Generate identical output to current system
- [ ] Python preprocessor marked deprecated

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| K&R C compatibility issues | Low | High | Test on actual VAX/BSD first |
| Memory leaks in parser | Medium | Medium | Careful malloc/free, testing |
| Edge case YAML syntax | Low | Low | Start with subset, expand gradually |
| Regression in existing builds | Low | High | Keep old parser until validated |

---

## Future Enhancements (Out of Scope)

- Comments support (`#`)
- Multiline strings (`|` and `>`)
- Flow style (`[1, 2, 3]`)
- Anchors and aliases
- Full YAML 1.2 compliance
- Error recovery
- Pretty-printing/formatting

---

## Related Documentation

- Current parser: `vax/bradman.c` lines 310-900
- Preprocessor: `resume_generator/vax_yaml.py`
- Tests: `tests/test_vax_yaml.py`
- Resume spec: `resume.yaml`


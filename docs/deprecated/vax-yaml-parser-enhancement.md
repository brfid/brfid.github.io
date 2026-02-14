# Enhancing the VAX YAML Parser

## Overview

This document explores replacing the Python preprocessing step (`vax_yaml.py`) with an enhanced VAX-side YAML parser that can directly parse the original `resume.yaml` file.

## Current Architecture

**Today's workflow:**

```
resume.yaml (190 lines, full YAML)
    ↓ Python: vax_yaml.py
resume.vax.yaml (simplified subset)
    ↓ VAX: bradman.c (200 lines)
brad.1 (roff output)
```

**Python preprocessing (`vax_yaml.py`) does:**
- Flattens multi-line strings to single lines
- Converts all strings to double-quoted format
- Simplifies nested structures (`basics.profiles[]` → `contact.linkedin`)
- Limits data size (max 6 jobs, 2 highlights, etc.)
- Adds schema version and build date

**C parser (`bradman.c`) handles:**
- Double-quoted strings only (escapes: `\"`, `\\`, `\n`)
- Fixed indentation levels (0, 2, 4, 6 spaces)
- Hardcoded structure (knows about work, skills, contact)
- Comments (`#`)

## Proposed Enhancement

**Enhanced workflow:**

```
resume.yaml (190 lines, original format)
    ↓ VAX: enhanced bradman.c (~285 lines)
brad.1 (roff output)
```

**Benefits:**
- Eliminates Python preprocessing step
- Parses original YAML directly
- Demonstrates more sophisticated C parsing
- Reduces overall system complexity
- Makes VAX stage truly independent

## What Needs to Be Added

### Feature 1: Bare String Parsing ⭐ (Priority: HIGH)

**Current requirement:**
```yaml
name: "Bradley Fidler"    # Must be quoted
```

**Original format:**
```yaml
name: Bradley Fidler      # No quotes needed
```

**Implementation:**
- Detect unquoted text after `:`
- Read until end of line or `#` comment
- Trim trailing whitespace
- ~20 lines of code

**Impact:** Handles 80% of fields in `resume.yaml`

---

### Feature 2: Multi-line String Support ⭐⭐ (Priority: HIGH)

**Current requirement:**
```yaml
summary: "Long text all on one line with spaces instead of newlines."
```

**Original format:**
```yaml
summary: Senior Technical Writer specializing in API documentation and docs-as-code.
  I lead documentation strategy, content development, and docs platform.
  I build OpenAPI and prose workflows that accelerate releases, enable SME contributions,
  and prepare documentation for AI applications.
```

**Implementation:**
- Detect when next line has more indentation than key
- Accumulate continuation lines
- Join with spaces (YAML folded style)
- Stop when indent returns to key level or less
- ~40 lines of code

**Impact:** Handles `summary`, long `highlights`, job descriptions

---

### Feature 3: Single-Quoted Strings ⭐ (Priority: MEDIUM)

**Current requirement:**
```yaml
startDate: "2023-10-01"   # Double quotes
```

**Original format:**
```yaml
startDate: '2023-10-01'   # Single quotes
```

**Implementation:**
- Similar to double-quoted parsing
- Only escape is `''` (two single quotes) → `'` (literal single quote)
- No other escapes in YAML single-quoted strings
- ~15 lines of code

**Impact:** Handles dates and strings with special characters

---

### Feature 4: Inline List Syntax ⭐ (Priority: LOW)

**Current requirement:**
```yaml
work:
  -                        # Dash alone
    company: "DomainTools"
```

**Original format:**
```yaml
work:
- name: DomainTools       # Dash + key/value
  position: Senior Technical Writer
```

**Implementation:**
- Parse key/value on same line as `-` marker
- Already partially supported
- ~10 lines of code

**Impact:** Cleaner list syntax

---

## Implementation Complexity

| Component | Lines of Code | Difficulty | Time Estimate |
|-----------|---------------|------------|---------------|
| Current parser | ~200 | ✅ Done | - |
| + Bare strings | +20 | ⭐ Easy | 2-3 hours |
| + Multi-line | +40 | ⭐⭐ Medium | 4-6 hours |
| + Single quotes | +15 | ⭐ Easy | 1-2 hours |
| + Inline lists | +10 | ⭐ Easy | 1 hour |
| **Total Enhanced** | **~285** | **⭐⭐ Medium** | **8-12 hours** |

For comparison:
- Full YAML 1.2 parser: 5000+ lines, ⭐⭐⭐⭐⭐ Expert, months of work
- Full JSON parser: ~500 lines, ⭐⭐⭐ Hard, 2-3 weeks

## JSON vs YAML Analysis

### Why Not Switch to JSON?

**JSON Approach:**
```
resume.yaml → (convert) → resume.json → VAX JSON parser (500 lines)
```

**Problems:**
1. Still need conversion (defeats the purpose)
2. More code to write (~500 vs ~285 lines)
3. JSON is more verbose (more quotes, no multi-line)
4. No comments support
5. Less human-readable

**YAML Approach:**
```
resume.yaml → VAX enhanced YAML parser (285 lines)
```

**Advantages:**
1. No conversion needed
2. Build on existing parser
3. More readable format
4. Multi-line strings are natural
5. Less total code

**Verdict:** YAML enhancement is the better path

See `vax/examples/minimal_json_parser.c` for a skeleton showing JSON parser complexity.

## Features We're NOT Adding (and why)

The original `resume.yaml` uses a **reasonable YAML subset**. We don't need:

- ❌ **Block scalars** (`|` and `>` indicators) - Not used in resume.yaml
- ❌ **Flow collections** (`{key: value}`, `[item, item]`) - Not used
- ❌ **Anchors/aliases** (`&anchor`, `*alias`) - Not used
- ❌ **Tags** (`!!str`, `!!int`) - Not used
- ❌ **Multiple documents** (`---`) - Single document only
- ❌ **Complex keys** - Simple string keys only

This keeps the parser manageable while handling real-world data.

## Implementation Strategy

### Phase 1: Bare Strings (High Value, Low Risk)
1. Add `parse_bare_string()` function
2. Modify string detection logic
3. Test with simple fields (name, email, location)
4. **Estimated effort:** 2-3 hours

### Phase 2: Multi-line Strings (High Value, Medium Risk)
1. Add line accumulation buffer
2. Track indentation state
3. Join continuation lines
4. Test with summary and highlights
5. **Estimated effort:** 4-6 hours

### Phase 3: Single Quotes (Medium Value, Low Risk)
1. Add `parse_single_quoted()` function
2. Handle `''` escape
3. Test with dates
4. **Estimated effort:** 1-2 hours

### Phase 4: Inline Lists (Low Value, Low Risk)
1. Improve list item parser
2. Test with work entries
3. **Estimated effort:** 1 hour

### Total: 8-12 hours of development

## Testing Strategy

1. **Unit tests** for each new parsing function
2. **Integration test** with full `resume.yaml`
3. **Regression test** against current `resume.vax.yaml` (should still work)
4. **VAX BSD test** in SIMH environment
5. **Pre-ANSI C compatibility** test (ensure K&R style works)

## Migration Path

The enhancement can be **incremental and backward compatible**:

### Option A: Gradual Migration
1. Keep `vax_yaml.py` for now
2. Add new parsing features to `bradman.c`
3. Test with both simplified and original YAML
4. Once stable, make original YAML the default
5. Remove Python preprocessing

### Option B: Parallel Implementation
1. Create `bradman_enhanced.c` alongside `bradman.c`
2. Develop and test independently
3. Once stable, replace `bradman.c`
4. Remove Python preprocessing

### Recommendation: Option A (Gradual)
- Lower risk
- Can test both paths
- Easy rollback if issues found

## Example Code Snippets

### Bare String Parser

```c
/* Parse unquoted YAML scalar (bare string) */
static char *parse_bare_string(const char *s) {
    const char *start = s;
    const char *end = s;
    BRADMAN_SIZE_T len;
    char *result;

    /* Read until end of line or comment */
    while (*end && *end != '\n' && *end != '\r' && *end != '#') {
        end++;
    }

    /* Trim trailing whitespace */
    while (end > start && isspace((unsigned char)*(end - 1))) {
        end--;
    }

    /* Allocate and copy */
    len = (BRADMAN_SIZE_T)(end - start);
    result = (char *)malloc(len + 1);
    if (!result) die("out of memory");
    memcpy(result, start, len);
    result[len] = '\0';
    return result;
}
```

### Multi-line String Accumulator

```c
/* Accumulate continuation lines for multi-line strings */
static char *accumulate_multiline(FILE *in, int base_indent) {
    char buf[4096];
    char *result = NULL;
    BRADMAN_SIZE_T cap = 0;
    BRADMAN_SIZE_T len = 0;
    long start_pos = ftell(in);

    while (fgets(buf, sizeof(buf), in)) {
        int indent = count_indent(buf);
        const char *line = buf + indent;

        /* Stop if dedented or at same level */
        if (indent <= base_indent) {
            fseek(in, start_pos, SEEK_SET);  /* Rewind */
            break;
        }

        /* Append line to result with space separator */
        BRADMAN_SIZE_T line_len = strlen(line);
        if (len + line_len + 2 > cap) {
            cap = (cap == 0) ? 256 : (cap * 2);
            result = (char *)xrealloc(result, cap);
        }
        if (len > 0) result[len++] = ' ';  /* Add space between lines */
        memcpy(result + len, line, line_len);
        len += line_len;

        start_pos = ftell(in);
    }

    if (result) result[len] = '\0';
    return result;
}
```

See `vax/examples/yaml_parser_analysis.md` for full feature breakdown.

## Learning Value

This enhancement is an excellent learning project for:

- **String parsing** - Multiple formats, escape handling
- **State machines** - Tracking context through file
- **Memory management** - Dynamic allocation, buffer growth
- **C compatibility** - Pre-ANSI K&R style, portability
- **Legacy systems** - Working within VAX BSD constraints
- **Parser design** - Trade-offs between generality and simplicity

The ~85 lines of new code touch fundamental CS concepts while staying practical.

## Conclusion

**Should we enhance the VAX YAML parser?**

**YES, if:**
- ✅ Want to eliminate Python preprocessing
- ✅ Interested in parser development as learning exercise
- ✅ Want more authentic VAX-side processing
- ✅ Have 8-12 hours for implementation

**NO, if:**
- ❌ Current system works well and there's no need to change
- ❌ Python preprocessing is fast and simple
- ❌ Don't want to maintain more C code
- ❌ Parser complexity isn't worth the benefit

**Current recommendation:** The Python preprocessing approach is pragmatic and works well. The enhancement would be a great learning project and demo of C parsing skills, but isn't required for functionality.

## References

- `vax/bradman.c` - Current parser implementation (~200 lines)
- `resume_generator/vax_yaml.py` - Current Python preprocessing
- `vax/examples/yaml_parser_analysis.md` - Detailed feature analysis
- `vax/examples/parsing_examples.txt` - Side-by-side comparisons
- `vax/examples/minimal_json_parser.c` - JSON parser complexity demo

## Next Steps

1. Review this proposal
2. Decide on implementation (gradual vs parallel)
3. Create feature branch if proceeding
4. Implement Phase 1 (bare strings)
5. Test in SIMH environment
6. Iterate through remaining phases

# Can We Implement a Full YAML Parser in C for VAX?

## TL;DR

**YES, technically possible.**
**NO, probably not practical.**

A full YAML 1.2 parser is 10,000-20,000 lines of C code, requires significant memory, and would be challenging to port to pre-ANSI C on VAX BSD. But it's been done before (libyaml exists), so it's feasible if you really want to.

---

## What "Full YAML" Means

YAML 1.2 specification includes:

### 1. **Block Scalars** (Literal and Folded)
```yaml
description: |
  This is a literal block.
  Newlines are preserved.
  Indentation matters.

summary: >
  This is a folded block.
  Newlines become spaces.
  Blank lines create paragraphs.
```

### 2. **Flow Collections** (JSON-like)
```yaml
inline_object: {name: Brad, role: Writer}
inline_array: [Python, C, YAML]
nested: {skills: [parsing, memory, state-machines]}
```

### 3. **Anchors and Aliases** (References)
```yaml
defaults: &defaults
  timeout: 30
  retries: 3

production:
  <<: *defaults        # Merge defaults
  timeout: 60          # Override

staging:
  <<: *defaults        # Reuse same defaults
```

### 4. **Tags** (Type Annotations)
```yaml
date: !!timestamp 2024-01-01
number: !!int 42
binary: !!binary R0lGODlhDAAMAIQAAP//9/X17unp5WZmZgAAAOfn515eXvPz7Y6OjuDg4J+fn5OTk6enp56enmleECcgggoBADs=
```

### 5. **Multiple Documents**
```yaml
---
document: 1
---
document: 2
---
document: 3
```

### 6. **Complex Keys**
```yaml
? [Blue, Green]
: RGB values
? {name: John, age: 30}
: Person object
```

### 7. **Directives**
```yaml
%YAML 1.2
%TAG ! tag:example.com,2024:
---
content: here
```

### 8. **Character Encodings**
- UTF-8, UTF-16, UTF-32
- Byte order marks (BOM)
- Unicode escapes (\uXXXX, \UXXXXXXXX)

### 9. **Escape Sequences** (Complete Set)
```yaml
escaped: "null: \0, bell: \a, backspace: \b, tab: \t, newline: \n,
vertical-tab: \v, form-feed: \f, carriage-return: \r, escape: \e,
space: \_, next-line: \N, non-breaking-space: \_, line-sep: \L,
paragraph-sep: \P, unicode: \u263A, wide-unicode: \U0001F600"
```

### 10. **Indentation Detection**
```yaml
# YAML doesn't require fixed indentation - parser must detect it
auto:
  detect:
    any:
      level: of
        nesting: works
```

---

## Existing Full YAML Parsers in C

### libyaml (Reference Implementation)

**Stats:**
- **Lines of code:** ~10,000-12,000 (core parser)
- **Memory usage:** Dynamic (allocates heavily)
- **Dependencies:** stdlib, string.h, assert.h
- **C standard:** C89/C90 (ANSI C)
- **Platforms:** POSIX, Windows, embedded systems

**Files:**
```
yaml_parser.c      ~3500 lines   # Main parser state machine
yaml_scanner.c     ~2800 lines   # Tokenization/lexing
yaml_emitter.c     ~2000 lines   # Writing YAML
yaml_reader.c      ~400 lines    # Input handling
yaml_writer.c      ~200 lines    # Output handling
yaml.h             ~1800 lines   # API definitions
```

**Data structures:**
- Token queue (dynamic array)
- Event queue (dynamic array)
- Stack for indentation tracking
- Tag directives table
- Anchor map (hash table)
- Node graph representation

**Would it run on VAX?**
- ✅ Written in ANSI C (mostly)
- ⚠️ Uses some C99 features (could be ported back to K&R)
- ⚠️ Requires significant memory (MB scale for large documents)
- ⚠️ Uses dynamic allocation heavily
- ❌ Would need build system adaptation (no CMake on VAX BSD)

---

## What Would VAX-Compatible Full YAML Parser Require?

### Memory Requirements

**Minimum:**
- Parser state: ~50 KB
- Token buffer: ~100 KB
- Output buffer: ~100 KB
- Stack space: ~50 KB
- **Total: ~300 KB minimum**

**For resume.yaml (190 lines):**
- Input: ~10 KB
- Parsed structure: ~50 KB
- Working memory: ~200 KB
- **Total: ~260 KB**

**VAX-11/780 (1977):**
- Address space: 4 GB virtual (4 MB typical physical)
- User space: ~2 MB available
- **Verdict: ✅ Plenty of memory**

### Compiler Compatibility

**Challenges:**
```c
/* Modern C (C99+) */
typedef enum {
    TOKEN_STREAM_START,
    TOKEN_STREAM_END,
    // ... 20 more
} yaml_token_type_t;

struct yaml_parser_s {
    size_t buffer_pos;
    bool eof;
    // ... many fields
};

/* Pre-ANSI C (K&R) for VAX BSD 4.3 */
#define TOKEN_STREAM_START 0
#define TOKEN_STREAM_END 1
/* ... manually number 20 enums */

struct yaml_parser_s {
    BRADMAN_SIZE_T buffer_pos;
    int eof;  /* bool doesn't exist */
    /* ... many fields */
};
```

**Required changes for VAX BSD:**
- Replace `enum` with `#define` constants
- Replace `bool` with `int`
- Replace `size_t` with `unsigned int`
- K&R function declarations
- Remove `//` comments (use `/* */`)
- Remove `inline` keyword
- Manual function prototypes

**Estimated porting effort: 20-40 hours**

### Dependencies

**Standard C library functions needed:**
- `malloc()`, `realloc()`, `free()` ✅ Available
- `memcpy()`, `memset()`, `memmove()` ✅ Available
- `strlen()`, `strcmp()`, `strncmp()` ✅ Available
- `fprintf()`, `vfprintf()` ✅ Available
- `fopen()`, `fread()`, `fclose()` ✅ Available
- `assert()` ⚠️ Available but may want to remove for production

**Would need to implement:**
- Hash table for anchors (not in standard C library)
- Dynamic array (growable buffer)
- Unicode handling (minimal in 1980s C)

---

## Implementation Complexity Breakdown

### Phase 1: Tokenizer/Scanner (~3000 lines)
```
Input: Raw YAML text
Output: Token stream (KEY, VALUE, BLOCK_START, FLOW_START, etc.)

Tasks:
- Character-by-character scanning
- Indentation tracking (critical for YAML!)
- Quote handling (single, double, none)
- Escape sequence processing
- Flow vs block context switching
- Comment stripping
- Line folding for multi-line strings
```

**Complexity: ⭐⭐⭐⭐ Very Hard**
- Must handle ambiguous syntax
- Complex state machine (20+ states)
- Look-ahead required for some tokens

### Phase 2: Parser (~3500 lines)
```
Input: Token stream
Output: Event stream (DOCUMENT_START, MAPPING_START, SCALAR, etc.)

Tasks:
- Convert flat tokens to hierarchical events
- Indentation-based structure detection
- Implicit key/value detection
- Block vs flow collection parsing
- Anchor registration
- Tag resolution
```

**Complexity: ⭐⭐⭐⭐⭐ Expert**
- Most complex part of YAML
- Must resolve indentation ambiguities
- Handle implicit typing
- Manage parser stack

### Phase 3: Composer/Constructor (~2000 lines)
```
Input: Event stream
Output: In-memory representation (tree/graph)

Tasks:
- Build node graph from events
- Resolve aliases (anchor references)
- Apply tag schemas
- Construct native types (int, float, string, etc.)
- Detect cycles in anchor graphs
```

**Complexity: ⭐⭐⭐ Hard**
- Graph building with circular references
- Memory management

### Phase 4: Utilities (~1500 lines)
```
- String handling
- Buffer management
- Error reporting
- Memory allocation wrappers
- Stack implementation
- Queue implementation
```

**Complexity: ⭐⭐ Medium**

---

## Comparison Table

| Parser Type | Lines | Memory | Complexity | VAX Port Time | Value for Resume |
|-------------|-------|--------|------------|---------------|------------------|
| **Current VAX-YAML** | 200 | 50 KB | ⭐ Easy | ✅ Done | ✅✅✅ Perfect |
| **Enhanced VAX-YAML** | 285 | 75 KB | ⭐⭐ Medium | 8-12 hrs | ✅✅✅ Perfect |
| **Minimal YAML** | 1500 | 150 KB | ⭐⭐⭐ Hard | 2-3 weeks | ✅✅ Good |
| **Full YAML 1.2** | 10000 | 300 KB | ⭐⭐⭐⭐⭐ Expert | 2-3 months | ✅ Overkill |
| **libyaml (port)** | 12000 | 500 KB | ⭐⭐⭐⭐ Very Hard | 1-2 months | ✅ Overkill |

---

## What Would "Minimal Full YAML" Look Like?

If you wanted **most** YAML features but not everything:

### Include:
- ✅ Block scalars (`|` and `>`)
- ✅ Flow collections (`{key: value}`, `[item]`)
- ✅ Anchors and aliases (`&anchor`, `*alias`)
- ✅ Multi-line strings (already proposed)
- ✅ All three quote styles (bare, single, double)
- ✅ Basic tags (`!!str`, `!!int`, `!!float`, `!!null`, `!!bool`)

### Exclude:
- ❌ Complex keys (who uses `? {key: object}` anyway?)
- ❌ Multiple documents (resume is single document)
- ❌ Directives (`%YAML`, `%TAG`)
- ❌ Advanced Unicode (stick to ASCII/UTF-8 basics)
- ❌ Full tag schema system
- ❌ Explicit typing in all contexts

**Result:** ~1,500-2,000 lines of C code

**Complexity:** ⭐⭐⭐ Hard (but doable)

**Time:** 2-3 weeks of focused development

**Memory:** ~150 KB

**Would it run on VAX?** ✅ YES, comfortably

---

## Real-World Example: Porting libyaml to VAX BSD

### Step-by-step process:

#### 1. **Download libyaml** (12,000 lines)
```sh
# On modern system:
git clone https://github.com/yaml/libyaml.git
tar czf libyaml.tar.gz libyaml/
# Transfer to VAX via tape or FTP
```

#### 2. **Convert C99/C11 to K&R C** (20-30 hours)
```c
/* Original: */
bool yaml_parser_scan(yaml_parser_t *parser) {
    // modern syntax
}

/* Converted: */
int yaml_parser_scan(parser)
    yaml_parser_t *parser;
{
    /* K&R style */
}
```

**Changes needed:**
- 500+ function declarations to convert
- Replace `bool` → `int` (100+ occurrences)
- Replace `//` comments → `/* */` (1000+ occurrences)
- Replace designated initializers (100+ occurrences)
- Remove inline functions (50+ occurrences)

#### 3. **Adapt Build System** (4-8 hours)
```sh
# libyaml uses CMake (not available on VAX)
# Write simple Makefile:

CFLAGS = -O -DYAML_DECLARE_STATIC
OBJS = yaml_parser.o yaml_scanner.o yaml_reader.o yaml_emitter.o

libyaml.a: $(OBJS)
    ar rcs libyaml.a $(OBJS)

yaml_parser.o: src/yaml_parser.c include/yaml.h
    cc $(CFLAGS) -c src/yaml_parser.c
```

#### 4. **Handle Platform Differences** (8-12 hours)
```c
/* Modern libyaml assumes: */
#include <stdint.h>
#include <stdbool.h>

/* VAX BSD 4.3 doesn't have these */
typedef unsigned char uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int uint32_t;
#define bool int
#define true 1
#define false 0
```

#### 5. **Test and Debug** (20-40 hours)
- Port test suite or write minimal tests
- Debug memory issues (VAX debuggers are primitive)
- Handle alignment issues (VAX is little-endian, 32-bit)

**Total porting time: 50-90 hours (1-2 months)**

---

## Should You Do This?

### ✅ YES, if you want to:
- Learn YAML internals deeply
- Demonstrate serious C parsing skills
- Have a portable, standalone YAML parser
- Handle arbitrary YAML documents (not just resumes)
- Create reusable library for other VAX projects
- Academic exercise in legacy system porting

### ❌ NO, if:
- You only need to parse `resume.yaml` (overkill by 100x)
- Time is limited (months of work)
- Current solution works fine
- Not interested in maintaining 10,000 lines of C
- VAX system has limited resources
- Other projects have higher priority

---

## Alternative: Hybrid Approach

**What if you wanted YAML anchors/aliases for resume?**

```yaml
# resume.yaml with anchors
skills-common: &py-skills
  - Python
  - pytest
  - Git

work:
- company: DomainTools
  skills: *py-skills      # Reference common skills
- company: JPMorgan
  skills: *py-skills      # Reuse same list
```

**Implementation:**
1. Add anchor tracking (~100 lines)
2. Add alias resolution (~50 lines)
3. Keep everything else simple

**Total: ~350 lines** (current 285 + 65)

**Complexity:** ⭐⭐ Medium

**Time:** 4-6 hours

**Benefit:** Get most useful YAML feature without full parser

---

## Conclusion

### Q: Can we implement a full YAML parser in C for VAX?
**A: YES, technically possible. It's been done (libyaml exists).**

### Q: How much work?
**A: 10,000-12,000 lines of C, 1-3 months of development, 50-90 hours to port libyaml.**

### Q: Would it run on VAX?
**A: YES, with K&R C adaptations. VAX has enough memory (need ~300 KB).**

### Q: Should we do it?
**A: Probably NO. Your resume.yaml needs ~285 lines (enhanced parser) or 350 lines (with anchors). Full YAML is 30x overkill.**

### Q: What's the sweet spot?
**A: Enhanced parser (285 lines) handles your resume perfectly. Add anchors/aliases if needed (350 lines). Stop there.**

---

## Decision Matrix

| Use Case | Recommended Parser | Lines | Time |
|----------|-------------------|-------|------|
| Resume only | Enhanced YAML | 285 | 8-12 hours |
| Resume + reuse | + Anchors | 350 | 16-20 hours |
| General YAML | Minimal YAML | 1500 | 2-3 weeks |
| Full spec | Port libyaml | 12000 | 1-3 months |

**Recommendation for your project: Enhanced YAML (285 lines)**

---

## References

- YAML 1.2 Specification: https://yaml.org/spec/1.2/spec.html
- libyaml: https://github.com/yaml/libyaml (~12,000 lines)
- PyYAML C extension: ~8,000 lines
- yaml-cpp: ~15,000 lines C++
- tinyyaml: ~600 lines (very limited subset)

---

## Next Steps

If you decide to explore this:

1. **Enhanced parser** (recommended): See `../docs/vax-yaml-parser-enhancement.md`
2. **With anchors**: Add ~65 lines to enhanced parser
3. **Minimal YAML**: Start from enhanced, add flow collections and block scalars
4. **Full YAML**: Port libyaml (multi-month project)

Want me to show you how to add anchor/alias support to the enhanced parser? That would be the next logical step after the 285-line version.

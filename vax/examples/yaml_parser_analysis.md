# YAML Parser Analysis: Original resume.yaml → VAX Parser

## Current Features vs Needed Features

### What the VAX Parser CURRENTLY Handles ✅

1. **Double-quoted strings only**
   ```yaml
   name: "Bradley Fidler"
   ```

2. **Fixed indentation levels** (0, 2, 4, 6 spaces)
   ```yaml
   work:
     - company: "Test"
       highlights:
         - "Did thing"
   ```

3. **Minimal escapes** (`\"`, `\\`, `\n`)

4. **Hardcoded structure** (knows about work, skills, contact fields)

---

## What Your Original resume.yaml Uses

### Feature 1: **Bare (Unquoted) Strings** ⭐ EASY to add
```yaml
basics:
  name: Bradley Fidler          # ← No quotes!
  email: brfid@icloud.com       # ← No quotes!
```

**Complexity:** LOW
- Stop reading at `:` or newline
- Trim whitespace
- ~20 lines of code

---

### Feature 2: **Single-Quoted Strings** ⭐ EASY to add
```yaml
startDate: '2023-10-01'         # ← Single quotes
```

**Complexity:** LOW
- Same as double-quoted but different delimiter
- No escape sequences in YAML single-quotes (just `''` for literal `'`)
- ~15 lines of code

---

### Feature 3: **Multi-line Strings** ⭐⭐ MEDIUM
```yaml
summary: Senior Technical Writer specializing in API documentation and docs-as-code.
  I lead documentation strategy, content development, and docs platform.
  I build OpenAPI and prose workflows that accelerate releases, enable SME contributions,
  and prepare documentation for AI applications.
```

**Complexity:** MEDIUM
- Need to detect when next line has MORE indent than key
- Join lines with spaces
- Stop when indent returns to key level or less
- ~40 lines of code

---

### Feature 4: **List Items with Inline Values** ⭐ EASY
```yaml
work:
- name: DomainTools              # ← Dash and key/value on same line
  position: Senior Technical Writer
```

vs current requirement:
```yaml
work:
  -                              # ← Dash alone
    name: "DomainTools"
```

**Complexity:** LOW
- Already partially supported!
- Just parse rest of line after `-` as key-value
- ~10 lines of code (already there, just needs enabling)

---

### Feature 5: **Comments** ✅ ALREADY SUPPORTED
```yaml
# This is a comment
name: Bradley Fidler
```

The parser already handles `#` comments (line 338 in bradman.c)

---

## Parser Complexity Comparison

| Parser Type | Lines of Code | Handles Resume | Difficulty |
|-------------|---------------|----------------|------------|
| **Current VAX-YAML** | ~200 | ✅ (simplified) | ✅ Done |
| **Enhanced VAX-YAML** | ~300 | ✅ (original) | ⭐⭐ Medium |
| **Full YAML 1.2** | 5000+ | ✅✅✅ (all YAML) | ⭐⭐⭐⭐⭐ Expert |
| **Minimal JSON** | ~500 | ✅ (need JSON input) | ⭐⭐⭐ Hard |
| **Full JSON** | ~1500 | ✅ (need JSON input) | ⭐⭐⭐⭐ Very Hard |

---

## Recommendation: Enhanced YAML Parser

**YES, you can definitely write a YAML parser that handles your original resume.yaml!**

### Advantages of YAML over JSON for this use case:

1. **Your source is already YAML** ✅
2. **YAML is more human-readable** (no quotes everywhere)
3. **Multi-line strings are easier** in YAML
4. **Simpler syntax** for lists and objects
5. **Already have working parser** to build on

### What to Add (Priority Order):

1. **Bare string parsing** (20 lines) → Handles 80% of your file
2. **Multi-line string support** (40 lines) → Handles `summary`, `highlights`
3. **Single-quote support** (15 lines) → Handles dates like `'2023-10-01'`
4. **Flexible list syntax** (10 lines) → Handles `- name: value` pattern

**Total additional code: ~85 lines**

---

## Code Architecture: State-Machine Parser

The current parser is a **state machine** that tracks:
- Current indent level
- Current top-level section (work, skills, contact)
- Current nested context (inside highlights, inside keywords)

To enhance it, you'd add:
- String type detection (bare, single, double)
- Multi-line accumulator
- More flexible state transitions

This is **much simpler** than a recursive descent parser (needed for JSON).

---

## Example: Adding Bare String Support

```c
/* Current code only handles double-quoted strings */
if (*rest != '"') die("expected quoted scalar for key '%s'", key);
val = parse_quoted(rest);

/* Enhanced version handles bare strings too */
if (*rest == '"') {
    val = parse_double_quoted(rest);
} else if (*rest == '\'') {
    val = parse_single_quoted(rest);
} else if (*rest != '\0') {
    val = parse_bare_string(rest);  /* NEW! */
} else {
    val = NULL;  /* No value */
}
```

```c
/* NEW FUNCTION: Parse bare string */
static char *parse_bare_string(const char *s) {
    const char *start = s;
    const char *end = s;

    /* Read until end of line, trimming trailing whitespace */
    while (*end && *end != '\n' && *end != '\r' && *end != '#') {
        end++;
    }

    /* Trim trailing whitespace */
    while (end > start && isspace((unsigned char)*(end - 1))) {
        end--;
    }

    /* Copy the string */
    size_t len = end - start;
    char *result = malloc(len + 1);
    if (!result) die("out of memory");
    memcpy(result, start, len);
    result[len] = '\0';
    return result;
}
```

That's literally it for bare strings! Add similar simple functions for the other features.

---

## Bottom Line

**Q: Can you write a YAML parser for VAX that handles resume.yaml?**
**A: YES! Add ~85 lines to the existing parser.**

**Q: Should you write a JSON parser instead?**
**A: NO. More work (500+ lines), and you'd need to convert YAML→JSON first.**

**Q: Is this a good learning project?**
**A: YES! Excellent way to learn:**
- String parsing
- State machines
- C memory management
- Working with legacy systems
- Practical compiler/parser techniques

Want me to show you how to implement one of these features step by step?

# Practical YAML Parser for VAX

## Goal
A parser that handles your `resume.yaml` plus common YAML features you'd find in config files, CI/CD, Docker Compose, etc. Not the full YAML 1.2 spec - just the practical subset people actually use.

---

## What Your Resume Uses (Priority 1)

### ✅ Already Supported
- Double-quoted strings: `"value"`
- Comments: `# comment`
- Fixed indentation: 2-space indent
- Lists: `- item`
- Mappings: `key: value`

### 📝 Need to Add (from enhancement proposal)
- **Bare strings**: `name: Bradley Fidler` (~20 lines)
- **Multi-line strings**: Text spanning multiple lines (~40 lines)
- **Single quotes**: `'2023-10-01'` (~15 lines)
- **Inline list syntax**: `- name: Value` (~10 lines)

**Subtotal: ~85 lines → 285 lines total**

---

## Common Features Beyond Your Resume (Priority 2)

### 1. Block Scalars (`|` and `>`) ⭐⭐
Used in: Docker Compose, Kubernetes, GitHub Actions

```yaml
# Literal block (preserves newlines)
script: |
  #!/bin/bash
  echo "Line 1"
  echo "Line 2"

# Folded block (joins lines)
description: >
  This is a long description
  that will be folded into
  a single line with spaces.
```

**Use cases:**
- Shell scripts in CI/CD
- Multi-line descriptions
- Embedded configs

**Implementation complexity:** ⭐⭐⭐ Medium
- Detect `|` or `>` after key
- Track indentation level
- Collect lines until dedent
- Join appropriately (preserve vs fold)

**Code estimate:** ~120 lines

---

### 2. Flow Collections (`{}` and `[]`) ⭐⭐⭐
Used in: Almost every YAML file

```yaml
# Inline object
container: {image: nginx, port: 80}

# Inline array
tags: [python, yaml, parser]

# Mixed
ports: [{container: 80, host: 8080}, {container: 443, host: 8443}]
```

**Use cases:**
- Short lists (tags, keywords)
- Single-line configs
- Compact notation

**Implementation complexity:** ⭐⭐⭐ Medium-Hard
- Lexer needs to track `{`, `}`, `[`, `]`, `,`
- Parse recursively
- Handle nested flow collections
- Switch between flow and block modes

**Code estimate:** ~200 lines

---

### 3. Anchors & Aliases (`&anchor`, `*alias`) ⭐⭐
Used in: Docker Compose, Kubernetes, Ansible

```yaml
# Define anchor
defaults: &defaults
  timeout: 30
  retries: 3
  log_level: info

# Reference it multiple times
production:
  <<: *defaults          # Merge operator
  timeout: 60            # Override one field

staging:
  <<: *defaults

development:
  timeout: 5
  retries: 1
  log_level: debug
```

**Use cases:**
- DRY (Don't Repeat Yourself)
- Shared configuration blocks
- Template inheritance

**Implementation complexity:** ⭐⭐⭐ Medium-Hard
- Track anchors in hash table
- Store node references
- Resolve aliases during construction
- Handle merge operator `<<:`
- Detect circular references

**Code estimate:** ~150 lines

---

### 4. Basic Type Inference ⭐
Common values need no quotes:

```yaml
enabled: true
port: 8080
timeout: 3.14
value: null
name: simple_string
```

**Use cases:**
- Booleans: `true`, `false`, `yes`, `no`, `on`, `off`
- Numbers: `42`, `-3`, `3.14`, `1e10`
- Null: `null`, `~`
- Strings: Everything else

**Implementation complexity:** ⭐ Easy
- Parse bare string
- Try to interpret as bool/number/null
- Fall back to string

**Code estimate:** ~40 lines

---

## Priority 3 Features (Nice to Have)

### 5. Empty Values
```yaml
key:              # Empty/null value
key: ~            # Explicit null
list:
  -               # Empty list item
```

**Code estimate:** ~20 lines

### 6. Quoted Key Support
```yaml
"key with spaces": value
'another:key': value
```

**Code estimate:** ~15 lines

---

## What We're NOT Adding (Even for Practical)

❌ **Multiple documents** (`---`) - Single document is fine
❌ **Complex keys** (`? complex: key`) - Almost never used
❌ **Tags** (`!!str`, `!!int`) - Type inference is enough
❌ **Directives** (`%YAML 1.2`) - Not needed
❌ **Full Unicode escapes** - ASCII/UTF-8 basics are fine
❌ **Explicit typing** everywhere - Implicit is enough

---

## Practical Parser Size Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| **Current parser** | 200 | ✅ Done |
| + Bare strings | 20 | ⭐ Easy |
| + Multi-line folding | 40 | ⭐⭐ Medium |
| + Single quotes | 15 | ⭐ Easy |
| + Inline lists | 10 | ⭐ Easy |
| + Block scalars (`\|`, `>`) | 120 | ⭐⭐⭐ Medium |
| + Flow collections (`{}`, `[]`) | 200 | ⭐⭐⭐ Hard |
| + Anchors/aliases | 150 | ⭐⭐⭐ Hard |
| + Type inference | 40 | ⭐ Easy |
| + Empty values | 20 | ⭐ Easy |
| + Quoted keys | 15 | ⭐ Easy |
| **Total Practical Parser** | **830** | **⭐⭐⭐ Hard** |

---

## Phased Implementation Plan

### Phase 1: Resume Coverage (285 lines, 8-12 hours)
✅ Handles your resume.yaml completely
- Bare strings
- Multi-line strings
- Single quotes
- Inline list syntax

**Value:** Parse original resume.yaml directly

---

### Phase 2: Common Config Features (515 lines, +16-20 hours)
✅ Handles Docker Compose, CI/CD configs
- Block scalars (`|` and `>`)
- Flow collections (`{}`, `[]`)
- Type inference (bool, int, float, null)

**Value:** Parse most common YAML files

---

### Phase 3: Advanced Features (830 lines, +24-30 hours)
✅ Handles complex configs with reuse
- Anchors and aliases
- Merge operator (`<<:`)
- Empty values
- Quoted keys

**Value:** Parse Kubernetes, Ansible, advanced configs

---

## Example: Docker Compose Coverage

Here's what you could parse after each phase:

### Current (200 lines) ❌
```yaml
# Requires Python preprocessing
version: "3.8"
services:
  web:
    image: "nginx:latest"
    ports:
      - "80:80"
```

### Phase 1 (285 lines) ⚠️ Partial
```yaml
version: 3.8              # ✅ Bare string
services:
  web:
    image: nginx:latest   # ✅ Bare string
    ports:
      - 80:80             # ❌ Flow syntax not supported
```

### Phase 2 (515 lines) ✅ Most features
```yaml
version: 3.8
services:
  web:
    image: nginx:latest
    ports: [80:80]        # ✅ Flow syntax
    environment:
      - DEBUG=true        # ✅ Type inference
    command: |            # ✅ Block scalar
      echo "Starting"
      nginx -g "daemon off;"
```

### Phase 3 (830 lines) ✅✅ Everything
```yaml
x-defaults: &defaults     # ✅ Anchor
  restart: always
  networks: [backend]     # ✅ Flow array

services:
  web:
    <<: *defaults         # ✅ Merge
    image: nginx:latest
    ports: [{host: 80, container: 80}]  # ✅ Flow object

  api:
    <<: *defaults         # ✅ Reuse
    image: node:18
    environment:
      DEBUG: true         # ✅ Bare bool
      PORT: 3000          # ✅ Bare number
```

---

## Coverage Comparison

| YAML File Type | Phase 1 | Phase 2 | Phase 3 |
|----------------|---------|---------|---------|
| **Your resume.yaml** | ✅ 100% | ✅ 100% | ✅ 100% |
| **GitHub Actions** | ⚠️ 60% | ✅ 95% | ✅ 100% |
| **Docker Compose** | ⚠️ 50% | ✅ 90% | ✅ 100% |
| **Kubernetes** | ❌ 30% | ⚠️ 70% | ✅ 95% |
| **Ansible** | ❌ 40% | ⚠️ 75% | ✅ 95% |
| **Basic config** | ✅ 90% | ✅ 100% | ✅ 100% |

---

## Memory Requirements

| Phase | Memory | Why |
|-------|--------|-----|
| Phase 1 | 75 KB | Basic parsing, no complex structures |
| Phase 2 | 150 KB | Flow collections need more buffering |
| Phase 3 | 250 KB | Anchor table + node graph |

**VAX Memory:** 2+ MB available → ✅ All phases fit easily

---

## Recommendation: Build Phase by Phase

### Start with Phase 1 (285 lines)
- ✅ Solves your immediate need (parse resume.yaml)
- ✅ Low risk, well-scoped
- ✅ 8-12 hours of work
- ✅ Builds on existing parser
- **Decision point:** Does this solve your problem? If yes, stop here!

### Continue to Phase 2 if needed (515 lines)
- Use case: Parse config files, Docker Compose
- Time: +16-20 hours
- **Decision point:** Do you need flow collections and block scalars? If yes, continue.

### Add Phase 3 if needed (830 lines)
- Use case: Complex configs with lots of reuse (Kubernetes, Ansible)
- Time: +24-30 hours
- **Decision point:** Do you need anchors/aliases? If yes, finish Phase 3.

---

## Practical Parser vs Alternatives

| Approach | Lines | Time | Coverage |
|----------|-------|------|----------|
| **Current + Python** | 200 C + Python | ✅ Done | Resume only |
| **Phase 1 (Enhanced)** | 285 | 8-12 hrs | Resume + simple configs |
| **Phase 2 (Common)** | 515 | 24-32 hrs | Most real-world YAML |
| **Phase 3 (Practical)** | 830 | 48-62 hrs | 95% of YAML in the wild |
| **Full YAML 1.2** | 10000+ | 3+ months | 100% (overkill) |

---

## Code Complexity by Feature

**Easy (⭐):**
- Bare strings
- Single quotes
- Inline lists
- Type inference
- Empty values
- Quoted keys

**Medium (⭐⭐):**
- Multi-line strings
- Block scalars

**Medium-Hard (⭐⭐⭐):**
- Flow collections (recursive parsing)
- Anchors/aliases (hash table, graph)

**Hard (⭐⭐⭐⭐):**
- Nothing in practical parser! (That's the point)

---

## What Would You Use It For?

### With Phase 1 (285 lines):
- ✅ Your resume.yaml
- ✅ Simple config files
- ✅ Basic data files

### With Phase 2 (515 lines):
- ✅ Docker Compose
- ✅ GitHub Actions
- ✅ CI/CD configs
- ✅ Most Python/Node project configs

### With Phase 3 (830 lines):
- ✅ Kubernetes manifests
- ✅ Ansible playbooks
- ✅ Helm charts
- ✅ Complex multi-environment configs

---

## Example Parsing Function

Here's what the interface might look like:

```c
/* Parse YAML from file */
yaml_node_t *yaml_parse_file(FILE *fp, yaml_error_t *error);

/* Sample usage */
FILE *fp = fopen("resume.yaml", "r");
yaml_error_t error;
yaml_node_t *root = yaml_parse_file(fp, &error);

if (!root) {
    fprintf(stderr, "Parse error: %s at line %d\n",
            error.message, error.line);
    return 1;
}

/* Access parsed data */
yaml_node_t *name = yaml_get(root, "basics.name");
printf("Name: %s\n", yaml_as_string(name));

yaml_node_t *work = yaml_get(root, "work");
for (int i = 0; i < yaml_array_length(work); i++) {
    yaml_node_t *job = yaml_array_get(work, i);
    char *company = yaml_as_string(yaml_get(job, "company"));
    printf("Company: %s\n", company);
}

yaml_free(root);
```

---

## Next Steps

**Question for you:** Which phase matches your actual needs?

1. **Just want to parse resume.yaml?** → Phase 1 (285 lines, 8-12 hours)
2. **Want to parse common configs too?** → Phase 2 (515 lines, 24-32 hours)
3. **Want to handle complex YAML?** → Phase 3 (830 lines, 48-62 hours)

I can help implement any of these, starting with Phase 1 (the enhanced parser we already discussed).

**Recommendation:** Start with Phase 1, see if it meets your needs. Add Phase 2 features only if you have a specific use case for them.

---

## Comparison Table (Summary)

| Feature | Current | Phase 1 | Phase 2 | Phase 3 |
|---------|---------|---------|---------|---------|
| Lines of C | 200 | 285 | 515 | 830 |
| Bare strings | ❌ | ✅ | ✅ | ✅ |
| Multi-line | ❌ | ✅ | ✅ | ✅ |
| Single quotes | ❌ | ✅ | ✅ | ✅ |
| Block scalars | ❌ | ❌ | ✅ | ✅ |
| Flow `{}[]` | ❌ | ❌ | ✅ | ✅ |
| Type inference | ❌ | ❌ | ✅ | ✅ |
| Anchors/aliases | ❌ | ❌ | ❌ | ✅ |
| Your resume | ⚠️ | ✅ | ✅ | ✅ |
| Docker Compose | ❌ | ⚠️ | ✅ | ✅ |
| Kubernetes | ❌ | ❌ | ⚠️ | ✅ |
| **Time to build** | Done | 8-12h | 24-32h | 48-62h |

What level of parser would actually be useful for you?

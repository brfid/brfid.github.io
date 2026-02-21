# YAML Enhancement Test Plan

**Date**: 2026-02-13  
**Related**: `docs/YAML-ENHANCEMENT-PLAN.md`  
**Goal**: Validate enhanced VAX C parser handles standard YAML

---

## Test Strategy

### Phase 1: Unit Tests (C Parser Functions)

Test individual parsing functions in isolation.

#### 1.1 Unquoted String Parsing

**Function**: `parse_string_value()`

| Test Case | Input | Expected Output | Notes |
|-----------|-------|-----------------|-------|
| Simple word | `Bradley` | `"Bradley"` | Single word |
| Multiple words | `Bradley Fidler` | `"Bradley Fidler"` | Spaces preserved |
| With colon after | `name: value` | `"value"` | Stop at `:` |
| Trailing spaces | `value   ` | `"value"` | Trim trailing |
| Leading spaces | `  value` | `"value"` | Trim leading |
| Long string | `Senior Technical Writer specializing in...` | Full string | Handle 100+ chars |
| Empty string | `` | `""` | Edge case |

#### 1.2 Quoted String Parsing

**Function**: `parse_quoted_string()` (existing, validate still works)

| Test Case | Input | Expected Output | Notes |
|-----------|-------|-----------------|-------|
| Simple quoted | `"Bradley"` | `"Bradley"` | Existing functionality |
| With escape | `"Hello \"world\""` | `"Hello "world""` | Escaped quotes |
| With backslash | `"path\\to\\file"` | `"path\to\file"` | Escaped backslashes |
| Empty quoted | `""` | `""` | Edge case |

#### 1.3 YAML Special Character Detection

**Function**: `is_yaml_special_char()`

| Character | Expected | Notes |
|-----------|----------|-------|
| `:` | true | Map separator |
| `#` | true | Comment start |
| `[` | true | Flow sequence |
| `]` | true | Flow sequence |
| `{` | true | Flow mapping |
| `}` | true | Flow mapping |
| `,` | true | Flow separator |
| `\n` | true | Line end |
| `-` | false | List marker (context-dependent) |
| `a-z` | false | Regular characters |

---

### Phase 2: Integration Tests (YAML Structures)

Test parsing complete YAML structures.

#### 2.1 Simple Map

**Input YAML**:
```yaml
name: Bradley Fidler
email: brfid@icloud.com
```

**Expected Parse**:
- Map with 2 entries
- Both values unquoted strings
- No errors

#### 2.2 Nested Map

**Input YAML**:
```yaml
basics:
  name: Bradley Fidler
  location:
    city: Warwick
    region: New York
```

**Expected Parse**:
- Top-level map with 1 entry (`basics`)
- Nested map with 2 entries (`name`, `location`)
- Double-nested map with 2 entries (`city`, `region`)
- Indentation correctly handled

#### 2.3 List of Strings

**Input YAML**:
```yaml
skills:
- Python
- C
- YAML
```

**Expected Parse**:
- Map with 1 entry (`skills`)
- List with 3 unquoted string items
- List marker `-` correctly handled

#### 2.4 List of Maps

**Input YAML**:
```yaml
work:
- name: DomainTools
  position: Senior Technical Writer
- name: JPMorgan
  position: Contract Writer
```

**Expected Parse**:
- Map with 1 entry (`work`)
- List with 2 map items
- Each map has 2 entries
- Mixed quoted/unquoted strings

#### 2.5 Mixed Quoted/Unquoted

**Input YAML**:
```yaml
name: Bradley Fidler
label: "Technical Writer: docs platforms"
summary: Senior Technical Writer specializing in API documentation
```

**Expected Parse**:
- `name`: unquoted
- `label`: quoted (contains `:`)
- `summary`: unquoted (long string)

---

### Phase 3: Real-World Test (Actual resume.yaml)

#### 3.1 Full Resume Parsing

**Test**: Parse actual `resume.yaml`

**Validation Steps**:
1. Parse without errors
2. Extract all expected fields
3. Compare field counts with Python PyYAML parse
4. Validate string content matches

**Expected Results**:
```
basics.name: "Bradley Fidler"
basics.email: "brfid@icloud.com"
work[0].name: "DomainTools"
work[0].position: "Senior Technical Writer"
work[0].highlights[0]: "Migrated 120+ documents..."
skills[0].group: "Technical Writing"
skills[0].keywords[0]: "API documentation"
... (all fields present)
```

#### 3.2 Output Comparison

**Test**: Compare generated manpage with current v1 output

**Commands**:
```bash
# Generate with v1 (current)
.venv/bin/resume-gen --out site-v1 --with-vax --vax-mode docker

# Generate with v2 (enhanced)
.venv/bin/resume-gen --out site-v2 --with-vax --vax-mode docker

# Compare outputs
diff site-v1/brad.man.txt site-v2/brad.man.txt
```

**Expected**: Outputs should be identical (or only differ in whitespace)

---

### Phase 4: Edge Cases & Error Handling

#### 4.1 Malformed YAML

| Test Case | Input | Expected Behavior |
|-----------|-------|-------------------|
| Missing colon | `name Bradley` | Error: "Expected ':' after key" |
| Unclosed quote | `name: "Bradley` | Error: "Unterminated string" |
| Invalid indent | `  name: value` (bad level) | Error: "Invalid indentation" |
| Empty file | `` | Error: "Empty input" |
| Only whitespace | `   \n  \n` | Error: "No content" |

#### 4.2 Boundary Conditions

| Test Case | Input | Expected Behavior |
|-----------|-------|-------------------|
| Max nesting | 10 levels deep | Parse successfully |
| Very long key | 200 char key | Parse successfully |
| Very long value | 1000 char value | Parse successfully |
| Large list | 100 items | Parse successfully |
| Unicode (if supported) | `name: Café` | Parse or graceful error |

---

### Phase 5: Memory & Performance Tests

#### 5.1 Memory Leak Testing

**Tools**: `valgrind` (if available on platform)

**Test**:
```bash
# Compile with debug symbols
cc -g -o bradman bradman.c

# Run with valgrind
valgrind --leak-check=full ./bradman resume.vax.yaml > /dev/null
```

**Expected**: 
- No memory leaks reported
- All `malloc`ed memory `free`d
- No invalid memory access

#### 5.2 Performance Benchmarking

**Test**: Parse time for resume.yaml

**Metrics**:
- v1 (quoted subset): ~X ms
- v2 (standard YAML): ~Y ms
- Acceptable if Y ≤ 2X (2x slowdown acceptable)

---

## Test Execution Checklist

### Development Testing

- [ ] Unit test: `parse_string_value()` with unquoted strings
- [ ] Unit test: `parse_quoted_string()` still works
- [ ] Unit test: `is_yaml_special_char()` correct
- [ ] Integration: Simple map parsing
- [ ] Integration: Nested map parsing
- [ ] Integration: List parsing
- [ ] Integration: Mixed structures
- [ ] Real-world: Parse `resume.yaml` successfully
- [ ] Real-world: Output matches v1 exactly

### Quality Testing

- [ ] Memory: No leaks (valgrind if available)
- [ ] Performance: Parse time acceptable
- [ ] Error handling: Malformed YAML caught
- [ ] Edge cases: Boundary conditions handled
- [ ] Regression: All existing tests still pass

### Deployment Testing

- [ ] Local mode: Build completes successfully
- [ ] Docker mode: VAX compile and run works
- [ ] GitHub Actions: CI pipeline passes
- [ ] Output verification: Published site identical to v1

---

## Success Criteria

The YAML enhancement is considered complete when:

1. ✅ All unit tests pass
2. ✅ All integration tests pass
3. ✅ Real `resume.yaml` parses successfully
4. ✅ Generated output identical to v1
5. ✅ No memory leaks detected
6. ✅ Error handling graceful
7. ✅ Documentation updated
8. ✅ CI pipeline passes
9. ✅ Deployed site validates correctly

---

## Test Data Files

Create these test files in `tests/fixtures/`:

**tests/fixtures/yaml/simple_map.yaml**:
```yaml
name: Bradley Fidler
email: test@example.com
```

**tests/fixtures/yaml/nested_map.yaml**:
```yaml
basics:
  name: Bradley Fidler
  location:
    city: Warwick
```

**tests/fixtures/yaml/list.yaml**:
```yaml
skills:
- Python
- C
```

**tests/fixtures/yaml/complex.yaml**:
```yaml
work:
- name: Company A
  highlights:
  - Achievement 1
  - Achievement 2
```

---

## Regression Prevention

After enhancement, add these Python tests:

**tests/test_yaml_v2_parser.py**:
```python
def test_vax_parser_handles_unquoted():
    """Verify VAX parser handles unquoted strings"""
    # Test implementation
    pass

def test_output_matches_v1():
    """Verify v2 output identical to v1"""
    # Test implementation
    pass
```

---

## Rollback Plan

If enhancement fails:

1. Keep v1 code in separate branch
2. v2 enhancement in feature branch
3. Can revert to v1 if needed
4. Both versions tested independently

---

## Related Documentation

- Implementation plan: `docs/YAML-ENHANCEMENT-PLAN.md`
- Current parser: `vax/bradman.c`
- Python preprocessor: `resume_generator/vax_yaml.py`
- Existing tests: `tests/test_vax_yaml.py`


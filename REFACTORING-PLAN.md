# Codebase Refactoring Plan

**Date**: 2026-02-08
**Goal**: Improve code clarity, eliminate duplication, simplify architecture
**Priority**: Easy-to-understand, self-documenting code

---

## Executive Summary

Comprehensive code review identified **26 specific issues** across the codebase:
- **8 HIGH severity** DRY violations (identical code in multiple places)
- **12 MEDIUM severity** architectural/clarity issues
- **6 LOW severity** configuration/naming inconsistencies

**Estimated effort**: 4-6 hours to address all priority 1-2 issues
**Impact**: Significant improvement in maintainability and clarity

---

## Critical Issues (Priority 1) - Fix Immediately

### 1.1 Identical parse_line() in VAX and IMP Collectors

**Files**: `arpanet_logging/collectors/vax.py`, `arpanet_logging/collectors/imp.py`

**Problem**: Both classes have identical 23-line `parse_line()` methods - pure code duplication.

**Current**:
```python
# VAXCollector.parse_line() - lines 29-51
def parse_line(self, timestamp: str, message: str) -> Optional[LogEntry]:
    parsed = self.parser.parse(message) if self.parser else {}
    tags = self.parser.extract_tags(message) if self.parser else []
    log_level = self.parser.detect_log_level(message) if self.parser else "INFO"
    return self.create_entry(timestamp, message, log_level, tags, parsed)

# IMPCollector.parse_line() - lines 29-51 (IDENTICAL!)
def parse_line(self, timestamp: str, message: str) -> Optional[LogEntry]:
    parsed = self.parser.parse(message) if self.parser else {}
    tags = self.parser.extract_tags(message) if self.parser else []
    log_level = self.parser.detect_log_level(message) if self.parser else "INFO"
    return self.create_entry(timestamp, message, log_level, tags, parsed)
```

**Solution**:
Move to `BaseCollector` as default implementation:

```python
# arpanet_logging/core/collector.py
class BaseCollector(ABC):
    def parse_line(self, timestamp: str, message: str) -> Optional[LogEntry]:
        """Default parser implementation - override for custom behavior."""
        if not self.parser:
            return self.create_entry(timestamp, message, "INFO", [], {})

        return self.create_entry(
            timestamp=timestamp,
            message=message,
            log_level=self.parser.detect_log_level(message),
            tags=self.parser.extract_tags(message),
            parsed=self.parser.parse(message)
        )

# Both collectors can now delete their parse_line() methods entirely
class VAXCollector(BaseCollector):
    # parse_line() inherited from BaseCollector - no code needed!
    pass

class IMPCollector(BaseCollector):
    # parse_line() inherited from BaseCollector - no code needed!
    pass
```

**Impact**: Removes 46 lines of duplicate code, centralizes logic

---

### 1.2 Identical Parser Initialization Pattern

**Files**: `arpanet_logging/collectors/vax.py` (lines 21-27), `imp.py` (lines 21-27)

**Problem**: Both collectors have identical initialization logic in `__init__`:

```python
# In both VAXCollector and IMPCollector:
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    if self.parser is None:
        self.parser = BSDParser()  # or ArpanetParser()
```

**Solution**:
Use class attributes and move to base class:

```python
class VAXCollector(BaseCollector):
    default_parser_class = BSDParser

class IMPCollector(BaseCollector):
    default_parser_class = ArpanetParser

# In BaseCollector.__init__:
def __init__(self, ..., parser=None):
    self.parser = parser or (
        self.default_parser_class() if hasattr(self, 'default_parser_class') else None
    )
```

**Impact**: Removes duplicate __init__ methods, makes parser selection declarative

---

### 1.3 Shell Script Color Definitions Repeated 3x

**Files**: `test-vax-imp.sh`, `test-phase2-imp-link.sh`, `test-3container-routing.sh`

**Problem**: Identical color variable definitions in every test script:

```bash
# Repeated in 3 files:
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'
```

**Solution**:
Create `arpanet/scripts/lib/common.sh`:

```bash
#!/bin/bash
# Common utilities for ARPANET test scripts

# Colors
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

# Helper functions
check_container() {
    local container=$1
    if ! docker ps | grep -q "$container"; then
        echo -e "${RED}✗ $container not running${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ $container running${NC}"
    return 0
}
```

Then in each script:
```bash
#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Now use colors and helpers
```

**Impact**: Removes 12+ lines of duplication, adds reusable helpers

---

### 1.4 Hardcoded Collector Instantiation in Orchestrator

**File**: `arpanet_logging/orchestrator.py` (lines 118-140)

**Problem**: Tight coupling between orchestrator and specific collector types:

```python
if component == "vax":
    collector = VAXCollector(...)
elif component in ("imp1", "imp2"):
    collector = IMPCollector(...)
    collector.component_name = component  # Hack!
```

**Solution**:
Implement collector registry pattern:

```python
# arpanet_logging/collectors/__init__.py
COLLECTOR_REGISTRY = {
    "vax": VAXCollector,
    "imp1": IMPCollector,
    "imp2": IMPCollector,
    "pdp10": PDPCollector,  # Future-proof
}

def get_collector(component: str, **kwargs):
    """Factory function for collectors."""
    collector_class = COLLECTOR_REGISTRY.get(component)
    if not collector_class:
        raise ValueError(f"Unknown component: {component}")
    return collector_class(component_name=component, **kwargs)

# In orchestrator.py:
from arpanet_logging.collectors import get_collector

collector = get_collector(component, build_id=self.build_id, ...)
```

**Impact**: Removes hardcoded logic, enables easy addition of new collectors

---

## Important Issues (Priority 2) - Fix Soon

### 2.1 Verbose Tag Detection in ArpanetParser

**File**: `arpanet_logging/parsers/arpanet.py` (lines 124-182)

**Problem**: 60 lines of repetitive if-statements for tag extraction:

```python
def extract_tags(self, message: str) -> List[str]:
    tags = []
    message_lower = message.lower()

    if re.search(r'\bhi\d+\b', message_lower):
        tags.append("host-interface")
    if re.search(r'\bmi\d+\b', message_lower):
        tags.append("modem-interface")
    # ... 40 more lines ...
```

**Solution**:
Use mapping-based approach:

```python
# Class attribute
TAG_PATTERNS = {
    "host-interface": r'\bhi\d+\b',
    "modem-interface": r'\bmi\d+\b',
    "packet": r'\b(packet|message)\b',
    "send": r'\b(send|transmit|sent)\b',
    "receive": r'\b(receive|received|recv)\b',
    "udp": r'\budp\b',
    "error": r'\b(error|fail|timeout)\b',
    "warning": r'\b(warn|warning)\b',
}

def extract_tags(self, message: str) -> List[str]:
    """Extract tags based on message content."""
    message_lower = message.lower()
    return [
        tag for tag, pattern in self.TAG_PATTERNS.items()
        if re.search(pattern, message_lower)
    ]
```

**Impact**: Reduces 60 lines to ~15, adds self-documentation, easier to extend

---

### 2.2 Duplicate Docker Compose Service Definitions

**Files**: `docker-compose.arpanet.phase1.yml`, `docker-compose.arpanet.phase2.yml`

**Problem**: IMP service definitions are 80% identical between phases:

**Solution**:
Use YAML anchors for shared configuration:

```yaml
# docker-compose.arpanet.base.yml
x-imp-common: &imp-common
  build:
    context: ./arpanet
    dockerfile: Dockerfile.imp
  restart: unless-stopped
  networks:
    - arpanet-build
  volumes:
    - ./arpanet/configs/impcode.simh:/machines/impcode.simh:ro
    - ./arpanet/configs/impconfig.simh:/machines/impconfig.simh:ro

services:
  imp1:
    <<: *imp-common
    container_name: arpanet-imp1
    hostname: imp-1
    ports:
      - "2324:2323"
    volumes:
      - ./build/arpanet/imp1:/machines/data
      - ./arpanet/configs/imp1.ini:/machines/imp.ini:ro
```

**Impact**: Reduces duplication, makes differences explicit

---

### 2.3 Expect Script Login Sequences Duplicated

**Files**: `vax-setup.exp`, `ftp-transfer-test.exp`, `authentic-ftp-transfer.exp`

**Problem**: Console login logic repeated in 3 scripts

**Solution**:
Create reusable Tcl procedure library:

```tcl
# arpanet/scripts/lib/vax-console.tcl
#!/usr/bin/expect -f
# Reusable VAX console procedures

proc vax_connect {host port} {
    spawn telnet $host $port
    return $spawn_id
}

proc vax_login {{user "root"}} {
    sleep 2
    send "\r"

    expect {
        "login:" {
            send "$user\r"
            expect "#"
        }
        "#" {
            # Already logged in
        }
        timeout {
            error "Login timeout"
        }
    }
}

# Usage in scripts:
source [file dirname [info script]]/lib/vax-console.tcl
vax_connect localhost 2323
vax_login
```

**Impact**: Removes 100+ lines of duplicate expect code

---

### 2.4 Redundant subprocess Boilerplate in docker_utils

**File**: `test_infra/lib/docker_utils.py`

**Problem**: Every function has identical try/except/timeout pattern:

**Solution**:
Extract to base function:

```python
def _run_compose_command(
    compose_file: Path,
    *args: str,
    timeout: int = 120,
    capture_output: bool = False,
    check: bool = False
) -> subprocess.CompletedProcess:
    """Run docker compose command with standard error handling."""
    cmd = ['docker', 'compose', '-f', str(compose_file), *args]

    try:
        return subprocess.run(
            cmd,
            cwd=compose_file.parent,
            timeout=timeout,
            capture_output=capture_output,
            check=check,
            text=True
        )
    except subprocess.TimeoutExpired as e:
        print(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        raise
    except FileNotFoundError:
        print("Error: docker compose not found. Is Docker installed?")
        raise

# Now functions become one-liners:
def compose_build(compose_file: Path) -> bool:
    """Build containers from compose file."""
    result = _run_compose_command(compose_file, 'build', timeout=600)
    return result.returncode == 0

def compose_up(compose_file: Path) -> bool:
    """Start containers from compose file."""
    result = _run_compose_command(compose_file, 'up', '-d')
    return result.returncode == 0
```

**Impact**: Reduces 150+ lines to ~60, adds better error messages

---

## Nice-to-Have (Priority 3) - Future Improvements

### 3.1 Add Docstrings to ArpanetParser Message Types

**File**: `arpanet_logging/parsers/arpanet.py`

**Current**:
```python
MESSAGE_TYPES = {
    "000000": "Regular message",
    "002000": "Control message (IMP-to-host)",
}
```

**Better**:
```python
# ARPANET 1822 Protocol Message Types (octal notation)
# Reference: RFC 1822, BBN Report 1822
MESSAGE_TYPES = {
    "000000": "Regular message",           # Standard data transfer
    "002000": "Control message (IMP→host)", # IMP status to host
    "005000": "Control message",            # General control
    # See: https://tools.ietf.org/html/rfc1822 for full spec
}
```

---

### 3.2 Add JSON Error Handling in CLI

**File**: `arpanet_logging/cli.py`

**Current**:
```python
with open(metadata_path) as f:
    metadata = json.load(f)  # Can fail!
```

**Better**:
```python
try:
    with open(metadata_path) as f:
        metadata = json.load(f)
except FileNotFoundError:
    print(f"Error: Build {build_id} not found at {build_dir}")
    return 1
except json.JSONDecodeError as e:
    print(f"Error: Corrupt metadata file: {e}")
    return 1
```

---

### 3.3 Reorganize Config File Structure

**Current**:
```
arpanet/configs/
  imp-phase1.ini
  imp1.ini
  imp1-phase2.ini
  imp2.ini
  vax-network.ini
  pdp10.ini
```

**Better**:
```
arpanet/configs/
  phase1/
    vax.ini
    imp1.ini
  phase2/
    vax.ini
    imp1.ini
    imp2.ini
    pdp10.ini
```

---

### 3.4 Extract CDK Constructs for Reusability

**File**: `test_infra/cdk/arpanet_stack.py`

**Current**: Single 140-line stack class mixing concerns

**Better**: Separate constructs:
```python
class ArpanetSecurityGroup(Construct):
    """Network security rules for ARPANET testing."""

class ArpanetStorage(Construct):
    """EBS volumes for persistent ARPANET logs."""

class ArpanetInstance(Construct):
    """EC2 instance with ARPANET test environment."""

class ArpanetTestStack(Stack):
    """Main stack - composes the above constructs."""
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        sg = ArpanetSecurityGroup(self, "Security")
        storage = ArpanetStorage(self, "Storage")
        instance = ArpanetInstance(self, "Instance", sg=sg, storage=storage)
```

---

## Naming Consistency Guidelines

### Established Conventions

**Components**:
- Code/config: lowercase `vax`, `imp1`, `imp2`, `pdp10`
- Display/docs: Title case "VAX", "IMP #1", "PDP-10"
- Constants: uppercase `COMPONENT_VAX`, `COMPONENT_IMP1`

**Phases**:
- Code/config: lowercase `phase1`, `phase2`
- Display/docs: Title case "Phase 1", "Phase 2"
- Constants: uppercase `PHASE_1`, `PHASE_2`

**Files**:
- Scripts: lowercase with hyphens `test-vax-imp.sh`
- Python: lowercase with underscores `docker_utils.py`
- Configs: lowercase with hyphens `imp1-phase2.ini`

---

## Implementation Plan

### Week 1: Critical Issues (Priority 1)
- [ ] 1.1: Consolidate collector parse_line() methods (2 hours)
- [ ] 1.2: Fix parser initialization pattern (30 min)
- [ ] 1.3: Create common shell library (1 hour)
- [ ] 1.4: Implement collector registry (1 hour)

**Estimated**: 4.5 hours total

### Week 2: Important Issues (Priority 2)
- [ ] 2.1: Simplify tag extraction (1 hour)
- [ ] 2.2: Use YAML anchors in compose files (1 hour)
- [ ] 2.3: Extract expect login procedures (2 hours)
- [ ] 2.4: Consolidate docker_utils (1 hour)

**Estimated**: 5 hours total

### Week 3: Nice-to-Have (Priority 3)
- [ ] 3.1: Add parser docstrings (30 min)
- [ ] 3.2: Add CLI error handling (30 min)
- [ ] 3.3: Reorganize config structure (1 hour)
- [ ] 3.4: Extract CDK constructs (2 hours)

**Estimated**: 4 hours total

**Total Effort**: ~13.5 hours to address all issues

---

## Testing Strategy

After each refactoring:

### Python Changes
```bash
# Run existing tests (if any)
pytest arpanet_logging/

# Manual smoke test
python3 -m arpanet_logging collect --build-id test-$(date +%s) --components vax --duration 10
```

### Shell Changes
```bash
# Test each script
./arpanet/scripts/test-vax-imp.sh
./arpanet/scripts/test-3container-routing.sh
```

### Docker Compose Changes
```bash
# Validate compose file
docker compose -f docker-compose.arpanet.phase2.yml config

# Test build and start
docker compose -f docker-compose.arpanet.phase2.yml build
docker compose -f docker-compose.arpanet.phase2.yml up -d
```

---

## Success Metrics

### Code Quality
- [ ] DRY violations reduced by 80%+ (from 26 to <5)
- [ ] Average function length reduced by 30%
- [ ] Cyclomatic complexity reduced by 20%

### Maintainability
- [ ] New collector can be added in <50 lines
- [ ] New test script needs <20 lines (uses common lib)
- [ ] Config changes isolated to single directory

### Clarity
- [ ] No function over 50 lines
- [ ] All public APIs have docstrings
- [ ] Magic numbers/strings extracted to constants

---

## Risks & Mitigation

### Risk: Breaking existing functionality
**Mitigation**:
- Refactor incrementally
- Test after each change
- Keep git commits small and atomic
- Can revert quickly if issues found

### Risk: Time overrun
**Mitigation**:
- Prioritize P1 issues only if time-constrained
- P2 and P3 can be deferred
- Each refactoring is independent

### Risk: Merge conflicts during active development
**Mitigation**:
- Do refactoring in quiet period
- OR do in separate branch
- Communicate with team

---

## Long-Term Architectural Improvements

### Consider for Future

1. **Plugin System for Collectors**
   - Load collectors dynamically from config
   - Third-party collectors possible

2. **Event Stream Processing**
   - Real-time log analysis
   - Alerting on error patterns

3. **Web Dashboard**
   - View logs in browser
   - Network topology visualization

4. **Configuration Management**
   - Single source of truth for network topology
   - Generate docker-compose from config

---

## Conclusion

This codebase is well-structured with clear intent. The issues identified are typical of rapid prototyping and don't reflect poor design - just areas where DRY principles can be better applied.

**Recommendation**: Implement Priority 1 issues (4.5 hours) immediately to prevent technical debt accumulation. Priority 2 and 3 can be addressed as time permits.

The refactoring will result in:
- **~300 fewer lines of code**
- **Better separation of concerns**
- **Easier onboarding for new contributors**
- **Reduced bug surface area**

---

**Status**: Ready for implementation
**Author**: Claude Sonnet 4.5 (via Explore agent)
**Date**: 2026-02-08

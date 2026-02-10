# Test Fixtures

Test data and configuration files for ARPANET testing.

## Purpose

Fixtures provide:
- Known-good configuration files
- Sample test data
- Expected output patterns
- Baseline logs for comparison

## Current Fixtures

### Configuration Files
ARPANET configuration files are maintained in `arpanet/configs/`:
- `impcode.simh` - IMP firmware (137KB)
- `impconfig.simh` - IMP base configuration
- `imp-phase1.ini` - Phase 1 IMP configuration

### Test Data
Currently no test data files needed. Phase 1 tests only verify:
- Container builds
- Network connectivity
- Basic initialization

## Future Fixtures

As testing expands, this directory will contain:

### Phase 2
- Multi-IMP configuration files
- PDP-10 test data
- Expected routing tables

### Phase 3
- Sample build artifacts for transfer
- Expected FTP session logs
- Build output checksums

## Usage

Tests automatically use fixtures from this directory via relative imports.

Example:
```python
from pathlib import Path

fixtures_dir = Path(__file__).parent.parent / 'fixtures'
test_config = fixtures_dir / 'test.ini'
```

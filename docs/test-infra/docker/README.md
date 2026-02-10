# Docker Integration Tests

Automated tests for ARPANET Docker containers.

## Purpose

Tests verify:
- Container builds complete successfully
- Containers start and stay running
- Network connectivity between VAX and IMP
- Console ports are accessible
- Logs indicate proper initialization

## Test Script

`test_arpanet.py` - Main test runner

### Usage

```bash
# Run all tests
./test_arpanet.py

# Run specific test mode
./test_arpanet.py --mode connectivity
./test_arpanet.py --mode build
./test_arpanet.py --mode logs

# Verbose output
./test_arpanet.py --verbose

# Skip cleanup (for debugging)
./test_arpanet.py --no-cleanup
```

## Test Modes

### Build Tests
- Verify Docker Compose file is valid
- Build IMP container from Dockerfile
- Check for build errors

### Connectivity Tests
- Start VAX and IMP containers
- Wait for boot sequence
- Test UDP port 2000 connectivity
- Test telnet console ports (2323, 2324)
- Verify bridge network creation

### Log Tests
- Parse VAX logs for boot messages
- Parse IMP logs for firmware load
- Check for error conditions
- Verify network interface initialization

## Exit Codes

- `0` - All tests passed
- `1` - Test failure
- `2` - Environment error (Docker not available, etc.)

## GitHub Actions Integration

These tests run automatically via `.github/workflows/test.yml` on every push to feature branches.

The workflow:
1. Checks out code
2. Builds containers
3. Starts network
4. Runs connectivity tests
5. Uploads logs as artifacts

## Timeouts

- VAX boot: 60 seconds
- IMP boot: 10 seconds
- Total test time: ~90 seconds
- GitHub Actions timeout: 10 minutes

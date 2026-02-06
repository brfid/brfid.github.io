# Testing Infrastructure

Test utilities and environments for the ARPANET build integration.

## Purpose

This directory contains tools for testing the ARPANET network simulation across different environments. Tests verify that VAX and IMP containers start correctly, establish network connectivity, and can transfer data.

## Structure

```
test_infra/
├── local/          # Local development machine testing
├── docker/         # Docker-based integration tests
├── fixtures/       # Test data and configuration files
└── lib/            # Shared Python utilities
```

## Quick Start

### Run all tests locally
```bash
make test
```

### Run specific test suites
```bash
make test_docker      # Docker integration tests
make test_local       # Local environment checks
```

### Check environment readiness
```bash
make check_env
```

## Testing Modes

### 1. Local Testing
For development on local workstations with Docker installed.
Quick iteration during development.
See `local/README.md` for setup instructions.

### 2. Cloud Testing (AWS)
For interactive debugging when GitHub Actions feedback is too slow.
Launch an EC2 instance (t3.medium, Ubuntu 22.04), run tests with full access.
Recommended for debugging complex build issues.
See `local/README.md` for AWS instructions.

### 3. Docker Testing
Automated integration tests that run locally or in CI/CD.
See `docker/README.md` for test details.

### 4. GitHub Actions
Automated testing on every push to feature branches.
See `.github/workflows/test.yml`.

## Requirements

- Docker and Docker Compose
- Python 3.8+
- Standard Unix utilities (nc, telnet, timeout)

## Documentation

Each subdirectory contains a README.md with specific instructions.

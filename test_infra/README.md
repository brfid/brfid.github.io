# Testing Infrastructure

Test utilities for the ARPANET build integration. All testing runs on AWS EC2 instances.

## Structure

```
test_infra/
├── aws/            # AWS EC2 setup and documentation
├── docker/         # Docker integration tests
├── fixtures/       # Test data and configuration files
└── lib/            # Shared Python utilities
```

## Quick Start

### 1. Launch AWS Instance
```bash
# Launch t3.medium with Ubuntu 22.04
# SSH into instance
# See aws/README.md for details
```

### 2. Run Setup
```bash
./test_infra/aws/setup.sh
```

### 3. Run Tests
```bash
make test
# or
./test_infra/docker/test_arpanet.py
```

## Why AWS?

Testing ARPANET integration requires:
- Full Docker access with build capabilities
- Interactive debugging of container logs
- Ability to connect to container consoles
- Fast feedback loop (faster than GitHub Actions)

AWS provides a consistent, accessible environment for debugging when GitHub Actions fails.

## Testing Workflow

1. **GitHub Actions** - Automated tests on every push
2. **If Actions fail** → Launch AWS instance for interactive debugging
3. **Debug on AWS** - Build with `--progress=plain`, view live logs
4. **Fix issues** - Commit and push fixes
5. **Verify** - Watch GitHub Actions pass

## Requirements

- Docker and Docker Compose
- Python 3.8+
- Standard Unix utilities (nc, telnet, timeout)

## Cost

Typical debugging session: ~$1-2 (1-2 hours on t3.medium)

## Documentation

- `aws/README.md` - AWS setup and usage
- `docker/README.md` - Test details
- `lib/*.py` - Utility function documentation

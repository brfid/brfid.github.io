# ARPANET Topology Management

Single-source-of-truth topology definitions for ARPANET simulation infrastructure.

## Overview

This package provides a declarative, type-safe approach to managing ARPANET network topologies. Instead of manually editing Docker Compose files and SIMH configuration files across 5+ locations, define your topology once in Python and generate all configurations automatically.

**Benefits:**
- **DRY**: One definition generates all configs (docker-compose.yml, SIMH .ini files)
- **Type Safety**: Frozen dataclasses prevent configuration errors at design time
- **Reviewable**: Python definitions show up clearly in git diffs
- **IDE Support**: Autocomplete and type checking for all configuration options
- **Scalable**: Add new hosts with a single code change, not 12 file edits

## Quick Start

### Generate Configurations

```bash
# Generate phase1 topology (VAX + IMP #1)
arpanet-topology phase1

# Generate phase2 topology (VAX + IMP #1 + IMP #2 + PDP-10)
arpanet-topology phase2

# List available topologies
arpanet-topology --list
```

### Start a Topology

```bash
# Generated files are ready to use
docker-compose -f docker-compose.arpanet.phase1.yml up -d

# View logs
docker-compose -f docker-compose.arpanet.phase1.yml logs -f

# Stop topology
docker-compose -f docker-compose.arpanet.phase1.yml down
```

## Adding a New Host

To add a new host to an existing topology:

1. **Edit the topology definition** in `arpanet/topology/definitions.py`:

```python
PHASE2_TOPOLOGY = TopologyDefinition(
    name="phase2",
    subnet="172.20.0.0/16",
    gateway="172.20.0.1",
    hosts={
        # ... existing hosts ...

        "pdp11": HostConfig(  # NEW HOST
            name="pdp11",
            component_type="pdp11",
            hostname="pdp11-host",
            container_name="arpanet-pdp11",
            console_port=2327,
            interfaces=[
                NetworkInterface(
                    network_type="arpanet",
                    ip_address="172.20.0.50",
                    udp_port=2000,
                    device="imp",
                    remote_host="172.20.0.30",
                    remote_port=2001,
                )
            ],
            dockerfile="./arpanet/Dockerfile.pdp11",
            volumes=[
                ("./build/arpanet/pdp11", "/machines/data"),
            ],
        ),
    },
)
```

2. **Regenerate configurations**:

```bash
arpanet-topology phase2
```

3. **Test the topology**:

```bash
docker-compose -f docker-compose.arpanet.phase2.yml up -d
```

That's it! No need to manually edit docker-compose.yml, SIMH configs, or test scripts.

## Architecture

### Data Model (Immutable)

All topology data structures are frozen dataclasses:

- **`NetworkInterface`**: Single network interface (IP, port, device, remote endpoint)
- **`HostConfig`**: Complete host specification (type, interfaces, volumes, dependencies)
- **`TopologyDefinition`**: Full network topology (hosts, subnet, gateway)

Frozen dataclasses provide:
- Immutability (no accidental modifications)
- Hashability (can be used as dict keys)
- Clear errors if you try to modify after creation

### Pure Functions (Stateless)

Configuration generation is performed by pure functions:

- **`generate_docker_compose(topology)`**: Topology → Docker Compose dict
- **`generate_simh_config(host, topology)`**: Host → SIMH .ini content
- **`write_generated_configs(topology, output_dir)`**: Write all configs to disk

Pure functions provide:
- Idempotent generation (same input = same output)
- Easy testing (no mocks needed)
- Composable transformations

### File Organization

```
arpanet/topology/
├── __init__.py              # Public API exports
├── registry.py              # Dataclass models (NetworkInterface, HostConfig, etc.)
├── definitions.py           # Concrete topologies (PHASE1_TOPOLOGY, PHASE2_TOPOLOGY)
├── generators.py            # Pure generation functions
├── cli.py                   # Command-line interface
└── README.md                # This file

Generated outputs:
├── docker-compose.arpanet.phase1.yml    # Docker Compose for phase1
├── docker-compose.arpanet.phase2.yml    # Docker Compose for phase2
└── arpanet/configs/
    ├── phase1/
    │   └── imp1.ini         # SIMH config for IMP #1 in phase1
    └── phase2/
        ├── imp1.ini         # SIMH config for IMP #1 in phase2
        ├── imp2.ini         # SIMH config for IMP #2 in phase2
        └── pdp10.ini        # SIMH config for PDP-10 in phase2
```

## Design Rationale

### Why Python, Not YAML?

Topology definitions are in Python (not YAML/JSON) because:

1. **Type safety**: IDE catches errors before runtime
2. **No parsing errors**: Invalid Python won't compile
3. **Autocomplete**: IDE suggests valid fields and values
4. **Documentation**: Inline comments and docstrings
5. **Reviewable**: Git diffs show semantic changes clearly

### Why Frozen Dataclasses?

Frozen dataclasses (immutable) prevent entire classes of bugs:

```python
# This will raise AttributeError at assignment time
topology.name = "modified"  # ERROR: can't set attribute

# Forces you to create new instances instead
new_topology = TopologyDefinition(
    name="modified",
    subnet=topology.subnet,
    gateway=topology.gateway,
    hosts=topology.hosts,
)
```

### Why Pure Functions?

Pure functions (no side effects except file I/O) provide:

- **Testability**: No mocks, just input → output assertions
- **Idempotence**: Same input always produces same output
- **Composability**: Outputs can feed into other functions
- **Parallelization**: Can generate configs concurrently (future)

## Testing

Comprehensive test suite covers:

- **Registry tests** (`test_topology_registry.py`):
  - Dataclass immutability
  - Topology validation (unique IPs, ports, dependencies)
  - Predefined topology correctness

- **Generator tests** (`test_topology_generators.py`):
  - YAML validity
  - Docker Compose structure
  - SIMH config accuracy
  - Idempotent generation
  - File writing

Run tests:

```bash
pytest tests/test_topology_registry.py tests/test_topology_generators.py -v
```

## Common Patterns

### Multiple Interfaces on One Host

IMPs typically have both host interfaces (HI) and modem interfaces (MI):

```python
interfaces=[
    NetworkInterface(  # Connection to VAX
        network_type="arpanet",
        ip_address="172.20.0.20",
        udp_port=2000,
        device="hi1",
        remote_host="172.20.0.10",
        remote_port=2000,
    ),
    NetworkInterface(  # Connection to IMP #2
        network_type="arpanet",
        ip_address="172.20.0.20",  # Same IP, different port
        udp_port=3001,
        device="mi1",
        remote_host="172.20.0.30",
        remote_port=3001,
    ),
]
```

### Host Dependencies

Use `depends_on` to ensure startup order:

```python
HostConfig(
    name="imp2",
    # ...
    depends_on=["imp1", "pdp10"],  # Wait for IMP1 and PDP10 to start
)
```

### Custom Dockerfiles vs Pre-built Images

```python
# Use pre-built image (VAX)
image="jguillaumes/simh-vaxbsd@sha256:...",
dockerfile=None,

# Use custom Dockerfile (IMP)
image=None,
dockerfile="./arpanet/Dockerfile.imp",
```

### Volume Mounts

```python
volumes=[
    ("./build/arpanet/imp1", "/machines/data"),           # Read-write
    ("./arpanet/configs/imp1.ini", "/machines/imp.ini:ro"),  # Read-only (:ro)
]
```

## Future Enhancements

Potential future features (not implemented yet):

- **Validation**: Check for port conflicts, IP overlaps, circular dependencies
- **Diff tool**: Compare two topologies and show differences
- **Visualization**: Generate network diagrams from topologies
- **Templates**: Host templates for common configurations
- **Multi-network**: Support multiple subnets in one topology

## Troubleshooting

### Generated configs don't match manual configs exactly

This is expected. Generated configs:
- May have different comment formatting
- Use consistent indentation (not mixed tabs/spaces)
- Include generation headers
- May order keys differently (but semantically equivalent)

To validate equivalence:
```bash
docker-compose -f docker-compose.arpanet.phase1.yml config
```

### Changes to topology not reflected

Make sure to regenerate after editing definitions:
```bash
arpanet-topology phase1
arpanet-topology phase2
```

### Type errors in IDE

Ensure you have mypy and type stubs installed:
```bash
pip install -e .[dev]
```

## Related Documentation

- **ARPANET Phase 1**: `arpanet/PHASE1-VALIDATION.md`
- **ARPANET Phase 2**: `arpanet/PHASE2-PLAN.md`
- **Project Memory**: `.claude/projects/-home-whf-brfid-github-io/memory/MEMORY.md`

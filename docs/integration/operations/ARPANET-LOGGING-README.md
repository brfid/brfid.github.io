# ARPANET Logging System

Modular, DRY Python logging infrastructure for ARPANET integration testing.

## Features

- **Real-time log collection** from Docker containers
- **Component-specific parsers** (BSD and ARPANET 1822 protocol)
- **Persistent storage** on EBS volume (survives instance termination)
- **Structured events** (JSON Lines format)
- **Statistics and indexing** for easy navigation
- **CLI interface** for management

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Log Orchestrator                   │
│              Manages multiple collectors             │
└─────────────────────┬───────────────────────────────┘
                      │
          ┌───────────┴───────────┬─────────────────┐
          │                       │                 │
    ┌─────▼─────┐          ┌─────▼─────┐    ┌─────▼─────┐
    │   VAX     │          │   IMP1    │    │   IMP2    │
    │ Collector │          │ Collector │    │ Collector │
    └─────┬─────┘          └─────┬─────┘    └─────┬─────┘
          │                      │                 │
    ┌─────▼──────────────────────▼─────────────────▼─────┐
    │            LogStorage (EBS Volume)                  │
    │       /mnt/arpanet-logs/builds/build-{id}/          │
    └─────────────────────────────────────────────────────┘
```

## Storage Layout

```
/mnt/arpanet-logs/
├── index.json                      # Index of all builds
└── builds/
    └── build-20260207-221530/
        ├── metadata.json           # Build metadata
        ├── vax/
        │   ├── vax.log            # Raw console output
        │   ├── events.jsonl       # Structured events
        │   └── summary.json       # Statistics
        ├── imp1/
        │   ├── imp1.log
        │   ├── events.jsonl
        │   └── summary.json
        └── imp2/
            ├── imp2.log
            ├── events.jsonl
            └── summary.json
```

## Installation

The package is already included in the main project dependencies:

```bash
# Install project with dependencies
.venv/bin/python -m pip install -e .
```

## Usage

### Collect Logs

```bash
# Collect from VAX only
.venv/bin/python -m arpanet_logging collect --components vax

# Collect from all Phase 2 components
.venv/bin/python -m arpanet_logging collect --components vax imp1 imp2

# Collect for 60 seconds then stop
.venv/bin/python -m arpanet_logging collect --components vax imp1 imp2 --duration 60

# Custom build ID
.venv/bin/python -m arpanet_logging collect --build-id test-build-001 --components vax
```

### Manage Builds

```bash
# List all builds
.venv/bin/python -m arpanet_logging list

# Show details of specific build
.venv/bin/python -m arpanet_logging show build-20260207-221530

# Clean up old builds (keep last 10)
.venv/bin/python -m arpanet_logging cleanup --keep 10
```

### Use in Scripts

```python
from arpanet_logging import LogOrchestrator

# Create orchestrator
orchestrator = LogOrchestrator(
    build_id="build-20260207-221530",
    components=["vax", "imp1", "imp2"],
    phase="phase2"
)

# Start collection
orchestrator.start()

# ... run your tests ...

# Stop and finalize
orchestrator.stop()
```

## Components

### Core Infrastructure

- **`core/models.py`** - Data models (LogEntry, BuildMetadata)
- **`core/storage.py`** - Persistent storage backend
- **`core/collector.py`** - Base collector class (DRY)
- **`core/parser.py`** - Base parser interface

### Collectors

- **`collectors/vax.py`** - VAX/BSD collector
- **`collectors/imp.py`** - IMP collector

Planned (not yet implemented):
- `collectors/pdp10.py` - PDP-10 collector

### Parsers

- **`parsers/bsd.py`** - BSD 4.3 log parser
- **`parsers/arpanet.py`** - ARPANET 1822 protocol parser

Planned (not yet implemented):
- `parsers/simh.py` - SIMH output parser

### Tools

- **`orchestrator.py`** - Multi-component orchestration
- **`cli.py`** - Command-line interface

## Log Entry Format

Each log entry is a structured JSON object:

```json
{
  "build_id": "build-20260207-221530",
  "component": "vax",
  "timestamp": "2026-02-07T22:30:15.123456Z",
  "phase": "phase2",
  "log_level": "INFO",
  "source": "console",
  "message": "de0: hardware address 08:00:2b:92:49:19",
  "parsed": {
    "event_type": "hw_address",
    "interface": "de0",
    "mac_address": "08:00:2b:92:49:19"
  },
  "tags": ["network", "interface-de0"]
}
```

## Development

### Adding a New Collector

1. Create collector class in `collectors/`
2. Inherit from `BaseCollector`
3. Implement `parse_line()` method
4. Optionally create custom parser in `parsers/`

Example:

```python
from arpanet_logging.core.collector import BaseCollector
from arpanet_logging.core.models import LogEntry

class MyCollector(BaseCollector):
    component_name = "my_component"

    def parse_line(self, timestamp: str, message: str) -> LogEntry:
        # Parse message
        tags = []
        if "error" in message.lower():
            tags.append("error")

        # Return structured entry
        return self.create_entry(
            timestamp=timestamp,
            message=message,
            log_level="INFO",
            tags=tags
        )
```

### Adding a New Parser

1. Create parser class in `parsers/`
2. Inherit from `BaseParser`
3. Implement `parse()` and `extract_tags()` methods

## AWS Infrastructure

The logging system requires a persistent EBS volume mounted at `/mnt/arpanet-logs`.

**CDK Configuration:**
- 20GB EBS volume (gp3 SSD)
- Delete on termination: **False** (persists across instances)
- Auto-formatted and mounted via user_data.sh
- Cost: ~$2/month

**Fallback:**
If EBS volume is not available, the system falls back to `./logs/` in the current directory.

## Cost

**Persistent storage**: ~$2-3/month on AWS
- EBS 20GB: $2/month
- S3 archival (optional): $0.12-0.50/month

**Per test run**: Negligible (storage only)

## Future Enhancements

- [ ] PDP-10 collector
- [ ] S3 sync for long-term archival
- [ ] Real-time web dashboard
- [ ] Alert system for errors
- [ ] Log compression
- [ ] Search/query interface

## License

Part of the brfid.github.io project.

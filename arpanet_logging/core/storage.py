"""Storage backend for ARPANET logs."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from arpanet_logging.core.models import LogEntry, BuildMetadata, ComponentStats


class LogStorage:
    """Manages persistent storage of logs on EBS volume.

    Directory structure:
        /mnt/arpanet-logs/
        ├── index.json                      # Index of all builds
        └── builds/
            └── build-20260207-221530/
                ├── metadata.json           # Build metadata
                ├── vax/
                │   ├── console.log        # Raw console output
                │   ├── events.jsonl       # Structured events (JSON Lines)
                │   └── summary.json       # Statistics
                ├── imp1/
                │   ├── simh.log
                │   ├── events.jsonl
                │   └── summary.json
                └── imp2/
                    ├── simh.log
                    ├── events.jsonl
                    └── summary.json
    """

    def __init__(
        self,
        build_id: str,
        base_path: str = "/mnt/arpanet-logs",
        local_fallback: bool = True
    ):
        """Initialize storage.

        Args:
            build_id: Unique build identifier
            base_path: Base path for log storage
            local_fallback: If True, fall back to ./logs if base_path doesn't exist
        """
        self.build_id = build_id
        self.base_path = Path(base_path)

        # Fallback to local directory if EBS not mounted
        if local_fallback and not self.base_path.exists():
            print(f"Warning: {base_path} not found, using local fallback")
            self.base_path = Path("./logs")

        self.build_path = self.base_path / "builds" / build_id
        self.index_path = self.base_path / "index.json"

        # Component log files (open handles)
        self._raw_handles: Dict[str, Any] = {}
        self._event_handles: Dict[str, Any] = {}

        # Statistics trackers
        self._stats: Dict[str, ComponentStats] = {}

    def initialize(self, metadata: BuildMetadata):
        """Initialize storage structure for a new build.

        Args:
            metadata: Build metadata
        """
        # Create directory structure
        self.build_path.mkdir(parents=True, exist_ok=True)

        for component in metadata.components:
            component_path = self.build_path / component
            component_path.mkdir(exist_ok=True)

            # Initialize stats
            self._stats[component] = ComponentStats(component=component)

        # Write metadata
        metadata_path = self.build_path / "metadata.json"
        with open(metadata_path, "w") as f:
            f.write(metadata.to_json())

        # Update index
        self._update_index(metadata)

        print(f"📁 Logs initialized at: {self.build_path}")

    def write_raw(self, component: str, message: str):
        """Write raw log message to component's log file.

        Args:
            component: Component name
            message: Raw log message
        """
        # Get or create file handle
        if component not in self._raw_handles:
            log_file = self.build_path / component / f"{component}.log"
            self._raw_handles[component] = open(log_file, "a", buffering=1)  # Line buffered

        # Write message (ensure newline)
        if not message.endswith("\n"):
            message += "\n"
        self._raw_handles[component].write(message)

    def write_event(self, entry: LogEntry):
        """Write structured log entry to component's events file.

        Args:
            entry: Log entry to write
        """
        component = entry.component

        # Get or create file handle
        if component not in self._event_handles:
            events_file = self.build_path / component / "events.jsonl"
            self._event_handles[component] = open(events_file, "a", buffering=1)

        # Write JSON Line
        self._event_handles[component].write(entry.to_json() + "\n")

        # Update statistics
        self._update_stats(entry)

    def _update_stats(self, entry: LogEntry):
        """Update statistics for a component.

        Args:
            entry: Log entry to process
        """
        component = entry.component

        if component not in self._stats:
            self._stats[component] = ComponentStats(component=component)

        stats = self._stats[component]
        stats.total_lines += 1

        # Update log levels
        if entry.log_level not in stats.log_levels:
            stats.log_levels[entry.log_level] = 0
        stats.log_levels[entry.log_level] += 1

        # Update tags
        for tag in entry.tags:
            if tag not in stats.tags:
                stats.tags[tag] = 0
            stats.tags[tag] += 1

        # Update timestamps
        if stats.first_timestamp is None:
            stats.first_timestamp = entry.timestamp
        stats.last_timestamp = entry.timestamp

        # Count errors/warnings
        if entry.log_level == "ERROR":
            stats.errors += 1
        elif entry.log_level == "WARN":
            stats.warnings += 1

    def finalize(self, metadata: BuildMetadata):
        """Finalize storage and write summaries.

        Args:
            metadata: Final build metadata
        """
        # Close all file handles
        for handle in self._raw_handles.values():
            handle.close()
        for handle in self._event_handles.values():
            handle.close()

        # Write component summaries
        for component, stats in self._stats.items():
            summary_path = self.build_path / component / "summary.json"
            with open(summary_path, "w") as f:
                f.write(stats.to_json())

        # Update metadata with end time
        metadata_path = self.build_path / "metadata.json"
        with open(metadata_path, "w") as f:
            f.write(metadata.to_json())

        # Update index
        self._update_index(metadata)

        print(f"✅ Logs finalized at: {self.build_path}")

    def _update_index(self, metadata: BuildMetadata):
        """Update the global index with this build.

        Args:
            metadata: Build metadata to add/update
        """
        # Load existing index
        index = []
        if self.index_path.exists():
            with open(self.index_path) as f:
                index = json.load(f)

        # Remove existing entry for this build_id if present
        index = [b for b in index if b.get("build_id") != self.build_id]

        # Add new entry
        index.append(metadata.to_dict())

        # Sort by start_time (most recent first)
        index.sort(key=lambda b: b.get("start_time", ""), reverse=True)

        # Write index
        self.base_path.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "w") as f:
            json.dump(index, f, indent=2)

    def get_stats(self, component: str) -> Optional[ComponentStats]:
        """Get current statistics for a component.

        Args:
            component: Component name

        Returns:
            Component statistics or None if not found
        """
        return self._stats.get(component)

    def list_components(self) -> List[str]:
        """List components being logged in this build.

        Returns:
            List of component names
        """
        return list(self._stats.keys())

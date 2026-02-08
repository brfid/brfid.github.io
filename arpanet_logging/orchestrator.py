"""Log collection orchestrator for multiple components."""

import subprocess
from datetime import datetime
from typing import List, Dict, Any
import time
import signal
import sys

from arpanet_logging.core.models import BuildMetadata
from arpanet_logging.core.storage import LogStorage
from arpanet_logging.collectors.vax import VAXCollector
from arpanet_logging.collectors.imp import IMPCollector


class LogOrchestrator:
    """Orchestrates log collection from multiple ARPANET components.

    Manages lifecycle of collectors, coordinates storage, and handles
    graceful shutdown.
    """

    def __init__(
        self,
        build_id: str,
        components: List[str],
        phase: str = "phase2",
        base_path: str = "/mnt/arpanet-logs"
    ):
        """Initialize orchestrator.

        Args:
            build_id: Unique build identifier
            components: List of components to collect from
            phase: Testing phase
            base_path: Base path for log storage
        """
        self.build_id = build_id
        self.components = components
        self.phase = phase
        self.base_path = base_path

        # Initialize storage
        self.storage = LogStorage(build_id, base_path)

        # Collectors
        self.collectors: List = []

        # Metadata
        self.metadata = BuildMetadata(
            build_id=build_id,
            phase=phase,
            start_time=datetime.utcnow().isoformat() + 'Z',
            components=components,
            git_commit=self._get_git_commit(),
            git_branch=self._get_git_branch(),
            environment=self._get_environment()
        )

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _get_git_branch(self) -> str:
        """Get current git branch."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _get_environment(self) -> Dict[str, Any]:
        """Get environment information."""
        import platform
        import os

        return {
            "hostname": platform.node(),
            "platform": platform.system(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "user": os.environ.get("USER", "unknown"),
        }

    def start(self):
        """Initialize storage and start all collectors."""
        print(f"\n{'='*60}")
        print(f"📝 ARPANET Logging System")
        print(f"{'='*60}")
        print(f"Build ID: {self.build_id}")
        print(f"Phase: {self.phase}")
        print(f"Components: {', '.join(self.components)}")
        print(f"Storage: {self.storage.build_path}")
        print(f"{'='*60}\n")

        # Initialize storage
        self.storage.initialize(self.metadata)

        # Create collectors for each component
        for component in self.components:
            container_name = f"arpanet-{component}"

            if component == "vax":
                collector = VAXCollector(
                    build_id=self.build_id,
                    container_name=container_name,
                    storage=self.storage,
                    phase=self.phase
                )
            elif component in ("imp1", "imp2"):
                collector = IMPCollector(
                    build_id=self.build_id,
                    container_name=container_name,
                    storage=self.storage,
                    phase=self.phase
                )
                # Override component name for storage
                collector.component_name = component
            else:
                # For now, skip other components
                print(f"⚠️  No specific collector for {component}, skipping")
                continue

            self.collectors.append(collector)
            collector.start()

        print(f"\n✅ All collectors started\n")

    def stop(self):
        """Stop all collectors and finalize storage."""
        print(f"\n{'='*60}")
        print(f"⏹️  Stopping collectors...")
        print(f"{'='*60}\n")

        # Stop all collectors
        for collector in self.collectors:
            collector.stop()

        # Update metadata with end time
        self.metadata.end_time = datetime.utcnow().isoformat() + 'Z'
        self.metadata.status = "success"

        # Finalize storage
        self.storage.finalize(self.metadata)

        # Print statistics
        print(f"\n{'='*60}")
        print(f"📊 Collection Statistics")
        print(f"{'='*60}")
        for component in self.storage.list_components():
            stats = self.storage.get_stats(component)
            if stats:
                print(f"\n{component.upper()}:")
                print(f"  Total lines: {stats.total_lines}")
                print(f"  Errors: {stats.errors}")
                print(f"  Warnings: {stats.warnings}")
                if stats.tags:
                    top_tags = sorted(stats.tags.items(), key=lambda x: x[1], reverse=True)[:5]
                    print(f"  Top tags: {', '.join(f'{tag}({count})' for tag, count in top_tags)}")

        print(f"\n{'='*60}")
        print(f"✅ Logs saved to: {self.storage.build_path}")
        print(f"{'='*60}\n")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n\n⚠️  Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def run(self, duration: int = None):
        """Run collection for specified duration or until interrupted.

        Args:
            duration: Duration in seconds (None = run until interrupted)
        """
        self.start()

        try:
            if duration:
                print(f"📅 Running for {duration} seconds (Ctrl-C to stop early)...\n")
                time.sleep(duration)
            else:
                print(f"📅 Running until interrupted (Ctrl-C to stop)...\n")
                while True:
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")

        finally:
            self.stop()

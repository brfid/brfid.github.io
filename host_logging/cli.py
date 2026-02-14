"""Command-line interface for ARPANET logging system."""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
import json

from host_logging.orchestrator import LogOrchestrator


def generate_build_id() -> str:
    """Generate a build ID based on current timestamp.

    Returns:
        Build ID string (e.g., "build-20260207-221530")
    """
    return datetime.now(timezone.utc).strftime("build-%Y%m%d-%H%M%S")


def cmd_collect(args):
    """Run log collection."""
    # Generate build ID if not provided
    if not args.build_id:
        args.build_id = generate_build_id()

    # Create orchestrator
    orchestrator = LogOrchestrator(
        build_id=args.build_id,
        components=args.components,
        phase=args.phase,
        base_path=args.path
    )

    # Run collection
    orchestrator.run(duration=args.duration)


def cmd_list(args):
    """List available builds."""
    base_path = Path(args.path)
    index_path = base_path / "index.json"

    if not index_path.exists():
        print(f"No builds found at {base_path}")
        return

    with open(index_path) as f:
        builds = json.load(f)

    if not builds:
        print("No builds found")
        return

    print(f"\n{'='*80}")
    print(f"Available Builds ({len(builds)} total)")
    print(f"{'='*80}\n")

    for build in builds[:args.limit]:
        print(f"Build ID: {build['build_id']}")
        print(f"  Phase: {build['phase']}")
        print(f"  Start: {build['start_time']}")
        print(f"  End: {build.get('end_time', 'N/A')}")
        print(f"  Status: {build.get('status', 'unknown')}")
        print(f"  Components: {', '.join(build['components'])}")
        print()


def cmd_show(args):
    """Show details of a specific build."""
    base_path = Path(args.path)
    build_path = base_path / "builds" / args.build_id

    if not build_path.exists():
        print(f"Build {args.build_id} not found")
        return

    # Load metadata
    metadata_path = build_path / "metadata.json"
    with open(metadata_path) as f:
        metadata = json.load(f)

    print(f"\n{'='*80}")
    print(f"Build: {metadata['build_id']}")
    print(f"{'='*80}\n")

    print(f"Phase: {metadata['phase']}")
    print(f"Start Time: {metadata['start_time']}")
    print(f"End Time: {metadata.get('end_time', 'N/A')}")
    print(f"Status: {metadata.get('status', 'unknown')}")
    print(f"Git Commit: {metadata.get('git_commit', 'N/A')}")
    print(f"Git Branch: {metadata.get('git_branch', 'N/A')}")
    print()

    print("Components:")
    for component in metadata['components']:
        component_path = build_path / component
        summary_path = component_path / "summary.json"

        if summary_path.exists():
            with open(summary_path) as f:
                summary = json.load(f)

            print(f"\n  {component.upper()}:")
            print(f"    Total lines: {summary['total_lines']}")
            print(f"    Errors: {summary['errors']}")
            print(f"    Warnings: {summary['warnings']}")
            print(f"    First log: {summary.get('first_timestamp', 'N/A')}")
            print(f"    Last log: {summary.get('last_timestamp', 'N/A')}")

            if summary.get('tags'):
                top_tags = sorted(summary['tags'].items(), key=lambda x: x[1], reverse=True)[:5]
                print(f"    Top tags: {', '.join(f'{tag}({count})' for tag, count in top_tags)}")

    print(f"\nPath: {build_path}")
    print()


def cmd_cleanup(args):
    """Clean up old builds."""
    base_path = Path(args.path)
    builds_path = base_path / "builds"

    if not builds_path.exists():
        print(f"No builds directory at {base_path}")
        return

    # Get all build directories
    builds = sorted(builds_path.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)

    if len(builds) <= args.keep:
        print(f"Only {len(builds)} builds, nothing to clean up (keeping {args.keep})")
        return

    # Remove old builds
    to_remove = builds[args.keep:]
    print(f"Removing {len(to_remove)} old build(s)...\n")

    for build_dir in to_remove:
        print(f"  Removing: {build_dir.name}")
        import shutil
        shutil.rmtree(build_dir)

    print(f"\n✅ Cleanup complete")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ARPANET Logging System - Collect and manage ARPANET component logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect logs from VAX only
  python -m host_logging collect --components vax

  # Collect from all Phase 2 components for 60 seconds
  python -m host_logging collect --components vax imp1 imp2 --duration 60

  # List available builds
  python -m host_logging list

  # Show details of a specific build
  python -m host_logging show build-20260207-221530

  # Clean up old builds (keep last 20)
  python -m host_logging cleanup --keep 20
        """
    )

    parser.add_argument(
        "--path",
        default="/mnt/arpanet-logs",
        help="Base path for log storage (default: /mnt/arpanet-logs)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # collect command
    collect_parser = subparsers.add_parser("collect", help="Collect logs from components")
    collect_parser.add_argument(
        "--build-id",
        help="Build ID (auto-generated if not provided)"
    )
    collect_parser.add_argument(
        "--components",
        nargs="+",
        default=["vax"],
        choices=["vax", "imp1", "imp2", "pdp10"],
        help="Components to collect from"
    )
    collect_parser.add_argument(
        "--phase",
        default="phase2",
        help="Testing phase"
    )
    collect_parser.add_argument(
        "--duration",
        type=int,
        help="Duration in seconds (omit to run until interrupted)"
    )

    # list command
    list_parser = subparsers.add_parser("list", help="List available builds")
    list_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of builds to show"
    )

    # show command
    show_parser = subparsers.add_parser("show", help="Show build details")
    show_parser.add_argument("build_id", help="Build ID to show")

    # cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old builds")
    cleanup_parser.add_argument(
        "--keep",
        type=int,
        default=20,
        help="Number of recent builds to keep"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to command handlers
    if args.command == "collect":
        cmd_collect(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "cleanup":
        cmd_cleanup(args)


if __name__ == "__main__":
    main()

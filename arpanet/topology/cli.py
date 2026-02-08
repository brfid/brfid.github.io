"""Command-line interface for topology configuration generation.

Usage:
    arpanet-topology phase1 [--output PATH]
    arpanet-topology phase2 [--output PATH]
    arpanet-topology --list
"""

import argparse
import sys
from pathlib import Path

from arpanet.topology.definitions import TOPOLOGIES
from arpanet.topology.generators import write_generated_configs


def main() -> int:
    """Main entry point for arpanet-topology CLI.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    parser = argparse.ArgumentParser(
        description="Generate ARPANET topology configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate phase1 configs in current directory
  arpanet-topology phase1

  # Generate phase2 configs in specific directory
  arpanet-topology phase2 --output /path/to/project

  # List available topologies
  arpanet-topology --list
        """,
    )

    parser.add_argument(
        "topology",
        nargs="?",
        choices=list(TOPOLOGIES.keys()),
        help="Topology name to generate (phase1, phase2, etc.)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path.cwd(),
        help="Output directory (default: current directory)",
    )

    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available topologies",
    )

    args = parser.parse_args()

    # Handle --list
    if args.list:
        print("Available topologies:")
        for name, topology in TOPOLOGIES.items():
            num_hosts = len(topology.hosts)
            print(f"  {name}: {num_hosts} hosts - {topology.subnet}")
        return 0

    # Validate topology argument
    if not args.topology:
        parser.error("topology name is required (or use --list)")
        return 1

    # Generate configurations
    try:
        topology = TOPOLOGIES[args.topology]
        output_dir = args.output.resolve()

        print(f"Generating {args.topology} topology configurations...")
        print(f"Output directory: {output_dir}")
        print(f"Hosts: {', '.join(topology.hosts.keys())}")
        print()

        write_generated_configs(topology, output_dir)

        print()
        print(f"✓ Successfully generated {args.topology} configuration")
        print(f"  Docker Compose: docker-compose.arpanet.{args.topology}.yml")
        print(f"  SIMH configs: arpanet/configs/{args.topology}/")
        print()
        print("To start the topology:")
        print(f"  docker-compose -f docker-compose.arpanet.{args.topology}.yml up -d")

        return 0

    except Exception as e:
        print(f"Error generating topology: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

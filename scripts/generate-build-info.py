#!/usr/bin/env python3
"""Generate build metadata and HTML snippet for site footer.

Usage:
    python scripts/generate-build-info.py <build-id> <base-path> <output-dir>

Collects stats from logs and generates:
  - build-info.json (metadata)
  - build-info.html (dropdown snippet for site footer)
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def count_log_stats(log_file: Path) -> Dict[str, int]:
    """Count lines and log levels in a log file."""
    if not log_file.exists():
        return {"lines": 0, "errors": 0, "warnings": 0}

    lines = 0
    errors = 0
    warnings = 0

    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            lines += 1
            if ' ERROR' in line or 'ERROR]' in line:
                errors += 1
            elif ' WARN' in line or 'WARN]' in line:
                warnings += 1

    return {"lines": lines, "errors": errors, "warnings": warnings}


def generate_build_info(build_id: str, base_path: Path) -> Dict[str, Any]:
    """Generate build metadata from logs."""
    build_dir = base_path / 'builds' / build_id

    if not build_dir.exists():
        raise FileNotFoundError(f"Build directory not found: {build_dir}")

    # Collect stats for each component
    components = {}
    total_lines = 0
    total_errors = 0
    total_warnings = 0

    for log_file in sorted(build_dir.glob('*.log')):
        if log_file.name == 'merged.log':
            continue

        component = log_file.stem
        stats = count_log_stats(log_file)
        components[component] = stats
        total_lines += stats['lines']
        total_errors += stats['errors']
        total_warnings += stats['warnings']

    # Determine status
    status = "success" if total_errors == 0 else "failed"

    return {
        "build_id": build_id,
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "total_lines": total_lines,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "components": components,
    }


def generate_html_snippet(info: Dict[str, Any]) -> str:
    """Generate HTML snippet for build info dropdown."""
    status_icon = "✓" if info['status'] == 'success' else "✗"
    status_class = "success" if info['status'] == 'success' else "failed"

    # Component rows
    component_rows = ""
    for name, stats in info['components'].items():
        component_rows += f"""
        <tr>
          <td>{name}</td>
          <td>{stats['lines']:,}</td>
          <td class="{'error' if stats['errors'] > 0 else ''}">{stats['errors']}</td>
          <td class="{'warning' if stats['warnings'] > 0 else ''}">{stats['warnings']}</td>
        </tr>"""

    html = f"""
<div class="build-info">
  <button class="build-badge" onclick="this.parentElement.classList.toggle('expanded')">
    Build: {info['build_id']} <span class="status {status_class}">{status_icon}</span>
  </button>
  <div class="build-details">
    <div class="build-summary">
      <h3>Build Information</h3>
      <table>
        <tr>
          <th>Build ID:</th>
          <td>{info['build_id']}</td>
        </tr>
        <tr>
          <th>Status:</th>
          <td class="{status_class}">{info['status'].upper()} {status_icon}</td>
        </tr>
        <tr>
          <th>Timestamp:</th>
          <td>{info['timestamp']}</td>
        </tr>
        <tr>
          <th>Total Events:</th>
          <td>{info['total_lines']:,}</td>
        </tr>
        <tr>
          <th>Errors:</th>
          <td class="{'error' if info['total_errors'] > 0 else ''}">{info['total_errors']}</td>
        </tr>
        <tr>
          <th>Warnings:</th>
          <td class="{'warning' if info['total_warnings'] > 0 else ''}">{info['total_warnings']}</td>
        </tr>
      </table>
    </div>
    <div class="component-stats">
      <h4>Components</h4>
      <table>
        <thead>
          <tr>
            <th>Component</th>
            <th>Events</th>
            <th>Errors</th>
            <th>Warnings</th>
          </tr>
        </thead>
        <tbody>{component_rows}
        </tbody>
      </table>
    </div>
    <div class="build-logs">
      <h4>Logs</h4>
      <ul>
        <li><a href="build-logs/merged.log" target="_blank">📄 merged.log</a> - Chronological from all sources</li>
        <li><a href="build-logs/VAX.log" target="_blank">📄 VAX.log</a> - VAX-specific events</li>
        <li><a href="build-logs/PDP11.log" target="_blank">📄 PDP11.log</a> - PDP-11-specific events</li>
        <li><a href="build-logs/GITHUB.log" target="_blank">📄 GITHUB.log</a> - GitHub Actions events</li>
      </ul>
    </div>
  </div>
</div>"""

    return html


def main() -> int:
    """Main entry point."""
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <build-id> <base-path> <output-dir>", file=sys.stderr)
        return 1

    build_id = sys.argv[1]
    base_path = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])

    # Generate build info
    try:
        info = generate_build_info(build_id, base_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Write JSON
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'build-info.json'
    with open(json_path, 'w') as f:
        json.dump(info, f, indent=2)
    print(f"✅ Generated: {json_path}")

    # Write HTML snippet
    html = generate_html_snippet(info)
    html_path = output_dir / 'build-info.html'
    with open(html_path, 'w') as f:
        f.write(html)
    print(f"✅ Generated: {html_path}")

    return 0


if __name__ == '__main__':
    sys.exit(main())

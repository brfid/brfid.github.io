#!/usr/bin/env python3
"""
Enterprise Logs Page Generator

Parses build logs and generates a professional, enterprise-quality logs viewer page
with timeline view, filtering, search, and evidence highlighting.

Usage:
    python3 scripts/generate-logs-page.py \\
        --build-id "build-20260214-121649" \\
        --merged site/build-logs/merged.log \\
        --output site/logs/index.html
"""

import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# Evidence patterns for vintage tool detection
EVIDENCE_PATTERNS = [
    (r'Compiler:.*BSD.*198\d', 'VAX Compiler (1986)', 'vax'),
    (r'Compiler:.*4\.3BSD.*K&R', 'VAX K&R C Compiler', 'vax'),
    (r'cc.*4\.3BSD', 'VAX C Compiler', 'vax'),
    (r'OS:.*BSD.*198\d', 'VAX Operating System', 'vax'),
    (r'Tool:.*dated.*199\d', 'PDP-11 Tools (1990s)', 'pdp11'),
    (r'uuencode|uudecode', 'Historical Transfer Method', 'courier'),
    (r'Console transfer|telnet.*2327', 'Console I/O Transfer', 'courier'),
    (r'Parser:.*bradman.*VAX', 'VAX C YAML Parser', 'vax'),
]


def parse_log_line(line: str) -> Optional[Dict]:
    """
    Parse a log line in format: [YYYY-MM-DD HH:MM:SS MACHINE] message

    Returns dict with timestamp, machine, message, and evidence flag
    """
    match = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (\w+)\] (.+)', line.strip())
    if not match:
        return None

    timestamp, machine, message = match.groups()
    machine = machine.upper()

    # Check for evidence patterns
    is_evidence = False
    evidence_label = None
    for pattern, label, _ in EVIDENCE_PATTERNS:
        if re.search(pattern, message, re.I):
            is_evidence = True
            evidence_label = label
            break

    return {
        'timestamp': timestamp,
        'machine': machine,
        'message': message,
        'is_evidence': is_evidence,
        'evidence_label': evidence_label
    }


def calculate_stats(logs: List[Dict]) -> Dict:
    """Calculate statistics from parsed logs"""
    if not logs:
        return {
            'total_events': 0,
            'duration': 0,
            'errors': 0,
            'warnings': 0,
            'per_machine': {}
        }

    # Count events per machine
    per_machine = {}
    errors = 0
    warnings = 0

    for log in logs:
        machine = log['machine']
        per_machine[machine] = per_machine.get(machine, 0) + 1

        # Count errors and warnings
        message_lower = log['message'].lower()
        if 'error' in message_lower or 'failed' in message_lower:
            errors += 1
        if 'warning' in message_lower or 'warn' in message_lower:
            warnings += 1

    # Calculate duration
    start_time = datetime.strptime(logs[0]['timestamp'], '%Y-%m-%d %H:%M:%S')
    end_time = datetime.strptime(logs[-1]['timestamp'], '%Y-%m-%d %H:%M:%S')
    duration = int((end_time - start_time).total_seconds())

    return {
        'total_events': len(logs),
        'duration': duration,
        'errors': errors,
        'warnings': warnings,
        'per_machine': per_machine
    }


def get_machine_color(machine: str) -> str:
    """Get color for machine badge"""
    colors = {
        'VAX': '#00aaff',
        'PDP11': '#ff8800',
        'GITHUB': '#24292e',
        'COURIER': '#9b59b6',
    }
    return colors.get(machine, '#6c757d')


def generate_html(logs: List[Dict], build_id: str, stats: Dict) -> str:
    """Generate complete HTML page with embedded logs"""

    # Extract evidence logs
    evidence_logs = [log for log in logs if log['is_evidence']]

    # Get unique machines for filter buttons
    machines = sorted(set(log['machine'] for log in logs))

    # Generate machine filter buttons HTML
    filter_buttons = '\n'.join([
        f'<button class="filter-btn" data-machine="{machine}" style="--machine-color: {get_machine_color(machine)}">{machine}</button>'
        for machine in machines
    ])

    # Generate component stats rows
    component_rows = '\n'.join([
        f'<tr><td>{machine}</td><td>{count}</td></tr>'
        for machine, count in sorted(stats['per_machine'].items())
    ])

    # Generate log lines HTML
    log_lines = []
    for log in logs:
        evidence_class = ' evidence' if log['is_evidence'] else ''
        evidence_icon = ' <span class="evidence-icon" title="Authenticity Evidence">⭐</span>' if log['is_evidence'] else ''
        machine_color = get_machine_color(log['machine'])

        log_lines.append(f'''
        <div class="log-line{evidence_class}" data-machine="{log['machine']}" data-full-timestamp="{log['timestamp']}">
            <span class="timestamp">{log['timestamp'].split()[1]}</span>
            <span class="machine-badge" style="background: {machine_color}">{log['machine']}</span>
            <span class="message">{escape_html(log['message'])}{evidence_icon}</span>
        </div>''')

    log_lines_html = '\n'.join(log_lines)

    # Generate evidence section HTML
    evidence_items = []
    for log in evidence_logs:
        machine_color = get_machine_color(log['machine'])
        evidence_items.append(f'''
        <div class="evidence-item">
            <div class="evidence-header">
                <span class="machine-badge" style="background: {machine_color}">{log['machine']}</span>
                <span class="evidence-label">{log['evidence_label']}</span>
            </div>
            <div class="evidence-message">{escape_html(log['message'])}</div>
        </div>''')

    evidence_html = '\n'.join(evidence_items) if evidence_items else '<p class="no-evidence">No evidence lines detected in this build.</p>'

    # Determine status
    status = 'success' if stats['errors'] == 0 else 'failed'
    status_icon = '✓' if status == 'success' else '✗'

    # Generate HTML
    html = f'''<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Build Logs: {build_id} | Bradley Fidler</title>
    <meta name="color-scheme" content="dark" />
    <style>
        :root {{
            --bg: #0f1115;
            --card: #151a23;
            --text: #e8eefc;
            --muted: #a8b3cf;
            --border: rgba(232, 238, 252, 0.12);
            --link: #e8eefc;
            --shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
            --success: #2ecc71;
            --failed: #e74c3c;
            --warning: #f39c12;
        }}

        html, body {{
            height: 100%;
        }}

        body {{
            margin: 0;
            background: radial-gradient(1200px 600px at 20% 0%, #131a2b, var(--bg));
            color: var(--text);
            font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial,
                "Apple Color Emoji", "Segoe UI Emoji";
            line-height: 1.45;
        }}

        a {{
            color: var(--link);
            text-decoration: none;
        }}

        a:hover, a:focus-visible {{
            text-decoration: underline;
            outline: none;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem 1.25rem 4rem;
        }}

        .header {{
            margin-bottom: 2rem;
        }}

        .header h1 {{
            font-size: 1.75rem;
            font-weight: 650;
            margin: 0 0 0.5rem 0;
            letter-spacing: 0.2px;
        }}

        .build-meta {{
            display: flex;
            gap: 1rem;
            align-items: center;
            flex-wrap: wrap;
            color: var(--muted);
            font-size: 0.95rem;
        }}

        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            background: var(--{status});
            color: white;
            font-weight: 600;
            font-size: 0.85rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: var(--shadow);
        }}

        .stat-label {{
            color: var(--muted);
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
        }}

        .stat-value {{
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text);
        }}

        .component-table {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: var(--shadow);
            margin-bottom: 2rem;
        }}

        .component-table h2 {{
            font-size: 1.1rem;
            margin: 0 0 1rem 0;
            color: var(--text);
        }}

        .component-table table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .component-table th {{
            text-align: left;
            padding: 0.5rem;
            color: var(--muted);
            font-size: 0.85rem;
            border-bottom: 1px solid var(--border);
        }}

        .component-table td {{
            padding: 0.5rem;
            border-bottom: 1px solid rgba(232, 238, 252, 0.06);
        }}

        .controls {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: var(--shadow);
            margin-bottom: 1rem;
        }}

        .controls-row {{
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: center;
        }}

        .filter-buttons {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}

        .filter-btn {{
            padding: 0.5rem 1rem;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.015);
            color: var(--muted);
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .filter-btn:hover {{
            border-color: var(--machine-color);
            background: rgba(255, 255, 255, 0.03);
        }}

        .filter-btn.active {{
            border-color: var(--machine-color);
            background: var(--machine-color);
            color: white;
            font-weight: 600;
        }}

        .search-box {{
            flex: 1;
            min-width: 250px;
            padding: 0.5rem 1rem;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.015);
            color: var(--text);
            font-size: 0.9rem;
        }}

        .search-box::placeholder {{
            color: var(--muted);
        }}

        .export-btn {{
            padding: 0.5rem 1rem;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.015);
            color: var(--muted);
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .export-btn:hover {{
            border-color: var(--link);
            background: rgba(255, 255, 255, 0.03);
            color: var(--text);
        }}

        .log-viewer {{
            background: #0a0c10;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem;
            box-shadow: var(--shadow);
            margin-bottom: 2rem;
            max-height: 600px;
            overflow-y: auto;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 0.85rem;
        }}

        .log-line {{
            display: flex;
            gap: 0.75rem;
            padding: 0.4rem 0.5rem;
            align-items: flex-start;
            border-bottom: 1px solid rgba(232, 238, 252, 0.03);
        }}

        .log-line:hover {{
            background: rgba(255, 255, 255, 0.02);
        }}

        .log-line.hidden {{
            display: none;
        }}

        .log-line.evidence {{
            background: rgba(46, 204, 113, 0.05);
            border-left: 3px solid var(--success);
            padding-left: calc(0.5rem - 3px);
        }}

        .timestamp {{
            color: var(--muted);
            flex-shrink: 0;
            font-size: 0.8rem;
        }}

        .machine-badge {{
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            color: white;
            font-weight: 600;
            font-size: 0.75rem;
            flex-shrink: 0;
            min-width: 70px;
            text-align: center;
        }}

        .message {{
            color: var(--text);
            flex: 1;
            word-break: break-word;
        }}

        .evidence-icon {{
            color: var(--success);
            font-size: 1rem;
        }}

        .evidence-section {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: var(--shadow);
            margin-bottom: 2rem;
        }}

        .evidence-section h2 {{
            font-size: 1.1rem;
            margin: 0 0 1rem 0;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .evidence-item {{
            margin-bottom: 1rem;
            padding: 0.75rem;
            background: rgba(255, 255, 255, 0.015);
            border-radius: 8px;
            border-left: 3px solid var(--success);
        }}

        .evidence-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.5rem;
        }}

        .evidence-label {{
            color: var(--success);
            font-weight: 600;
            font-size: 0.85rem;
        }}

        .evidence-message {{
            color: var(--muted);
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 0.8rem;
        }}

        .no-evidence {{
            color: var(--muted);
            font-style: italic;
        }}

        .footer {{
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border);
            color: var(--muted);
            font-size: 0.9rem;
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
        }}

        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}

            .controls-row {{
                flex-direction: column;
                align-items: stretch;
            }}

            .search-box {{
                min-width: auto;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>Build Logs</h1>
            <div class="build-meta">
                <span>Build: <strong>{build_id}</strong></span>
                <span class="status-badge">{status_icon} {status.upper()}</span>
            </div>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Events</div>
                <div class="stat-value">{stats['total_events']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Duration</div>
                <div class="stat-value">{stats['duration']}s</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Errors</div>
                <div class="stat-value" style="color: {('var(--failed)' if stats['errors'] > 0 else 'var(--text)')}">{stats['errors']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Warnings</div>
                <div class="stat-value" style="color: {('var(--warning)' if stats['warnings'] > 0 else 'var(--text)')}">{stats['warnings']}</div>
            </div>
        </div>

        <div class="component-table">
            <h2>Component Statistics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Component</th>
                        <th>Events</th>
                    </tr>
                </thead>
                <tbody>
                    {component_rows}
                </tbody>
            </table>
        </div>

        <div class="controls">
            <div class="controls-row">
                <div class="filter-buttons">
                    <button class="filter-btn active" data-machine="all" style="--machine-color: var(--link)">All</button>
                    {filter_buttons}
                </div>
                <input type="text" class="search-box" placeholder="Search logs..." id="searchBox" />
                <button class="export-btn" id="exportBtn">Export Logs</button>
            </div>
        </div>

        <div class="log-viewer" id="logViewer">
            {log_lines_html}
        </div>

        <div class="evidence-section">
            <h2>⭐ Authenticity Evidence</h2>
            <p style="color: var(--muted); margin-bottom: 1rem; font-size: 0.9rem;">
                Key lines proving the use of vintage tools (1986 VAX compiler, 1970s-80s transfer methods).
            </p>
            {evidence_html}
        </div>

        <footer class="footer">
            <a href="/">← Back to Home</a>
            <a href="/build-logs/merged.log">View Raw Logs</a>
            <a href="/build-logs/VAX.log">VAX Log</a>
            <a href="/build-logs/COURIER.log">COURIER Log</a>
            <a href="/build-logs/GITHUB.log">GITHUB Log</a>
        </footer>
    </div>

    <script src="/logs/logs.js"></script>
</body>
</html>'''

    return html


def escape_html(text: str) -> str:
    """Escape HTML special characters"""
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;'))


def main():
    parser = argparse.ArgumentParser(description='Generate enterprise logs viewer page')
    parser.add_argument('--build-id', required=True, help='Build ID (e.g., build-20260214-121649)')
    parser.add_argument('--merged', required=True, help='Path to merged.log file')
    parser.add_argument('--output', required=True, help='Output HTML path')
    args = parser.parse_args()

    # Read merged.log
    merged_path = Path(args.merged)
    if not merged_path.exists():
        print(f"Error: {args.merged} not found")
        return 1

    with open(merged_path) as f:
        lines = f.readlines()

    # Parse logs
    logs = []
    for line in lines:
        parsed = parse_log_line(line)
        if parsed:
            logs.append(parsed)

    if not logs:
        print("Warning: No valid log lines found")
        return 1

    # Calculate stats
    stats = calculate_stats(logs)

    # Generate HTML
    html = generate_html(logs, args.build_id, stats)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✓ Generated logs page: {args.output}")
    print(f"  Total events: {stats['total_events']}")
    print(f"  Duration: {stats['duration']}s")
    print(f"  Components: {', '.join(sorted(stats['per_machine'].keys()))}")
    print(f"  Evidence lines: {sum(1 for log in logs if log['is_evidence'])}")

    return 0


if __name__ == '__main__':
    exit(main())

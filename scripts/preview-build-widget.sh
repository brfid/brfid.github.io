#!/bin/bash
# Quick preview of the build info widget with mock data

set -e

echo "🎨 Generating preview with mock build info..."

# Activate venv
source .venv/bin/activate

# Generate the site first
python -m resume_generator --out site --with-vax --vax-mode local

# Create mock build info files
mkdir -p site/build-info
mkdir -p site/build-logs

# Mock build info HTML
cat > site/build-info/build-info.html << 'EOF'
<div class="build-info">
  <button class="build-badge" onclick="this.parentElement.classList.toggle('expanded')">
    Build: build-20260213-154523 <span class="status success">✓</span>
  </button>
  <div class="build-details">
    <div class="build-summary">
      <h3>Build Information</h3>
      <table>
        <tr>
          <th>Build ID:</th>
          <td>build-20260213-154523</td>
        </tr>
        <tr>
          <th>Status:</th>
          <td class="success">SUCCESS ✓</td>
        </tr>
        <tr>
          <th>Timestamp:</th>
          <td>2026-02-13T15:45:23Z</td>
        </tr>
        <tr>
          <th>Total Events:</th>
          <td>1,247</td>
        </tr>
        <tr>
          <th>Errors:</th>
          <td>0</td>
        </tr>
        <tr>
          <th>Warnings:</th>
          <td>3</td>
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
        <tbody>
        <tr>
          <td>VAX</td>
          <td>847</td>
          <td>0</td>
          <td class="warning">2</td>
        </tr>
        <tr>
          <td>GITHUB</td>
          <td>234</td>
          <td>0</td>
          <td class="warning">1</td>
        </tr>
        <tr>
          <td>PDP11</td>
          <td>166</td>
          <td>0</td>
          <td>0</td>
        </tr>
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
</div>
EOF

# Copy CSS
cp templates/build-info.css site/build-info/

# Create mock log files
cat > site/build-logs/merged.log << 'EOF'
[2026-02-13 15:45:23 GITHUB] Starting AWS VAX instance...
[2026-02-13 15:45:45 GITHUB] Transferring files to VAX...
[2026-02-13 15:46:02 VAX] cc -o bradman bradman.c
[2026-02-13 15:46:08 VAX] bradman: parsing resume.vax.yaml
[2026-02-13 15:46:12 VAX] bradman: truncating long title (warning)
[2026-02-13 15:46:15 VAX] bradman: generating roff output
[2026-02-13 15:46:18 VAX] Build complete
[2026-02-13 15:46:25 GITHUB] Retrieving build output...
[2026-02-13 15:46:30 GITHUB] Build successful
EOF

cp site/build-logs/merged.log site/build-logs/VAX.log
cp site/build-logs/merged.log site/build-logs/PDP11.log
cp site/build-logs/merged.log site/build-logs/GITHUB.log

# Regenerate landing page to include build info
python -m resume_generator --out site --with-vax --vax-mode local

echo ""
echo "✅ Preview ready!"
echo ""
echo "Open: file://$(pwd)/site/index.html"
echo ""
echo "Look for the build badge in the bottom-right corner."
echo "Click it to see the dropdown!"

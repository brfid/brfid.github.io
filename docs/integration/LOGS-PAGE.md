# Enterprise Logs Page

**Status**: ✅ Implemented (2026-02-14)
**URL**: https://brfid.github.io/logs/
**Purpose**: Professional, enterprise-quality viewer for build logs with authenticity evidence highlighting

---

## Overview

The enterprise logs page transforms raw build logs into a professional, interactive viewer that:

1. **Proves Historical Authenticity**: Highlights evidence of vintage tools (1986 VAX compiler, 1970s-80s transfer methods)
2. **Shows System Coordination**: Timeline view of VAX, PDP-11, GitHub Actions, and COURIER working together
3. **Enables Exploration**: Filtering by component, search functionality, and export capabilities
4. **Maintains Cold-Start Readiness**: Fully documented for future maintenance

---

## Features

### Timeline View
- Chronological display of all build events
- Color-coded machine badges (VAX, PDP-11, GITHUB, COURIER)
- Evidence lines highlighted with ⭐ icon and green accent

### Statistics Dashboard
- Total events count
- Build duration
- Error and warning counts
- Per-component event breakdown

### Interactive Filtering
- Filter by component (All/VAX/PDP-11/GITHUB/COURIER)
- Real-time search across messages and timestamps
- Export visible logs to `.txt` file

### Authenticity Evidence Section
- Dedicated section showing vintage tool proof
- Key lines extracted automatically via regex patterns
- Examples: "cc (4.3BSD K&R C)", "uuencode", "Console transfer"

### Progressive Enhancement
- Page works without JavaScript (pre-rendered HTML)
- JavaScript adds filtering, search, and export
- Fast initial load via server-side generation

---

## Architecture

### Build Time (GitHub Actions)

**Script**: `scripts/generate-logs-page.py`

**Process**:
1. Read `site/build-logs/merged.log`
2. Parse format: `[YYYY-MM-DD HH:MM:SS MACHINE] message`
3. Detect evidence lines via regex patterns
4. Calculate statistics (event counts, duration, errors/warnings)
5. Generate HTML with embedded log lines
6. Write `site/logs/index.html`

**Evidence Detection**:
```python
EVIDENCE_PATTERNS = [
    (r'Compiler:.*BSD.*198\d', 'VAX Compiler (1986)', 'vax'),
    (r'Compiler:.*4\.3BSD.*K&R', 'VAX K&R C Compiler', 'vax'),
    (r'cc.*4\.3BSD', 'VAX C Compiler', 'vax'),
    (r'Tool:.*dated.*199\d', 'PDP-11 Tools (1990s)', 'pdp11'),
    (r'uuencode|uudecode', 'Historical Transfer Method', 'courier'),
    (r'Console transfer|telnet.*2327', 'Console I/O Transfer', 'courier'),
    (r'Parser:.*bradman.*VAX', 'VAX C YAML Parser', 'vax'),
]
```

### Runtime (Browser)

**Script**: `site/logs/logs.js`

**Features**:
- Machine filtering (show/hide log lines by component)
- Search with debouncing (300ms delay for performance)
- Export to `.txt` file (via blob URL download)
- Progressive enhancement (works without JS)

---

## File Structure

```
site/
├── logs/
│   ├── index.html       # Generated logs viewer page
│   └── logs.js          # Client-side interactivity
└── build-logs/          # Source data (generated during build)
    ├── merged.log       # All logs merged chronologically
    ├── VAX.log          # VAX component logs
    ├── PDP11.log        # PDP-11 component logs
    ├── COURIER.log      # COURIER transfer logs
    └── GITHUB.log       # GitHub Actions logs

scripts/
└── generate-logs-page.py  # Build-time generator

docs/integration/
└── LOGS-PAGE.md          # This document
```

---

## Maintenance

### Adding New Evidence Patterns

Edit `scripts/generate-logs-page.py`:

```python
EVIDENCE_PATTERNS = [
    # Existing patterns...
    (r'your-regex-pattern', 'Display Label', 'machine'),
]
```

**Pattern format**: `(regex_pattern, label, machine_tag)`

**Example**:
```python
(r'BSD.*1986', 'VAX Operating System', 'vax'),
```

### Updating Styles

**Color Scheme** (matching site theme):
- Background: `#0f1115` (dark blue-black)
- Card: `#151a23` (slightly lighter)
- Text: `#e8eefc` (light blue-white)
- Muted: `#a8b3cf` (gray-blue)

**Machine Colors**:
- VAX: `#00aaff` (cyan)
- PDP-11: `#ff8800` (orange)
- GITHUB: `#24292e` (dark gray)
- COURIER: `#9b59b6` (purple)

To modify, edit the `<style>` section in the HTML template within `scripts/generate-logs-page.py`.

### Updating JavaScript Features

Edit `site/logs/logs.js`:

**Add new filter**:
```javascript
setFilter(machine) {
    this.activeFilter = machine;
    this.applyFilters();
    // Add custom logic here
}
```

**Change search behavior**:
```javascript
initializeSearch() {
    // Modify debounce timeout (default: 300ms)
    this.searchTimeout = setTimeout(() => {
        this.searchTerm = e.target.value.toLowerCase();
        this.applyFilters();
    }, 500); // Changed to 500ms
}
```

---

## Integration Points

### GitHub Actions Workflow

**File**: `.github/workflows/deploy.yml`

**Step**: "Generate enterprise logs page" (runs after log collection)

```yaml
- name: Generate enterprise logs page
  if: steps.mode.outputs.vax_mode == 'docker'
  env:
    BUILD_ID: ${{ steps.build_id.outputs.build_id }}
  run: |
    python3 scripts/generate-logs-page.py \
      --build-id "$BUILD_ID" \
      --merged site/build-logs/merged.log \
      --output site/logs/index.html
```

### Site Navigation

**File**: `site/index.html` (line 165)

```html
<footer>
    <a href="/logs/">build logs</a>
</footer>
```

---

## Testing

### Local Testing

```bash
# Generate logs page
python3 scripts/generate-logs-page.py \
    --build-id "build-20260214-121649" \
    --merged site/build-logs/merged.log \
    --output site/logs/index.html

# Serve locally
cd site
python3 -m http.server 8000

# Open: http://localhost:8000/logs/
```

### Manual Test Checklist

**Visual**:
- [ ] Page matches dark theme aesthetic
- [ ] Stats dashboard displays correct counts
- [ ] Log lines have color-coded machine badges
- [ ] Evidence section shows highlighted lines
- [ ] Responsive layout works on mobile (<768px)

**Functional**:
- [ ] Filter buttons toggle (All/VAX/PDP-11/GITHUB/COURIER)
- [ ] Active filter shows correct log subset
- [ ] Search box filters in real-time
- [ ] Export downloads correct `.txt` file
- [ ] Navigation: Home → Logs → Home works
- [ ] Raw log links still accessible

**Cross-Browser**:
- [ ] Chrome/Edge
- [ ] Firefox
- [ ] Safari
- [ ] Mobile Safari

**Accessibility**:
- [ ] Keyboard navigation (tab through filters)
- [ ] Color contrast meets WCAG AA
- [ ] Search box has label

---

## Production Deployment

### Automatic Deployment

Logs page is auto-generated during GitHub Actions deploy when using `publish-vax` or `publish-docker` tags.

**Workflow**:
1. Push code to `main` branch
2. Tag commit: `git tag publish-vax && git push origin publish-vax`
3. GitHub Actions runs full build pipeline
4. Logs collected from VAX, PDP-11, COURIER, GitHub
5. Logs merged chronologically
6. **Logs page generated** from merged logs
7. Deployed to GitHub Pages

**URL**: https://brfid.github.io/logs/

### Manual Regeneration

If you need to regenerate the logs page from existing logs:

```bash
# From project root
python3 scripts/generate-logs-page.py \
    --build-id "build-YYYYMMDD-HHMMSS" \
    --merged site/build-logs/merged.log \
    --output site/logs/index.html

# Commit and push
git add site/logs/index.html
git commit -m "docs: regenerate logs page"
git push origin main
```

---

## Cold Start Instructions

**Scenario**: You're returning to this project after months/years away.

**Quick Start**:

1. **Understand the System**:
   - Read this document (you're doing it!)
   - Review `CHANGELOG.md` for current project state
   - Check `docs/PRE-DEPLOY-CHECKLIST.md` for deployment flow

2. **View Logs Page**:
   - Visit: https://brfid.github.io/logs/
   - Inspect features: filtering, search, evidence highlighting
   - Check browser console for any errors

3. **Make Changes**:
   - Update patterns: Edit `scripts/generate-logs-page.py`
   - Update styles: Modify `<style>` section in Python template
   - Update features: Edit `site/logs/logs.js`

4. **Test Locally**:
   ```bash
   python3 scripts/generate-logs-page.py \
       --build-id "test-$(date +%Y%m%d-%H%M%S)" \
       --merged site/build-logs/merged.log \
       --output site/logs/index.html

   cd site && python3 -m http.server 8000
   # Open: http://localhost:8000/logs/
   ```

5. **Deploy**:
   ```bash
   git add .
   git commit -m "feat: update logs page [description]"
   git tag publish-vax
   git push origin main --tags
   ```

---

## Design Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Layout** | Unified timeline | Shows build flow chronologically, matches Grafana/Datadog patterns |
| **Data Loading** | Server-side generation | Faster page load, SEO-friendly, works without JS |
| **Filtering** | Client-side JavaScript | Simple implementation, instant response, no server needed |
| **Styling** | Inline CSS in HTML | Self-contained page, easier deployment, fewer HTTP requests |
| **Evidence Detection** | Regex patterns | Automated, consistent, easy to extend |
| **Machine Colors** | Existing palette | Consistency with build-info widget |
| **No Pagination** | Single page display | Current logs ~50 lines, fast rendering |

---

## Troubleshooting

### Problem: No evidence lines shown

**Cause**: Evidence patterns not matching log content

**Fix**:
1. Check `site/build-logs/merged.log` for actual log content
2. Update `EVIDENCE_PATTERNS` in `scripts/generate-logs-page.py`
3. Regenerate page

### Problem: Stats show 0 events

**Cause**: Log parsing failed (wrong format)

**Fix**:
1. Verify merged.log format: `[YYYY-MM-DD HH:MM:SS MACHINE] message`
2. Check `parse_log_line()` regex in `scripts/generate-logs-page.py`
3. Run script with verbose output to debug parsing

### Problem: Filtering doesn't work

**Cause**: JavaScript not loading or error

**Fix**:
1. Check browser console for errors
2. Verify `site/logs/logs.js` is deployed
3. Check `<script src="/logs/logs.js"></script>` tag in HTML

### Problem: Export downloads empty file

**Cause**: No visible logs after filtering

**Fix**:
1. Clear filters (click "All")
2. Clear search box
3. Check browser console for errors in `exportLogs()` function

---

## Future Enhancements

**Phase 2** (not yet implemented):
- Build history: Show multiple past builds in dropdown
- JSON log viewer toggle: Switch between timeline and raw JSON
- Advanced regex search: User-provided regex patterns
- Virtual scrolling: Handle very large logs (1000+ lines)
- Timestamp filtering: Show logs in specific time ranges
- Permalinks: Deep links to specific log lines (e.g., `/logs/#L42`)

**Phase 3** (future):
- Log diffing: Compare two builds side-by-side
- Performance metrics: Build duration trends over time
- Evidence summary: Count of evidence types per build
- Export formats: CSV, JSON, HTML

---

## Related Documentation

- **Project Status**: `CHANGELOG.md`
- **Deployment Guide**: `docs/PRE-DEPLOY-CHECKLIST.md`
- **Build Info Widget**: `templates/build-info-widget.html`
- **Log Collection**: `scripts/merge-logs.py`
- **GitHub Workflow**: `.github/workflows/deploy.yml`

---

## Change Log

**2026-02-14**: Initial implementation
- Created `scripts/generate-logs-page.py`
- Created `site/logs/logs.js`
- Integrated into GitHub Actions workflow
- Updated site navigation footer link
- Added comprehensive documentation

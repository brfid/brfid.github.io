# Expected Log Format - Authentic Vintage Build

Based on the updated logging scripts, here's what the actual logs will contain when the pipeline runs.

## Log Structure

### Directory Layout
```
/mnt/arpanet-logs/builds/<build-id>/
├── VAX.log           # VAX compilation logs
├── PDP11.log         # PDP-11 validation logs
├── GITHUB.log        # GitHub Actions orchestration
├── COURIER.log       # Console transfer logs (optional)
└── merged.log        # Chronologically merged all logs
```

### Log Format
```
[YYYY-MM-DD HH:MM:SS MACHINE] message
```

- **Timestamp**: UTC, second precision (BSD date limitation)
- **Machine**: VAX, PDP11, GITHUB, COURIER
- **Message**: Free-form text, may span multiple lines

---

## Example: VAX.log

This shows actual vintage K&R C compilation with tool evidence:

```log
[2026-02-14 18:30:00 VAX] === VAX BUILD & ENCODE ===
[2026-02-14 18:30:00 VAX] Build ID: build-20260214-183000
[2026-02-14 18:30:00 VAX] Date: Thu Feb 14 18:30:00 UTC 2026
[2026-02-14 18:30:00 VAX]
[2026-02-14 18:30:00 VAX] System Information:
[2026-02-14 18:30:01 VAX]   OS: 4.3 BSD UNIX #1: Fri Jun  6 19:55:29 PDT 1986
[2026-02-14 18:30:01 VAX]   Hostname: vax
[2026-02-14 18:30:01 VAX]
[2026-02-14 18:30:01 VAX] Compiling bradman.c...
[2026-02-14 18:30:01 VAX]   Compiler: cc: Berkeley C compiler, version 4.3 BSD, 7 June 1986
[2026-02-14 18:30:02 VAX]   Compiler binary: /bin/cc (45056 bytes, dated Jun  7  1986)
[2026-02-14 18:30:02 VAX]   Source: bradman.c (1037 lines)
[2026-02-14 18:30:05 VAX] Compilation successful
[2026-02-14 18:30:05 VAX]   Binary size: 45056 bytes
[2026-02-14 18:30:05 VAX]
[2026-02-14 18:30:05 VAX] Generating manpage from resume.vax.yaml...
[2026-02-14 18:30:06 VAX]   Input: resume.vax.yaml (50 lines)
[2026-02-14 18:30:06 VAX]   Parser: bradman (VAX C YAML parser)
[2026-02-14 18:30:08 VAX] Manpage generated successfully
[2026-02-14 18:30:08 VAX]   Output: brad.1 (8192 bytes, 200 lines)
[2026-02-14 18:30:08 VAX]   Sections: 8 (.SH directives)
[2026-02-14 18:30:08 VAX]   Format: troff/nroff man(7) macros
[2026-02-14 18:30:09 VAX]   Sample (first 3 lines):
[2026-02-14 18:30:09 VAX]     .TH BRAD 1 "February 2026" "Resume" "User Commands"
[2026-02-14 18:30:09 VAX]     .SH NAME
[2026-02-14 18:30:09 VAX]     Brad Field \- Software Engineer
[2026-02-14 18:30:09 VAX]
[2026-02-14 18:30:09 VAX] Encoding output for console transfer...
[2026-02-14 18:30:10 VAX]   Tool: uuencode (6366 bytes, dated Jun  7  1986)
[2026-02-14 18:30:12 VAX] Encoding complete
[2026-02-14 18:30:12 VAX]   Original file: brad.1 (8192 bytes)
[2026-02-14 18:30:12 VAX]   Encoded file: brad.1.uu (10920 bytes, 340 lines)
[2026-02-14 18:30:12 VAX]   Overhead: 33%
[2026-02-14 18:30:12 VAX] VAX build complete - Output ready for transfer
```

### Key Evidence Points in VAX.log

1. **Compiler Version**: `cc: Berkeley C compiler, version 4.3 BSD, 7 June 1986`
   - ✅ Proves actual 1986 compiler used

2. **Binary Date**: `dated Jun  7  1986`
   - ✅ Proves original BSD binary, not modern rebuild

3. **Tool Sizes**: Exact byte counts matching vintage BSD distribution
   - ✅ Cross-verifiable with BSD 4.3 archives

4. **OS Version**: `4.3 BSD UNIX #1: Fri Jun  6 19:55:29 PDT 1986`
   - ✅ Proves vintage OS kernel

---

## Example: PDP11.log

This shows validation on 2.11BSD with vintage nroff:

```log
[2026-02-14 18:30:20 PDP11] === PDP-11 VALIDATION ===
[2026-02-14 18:30:20 PDP11] Build ID: build-20260214-183000
[2026-02-14 18:30:20 PDP11] Date: Thu Feb 14 18:30:20 UTC 2026
[2026-02-14 18:30:20 PDP11]
[2026-02-14 18:30:20 PDP11] System Information:
[2026-02-14 18:30:21 PDP11]   OS: 2.11 BSD UNIX #1: Sun Nov  7 22:40:28 PST 1999
[2026-02-14 18:30:21 PDP11]   Hostname: pdp11
[2026-02-14 18:30:21 PDP11]
[2026-02-14 18:30:21 PDP11] Step 1: Decoding uuencoded file...
[2026-02-14 18:30:21 PDP11]   Input: /tmp/brad.1.uu
[2026-02-14 18:30:22 PDP11]   Size: 10920 bytes, 340 lines
[2026-02-14 18:30:22 PDP11]   Tool: uudecode (16716 bytes, dated Nov  7  1999)
[2026-02-14 18:30:25 PDP11]   ✓ Decode successful
[2026-02-14 18:30:25 PDP11]   Output: brad.1 (8192 bytes, 200 lines)
[2026-02-14 18:30:25 PDP11]   Sections: 8 (.SH directives)
[2026-02-14 18:30:26 PDP11]   Sample (first 3 lines):
[2026-02-14 18:30:26 PDP11]     .TH BRAD 1 "February 2026" "Resume" "User Commands"
[2026-02-14 18:30:26 PDP11]     .SH NAME
[2026-02-14 18:30:26 PDP11]     Brad Field \- Software Engineer
[2026-02-14 18:30:26 PDP11]
[2026-02-14 18:30:26 PDP11] Step 2: Rendering with nroff...
[2026-02-14 18:30:27 PDP11]   Tool: nroff -man (44940 bytes, dated Nov  7  1999)
[2026-02-14 18:30:27 PDP11]   Purpose: Validate manpage format and render to text
[2026-02-14 18:30:30 PDP11]   ✓ Rendering successful
[2026-02-14 18:30:30 PDP11]   Output: brad.txt (4096 bytes, 120 lines)
[2026-02-14 18:30:31 PDP11]   Sample (first 5 lines):
[2026-02-14 18:30:31 PDP11]     BRAD(1)                User Commands               BRAD(1)
[2026-02-14 18:30:31 PDP11]
[2026-02-14 18:30:31 PDP11]     NAME
[2026-02-14 18:30:31 PDP11]            Brad Field - Software Engineer
[2026-02-14 18:30:31 PDP11]
[2026-02-14 18:30:31 PDP11]
[2026-02-14 18:30:31 PDP11] Validation Summary:
[2026-02-14 18:30:31 PDP11]   ✓ uuencode transfer: Successful
[2026-02-14 18:30:32 PDP11]   ✓ uudecode: Successful
[2026-02-14 18:30:32 PDP11]   ✓ nroff rendering: Successful
[2026-02-14 18:30:32 PDP11]   ✓ Cross-system validation: 2.11BSD tools
[2026-02-14 18:30:32 PDP11]
[2026-02-14 18:30:32 PDP11] Status: PASS
[2026-02-14 18:30:32 PDP11] ================================
```

### Key Evidence Points in PDP11.log

1. **OS Version**: `2.11 BSD UNIX #1: Sun Nov  7 22:40:28 PST 1999`
   - ✅ Proves 2.11BSD (last PDP-11 BSD release)

2. **Tool Dates**: `dated Nov  7  1999`
   - ✅ Matches 2.11BSD final release date

3. **nroff Output**: Actual rendered manpage text
   - ✅ Proves vintage text formatter working

4. **Cross-System Validation**: File created on VAX successfully processed on PDP-11
   - ✅ Proves authentic Unix interoperability

---

## Example: GITHUB.log

Orchestration logs from GitHub Actions:

```log
[2026-02-14 18:29:45 GITHUB] Starting AWS VAX instance...
[2026-02-14 18:29:50 GITHUB] Waiting for instance to be running...
[2026-02-14 18:30:15 GITHUB] VAX instance ready at 34.228.166.115
[2026-02-14 18:30:20 GITHUB] Starting AWS PDP-11 instance...
[2026-02-14 18:30:45 GITHUB] PDP-11 instance ready at 54.210.123.45
[2026-02-14 18:30:50 GITHUB] Transferring files to VAX...
[2026-02-14 18:31:00 GITHUB] Uploading arpanet-log.sh to VAX BSD...
[2026-02-14 18:31:05 GITHUB] Uploading bradman.c to VAX BSD...
[2026-02-14 18:31:10 GITHUB] Uploading resume.vax.yaml to VAX BSD...
[2026-02-14 18:31:15 GITHUB] Executing build inside VAX BSD (vintage K&R C)...
[2026-02-14 18:31:50 GITHUB] Build succeeded (verified via console)
[2026-02-14 18:31:55 GITHUB] Logs extracted to EFS
[2026-02-14 18:32:00 GITHUB] Retrieving encoded file from VAX BSD...
[2026-02-14 18:32:05 GITHUB] Starting console transfer to PDP-11...
[2026-02-14 18:32:30 GITHUB] Console transfer complete
[2026-02-14 18:32:35 GITHUB] Sending validation commands to PDP-11...
[2026-02-14 18:33:00 GITHUB] Validation succeeded (verified via console)
[2026-02-14 18:33:05 GITHUB] Retrieving build output...
[2026-02-14 18:33:10 GITHUB] Build successful
```

---

## Example: merged.log

All logs chronologically merged:

```log
[2026-02-14 18:29:45 GITHUB] Starting AWS VAX instance...
[2026-02-14 18:29:50 GITHUB] Waiting for instance to be running...
[2026-02-14 18:30:00 VAX] === VAX BUILD & ENCODE ===
[2026-02-14 18:30:00 VAX] Build ID: build-20260214-183000
[2026-02-14 18:30:01 VAX] System Information:
[2026-02-14 18:30:01 VAX]   OS: 4.3 BSD UNIX #1: Fri Jun  6 19:55:29 PDT 1986
[2026-02-14 18:30:01 VAX]   Compiler: cc: Berkeley C compiler, version 4.3 BSD, 7 June 1986
[2026-02-14 18:30:15 GITHUB] VAX instance ready at 34.228.166.115
[2026-02-14 18:30:20 PDP11] === PDP-11 VALIDATION ===
[2026-02-14 18:30:21 PDP11] System Information:
[2026-02-14 18:30:21 PDP11]   OS: 2.11 BSD UNIX #1: Sun Nov  7 22:40:28 PST 1999
... (interleaved chronologically)
```

---

## Webpage Integration Design

### Option 1: Build Info Widget (Recommended)

Display recent build with expandable logs:

```html
<div class="build-info">
  <h3>Latest Vintage Build</h3>
  <div class="build-meta">
    <span>Build ID: <code>build-20260214-183000</code></span>
    <span>Date: 2026-02-14 18:30 UTC</span>
    <span>Status: ✓ Success</span>
  </div>

  <div class="build-evidence">
    <h4>Vintage Tool Evidence</h4>
    <ul>
      <li><strong>VAX Compiler:</strong> cc (4.3 BSD, June 7 1986)</li>
      <li><strong>PDP-11 OS:</strong> 2.11 BSD (Nov 7 1999)</li>
      <li><strong>Transfer Method:</strong> uuencode console I/O</li>
    </ul>
  </div>

  <div class="build-logs">
    <h4>Build Logs</h4>
    <a href="/build-logs/VAX.log">VAX.log</a> (compilation)
    <a href="/build-logs/PDP11.log">PDP11.log</a> (validation)
    <a href="/build-logs/merged.log">merged.log</a> (complete timeline)
  </div>
</div>
```

### Option 2: Inline Log Viewer

Embed key excerpts with syntax highlighting:

```html
<section class="vintage-proof">
  <h3>Proof of Vintage Toolchain</h3>

  <div class="log-excerpt">
    <h4>VAX Compilation (4.3BSD, 1986)</h4>
    <pre><code>[2026-02-14 18:30:01 VAX] Compiler: cc: Berkeley C compiler, version 4.3 BSD, 7 June 1986
[2026-02-14 18:30:02 VAX] Compiler binary: /bin/cc (45056 bytes, dated Jun  7  1986)
[2026-02-14 18:30:05 VAX] Compilation successful</code></pre>
    <a href="/build-logs/VAX.log">View full VAX log →</a>
  </div>

  <div class="log-excerpt">
    <h4>PDP-11 Validation (2.11BSD, 1999)</h4>
    <pre><code>[2026-02-14 18:30:21 PDP11] OS: 2.11 BSD UNIX #1: Sun Nov  7 22:40:28 PST 1999
[2026-02-14 18:30:27 PDP11] Tool: nroff -man (44940 bytes, dated Nov  7  1999)
[2026-02-14 18:30:32 PDP11] Status: PASS</code></pre>
    <a href="/build-logs/PDP11.log">View full PDP-11 log →</a>
  </div>
</section>
```

### Option 3: Timeline View

Visual timeline showing the build flow:

```
┌─────────────────────────────────────────────────────────┐
│ Build Timeline: build-20260214-183000                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ 18:29:45  [GITHUB] Start VAX instance                  │
│ 18:30:00  [VAX]    Compile with K&R C (1986)    ← PROOF│
│ 18:30:12  [VAX]    Encode with uuencode                 │
│ 18:30:20  [PDP11]  Decode on 2.11BSD (1999)     ← PROOF│
│ 18:30:30  [PDP11]  Render with nroff                    │
│ 18:30:32  [PDP11]  ✓ Validation PASS                    │
│                                                          │
│ [View VAX.log] [View PDP11.log] [View merged.log]      │
└─────────────────────────────────────────────────────────┘
```

---

## Log Rotation & Storage

### Current Builds
- Latest 20 builds kept in `/mnt/arpanet-logs/builds/`
- Older builds auto-deleted by workflow cleanup step

### Published Logs
- `site/build-logs/VAX.log` - Latest VAX compilation
- `site/build-logs/PDP11.log` - Latest PDP-11 validation
- `site/build-logs/merged.log` - Latest complete timeline

These are updated on each successful publish and committed to git.

---

## Key Insights for Webpage Design

### Highlighting Strategy

**The "Money Shot" Lines**:
1. `cc: Berkeley C compiler, version 4.3 BSD, 7 June 1986` ← Highlight this!
2. `Compiler binary: /bin/cc (45056 bytes, dated Jun  7  1986)` ← And this!
3. `OS: 2.11 BSD UNIX #1: Sun Nov  7 22:40:28 PST 1999` ← And this!

These prove authentic vintage tools, not modern emulation.

### CSS Styling Suggestions

```css
.log-excerpt {
  background: #1e1e1e;
  border-left: 4px solid #00ff00;
  padding: 1em;
  font-family: 'Courier New', monospace;
  overflow-x: auto;
}

.log-timestamp {
  color: #888;
}

.log-machine-vax {
  color: #00aaff;
  font-weight: bold;
}

.log-machine-pdp11 {
  color: #ff8800;
  font-weight: bold;
}

.vintage-proof {
  background: #f9f9f9;
  border: 2px solid #ddd;
  padding: 2em;
  margin: 2em 0;
}

.vintage-proof h3::before {
  content: "🏛️ ";
}
```

### Interactive Elements

Consider:
- Log viewer with syntax highlighting
- Filter by machine (VAX/PDP11/GITHUB)
- Search within logs
- Download logs as .txt
- "Share this build" permalink

---

## Next: Generate Real Logs

Once the pipeline runs, these examples will be replaced with **actual execution logs** showing real timestamps and tool output from the AWS instances.

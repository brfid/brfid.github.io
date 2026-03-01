#!/usr/bin/env bash
# Vintage artifact pipeline runner — pexpect edition.
#
# Orchestrates the VAX → PDP-11 pipeline using pexpect-driven SIMH containers.
# Replaces the former screen/telnet/sleep approach entirely.
#
# Pipeline:
#   1. prepare_host         — install deps, set up Python venv
#   2. build_pexpect_images — docker build pdp11-pexpect and vax-pexpect images
#   3. generate_vintage_yaml — Python: resume.yaml → build/vintage/resume.vintage.yaml
#   4. stage_b_vax          — docker run vax-pexpect → build/vintage/brad.1.uu  (VAX spools via UUCP)
#   5. stage_a_pdp11        — docker run pdp11-pexpect → build/vintage/brad.man.txt  (PDP-11 receives spool)
#   6. emit_artifact        — copy to hugo/static, emit base64 markers on stdout
#
# Usage:
#   ./scripts/edcloud-vintage-runner.sh <build-id>
#
# Environment:
#   ROOT_DIR      repo root (default: cwd)
#   LOG_DIR       log directory (default: /tmp/edcloud-vintage)
#   KEEP_IMAGES   if 1, skip 'docker rmi' of built images on exit (default: 0)

set -euo pipefail

BUILD_ID="${1:-}"
if [[ -z "$BUILD_ID" ]]; then
  echo "Usage: $0 <build-id>" >&2
  exit 1
fi

ROOT_DIR="${ROOT_DIR:-$(pwd)}"
LOG_DIR="${LOG_DIR:-/tmp/edcloud-vintage}"
LOG_FILE="${LOG_DIR}/${BUILD_ID}.log"
SECTIONS_LOG="${LOG_DIR}/${BUILD_ID}.sections.jsonl"
KEEP_IMAGES="${KEEP_IMAGES:-0}"

PDP11_IMAGE="pdp11-pexpect"
VAX_IMAGE="vax-pexpect"

# ghcr.io coordinates for pre-built cached images (set to Public in GitHub
# package settings so edcloud can pull without credentials).
GHCR_VAX="ghcr.io/brfid/vax-pexpect:latest"
GHCR_PDP11="ghcr.io/brfid/pdp11-pexpect:latest"

mkdir -p "$LOG_DIR"

# Keep stdout clean for marker-based artifact extraction.
exec 3>&1
exec >"$LOG_FILE" 2>&1

on_exit() {
  local code="$1"

  if (( code != 0 )); then
    printf '<<<EDCLOUD_RUNNER_FAILED>>> build_id=%s log=%s\n' "$BUILD_ID" "$LOG_FILE" >&3
    printf '<<<EDCLOUD_RUNNER_LOG_TAIL_BEGIN>>>\n' >&3
    tail -80 "$LOG_FILE" >&3 || true
    printf '<<<EDCLOUD_RUNNER_LOG_TAIL_END>>>\n' >&3
  fi

  cleanup

  trap - EXIT
  exit "$code"
}
trap 'on_exit $?' EXIT

stage() {
  printf '\n[%s] %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S')" "$1"
}

require_bin() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 1
  }
}

cleanup() {
  stage "cleanup"

  # Remove any containers from this run still running (docker run --rm handles
  # the normal case; this is a safety net for interrupted runs).
  docker ps -aq --filter "label=vintage-build-id=${BUILD_ID}" | xargs -r docker rm -f || true

  if [[ "$KEEP_IMAGES" != "1" ]]; then
    docker rmi "$PDP11_IMAGE" "$VAX_IMAGE" 2>/dev/null || true
  fi

  # Temporary copy of bradman.c in the build volume.
  rm -f "${ROOT_DIR}/build/vintage/bradman.c" || true
}

prepare_host() {
  stage "prepare-host"

  if ! command -v docker >/dev/null 2>&1; then
    apt-get update
    apt-get install -y docker.io
  fi

  require_bin docker
  require_bin git
  require_bin python3

  cd "$ROOT_DIR"
  mkdir -p build/vintage hugo/static

  if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
  fi

  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet -e .
}

_pull_or_build() {
  # Pull a pre-built image from ghcr.io; fall back to local docker build.
  # Args: <local-tag> <ghcr-ref> <dockerfile> [docker-build-args...]
  local local_tag="$1"; shift
  local ghcr_ref="$1"; shift
  local dockerfile="$1"; shift

  if docker pull "$ghcr_ref" 2>/dev/null; then
    docker tag "$ghcr_ref" "$local_tag"
    echo "Pulled ${local_tag} from ${ghcr_ref}"
  else
    echo "Pull failed for ${ghcr_ref}; building locally…"
    docker build -f "$dockerfile" -t "$local_tag" "$@" .
    echo "Built ${local_tag} locally"
  fi
}

build_pexpect_images() {
  stage "build-pexpect-images"
  cd "$ROOT_DIR"

  _pull_or_build \
    "$PDP11_IMAGE" \
    "$GHCR_PDP11" \
    vintage/machines/pdp11/Dockerfile.pdp11-pexpect

  _pull_or_build \
    "$VAX_IMAGE" \
    "$GHCR_VAX" \
    vintage/machines/vax/Dockerfile.vax-pexpect

  echo "Images ready: ${PDP11_IMAGE}  ${VAX_IMAGE}"
}

generate_vintage_yaml() {
  stage "generate-vintage-yaml"
  cd "$ROOT_DIR"

  .venv/bin/python - <<'PY'
from datetime import date
from pathlib import Path

from resume_generator.render import load_resume
from resume_generator.vintage_yaml import build_vintage_resume_v1, emit_vintage_yaml

resume = load_resume(Path("resume.yaml"))
vintage = build_vintage_resume_v1(resume, build_date=date.today())
out_path = Path("build/vintage/resume.vintage.yaml")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(emit_vintage_yaml(vintage), encoding="utf-8")
print(f"Wrote: {out_path}  ({sum(1 for _ in out_path.open())} lines)")
PY
}

stage_b_vax() {
  stage "stage-b-vax"
  cd "$ROOT_DIR"

  # bradman.c lives in the repo tree; copy it into the shared build volume
  # so both inputs are accessible to the container at /build/*.
  cp vintage/machines/vax/bradman.c build/vintage/bradman.c

  docker run --rm \
    --label "vintage-build-id=${BUILD_ID}" \
    -v "$(pwd)/build/vintage:/build" \
    -e "SECTIONS_LOG=/build/sections.jsonl" \
    "$VAX_IMAGE" \
    --bradman /build/bradman.c \
    --resume-yaml /build/resume.vintage.yaml \
    --output /build/brad.1.uu \
    --bio-output /build/brad.bio.txt

  if [[ ! -s build/vintage/brad.1.uu ]]; then
    echo "Stage B (VAX) failed: build/vintage/brad.1.uu is missing or empty"
    return 1
  fi

  echo "Stage B complete: build/vintage/brad.1.uu  ($(wc -l < build/vintage/brad.1.uu) encoded lines)"
  echo "[uucp] brad.1.uu spooled on VAX — routing via host to PDP-11"
}

stage_a_pdp11() {
  stage "stage-a-pdp11"
  cd "$ROOT_DIR"

  echo "[uucp] Delivering brad.1.uu spool to PDP-11…"
  docker run --rm \
    --label "vintage-build-id=${BUILD_ID}" \
    -v "$(pwd)/build/vintage:/build" \
    -e "SECTIONS_LOG=/build/sections.jsonl" \
    "$PDP11_IMAGE" \
    --input /build/brad.1.uu \
    --output /build/brad.man.txt

  if [[ ! -s build/vintage/brad.man.txt ]]; then
    echo "Stage A (PDP-11) failed: build/vintage/brad.man.txt is missing or empty"
    return 1
  fi

  echo "[uucp] brad.1.uu delivered and decoded on PDP-11"
  echo "Stage A complete: build/vintage/brad.man.txt  ($(wc -l < build/vintage/brad.man.txt) lines)"
}

emit_artifact() {
  stage "emit-artifact"
  cd "$ROOT_DIR"

  mkdir -p hugo/static

  cp build/vintage/brad.man.txt hugo/static/brad.man.txt
  local b64
  b64="$(base64 -w 0 build/vintage/brad.man.txt)"
  printf '<<<BRAD_MAN_TXT_BASE64_BEGIN>>>\n%s\n<<<BRAD_MAN_TXT_BASE64_END>>>\n' "$b64" >&3

  if [[ -s build/vintage/brad.bio.txt ]]; then
    cp build/vintage/brad.bio.txt hugo/static/brad.bio.txt
    local bio_b64
    bio_b64="$(base64 -w 0 build/vintage/brad.bio.txt)"
    printf '<<<BRAD_BIO_TXT_BASE64_BEGIN>>>\n%s\n<<<BRAD_BIO_TXT_BASE64_END>>>\n' "$bio_b64" >&3
  fi

  printf 'LOG_FILE=%s\n' "$LOG_FILE" >&3
}

emit_build_log() {
  stage "emit-build-log"
  cd "$ROOT_DIR"

  # Copy sections.jsonl from build volume into LOG_DIR for the Python script.
  if [[ -s build/vintage/sections.jsonl ]]; then
    cp build/vintage/sections.jsonl "$SECTIONS_LOG"
  fi

  local build_log
  build_log="$(.venv/bin/python - "$LOG_FILE" "$BUILD_ID" "$SECTIONS_LOG" <<'PY'
import sys, re, json, os, html as html_mod

log_path   = sys.argv[1]
build_id   = sys.argv[2]
sections_f = sys.argv[3] if len(sys.argv) > 3 else ""

with open(log_path) as f:
    log_lines = f.readlines()

# Load console sections from JSONLines file written by pexpect scripts.
sections = {}
if sections_f and os.path.exists(sections_f):
    with open(sections_f) as f:
        for line in f:
            try:
                e = json.loads(line)
                sections[e["section"]] = e
            except (json.JSONDecodeError, KeyError):
                pass

TS = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'

def find_ts(pattern):
    for line in log_lines:
        m = re.search(pattern, line)
        if m:
            return m.group(1)
    return ""

def find_line(pattern):
    for line in log_lines:
        if re.search(pattern, line):
            return line.strip()
    return ""

host_ts    = find_ts(rf'\[{TS}\] prepare-host')
yaml_ts    = find_ts(rf'\[{TS}\] generate-vintage-yaml')
vax_ts     = find_ts(rf'\[{TS}\] stage-b-vax')
pdp11_ts   = find_ts(rf'\[{TS}\] stage-a-pdp11')
art_ts     = find_ts(rf'\[{TS}\] emit-artifact')
compile_ts = find_ts(rf'\[vax_pexpect\] {TS}\s+Compiling:')
nroff_ts   = find_ts(rf'\[pdp11_pexpect\] {TS}\s+nroff complete')

yaml_line  = find_line(r'Wrote: build/vintage/resume')
brad1_line = find_line(r'\[uucp\] Wrote spool:')
man_line   = find_line(r'Wrote:.*brad\.man\.txt')
bio_line   = find_line(r'Wrote bio:')

def sec(name):
    e = sections.get(name, {})
    raw = e.get("content", "").strip()
    return html_mod.escape(raw) if raw else "<em>(no console output captured)</em>"

def ts_span(ts):
    return f'<span class="ts">{html_mod.escape(ts)}</span>' if ts else ""

CSS = """
* { box-sizing: border-box; }
body { font-family: ui-monospace, SFMono-Regular, Menlo, 'Courier New', monospace;
       font-size: 12px; background: #0d1117; color: #e6edf3;
       margin: 0; padding: 20px 24px; line-height: 1.6; }
h1 { font-size: 13px; color: #8b949e; font-weight: normal; margin: 0 0 20px; }
h1 a { color: #58a6ff; text-decoration: none; }
h1 a:hover { text-decoration: underline; }
details { margin: 0 0 4px; border: 1px solid #30363d; border-radius: 6px; overflow: hidden; }
summary { padding: 8px 14px; background: #161b22; cursor: pointer;
          list-style: none; display: flex; align-items: baseline; gap: 10px;
          user-select: none; }
summary::-webkit-details-marker { display: none; }
.arrow { color: #58a6ff; font-size: 10px; width: 10px; flex-shrink: 0; }
details:not([open]) .arrow::after { content: "▶"; }
details[open] .arrow::after { content: "▼"; }
.step-name { color: #e6edf3; font-weight: bold; }
.step-meta { color: #8b949e; flex: 1; }
.step-ts   { color: #6e7681; font-size: 11px; }
pre { margin: 0; padding: 12px 16px; overflow-x: auto;
      white-space: pre-wrap; word-break: break-all;
      background: #0d1117; color: #c9d1d9;
      border-top: 1px solid #30363d; font-size: 11.5px; line-height: 1.55; }
.ts   { color: #6e7681; }
.ok   { color: #3fb950; }
.info { color: #58a6ff; }
em { color: #6e7681; font-style: normal; }
"""

def section(name, title, meta, ts_val, content_html, open_attr=""):
    ts_part = f' <span class="step-ts">{html_mod.escape(ts_val)}</span>' if ts_val else ""
    return f"""<details{open_attr}>
  <summary><span class="arrow"></span><span class="step-name">{title}</span><span class="step-meta">{meta}</span>{ts_part}</summary>
  <pre>{content_html}</pre>
</details>"""

# --- Host setup section ---
host_lines = []
if host_ts:
    host_lines.append(f'{ts_span(host_ts)}  <span class="ok">pipeline started</span>')
if yaml_ts:
    host_lines.append(f'{ts_span(yaml_ts)}  resume.yaml → resume.vintage.yaml')
if yaml_line:
    host_lines.append(f'  {html_mod.escape(yaml_line)}')
host_content = "\n".join(host_lines) if host_lines else "<em>(no events)</em>"

# --- Host UUCP routing ---
uucp_lines = []
if pdp11_ts:
    uucp_lines.append(f'{ts_span(pdp11_ts)}  routing brad.1.uu → PDP-11')
if brad1_line:
    uucp_lines.append(f'  {html_mod.escape(brad1_line)}')
uucp_content = "\n".join(uucp_lines) if uucp_lines else "<em>(no events)</em>"

# --- Artifact section ---
art_lines = []
if art_ts:
    art_lines.append(f'{ts_span(art_ts)}  <span class="ok">pipeline complete</span>')
for info in [man_line, bio_line]:
    if info:
        art_lines.append(f'  {html_mod.escape(info)}')
art_content = "\n".join(art_lines) if art_lines else "<em>(no events)</em>"

parts = [f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<title>{html_mod.escape(build_id)} — vintage pipeline log</title>
<style>{CSS}</style>
</head>
<body>
<h1>vintage pipeline &middot; <a href="https://github.com/brfid/brfid.github.io">brfid/brfid.github.io</a> &middot; {html_mod.escape(build_id)}</h1>
"""]

parts.append(section("host-setup", "host", "pipeline setup", host_ts, host_content, " open"))
parts.append(section("vax-boot",   "VAX 4.3BSD", "SIMH vax780 &middot; boot", vax_ts, sec("vax-boot")))
parts.append(section("vax-run",    "VAX 4.3BSD", "compile bradman.c &rarr; brad.1 &rarr; uuencode", compile_ts, sec("vax-compile") + "\n\n" + sec("vax-run"), " open"))
parts.append(section("uucp",       "host", "UUCP routing brad.1.uu &rarr; PDP-11", pdp11_ts, uucp_content))
parts.append(section("pdp11-boot", "PDP-11 2.11BSD", "SIMH pdp11 &middot; boot", pdp11_ts, sec("pdp11-boot")))
parts.append(section("pdp11-nroff","PDP-11 2.11BSD", "nroff -man &rarr; brad.man.txt", nroff_ts, sec("pdp11-nroff"), " open"))
parts.append(section("artifacts",  "host", "artifact extraction", art_ts, art_content, " open"))

parts.append("</body>\n</html>")
print("".join(parts))
PY
)"

  if [[ -n "$build_log" ]]; then
    local log_b64
    log_b64="$(printf '%s' "$build_log" | base64 -w 0)"
    printf '<<<BUILD_LOG_BASE64_BEGIN>>>\n%s\n<<<BUILD_LOG_BASE64_END>>>\n' "$log_b64" >&3
  fi
}

main() {
  prepare_host
  build_pexpect_images
  generate_vintage_yaml
  stage_b_vax
  stage_a_pdp11
  emit_artifact
  emit_build_log
}

main "$@"

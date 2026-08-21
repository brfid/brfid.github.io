#!/usr/bin/env bash
# Vintage artifact pipeline runner — pexpect edition.
#
# Orchestrates the VAX → PDP-11 pipeline using pexpect-driven SIMH containers.
# Replaces the former screen/telnet/sleep approach entirely.
#
# Pipeline:
#   1. prepare_host         — install deps, set up Python venv
#   2. build_pexpect_images — docker build pdp11-pexpect and vax-pexpect images
#   3. generate_vintage_yaml — Python: site.yaml → build/vintage/bio.vintage.yaml
#   4. stage_b_vax          — docker run vax-pexpect → build/vintage/brad.bio.uu  (VAX spools via UUCP)
#   5. stage_a_pdp11        — docker run pdp11-pexpect → build/vintage/brad.bio.txt  (PDP-11 nroff renders)
#   6. emit_artifact        — emit internal artifacts as base64 markers on stdout
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
GIT_SHA="${GIT_SHA:-$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || echo 'unknown')}"

PDP11_IMAGE="pdp11-pexpect"
VAX_IMAGE="vax-pexpect"

# ghcr.io coordinates for pre-built cached images (set to Public in GitHub
# package settings so hosted and local runners can pull without credentials).
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

import yaml

from resume_generator.vintage_yaml import build_vintage_bio, emit_vintage_yaml

site = yaml.safe_load(Path("site.yaml").read_text(encoding="utf-8"))
resume = yaml.safe_load(Path("resume.yaml").read_text(encoding="utf-8"))
vintage = build_vintage_bio(site, resume, build_date=date.today())
out_path = Path("build/vintage/bio.vintage.yaml")
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
    -v "$(pwd)/scripts/vax_pexpect.py:/opt/vax_pexpect.py:ro" \
    -v "$(pwd)/scripts/simh_session.py:/opt/simh_session.py:ro" \
    -e "SECTIONS_LOG=/build/sections.jsonl" \
    "$VAX_IMAGE" \
    --bradman /build/bradman.c \
    --bio-yaml /build/bio.vintage.yaml \
    --output /build/brad.bio.uu

  if [[ ! -s build/vintage/brad.bio.uu ]]; then
    echo "Stage B (VAX) failed: build/vintage/brad.bio.uu is missing or empty"
    return 1
  fi

  echo "Stage B complete: build/vintage/brad.bio.uu  ($(wc -l < build/vintage/brad.bio.uu) encoded lines)"
  echo "[uucp] brad.bio.uu spooled on VAX — routing via host to PDP-11"
}

stage_a_pdp11() {
  stage "stage-a-pdp11"
  cd "$ROOT_DIR"

  echo "[uucp] Delivering brad.bio.uu spool to PDP-11…"
  docker run --rm \
    --label "vintage-build-id=${BUILD_ID}" \
    -v "$(pwd)/build/vintage:/build" \
    -v "$(pwd)/scripts/pdp11_pexpect.py:/opt/pdp11/pdp11_pexpect.py:ro" \
    -v "$(pwd)/scripts/simh_session.py:/opt/pdp11/simh_session.py:ro" \
    -e "SECTIONS_LOG=/build/sections.jsonl" \
    "$PDP11_IMAGE" \
    --input /build/brad.bio.uu \
    --output /build/brad.bio.txt

  if [[ ! -s build/vintage/brad.bio.txt ]]; then
    echo "Stage A (PDP-11) failed: build/vintage/brad.bio.txt is missing or empty"
    return 1
  fi

  echo "[uucp] brad.bio.uu delivered and decoded on PDP-11"
  echo "Stage A complete: build/vintage/brad.bio.txt  ($(wc -l < build/vintage/brad.bio.txt) lines)"
}

emit_status_json() {
  # Emit a machine-readable pipeline status artifact for CI triage.
  # Called from main() after all stages complete (or from on_exit on failure).
  cd "$ROOT_DIR"

  local status_file="build/vintage/pipeline-status.json"
  local exit_code="${1:-0}"
  local now
  now="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  # Collect stage-level stats
  local yaml_lines=0 spool_lines=0 bio_lines=0
  [[ -s build/vintage/bio.vintage.yaml ]] && yaml_lines=$(wc -l < build/vintage/bio.vintage.yaml)
  [[ -s build/vintage/brad.bio.uu ]] && spool_lines=$(wc -l < build/vintage/brad.bio.uu)
  [[ -s build/vintage/brad.bio.txt ]] && bio_lines=$(wc -l < build/vintage/brad.bio.txt)

  python3 - "$exit_code" "$now" "$yaml_lines" "$spool_lines" "$bio_lines" "$BUILD_ID" "$GIT_SHA" > "$status_file" <<'PY'
import json, sys

exit_code    = int(sys.argv[1])
completed_at = sys.argv[2]
yaml_lines   = int(sys.argv[3])
spool_lines  = int(sys.argv[4])
bio_lines    = int(sys.argv[5])
build_id     = sys.argv[6]
git_sha      = sys.argv[7] if len(sys.argv) > 7 else ""

status = {
    "pipeline": "edcloud-vintage",
    "build_id": build_id,
    "git_sha": git_sha,
    "completed_at": completed_at,
    "exit_code": exit_code,
    "result": "success" if exit_code == 0 else "failure",
    "stages": {
        "generate_vintage_yaml": {"lines": yaml_lines},
        "stage_b_vax":           {"brad_bio_uu_lines": spool_lines},
        "stage_a_pdp11":         {"brad_bio_txt_lines": bio_lines},
    },
}
print(json.dumps(status, indent=2))
PY
}

emit_artifact() {
  stage "emit-artifact"
  cd "$ROOT_DIR"

  mkdir -p hugo/static

  if [[ ! -s build/vintage/brad.bio.txt ]]; then
    echo "emit-artifact: build/vintage/brad.bio.txt is missing or empty" >&2
    return 1
  fi

  # `base64 | tr -d '\n'` is portable: GNU wraps at 76 and BSD/macOS has no
  # -w flag, so strip newlines afterwards instead of asking base64 not to wrap.
  local bio_b64
  bio_b64="$(base64 < build/vintage/brad.bio.txt | tr -d '\n')"
  printf '<<<BRAD_BIO_TXT_BASE64_BEGIN>>>\n%s\n<<<BRAD_BIO_TXT_BASE64_END>>>\n' "$bio_b64" >&3

  # Emit machine-readable pipeline status JSON (base64-encoded for safe transport)
  if [[ -s build/vintage/pipeline-status.json ]]; then
    local status_b64
    status_b64="$(base64 < build/vintage/pipeline-status.json | tr -d '\n')"
    printf '<<<PIPELINE_STATUS_JSON_BASE64_BEGIN>>>\n%s\n<<<PIPELINE_STATUS_JSON_BASE64_END>>>\n' "$status_b64" >&3
  fi

  printf 'LOG_FILE=%s\n' "$LOG_FILE" >&3
}

emit_build_log() {
  stage "emit-build-log"
  cd "$ROOT_DIR"

  # Copy sections.jsonl from the build volume into LOG_DIR for the renderer.
  if [[ -s build/vintage/sections.jsonl ]]; then
    cp build/vintage/sections.jsonl "$SECTIONS_LOG"
  fi

  local build_log
  build_log="$(.venv/bin/python -m resume_generator.build_log "$LOG_FILE" "$BUILD_ID" "$SECTIONS_LOG")"

  if [[ -n "$build_log" ]]; then
    local log_b64
    log_b64="$(printf '%s' "$build_log" | base64 | tr -d '\n')"
    printf '<<<BUILD_LOG_BASE64_BEGIN>>>\n%s\n<<<BUILD_LOG_BASE64_END>>>\n' "$log_b64" >&3
  fi
}

main() {
  prepare_host
  build_pexpect_images
  generate_vintage_yaml
  stage_b_vax
  stage_a_pdp11
  emit_status_json 0
  emit_artifact
  emit_build_log
}

main "$@"

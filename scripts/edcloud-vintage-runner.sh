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
KEEP_IMAGES="${KEEP_IMAGES:-0}"

PDP11_IMAGE="pdp11-pexpect"
VAX_IMAGE="vax-pexpect"

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

build_pexpect_images() {
  stage "build-pexpect-images"
  cd "$ROOT_DIR"

  echo "Building ${PDP11_IMAGE} image…"
  docker build \
    -f vintage/machines/pdp11/Dockerfile.pdp11-pexpect \
    -t "$PDP11_IMAGE" \
    .

  echo "Building ${VAX_IMAGE} image…"
  docker build \
    -f vintage/machines/vax/Dockerfile.vax-pexpect \
    -t "$VAX_IMAGE" \
    .

  echo "Images built: ${PDP11_IMAGE}  ${VAX_IMAGE}"
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
    "$VAX_IMAGE" \
    --bradman /build/bradman.c \
    --resume-yaml /build/resume.vintage.yaml \
    --output /build/brad.1.uu

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

  cp build/vintage/brad.man.txt hugo/static/brad.man.txt

  local b64
  b64="$(base64 -w 0 build/vintage/brad.man.txt)"
  printf '<<<BRAD_MAN_TXT_BASE64_BEGIN>>>\n%s\n<<<BRAD_MAN_TXT_BASE64_END>>>\n' "$b64" >&3
  printf 'LOG_FILE=%s\n' "$LOG_FILE" >&3
}

main() {
  prepare_host
  build_pexpect_images
  generate_vintage_yaml
  stage_b_vax
  stage_a_pdp11
  emit_artifact
}

main "$@"

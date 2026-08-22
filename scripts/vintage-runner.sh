#!/usr/bin/env bash
# Usage:
#   ./scripts/vintage-runner.sh <build-id>
#
# Outputs:
#   build/vintage/          guest inputs, spool, bio, build log, sections, and status
#   LOG_DIR                 detailed host log and copied console sections
#   stdout                  concise completion status or failure diagnostics
#
# Environment:
#   ROOT_DIR                repository root (default: current directory)
#   LOG_DIR                 log directory (default: /tmp/edcloud-vintage)
#   KEEP_IMAGES             retain local image tags when set to 1 (default: 0)
#   ALLOW_LOCAL_IMAGE_BUILD build checked-out Dockerfiles after a pull failure
#                            when set to 1 (default: 1; production sets 0)

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
ALLOW_LOCAL_IMAGE_BUILD="${ALLOW_LOCAL_IMAGE_BUILD:-1}"
GIT_SHA="${GIT_SHA:-$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || echo 'unknown')}"

PDP11_IMAGE="pdp11-pexpect"
VAX_IMAGE="vax-pexpect"

# Production image digests. Promote and validate both as one pair.
GHCR_VAX="ghcr.io/brfid/vax-pexpect@sha256:c576baf49fc69a1b4da53abd3e2b3d94541ebcb2fbf864619edcfcd76f4b14f7"
GHCR_PDP11="ghcr.io/brfid/pdp11-pexpect@sha256:9e44185b9b128a7999292e5780413c46cad19f9af532273b0e739de9c3c8ad77"

mkdir -p "$LOG_DIR"

# Keep verbose output in the host log while preserving stdout for concise status.
exec 3>&1
exec >"$LOG_FILE" 2>&1

on_exit() {
  local code="$1"

  if (( code != 0 )); then
    # Failures after environment setup overwrite status from an earlier run.
    set +e
    if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
      emit_status_json "$code"
    fi
    printf 'Vintage pipeline failed: build_id=%s log=%s\n' "$BUILD_ID" "$LOG_FILE" >&3
    tail -80 "$LOG_FILE" >&3 || true
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

  # Remove containers left by an interrupted run.
  if command -v docker >/dev/null 2>&1; then
    docker ps -aq --filter "label=vintage-build-id=${BUILD_ID}" | xargs -r docker rm -f || true

    if [[ "$KEEP_IMAGES" != "1" ]]; then
      docker rmi "$PDP11_IMAGE" "$VAX_IMAGE" 2>/dev/null || true
    fi
  fi

  rm -f "${ROOT_DIR}/build/vintage/bradman.c" || true
}

prepare_host() {
  stage "prepare-host"

  require_bin docker
  require_bin git
  require_bin python3

  cd "$ROOT_DIR"
  mkdir -p build/vintage

  # Clear all files owned by one run before creating new status or artifacts.
  rm -f \
    build/vintage/bio.vintage.yaml \
    build/vintage/build.log.html \
    build/vintage/brad.bio.uu \
    build/vintage/brad.bio.txt \
    build/vintage/bradman.c \
    build/vintage/pipeline-status.json \
    build/vintage/sections.jsonl

  if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
  fi

  # A standalone run installs only when the local environment is incomplete.
  if ! .venv/bin/python -c 'import yaml; import resume_generator.vintage_yaml' >/dev/null 2>&1; then
    .venv/bin/python -m pip install --quiet -e .
  fi
}

_pull_or_build() {
  # Usage: _pull_or_build LOCAL_TAG GHCR_REFERENCE DOCKERFILE [BUILD_ARGS]
  local local_tag="$1"; shift
  local ghcr_ref="$1"; shift
  local dockerfile="$1"; shift

  if docker pull "$ghcr_ref" 2>/dev/null; then
    docker tag "$ghcr_ref" "$local_tag"
    echo "Pulled ${local_tag} from ${ghcr_ref}"
  else
    if [[ "$ALLOW_LOCAL_IMAGE_BUILD" != "1" ]]; then
      echo "Pull failed for pinned image ${ghcr_ref}; local fallback is disabled"
      return 1
    fi
    echo "Pull failed for ${ghcr_ref}; building from the checked-out Dockerfile"
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

  # Put both VAX inputs in the bind-mounted build directory.
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
  echo "[uucp] brad.bio.uu spooled on VAX; routing via host to PDP-11"
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
  # Write current-run status after success and again after any later failure.
  cd "$ROOT_DIR"

  local status_file="build/vintage/pipeline-status.json"
  local exit_code="${1:-0}"
  local now
  now="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  local yaml_lines=0 spool_lines=0 bio_lines=0
  [[ -s build/vintage/bio.vintage.yaml ]] && yaml_lines=$(wc -l < build/vintage/bio.vintage.yaml)
  [[ -s build/vintage/brad.bio.uu ]] && spool_lines=$(wc -l < build/vintage/brad.bio.uu)
  [[ -s build/vintage/brad.bio.txt ]] && bio_lines=$(wc -l < build/vintage/brad.bio.txt)

  .venv/bin/python - "$exit_code" "$now" "$yaml_lines" "$spool_lines" "$bio_lines" "$BUILD_ID" "$GIT_SHA" > "$status_file" <<'PY'
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

write_build_log() {
  stage "finalize-artifacts"
  cd "$ROOT_DIR"

  # The renderer reads console sections beside the host log.
  if [[ -s build/vintage/sections.jsonl ]]; then
    cp build/vintage/sections.jsonl "$SECTIONS_LOG"
  fi

  .venv/bin/python -m resume_generator.build_log \
    "$LOG_FILE" \
    "$BUILD_ID" \
    "$SECTIONS_LOG" \
    > build/vintage/build.log.html

  if [[ ! -s build/vintage/build.log.html ]]; then
    echo "write-build-log: build/vintage/build.log.html is missing or empty" >&2
    return 1
  fi
}

verify_final_artifacts() {
  stage "verify-final-artifacts"
  cd "$ROOT_DIR"

  local artifact
  for artifact in brad.bio.txt build.log.html pipeline-status.json; do
    if [[ ! -s "build/vintage/${artifact}" ]]; then
      echo "Final artifact is missing or empty: build/vintage/${artifact}" >&2
      return 1
    fi
  done
}

main() {
  prepare_host
  build_pexpect_images
  generate_vintage_yaml
  stage_b_vax
  stage_a_pdp11
  emit_status_json 0
  write_build_log
  verify_final_artifacts
  printf 'Vintage pipeline complete: build_id=%s artifacts=%s log=%s\n' \
    "$BUILD_ID" \
    "${ROOT_DIR}/build/vintage" \
    "$LOG_FILE" \
    >&3
}

main "$@"

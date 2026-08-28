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
#   ALLOW_ENVIRONMENT_BOOTSTRAP create and populate .venv when set to 1
#                            (default: 1; hosted jobs set 0)
#   BUILD_LOCAL_IMAGE_PAIR   build both images from current source instead of
#                            loading the promoted manifest (default: 0)

set -euo pipefail

BUILD_ID="${1:-}"
if [[ ! "$BUILD_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]]; then
  echo "Usage: $0 <safe-build-id>" >&2
  exit 1
fi

ROOT_DIR="${ROOT_DIR:-$(pwd)}"
LOG_DIR="${LOG_DIR:-/tmp/edcloud-vintage}"
LOG_FILE="${LOG_DIR}/${BUILD_ID}.log"
SECTIONS_LOG="${LOG_DIR}/${BUILD_ID}.sections.jsonl"
KEEP_IMAGES="${KEEP_IMAGES:-0}"
ALLOW_LOCAL_IMAGE_BUILD="${ALLOW_LOCAL_IMAGE_BUILD:-1}"
ALLOW_ENVIRONMENT_BOOTSTRAP="${ALLOW_ENVIRONMENT_BOOTSTRAP:-1}"
BUILD_LOCAL_IMAGE_PAIR="${BUILD_LOCAL_IMAGE_PAIR:-0}"
GIT_SHA="${GIT_SHA:-$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || echo 'unknown')}"
HOST_OUTPUT_READY=0

PDP11_IMAGE="pdp11-pexpect"
VAX_IMAGE="vax-pexpect"
PINNED_VAX=""
PINNED_PDP11=""
CONTAINER_SECURITY_ARGS=(
  --rm
  --network none
  --cap-drop ALL
  --security-opt no-new-privileges
  --pids-limit 256
  --memory 2g
)

if [[ -L "$LOG_DIR" ]]; then
  echo "Refusing symbolic-link log directory: $LOG_DIR" >&2
  exit 1
fi
mkdir -p "$LOG_DIR"
if [[ ! -d "$LOG_DIR" || -L "$LOG_FILE" || -L "$SECTIONS_LOG" ]]; then
  echo "Unsafe vintage log path under: $LOG_DIR" >&2
  exit 1
fi

# Keep verbose output in the host log while preserving stdout for concise status.
exec 3>&1
exec >"$LOG_FILE" 2>&1

on_exit() {
  local code="$1"

  if (( code != 0 )); then
    # Failures after environment setup overwrite status from an earlier run.
    set +e
    if [[ "$HOST_OUTPUT_READY" == "1" && ! -L "${ROOT_DIR}/.venv" && -x "${ROOT_DIR}/.venv/bin/python" ]]; then
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

}

prepare_host() {
  stage "prepare-host"

  require_bin docker
  require_bin git
  require_bin python3

  cd "$ROOT_DIR"
  if [[ -L build || ( -e build && ! -d build ) ]]; then
    echo "Unsafe generated-output parent: ${ROOT_DIR}/build"
    return 1
  fi
  mkdir -p build
  if [[ -L build/vintage ]]; then
    echo "Refusing generated output through a symbolic link: ${ROOT_DIR}/build/vintage"
    return 1
  fi
  rm -rf build/vintage
  mkdir -p build/vintage/stages/vax build/vintage/stages/pdp11
  if [[ "$ALLOW_LOCAL_IMAGE_BUILD" != "0" && "$ALLOW_LOCAL_IMAGE_BUILD" != "1" ]]; then
    echo "ALLOW_LOCAL_IMAGE_BUILD must be 0 or 1"
    return 1
  fi
  if [[ "$ALLOW_ENVIRONMENT_BOOTSTRAP" != "0" && "$ALLOW_ENVIRONMENT_BOOTSTRAP" != "1" ]]; then
    echo "ALLOW_ENVIRONMENT_BOOTSTRAP must be 0 or 1"
    return 1
  fi
  if [[ "$BUILD_LOCAL_IMAGE_PAIR" != "0" && "$BUILD_LOCAL_IMAGE_PAIR" != "1" ]]; then
    echo "BUILD_LOCAL_IMAGE_PAIR must be 0 or 1"
    return 1
  fi
  if [[ "$BUILD_LOCAL_IMAGE_PAIR" == "1" && "$ALLOW_LOCAL_IMAGE_BUILD" != "1" ]]; then
    echo "BUILD_LOCAL_IMAGE_PAIR=1 requires ALLOW_LOCAL_IMAGE_BUILD=1"
    return 1
  fi
  if [[ -L .venv ]]; then
    echo "Refusing Python environment through a symbolic link: ${ROOT_DIR}/.venv"
    return 1
  fi

  if [[ ! -x .venv/bin/python ]] || \
     ! .venv/bin/python -c 'import yaml; import resume_generator.vintage_yaml' >/dev/null 2>&1; then
    if [[ "$ALLOW_ENVIRONMENT_BOOTSTRAP" != "1" ]]; then
      echo "Prepared Python environment is required; hosted bootstrap is disabled"
      return 1
    fi
    rm -rf .venv
    python3 -m venv .venv
    .venv/bin/python -m pip install --require-hashes -r requirements/build.lock
    .venv/bin/python -m pip install --require-hashes -r requirements/runtime.lock
    .venv/bin/python -m pip install --no-deps --no-build-isolation -e .
  fi
  HOST_OUTPUT_READY=1
}

load_image_pair() {
  stage "validate-image-pair"
  cd "$ROOT_DIR"

  if [[ "$BUILD_LOCAL_IMAGE_PAIR" == "1" ]]; then
    echo "Using an explicit local image-pair build"
    return 0
  fi
  PINNED_VAX="$(.venv/bin/python -m resume_generator.image_manifest --root "$ROOT_DIR" field vax)"
  PINNED_PDP11="$(.venv/bin/python -m resume_generator.image_manifest --root "$ROOT_DIR" field pdp11)"
}

verify_promoted_image() {
  local machine="$1"
  local reference="$2"
  local revision image_inputs

  revision="$(docker image inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$reference")"
  image_inputs="$(docker image inspect --format '{{ index .Config.Labels "io.brfid.vintage.image-inputs-sha256" }}' "$reference")"
  if [[ "$image_inputs" == "<no value>" || -z "$image_inputs" ]]; then
    image_inputs="-"
  fi
  .venv/bin/python -m resume_generator.image_manifest \
    --root "$ROOT_DIR" \
    validate-labels "$machine" "$revision" "$image_inputs"
}

build_local_images() {
  local source_sha image_inputs

  source_sha="$(git -C "$ROOT_DIR" rev-parse --verify 'HEAD^{commit}')"
  image_inputs="$(.venv/bin/python -m resume_generator.image_manifest --root "$ROOT_DIR" inputs-sha256)"
  docker build \
    --label "org.opencontainers.image.revision=${source_sha}" \
    --label "io.brfid.vintage.image-inputs-sha256=${image_inputs}" \
    --file vintage/machines/pdp11/Dockerfile.pdp11-pexpect \
    --tag "$PDP11_IMAGE" \
    .
  docker build \
    --label "org.opencontainers.image.revision=${source_sha}" \
    --label "io.brfid.vintage.image-inputs-sha256=${image_inputs}" \
    --file vintage/machines/vax/Dockerfile.vax-pexpect \
    --tag "$VAX_IMAGE" \
    .
  echo "Built both vintage images from the checked-out source"
}

build_pexpect_images() {
  stage "build-pexpect-images"
  cd "$ROOT_DIR"

  if [[ "$BUILD_LOCAL_IMAGE_PAIR" == "1" ]]; then
    build_local_images
  elif docker pull "$PINNED_PDP11" && docker pull "$PINNED_VAX"; then
    verify_promoted_image pdp11 "$PINNED_PDP11"
    verify_promoted_image vax "$PINNED_VAX"
    PDP11_IMAGE="$PINNED_PDP11"
    VAX_IMAGE="$PINNED_VAX"
    echo "Pulled and verified the promoted vintage image pair"
  elif [[ "$ALLOW_LOCAL_IMAGE_BUILD" == "1" ]]; then
    echo "A promoted image pull failed; rebuilding both images from current source"
    build_local_images
  else
    echo "Promoted image-pair pull failed; local fallback is disabled"
    return 1
  fi

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

  local output_dir="${ROOT_DIR}/build/vintage/stages/vax"
  local spool="${output_dir}/brad.bio.uu"
  local sections="${output_dir}/sections.jsonl"
  local source="${ROOT_DIR}/vintage/machines/vax/bradman.c"
  local yaml_input="${ROOT_DIR}/build/vintage/bio.vintage.yaml"

  for input in "$source" "$yaml_input" "${ROOT_DIR}/scripts/vax_pexpect.py" "${ROOT_DIR}/scripts/simh_session.py"; do
    if [[ -L "$input" || ! -f "$input" ]]; then
      echo "Stage B input is missing or unsafe: $input"
      return 1
    fi
  done

  docker run "${CONTAINER_SECURITY_ARGS[@]}" \
    --label "vintage-build-id=${BUILD_ID}" \
    --mount "type=bind,src=${source},dst=/inputs/bradman.c,readonly" \
    --mount "type=bind,src=${yaml_input},dst=/inputs/bio.vintage.yaml,readonly" \
    --mount "type=bind,src=${output_dir},dst=/output" \
    --mount "type=bind,src=${ROOT_DIR}/scripts/vax_pexpect.py,dst=/opt/vax_pexpect.py,readonly" \
    --mount "type=bind,src=${ROOT_DIR}/scripts/simh_session.py,dst=/opt/simh_session.py,readonly" \
    -e "SECTIONS_LOG=/output/sections.jsonl" \
    "$VAX_IMAGE" \
    --bradman /inputs/bradman.c \
    --bio-yaml /inputs/bio.vintage.yaml \
    --output /output/brad.bio.uu

  for output in "$spool" "$sections"; do
    if [[ -L "$output" || ! -f "$output" || ! -s "$output" ]]; then
      echo "Stage B output is missing, empty, or unsafe: $output"
      return 1
    fi
  done
  cp -- "$spool" build/vintage/brad.bio.uu

  echo "Stage B complete: build/vintage/brad.bio.uu  ($(wc -l < build/vintage/brad.bio.uu) encoded lines)"
  echo "[uucp] brad.bio.uu spooled on VAX; routing via host to PDP-11"
}

stage_a_pdp11() {
  stage "stage-a-pdp11"
  cd "$ROOT_DIR"

  local output_dir="${ROOT_DIR}/build/vintage/stages/pdp11"
  local spool="${ROOT_DIR}/build/vintage/brad.bio.uu"
  local bio="${output_dir}/brad.bio.txt"
  local sections="${output_dir}/sections.jsonl"

  for input in "$spool" "${ROOT_DIR}/scripts/pdp11_pexpect.py" "${ROOT_DIR}/scripts/simh_session.py"; do
    if [[ -L "$input" || ! -f "$input" || ! -s "$input" ]]; then
      echo "Stage A input is missing, empty, or unsafe: $input"
      return 1
    fi
  done

  echo "[uucp] Delivering brad.bio.uu spool to PDP-11…"
  docker run "${CONTAINER_SECURITY_ARGS[@]}" \
    --label "vintage-build-id=${BUILD_ID}" \
    --mount "type=bind,src=${spool},dst=/inputs/brad.bio.uu,readonly" \
    --mount "type=bind,src=${output_dir},dst=/output" \
    --mount "type=bind,src=${ROOT_DIR}/scripts/pdp11_pexpect.py,dst=/opt/pdp11/pdp11_pexpect.py,readonly" \
    --mount "type=bind,src=${ROOT_DIR}/scripts/simh_session.py,dst=/opt/pdp11/simh_session.py,readonly" \
    -e "SECTIONS_LOG=/output/sections.jsonl" \
    "$PDP11_IMAGE" \
    --input /inputs/brad.bio.uu \
    --output /output/brad.bio.txt

  for output in "$bio" "$sections"; do
    if [[ -L "$output" || ! -f "$output" || ! -s "$output" ]]; then
      echo "Stage A output is missing, empty, or unsafe: $output"
      return 1
    fi
  done
  cp -- "$bio" build/vintage/brad.bio.txt
  cat -- build/vintage/stages/vax/sections.jsonl build/vintage/stages/pdp11/sections.jsonl \
    > build/vintage/sections.jsonl

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
  if [[ -L build/vintage/sections.jsonl || ! -f build/vintage/sections.jsonl || ! -s build/vintage/sections.jsonl ]]; then
    echo "write-build-log: build/vintage/sections.jsonl is missing, empty, or unsafe" >&2
    return 1
  fi
  rm -f -- "$SECTIONS_LOG"
  cp -- build/vintage/sections.jsonl "$SECTIONS_LOG"

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
    if [[ -L "build/vintage/${artifact}" || ! -f "build/vintage/${artifact}" || ! -s "build/vintage/${artifact}" ]]; then
      echo "Final artifact is missing, empty, or unsafe: build/vintage/${artifact}" >&2
      return 1
    fi
  done
}

main() {
  prepare_host
  load_image_pair
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

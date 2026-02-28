#!/usr/bin/env bash
# Run the vintage VAX->PDP-11 artifact pipeline entirely on edcloud.
# Emits brad.man.txt as base64 between hard markers on stdout.

set -euo pipefail

BUILD_ID="${1:-}"
if [[ -z "$BUILD_ID" ]]; then
  echo "Usage: $0 <build-id>" >&2
  exit 1
fi

ROOT_DIR="${ROOT_DIR:-$(pwd)}"
LOG_DIR="${LOG_DIR:-/tmp/edcloud-vintage}"
LOG_FILE="${LOG_DIR}/${BUILD_ID}.log"
KEEP_RUNTIME="${KEEP_RUNTIME:-0}"

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

  cleanup_runtime

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

wait_for_log_signal() {
  local container="$1"
  local pattern="$2"
  local max_wait_seconds="$3"
  local waited=0

  while (( waited < max_wait_seconds )); do
    if docker logs --tail 80 "$container" 2>&1 | grep -q "$pattern"; then
      return 0
    fi
    sleep 1
    ((waited += 1))
  done

  echo "Timed out waiting for pattern '$pattern' in container '$container'"
  docker logs --tail 160 "$container" 2>&1 || true
  return 1
}

send_screen() {
  local session="$1"
  local payload="$2"
  screen -S "$session" -X stuff "$payload"
}

cleanup_screen() {
  local session="$1"
  screen -S "$session" -X quit 2>/dev/null || true
}

cleanup_runtime() {
  stage "cleanup-runtime"
  cd "$ROOT_DIR" 2>/dev/null || true

  # Remove known screen sessions created by this runner.
  if command -v screen >/dev/null 2>&1; then
    cleanup_screen "vax-chmod-${BUILD_ID}"
    cleanup_screen "vax-chmod2-${BUILD_ID}"
    cleanup_screen "vax-build-${BUILD_ID}"
    cleanup_screen "vax-retrieve-${BUILD_ID}"
    cleanup_screen "pdp11-upload-${BUILD_ID}"
    cleanup_screen "pdp11-console"
    screen -wipe >/dev/null 2>&1 || true
  fi

  # Default behavior is clean shutdown of containers and runtime volume state.
  if [[ "$KEEP_RUNTIME" == "1" ]]; then
    echo "KEEP_RUNTIME=1 set; skipping docker compose teardown"
  elif command -v docker >/dev/null 2>&1; then
    docker compose -f docker-compose.production.yml down --remove-orphans --volumes || true
  fi

  rm -f \
    "/tmp/vax-build-console-${BUILD_ID}.txt" \
    "/tmp/vax-cat-output-${BUILD_ID}.txt" \
    "/tmp/pdp11-boot-verify.txt" \
    "/tmp/pdp11-validation-${BUILD_ID}.txt" \
    "/tmp/pdp11-console-${BUILD_ID}.txt" \
    "/tmp/COURIER-${BUILD_ID}.log" \
    "/tmp/brad.1.uu" || true
}

prepare_host() {
  stage "prepare-host"
  if ! command -v screen >/dev/null 2>&1 || ! command -v telnet >/dev/null 2>&1; then
    apt-get update
    apt-get install -y screen telnet
  fi

  require_bin docker
  require_bin screen
  require_bin telnet
  require_bin git
  require_bin python3

  cd "$ROOT_DIR"
  mkdir -p build/vintage build/pdp11 site

  if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
  fi

  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -e .
}

start_stack() {
  stage "start-stack"
  cd "$ROOT_DIR"
  docker compose -f docker-compose.production.yml up -d --build

  # VAX SIMH emits "Listening on port 2323" without the %SIM-INFO prefix.
  wait_for_log_signal "vax-host" "Listening on port 2323" 120
  wait_for_log_signal "pdp11-host" "%SIM-INFO: Listening on port 2327" 120
}

boot_pdp11() {
  stage "boot-pdp11"
  cd "$ROOT_DIR"

  # SIMH exits if no telnet console connection is made within ~60 seconds of boot.
  # Stage 2 runs after Stage 1's multi-minute upload+build, so we must establish
  # the console session immediately and keep it alive throughout the pipeline.
  local session="pdp11-console"
  cleanup_screen "$session"
  screen -dmS "$session" telnet 127.0.0.1 2327
  sleep 3
  # Press Enter at the 2.11BSD Boot: prompt to boot the unix kernel.
  send_screen "$session" "\n"
  sleep 12
  # Mount /usr to make uudecode and nroff available.
  send_screen "$session" "mount /usr\n"
  sleep 3
  screen -S "$session" -X hardcopy "/tmp/pdp11-boot-verify.txt"
  if ! grep -q '#' "/tmp/pdp11-boot-verify.txt"; then
    echo "PDP-11 did not reach root shell after boot"
    cat "/tmp/pdp11-boot-verify.txt" || true
    return 1
  fi
  echo "PDP-11 booted; session $session is live"
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
print(out_path)
PY
}

stage1_vax_build() {
  stage "stage1-vax-build"
  cd "$ROOT_DIR"

  bash scripts/vax-console-upload.sh scripts/arpanet-log.sh /tmp/arpanet-log.sh 127.0.0.1

  local session="vax-chmod-${BUILD_ID}"
  cleanup_screen "$session"
  screen -dmS "$session" telnet 127.0.0.1 2323
  sleep 3
  send_screen "$session" "\n"
  sleep 1
  send_screen "$session" "root\n"
  sleep 2
  send_screen "$session" "chmod +x /tmp/arpanet-log.sh\n"
  sleep 1
  cleanup_screen "$session"

  bash scripts/vax-console-upload.sh vintage/machines/vax/bradman.c /tmp/bradman.c 127.0.0.1
  bash scripts/vax-console-upload.sh build/vintage/resume.vintage.yaml /tmp/resume.vintage.yaml 127.0.0.1
  bash scripts/vax-console-upload.sh scripts/vax-build-and-encode.sh /tmp/vax-build-and-encode.sh 127.0.0.1

  session="vax-chmod2-${BUILD_ID}"
  cleanup_screen "$session"
  screen -dmS "$session" telnet 127.0.0.1 2323
  sleep 3
  send_screen "$session" "\n"
  sleep 1
  send_screen "$session" "root\n"
  sleep 2
  send_screen "$session" "chmod +x /tmp/vax-build-and-encode.sh\n"
  sleep 1
  cleanup_screen "$session"

  session="vax-build-${BUILD_ID}"
  cleanup_screen "$session"
  screen -dmS "$session" telnet 127.0.0.1 2323
  sleep 8
  send_screen "$session" "\n"
  sleep 2
  send_screen "$session" "root\n"
  sleep 2
  send_screen "$session" "\n"
  sleep 2
  send_screen "$session" "root\n"
  sleep 2
  send_screen "$session" "echo __VAX_BUILD_READY__\n"
  sleep 2
  screen -S "$session" -X hardcopy "/tmp/vax-build-console-$BUILD_ID.txt"
  if ! grep -q "__VAX_BUILD_READY__" "/tmp/vax-build-console-$BUILD_ID.txt"; then
    echo "VAX build session did not reach a shell prompt"
    tail -80 "/tmp/vax-build-console-$BUILD_ID.txt" || true
    cleanup_screen "$session"
    return 1
  fi
  send_screen "$session" "cd /tmp\n"
  sleep 1
  send_screen "$session" "/tmp/vax-build-and-encode.sh $BUILD_ID\n"

  sleep 45
  screen -S "$session" -X hardcopy "/tmp/vax-build-console-$BUILD_ID.txt"
  cleanup_screen "$session"

  if ! grep -q "VAX build complete" "/tmp/vax-build-console-$BUILD_ID.txt"; then
    echo "VAX build did not report completion"
    tail -80 "/tmp/vax-build-console-$BUILD_ID.txt" || true
    return 1
  fi
}

stage2_transfer() {
  stage "stage2-transfer"
  cd "$ROOT_DIR"

  local session="vax-retrieve-${BUILD_ID}"
  cleanup_screen "$session"
  screen -dmS "$session" telnet 127.0.0.1 2323
  sleep 3
  send_screen "$session" "\n"
  sleep 1
  send_screen "$session" "root\n"
  sleep 2
  send_screen "$session" "cat /tmp/brad.1.uu\n"
  sleep 5
  screen -S "$session" -X hardcopy "/tmp/vax-cat-output-$BUILD_ID.txt"
  cleanup_screen "$session"

  awk '
    /^begin [0-7][0-7][0-7] brad\.1$/ {capture=1}
    capture {print}
    capture && /^end$/ {exit}
  ' "/tmp/vax-cat-output-$BUILD_ID.txt" > "/tmp/brad.1.uu"

  if [[ ! -s /tmp/brad.1.uu ]] || ! grep -q '^begin [0-7][0-7][0-7] brad\.1$' /tmp/brad.1.uu || ! grep -q '^end$' /tmp/brad.1.uu; then
    echo "Failed to extract a complete uuencoded payload from VAX output"
    return 1
  fi

  # Reuse the pdp11-console session established in boot_pdp11().
  # That session is already at root # with /usr mounted; no reconnect needed.
  local pdp11_session="pdp11-console"
  send_screen "$pdp11_session" "cat > /tmp/arpanet-log.sh << 'UPLOAD_EOF'\n"
  sleep 1
  while IFS= read -r line; do
    screen -S "$pdp11_session" -X stuff "$line\r"
    sleep 0.02
  done < scripts/arpanet-log.sh
  send_screen "$pdp11_session" "UPLOAD_EOF\n"
  sleep 1
  send_screen "$pdp11_session" "chmod +x /tmp/arpanet-log.sh\n"
  sleep 1

  python3 scripts/console-transfer.py "$BUILD_ID" 127.0.0.1 127.0.0.1
}

stage3_validate() {
  stage "stage3-validate"
  cd "$ROOT_DIR"

  PDP11_IP=127.0.0.1 bash scripts/pdp11-validate.sh "$BUILD_ID"
  if ! grep -q "Status: PASS" "/tmp/pdp11-validation-$BUILD_ID.txt"; then
    echo "PDP-11 validation did not report PASS"
    tail -80 "/tmp/pdp11-validation-$BUILD_ID.txt" || true
    return 1
  fi
}

stage4_render_host() {
  stage "stage4-render-host"
  cd "$ROOT_DIR"

  python3 - <<'PY'
import uu
uu.decode('/tmp/brad.1.uu', 'build/vintage/brad.1', quiet=True)
PY

  .venv/bin/python -m resume_generator.manpage --in build/vintage/brad.1 --out build/vintage/brad.txt
  if [[ ! -s build/vintage/brad.txt ]]; then
    echo "Rendered brad.txt is missing or empty"
    return 1
  fi
}

emit_artifact_markers() {
  stage "emit-artifact"
  cd "$ROOT_DIR"

  cp build/vintage/brad.txt hugo/static/brad.man.txt

  local b64
  b64="$(base64 -w 0 build/vintage/brad.txt)"
  printf '<<<BRAD_MAN_TXT_BASE64_BEGIN>>>\n%s\n<<<BRAD_MAN_TXT_BASE64_END>>>\n' "$b64" >&3
  printf 'LOG_FILE=%s\n' "$LOG_FILE" >&3
}

main() {
  prepare_host
  start_stack
  boot_pdp11
  generate_vintage_yaml
  stage1_vax_build
  stage2_transfer
  stage3_validate
  stage4_render_host
  emit_artifact_markers
}

main "$@"

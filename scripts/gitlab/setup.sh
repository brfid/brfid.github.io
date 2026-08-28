#!/usr/bin/env bash
# Prepare a GitLab-hosted Debian job from committed dependency locks.

set -euo pipefail

readonly MODE="${1:-}"
readonly HUGO_VERSION="0.163.3"
readonly HUGO_ASSET="hugo_extended_${HUGO_VERSION}_linux-amd64.deb"
readonly HUGO_RELEASE="https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}"

case "$MODE" in
  checks|publish|vintage) ;;
  *)
    echo "Usage: $0 checks|publish|vintage" >&2
    exit 2
    ;;
esac

export DEBIAN_FRONTEND=noninteractive
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_INPUT=1
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git make

install_hugo() {
  if [[ "$(uname -m)" != "x86_64" ]]; then
    echo "GitLab publication requires an amd64 runner" >&2
    exit 1
  fi

  curl --fail --location --silent --show-error \
    --output "/tmp/${HUGO_ASSET}" \
    "${HUGO_RELEASE}/${HUGO_ASSET}"
  cp requirements/hugo.sha256 /tmp/hugo.sha256
  (cd /tmp && sha256sum --check hugo.sha256)
  dpkg --install "/tmp/${HUGO_ASSET}"
  rm -f "/tmp/${HUGO_ASSET}" /tmp/hugo.sha256
  hugo version
}

install_python_environment() {
  local lock_file="$1"

  rm -rf .venv
  python -m venv .venv
  .venv/bin/python -m pip install --require-hashes -r requirements/build.lock
  .venv/bin/python -m pip install --require-hashes -r "$lock_file"
  .venv/bin/python -m pip install --no-deps --no-build-isolation -e .
}

wait_for_docker() {
  local attempt
  for attempt in {1..30}; do
    if docker info >/dev/null 2>&1; then
      docker version
      return 0
    fi
    sleep 1
  done
  echo "Docker-in-Docker did not become ready within 30 seconds" >&2
  return 1
}

if [[ "$MODE" == "checks" ]]; then
  install_hugo
  install_python_environment requirements/dev.lock
elif [[ "$MODE" == "publish" ]]; then
  install_hugo
  install_python_environment requirements/publish.lock
  apt-get install -y --no-install-recommends docker.io poppler-utils
  .venv/bin/python -m playwright install --with-deps chromium
  wait_for_docker
else
  install_python_environment requirements/runtime.lock
  apt-get install -y --no-install-recommends docker.io
  wait_for_docker
fi

apt-get clean
rm -rf /var/lib/apt/lists/*

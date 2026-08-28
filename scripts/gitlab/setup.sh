#!/usr/bin/env bash
# Prepare a GitLab-hosted Debian job for checks, publication, or vintage validation.

set -euo pipefail

MODE="${1:-}"
HUGO_VERSION="${HUGO_VERSION:-0.163.3}"

case "$MODE" in
  checks|publish|vintage) ;;
  *)
    echo "Usage: $0 checks|publish|vintage" >&2
    exit 2
    ;;
esac

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git make

install_hugo() {
  local asset="hugo_extended_${HUGO_VERSION}_linux-amd64.deb"
  local release="https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}"

  if [[ "$(uname -m)" != "x86_64" ]]; then
    echo "GitLab publication requires an amd64 runner" >&2
    exit 1
  fi

  curl --fail --location --silent --show-error --output "/tmp/${asset}" "${release}/${asset}"
  curl --fail --location --silent --show-error \
    --output /tmp/hugo-checksums.txt \
    "${release}/hugo_${HUGO_VERSION}_checksums.txt"
  grep " ${asset}$" /tmp/hugo-checksums.txt > /tmp/hugo-asset.sha256
  (cd /tmp && sha256sum --check hugo-asset.sha256)
  dpkg --install "/tmp/${asset}"
  hugo version
}

install_python_environment() {
  rm -rf .venv
  python -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -e '.[dev,pdf]'
}

wait_for_docker() {
  local attempt
  for attempt in $(seq 1 30); do
    if docker info >/dev/null 2>&1; then
      docker version
      return 0
    fi
    sleep 1
  done
  echo "Docker-in-Docker did not become ready within 30 seconds" >&2
  return 1
}

if [[ "$MODE" == "checks" || "$MODE" == "publish" ]]; then
  install_hugo
  install_python_environment
fi

if [[ "$MODE" == "publish" ]]; then
  apt-get install -y --no-install-recommends docker.io poppler-utils
  .venv/bin/python -m playwright install --with-deps chromium
  wait_for_docker
elif [[ "$MODE" == "vintage" ]]; then
  apt-get install -y --no-install-recommends docker.io
  rm -rf .venv
  python -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -e .
  wait_for_docker
fi

apt-get clean
rm -rf /var/lib/apt/lists/*

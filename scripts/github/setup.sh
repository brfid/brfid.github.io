#!/usr/bin/env bash
# Prepare a GitHub-hosted Ubuntu job from committed dependency locks.

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

install_hugo() {
  if [[ "$(uname -m)" != "x86_64" ]]; then
    echo "GitHub publication requires an amd64 runner" >&2
    exit 1
  fi

  curl --fail --location --silent --show-error \
    --output "/tmp/${HUGO_ASSET}" \
    "${HUGO_RELEASE}/${HUGO_ASSET}"
  cp requirements/hugo.sha256 /tmp/hugo.sha256
  (cd /tmp && sha256sum --check hugo.sha256)
  sudo dpkg --install "/tmp/${HUGO_ASSET}"
  rm -f "/tmp/${HUGO_ASSET}" /tmp/hugo.sha256
  hugo version
}

install_python_environment() {
  local lock_file="$1"

  rm -rf .venv
  python3 -m venv .venv
  .venv/bin/python -m pip install --require-hashes -r requirements/build.lock
  .venv/bin/python -m pip install --require-hashes -r "$lock_file"
  .venv/bin/python -m pip install --no-deps --no-build-isolation -e .
}

# GitHub-hosted ubuntu-latest runners already provide git, make, curl, and Docker natively;
# unlike a GitLab job container built FROM a slim image, there is no base image to bootstrap.
if [[ "$MODE" == "checks" ]]; then
  install_hugo
  install_python_environment requirements/dev.lock
elif [[ "$MODE" == "publish" ]]; then
  install_hugo
  install_python_environment requirements/publish.lock
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends poppler-utils
  .venv/bin/python -m playwright install --with-deps chromium
  docker version
else
  install_python_environment requirements/runtime.lock
  docker version
fi

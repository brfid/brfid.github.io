#!/usr/bin/env bash
# Install the same tools for pull-request validation and main-branch builds.
set -euo pipefail

readonly HUGO_VERSION="0.163.3"
readonly HUGO_ASSET="hugo_extended_${HUGO_VERSION}_linux-amd64.deb"
readonly HUGO_RELEASE="https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}"

if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "GitHub publication requires an amd64 runner" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_INPUT=1

curl --fail --location --silent --show-error --retry 3 \
  --output "/tmp/${HUGO_ASSET}" "${HUGO_RELEASE}/${HUGO_ASSET}"
cp requirements/hugo.sha256 /tmp/hugo.sha256
(cd /tmp && sha256sum --check hugo.sha256)
sudo dpkg --install "/tmp/${HUGO_ASSET}"
rm -f "/tmp/${HUGO_ASSET}" /tmp/hugo.sha256

python -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements/build.lock
.venv/bin/python -m pip install --require-hashes -r requirements/dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
# Chromium comes from Playwright; the runner's Google APT index is unused.
for apt_source in /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
  if [[ -f "$apt_source" ]] && grep -Eq 'https?://dl\.google\.com/linux/chrome(-stable)?/deb/?([[:space:]]|$)' "$apt_source"; then
    sudo mv "$apt_source" "${apt_source}.disabled"
  fi
done
sudo apt-get update
sudo apt-get install -y --no-install-recommends poppler-utils
.venv/bin/python -m playwright install --with-deps chromium
make check_env

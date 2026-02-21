#!/bin/bash
# Start the single edcloud instance.
# Thin bash wrapper retained for operator ergonomics.

set -euo pipefail

exec .venv/bin/python scripts/edcloud_lifecycle.py start

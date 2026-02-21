#!/bin/bash
# Check edcloud host status.
# Thin bash wrapper retained for operator ergonomics.

set -euo pipefail

exec .venv/bin/python scripts/edcloud_lifecycle.py status

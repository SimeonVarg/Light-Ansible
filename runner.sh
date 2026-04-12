#!/bin/bash
set -euo pipefail

# Resolve the directory this script lives in — no hardcoded paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Light-Ansible Provisioner..."

# Ensure Python3 is available
if ! command -v python3 &>/dev/null; then
    echo "Python3 not found — installing..."
    apt-get update && apt-get install -y python3
fi

# Pass any arguments through (e.g. --dry-run)
sudo python3 "$SCRIPT_DIR/provisioner.py" "$@"

echo "Provisioning complete."

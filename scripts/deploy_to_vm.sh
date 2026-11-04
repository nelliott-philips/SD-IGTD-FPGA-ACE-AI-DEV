#!/bin/sh
# Deploys the whole ai_ace_development repo root (including the firmware/
# submodule tree) to a fresh, uniquely-named directory on the VM under
# /repos. Plain files only -- no .git metadata goes to the VM, and the VM
# never needs its own GitHub credentials (see docs/vm-ssh-sftp-setup.md
# and the firmware submodule's own README for why).
#
# Destination name: SD-IGTD-ACE-FPGA_<YYYYMMDD>_<HHMMSS>_<shortsha>
#   - timestamp = when this deploy ran (unique per run, sorts chronologically)
#   - shortsha  = firmware/'s HEAD commit at deploy time (traceability)
#
# Usage (from the repo root or anywhere):
#   ./scripts/deploy_to_vm.sh

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d firmware/.git ] && [ ! -f firmware/.git ]; then
    echo "FAIL: firmware/ submodule isn't checked out yet (run git submodule update --init --recursive first)"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SHORTSHA=$(git -C firmware rev-parse --short HEAD)
REMOTE_DIR="/repos/SD-IGTD-ACE-FPGA_${TIMESTAMP}_${SHORTSHA}"
ARCHIVE="/tmp/ai_ace_development_deploy_${TIMESTAMP}.tar.gz"

echo "=== [1/4] Packaging ${REPO_ROOT} (excluding all .git metadata) ==="
tar --exclude-vcs -czf "$ARCHIVE" -C "$REPO_ROOT" .
ls -la "$ARCHIVE"

echo "=== [2/4] Creating ${REMOTE_DIR} on the VM ==="
ssh xilinx-ise-github "mkdir -p '${REMOTE_DIR}'"

echo "=== [3/4] Transferring and extracting ==="
scp "$ARCHIVE" "xilinx-ise-github:${REMOTE_DIR}/deploy.tar.gz"
ssh xilinx-ise-github "cd '${REMOTE_DIR}' && tar xzf deploy.tar.gz && rm deploy.tar.gz"

echo "=== [4/4] Done ==="
rm -f "$ARCHIVE"
echo "Deployed to ${REMOTE_DIR}"

#!/bin/sh
# Automated SFTP-based sync to ONE stable directory on the VM (no git,
# no credentials on the VM) -- for scheduled/automated runs. Unlike
# deploy_to_vm.sh (which makes a new timestamped snapshot every run, for
# deliberate on-demand use), this overwrites /repos/ai_ace_development_live
# in place every time, via an atomic directory swap: extract into a fresh
# ".new" directory, then rename it into place. A build process reading the
# live directory mid-sync always sees either the complete old tree or the
# complete new one -- never a half-updated mix.
#
# Intended to run on its own schedule (e.g. Windows Task Scheduler on the
# host), independent of git pushes.
#
# Usage: ./scripts/sync_to_vm_stable.sh

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

STABLE_DIR=/repos/ai_ace_development_live
NEW_DIR="${STABLE_DIR}.new"
PREV_DIR="${STABLE_DIR}.prev"
ARCHIVE="/tmp/ai_ace_development_stable_sync.tar.gz"

echo "=== $(date -Iseconds) [1/4] Packaging ${REPO_ROOT} (excluding .git) ==="
tar --exclude-vcs -czf "$ARCHIVE" -C "$REPO_ROOT" .

echo "=== [2/4] Transferring ==="
ssh xilinx-ise-github "rm -rf '${NEW_DIR}' && mkdir -p '${NEW_DIR}'"
scp "$ARCHIVE" "xilinx-ise-github:${NEW_DIR}/sync.tar.gz"

echo "=== [3/4] Extracting and atomically swapping into place ==="
ssh xilinx-ise-github "
  set -e
  cd '${NEW_DIR}' && tar xzf sync.tar.gz && rm sync.tar.gz
  rm -rf '${PREV_DIR}'
  if [ -d '${STABLE_DIR}' ]; then mv '${STABLE_DIR}' '${PREV_DIR}'; fi
  mv '${NEW_DIR}' '${STABLE_DIR}'
  rm -rf '${PREV_DIR}'
"

echo "=== [4/4] Done ==="
rm -f "$ARCHIVE"
echo "Synced to ${STABLE_DIR}"

#!/bin/sh
# Keeps the VM's checkout of this repo concurrent with GitHub -- intended
# to run on a schedule via cron, no manual or AI involvement needed per run.
#
# One-time setup (interactive, at the VM console, so the GitHub login
# prompt has somewhere to render):
#   git config --global credential.helper store
#   git clone https://github.com/nelliott-philips/SD-IGTD-FPGA-ACE-AI-DEV.git /repos/ai_ace_development
#   cd /repos/ai_ace_development
#   git config url."https://github.com/".insteadOf "git@github.com:"
#   git submodule update --init --recursive
#
# Then add this script to cron, e.g. every 15 minutes:
#   */15 * * * * /repos/ai_ace_development/scripts/vm_sync_from_github.sh >> /var/log/ai_ace_sync.log 2>&1
#
# --ff-only is deliberate: changes only ever flow host -> VM. If the VM's
# branch ever diverges (it shouldn't), this fails loudly instead of
# silently creating a merge commit.

set -e
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "=== $(date -Iseconds) syncing ${REPO_DIR} ==="
git pull --ff-only
git submodule update --init --recursive
echo "=== sync ok, now at $(git rev-parse --short HEAD) ==="

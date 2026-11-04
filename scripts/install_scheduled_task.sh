#!/bin/sh
# Installs (or re-installs) the Windows Scheduled Task that runs
# sync_to_vm_stable.sh automatically. See docs/vm-scheduled-sync-task.md
# for the full picture, including how to disable/remove/modify it by hand.
#
# Idempotent: re-running this replaces the existing task definition
# (schtasks /f), so it's safe to re-run after changing INTERVAL_HOURS
# below, or on a fresh machine after cloning this repo.
#
# Usage: ./scripts/install_scheduled_task.sh

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK_NAME="AI_ACE_Dev_VM_Stable_Sync"
INTERVAL_HOURS=4
BASH_EXE="C:\Program Files\Git\usr\bin\bash.exe"
SCRIPT_UNIX_PATH="${REPO_ROOT}/scripts/sync_to_vm_stable.sh"
LOG_UNIX_PATH="${REPO_ROOT}/sync_to_vm_stable.log"

echo "Installing scheduled task '${TASK_NAME}' (every ${INTERVAL_HOURS}h)..."
MSYS2_ARG_CONV_EXCL="*" schtasks /create /tn "${TASK_NAME}" \
  /tr "\"${BASH_EXE}\" -lc \"${SCRIPT_UNIX_PATH} >> ${LOG_UNIX_PATH} 2>&1\"" \
  /sc hourly /mo "${INTERVAL_HOURS}" /st 00:00 /f

echo "Done. Check with: schtasks /query /tn \"${TASK_NAME}\" /v /fo list"

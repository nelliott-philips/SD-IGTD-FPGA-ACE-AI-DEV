#!/bin/sh
# Removes the Windows Scheduled Task created by install_scheduled_task.sh.
# See docs/vm-scheduled-sync-task.md for disable-vs-remove guidance --
# this deletes the task definition entirely; use `schtasks /change /tn
# AI_ACE_Dev_VM_Stable_Sync /disable` instead if you just want to pause it.
#
# Usage: ./scripts/uninstall_scheduled_task.sh

set -e
TASK_NAME="AI_ACE_Dev_VM_Stable_Sync"

echo "Removing scheduled task '${TASK_NAME}'..."
MSYS2_ARG_CONV_EXCL="*" schtasks /delete /tn "${TASK_NAME}" /f
echo "Done."

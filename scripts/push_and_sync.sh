#!/bin/sh
# Event-driven alternative to cron polling: run this instead of a bare
# `git push`. The instant the push to GitHub succeeds, it immediately
# triggers the VM to pull -- no polling, no fixed interval, fires exactly
# once per push. (There's no standard git "post-push" hook to attach this
# to automatically; this wrapper is the simple substitute -- use it in
# place of `git push`, or point your own alias at it.)
#
# Usage: ./scripts/push_and_sync.sh [git push args...]
# e.g.:  ./scripts/push_and_sync.sh origin main

set -e
git push "$@"
echo "=== push ok, triggering VM sync ==="
ssh xilinx-ise-github '/repos/ai_ace_development/scripts/vm_sync_from_github.sh'

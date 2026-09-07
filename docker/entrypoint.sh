#!/bin/sh
set -e
cd /app
if [ "${1:-}" = "agent" ]; then
  shift
  exec python /app/agent_core.py "$@"
fi
if [ "${CYBOPAL_AGENT:-0}" = "1" ]; then
  python /app/agent_core.py --mode demo &
fi
exec python /app/mock_device.py

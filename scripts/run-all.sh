#!/usr/bin/env bash
# Bring up the visual simulator + Hermes demo loop (no GPU).
# Pass --vllm to also expect a model server on :8000.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p "$HOME/.grok/long-running-background-tasks"

if ss -tln | grep -q ':5000 '; then
  echo "simulator already listening on :5000"
else
  nohup python3 mock_device.py >"$HOME/.grok/long-running-background-tasks/cybopal-sim.log" 2>&1 &
  echo "simulator pid $!"
fi

for i in $(seq 1 30); do
  curl -fsS http://127.0.0.1:5000/api/v1/health >/dev/null 2>&1 && break
  sleep 0.2
done
curl -fsS http://127.0.0.1:5000/api/v1/health

MODE="demo"
if [[ "${1:-}" == "--vllm" ]]; then
  MODE="vllm"
fi
echo
echo "Dashboard  http://127.0.0.1:5000/"
echo "Starting Hermes loop (--mode ${MODE})"
exec python3 agent_core.py --mode "$MODE"

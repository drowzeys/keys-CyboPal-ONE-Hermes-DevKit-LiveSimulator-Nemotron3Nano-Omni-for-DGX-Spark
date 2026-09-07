#!/usr/bin/env bash
# One-shot: venv + deps + live CyboPal simulator (+ optional Hermes demo loop).
#   ./oneshot.sh           # dashboard only (no GPU)
#   ./oneshot.sh --agent   # dashboard + Hermes demo tracker
#   ./oneshot.sh --omni    # also print the vLLM Nemotron Omni command (does not autostart GPU)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
PORT="${PORT:-5000}"
PY="${PYTHON:-python3}"

echo "== keys CyboPal ONE Hermes DevKit =="
echo "root  $ROOT"

if [[ ! -d .venv ]]; then
  echo "== venv =="
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

if ss -tln 2>/dev/null | grep -q ":${PORT} "; then
  echo "simulator already on :${PORT}"
else
  echo "== simulator :${PORT} =="
  mkdir -p "$HOME/.grok/long-running-background-tasks"
  nohup python mock_device.py >"$HOME/.grok/long-running-background-tasks/cybopal-sim.log" 2>&1 &
  echo "pid $!"
fi

for _ in $(seq 1 40); do
  curl -fsS "http://127.0.0.1:${PORT}/api/v1/health" >/dev/null 2>&1 && break
  sleep 0.15
done
curl -fsS "http://127.0.0.1:${PORT}/api/v1/health"
echo
echo "Dashboard   http://127.0.0.1:${PORT}/"
echo "Walkthrough video/simplescreenrecorder.mp4"
echo
echo "Program it:"
echo "  ./scripts/cybopal.sh mode sit"
echo "  ./scripts/cybopal.sh skill skills/examples/wave-hello.json"
echo "  ./scripts/cybopal.sh md skills/examples/briefing.md"

if [[ "${1:-}" == "--agent" || "${1:-}" == "--demo" ]]; then
  echo "== Hermes demo loop (no GPU) =="
  exec python agent_core.py --mode demo
fi

if [[ "${1:-}" == "--omni" ]]; then
  echo
  echo "Nemotron 3 Nano Omni on this Spark (GMU cap 0.85) — run in another terminal:"
  echo "  bash scripts/serve-vllm.sh"
  echo "  python agent_core.py --mode vllm"
fi

#!/usr/bin/env bash
# One-shot CyboPal ONE Hermes DevKit.
# Prefers the prebuilt GHCR image. Falls back to a local venv.
#
#   ./oneshot.sh              # dashboard (docker pull if possible)
#   ./oneshot.sh --agent      # dashboard + Hermes demo tracker
#   ./oneshot.sh --local      # skip docker, use ./venv
#   ./oneshot.sh --omni       # print the vLLM Nemotron Omni command (does not autostart GPU)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
PORT="${PORT:-5000}"
PY="${PYTHON:-python3}"
TAG="${CYBOPAL_TAG:-0.1.0}"
SHORT="ghcr.io/drowzeys/keys-cybopal-one-hermes-devkit:${TAG}"
LONG="ghcr.io/drowzeys/keys-cybopal-one-hermes-devkit-livesimulator-nemotron3nano-omni-for-dgx-spark:${TAG}"
IMAGE="${CYBOPAL_IMAGE:-$SHORT}"

echo "== keys CyboPal ONE Hermes DevKit =="
echo "root  $ROOT"

use_docker=0
if [[ "${1:-}" != "--local" ]] && command -v docker >/dev/null 2>&1; then
  use_docker=1
fi

if [[ "$use_docker" -eq 1 ]]; then
  echo "== docker ${IMAGE} =="
  if ! docker pull "$IMAGE"; then
    echo "short tag miss, trying ${LONG}"
    IMAGE="$LONG"
    docker pull "$IMAGE"
  fi
  extra=()
  [[ "${1:-}" == "--agent" || "${1:-}" == "--demo" ]] && extra=(-e CYBOPAL_AGENT=1)
  if docker ps -a --format '{{.Names}}' | grep -qx cybopal-sim; then
    docker rm -f cybopal-sim >/dev/null 2>&1 || true
  fi
  docker run -d --name cybopal-sim --network host --restart unless-stopped \
    -e PORT="$PORT" "${extra[@]}" "$IMAGE" >/dev/null
  echo "container cybopal-sim"
else
  echo "== venv (no docker) =="
  if [[ ! -d .venv ]]; then
    "$PY" -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install -q --upgrade pip
  python -m pip install -q -r requirements.txt
  if ss -tln 2>/dev/null | grep -q ":${PORT} "; then
    echo "simulator already on :${PORT}"
  else
    mkdir -p "$HOME/.grok/long-running-background-tasks"
    nohup python mock_device.py >"$HOME/.grok/long-running-background-tasks/cybopal-sim.log" 2>&1 &
    echo "pid $!"
  fi
  if [[ "${1:-}" == "--agent" || "${1:-}" == "--demo" ]]; then
    echo "== Hermes demo loop (no GPU) =="
    exec python agent_core.py --mode demo
  fi
fi

for _ in $(seq 1 50); do
  curl -fsS "http://127.0.0.1:${PORT}/api/v1/health" >/dev/null 2>&1 && break
  sleep 0.2
done
curl -fsS "http://127.0.0.1:${PORT}/api/v1/health"
echo
echo "Dashboard   http://127.0.0.1:${PORT}/"
echo "Walkthrough https://github.com/drowzeys/keys-CyboPal-ONE-Hermes-DevKit-LiveSimulator-Nemotron3Nano-Omni-for-DGX-Spark/releases/download/v0.1.0/CyboPal-ONE-Simulator.mov"
echo
echo "Program it:"
echo "  ./scripts/cybopal.sh mode sit"
echo "  ./scripts/cybopal.sh skill skills/examples/wave-hello.json"

if [[ "${1:-}" == "--omni" ]]; then
  echo
  echo "Nemotron 3 Nano Omni on this Spark (GMU cap 0.85) — other terminal:"
  echo "  bash scripts/serve-vllm.sh"
  echo "  python agent_core.py --mode vllm"
fi

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONUNBUFFERED=1
MODE="${1:-auto}"
exec python3 agent_core.py --mode "$MODE"

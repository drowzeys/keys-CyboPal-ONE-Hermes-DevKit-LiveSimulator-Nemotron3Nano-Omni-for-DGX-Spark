#!/usr/bin/env bash
# Nemotron 3 Nano Omni on this DGX Spark. GPU util is hard-capped at 0.85.
set -euo pipefail

GMU="${GPU_MEM_UTIL:-0.85}"
python3 - <<PY
g = float("${GMU}")
if g > 0.85:
    raise SystemExit(f"gpu-memory-utilization {g} exceeds fleet cap 0.85")
PY

PORT="${PORT:-8000}"
MAXLEN="${MAXLEN:-32768}"
NAME="${SERVED_NAME:-nemotron-omni}"
OFFICIAL="nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4"
AEON="${AEON_OMNI_PATH:-${HOME}/a4q-lab/models/aeon-omni}"
MODEL="${MODEL:-}"

if [[ -z "$MODEL" ]]; then
  if [[ -d "${HOME}/.cache/huggingface/hub/models--nvidia--Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4/snapshots" ]]; then
    MODEL="$OFFICIAL"
  elif [[ -f "${AEON}/config.json" ]]; then
    echo "official NVFP4 snapshot not in HF cache; using ${AEON}"
    MODEL="$AEON"
  else
    MODEL="$OFFICIAL"
    echo "will pull ${OFFICIAL} from Hugging Face on first serve"
  fi
fi

echo "vLLM serve  model=${MODEL}"
echo "  port=${PORT}  max-model-len=${MAXLEN}  gpu-memory-utilization=${GMU}  served-name=${NAME}"

exec vllm serve "$MODEL" \
  --served-model-name "$NAME" \
  --host 0.0.0.0 \
  --port "$PORT" \
  --tensor-parallel-size 1 \
  --trust-remote-code \
  --gpu-memory-utilization "$GMU" \
  --max-model-len "$MAXLEN" \
  --max-num-seqs 8 \
  --max-num-batched-tokens 8192 \
  --kv-cache-dtype fp8 \
  --limit-mm-per-prompt '{"video":1,"image":1,"audio":1}' \
  --media-io-kwargs '{"video":{"num_frames":128,"fps":1}}' \
  --video-pruning-rate 0.5 \
  --reasoning-parser nemotron_v3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --generation-config auto

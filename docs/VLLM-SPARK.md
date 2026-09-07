# Nemotron 3 Nano Omni on DGX Spark

Fleet hard cap: **`--gpu-memory-utilization` ≤ 0.85**. Do not raise it. If KV does not fit, lower `max-model-len` / `max-num-seqs` / `max-num-batched-tokens`.

```bash
bash scripts/serve-vllm.sh
python agent_core.py --mode vllm
```

Default checkpoint: [`nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4`](https://huggingface.co/nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4).

Overrides:

```bash
MODEL=/abs/path/to/weights bash scripts/serve-vllm.sh
AEON_OMNI_PATH=$HOME/a4q-lab/models/aeon-omni bash scripts/serve-vllm.sh
GPU_MEM_UTIL=0.80 MAXLEN=16384 PORT=8000 bash scripts/serve-vllm.sh
```

`agent_core.py` talks OpenAI-compatible `/v1` at `VLLM_URL` (default `http://127.0.0.1:8000/v1`) with tool `update_cybopal_state`. `--mode auto` uses vLLM when that port answers, otherwise the on-device tracker so the dashboard still moves.

Required on this box: vLLM ≥ 0.20 with audio extra (`vllm[audio]`), `reasoning-parser nemotron_v3`, `tool-call-parser qwen3_coder`.

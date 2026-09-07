---
name: cybopal-hermes-devkit
description: >
  Program, test, and control the CyboPal ONE live simulator and Hermes/Nemotron
  Omni loop on DGX Spark. Use when the user mentions CyboPal, Pauli, the desk
  robot monitor, Hermes DevKit, Nemotron 3 Nano Omni embodiment, or
  /cybopal-hermes-devkit.
---

# CyboPal ONE Hermes DevKit

Work in the repo root (clone of `keys-CyboPal-ONE-Hermes-DevKit-LiveSimulator-Nemotron3Nano-Omni-for-DGX-Spark`). Dashboard is `http://127.0.0.1:5000/`.

## Bring-up

```bash
./oneshot.sh            # sim only, no GPU
./oneshot.sh --agent    # sim + Hermes demo tracker
```

Never start vLLM unless asked. If asked: `bash scripts/serve-vllm.sh` then `python agent_core.py --mode vllm`. **gpu-memory-utilization ≤ 0.85.**

## Control

```bash
./scripts/cybopal.sh health
./scripts/cybopal.sh mode sit|stand|recline|tracking|wave|meeting|stow|idle|estop
./scripts/cybopal.sh pose pan=12 tilt=-6
./scripts/cybopal.sh md skills/examples/briefing.md
./scripts/cybopal.sh skill skills/examples/wave-hello.json
```

REST contract: `docs/API.md`. New repeatable behaviours go in `skills/examples/*.json` (schema in `skills/README.md`), then run them with `cybopal.sh skill`.

## Hardware later

Keep `/api/v1/control` and `/api/v1/mode`. Replace `cybopal/device.py` only.

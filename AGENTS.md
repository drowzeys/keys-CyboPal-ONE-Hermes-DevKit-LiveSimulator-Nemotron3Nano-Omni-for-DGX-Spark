# Agents

- Dashboard: `http://127.0.0.1:5000/` after `./oneshot.sh`
- Control CLI: `./scripts/cybopal.sh`
- Skills: `skills/examples/*.json` + `skills/README.md`
- GPU: only `scripts/serve-vllm.sh`. **gpu-memory-utilization ≤ 0.85**
- Hardware cutover: replace `cybopal/device.py`, keep REST paths
- Grok skill: `.grok/skills/cybopal-hermes-devkit/SKILL.md`

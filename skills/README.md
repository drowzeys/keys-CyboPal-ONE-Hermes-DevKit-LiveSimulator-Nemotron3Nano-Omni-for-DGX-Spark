# CyboPal skills

A skill is a JSON list of REST steps the live simulator already understands.
The same files will drive the physical CyboPal when `/api/v1/control` is pointed at hardware.

## Schema

```json
{
  "name": "short-id",
  "description": "what a human / Hermes should pick this for",
  "steps": [
    { "mode": "wave", "pauli_text": "HELLO", "display_markdown": "# Hi" },
    { "sleep": 2.0 },
    { "pan": 12, "tilt": -4, "height_mm": 220 }
  ]
}
```

Fields on a step (all optional except you need *something*):

| field | effect |
|---|---|
| `mode` | `tracking` `sit` `stand` `recline` `wave` `meeting` `stow` `idle` `estop` |
| `pan` `tilt` `roll` `elbow` | degrees |
| `height_mm` `reach_mm` | millimetres, 700 mm max reach |
| `display_markdown` | 27″ canvas |
| `pauli_text` | 3.5″ companion, keep it short |
| `sleep` | seconds after the step (or a sleep-only step) |

## Run

```bash
./scripts/cybopal.sh skill skills/examples/wave-hello.json
./scripts/cybopal.sh skill skills/examples/posture-cycle.json
```

Hermes on Nemotron Omni does not need JSON — it calls `update_cybopal_state` from `agent_core.py`. Use JSON skills for repeatable tests and for Grok / scripts that should not spend GPU.

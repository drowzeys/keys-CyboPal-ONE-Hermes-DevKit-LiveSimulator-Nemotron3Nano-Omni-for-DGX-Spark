# Architecture

```
                 DGX SPARK
        ┌────────────┴────────────┐
        │                         │
   :8000 vLLM                :5000 FastAPI
 Nemotron 3 Nano Omni     CyboPal ONE sim
   (vision + tools)        6-DOF + cameras
        │                         ▲
        └──────► Hermes ──────────┘
              agent_core.py
              update_cybopal_state
```

- **Firmware follow** lives inside `cybopal/device.py`. When `mode=tracking`, the chassis PID-tracks the simulated operator in the bezel camera. Hermes does not have to servo the joints unless you want it to.
- **Dashboard** (`static/`) is a WebSocket client: 3D-ish arm, Pauli, 27″ markdown, dual MJPEG, joint meters, action log, manual sliders.
- **Skills** are JSON step lists posted at the same REST contract (`scripts/run_skill.py`).
- **Hardware cutover:** implement the same methods `CyboPalSim` exposes (telemetry, apply_control, set_mode, camera JPEG). `agent_core.py` and the dashboard stay.

Joint envelope (stand-in until CyboPal publishes an SDK):

| joint | range |
|---|---|
| pan | −55 … +55 ° |
| tilt | −35 … +35 ° |
| height_mm | 80 … 420 |
| reach_mm | 80 … 700 |
| roll | −18 … +18 ° |
| elbow | −40 … +25 ° |

Presets: `sit` `stand` `recline` `meeting` `stow` `wave`.

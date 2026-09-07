# HTTP contract

Keep these paths when the USB-C CyboPal ships. Swap `cybopal/device.py`, not the agent.

Base URL: `http://127.0.0.1:5000`

| Method | Path | Body / notes |
|---|---|---|
| GET | `/` | Live dashboard |
| GET | `/api/v1/health` | `{ok, device, mode}` |
| GET | `/api/v1/limits` | Joint limits + named presets |
| GET | `/api/v1/telemetry` | `{status, hardware_state}` — pose, cartesian, user, displays, events |
| POST | `/api/v1/control` | Any subset of `pan, tilt, height_mm, reach_mm, roll, elbow, display_markdown, pauli_text, mode` |
| POST | `/api/v1/mode` | `{ "mode": "tracking" }` |
| GET | `/api/v1/camera/frame` | Bezel JPEG (recipe name) |
| GET | `/api/v1/camera/bezel` | same |
| GET | `/api/v1/camera/base` | Base JPEG |
| GET | `/api/v1/camera/bezel.mjpeg` | multipart stream |
| GET | `/api/v1/camera/base.mjpeg` | multipart stream |
| WS | `/ws/telemetry` | ~20 Hz JSON snapshot |

Recipe-compatible control:

```bash
curl -s -X POST http://127.0.0.1:5000/api/v1/control \
  -H 'content-type: application/json' \
  -d '{"tilt":8,"pan":-12,"display_markdown":"# Hermes\nReady."}'
```

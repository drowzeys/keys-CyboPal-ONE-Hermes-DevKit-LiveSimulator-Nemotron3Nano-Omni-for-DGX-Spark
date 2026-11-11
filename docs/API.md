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
| POST | `/api/v1/media?caption=` | Raw picture or video bytes (`Content-Type` image/png, jpeg, webp, gif, video/mp4, webm; up to 64 MB) shown on the 27″ screen; 409 while E-stopped |
| GET | `/api/v1/media/{id}` | The picture or video on screen |
| DELETE | `/api/v1/media` | Take it off the screen (new `display_markdown` also replaces it) |
| POST | `/api/v1/camera/feed/{bezel\|base}` | A photo (png, jpeg, webp) standing in for that camera: a receipt held up, a person at the desk; for tests and demos |
| DELETE | `/api/v1/camera/feed/{bezel\|base}` | Back to the simulated scene |

Recipe-compatible control:

```bash
curl -s -X POST http://127.0.0.1:5000/api/v1/control \
  -H 'content-type: application/json' \
  -d '{"tilt":8,"pan":-12,"display_markdown":"# Hermes\nReady."}'
```

Telemetry's `hardware_state` also carries `display_media` (`{id, kind, mime, caption, url, bytes}` or null) and
`camera_feed` (`{bezel, base}`: whether a feed photo is attached).

## Engineer actions here, deploy them on the unit

The simulator is the place to build and test new actions before they reach hardware: a Hermes routine (see the
`hermes-cybopal-one-devkit` plugin's `save_as`) or a JSON skill is run and adjusted here, and since the hardware
keeps these same paths, it runs unchanged on the physical CyboPal ONE once clients point at it.

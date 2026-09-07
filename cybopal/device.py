"""In-memory CyboPal ONE: 6-DOF arm, dual cameras, Pauli + main displays.

When the physical unit arrives, keep the REST contract in mock_device.py and
replace CyboPalSim with a USB-C / vendor-SDK backend. Joint names and limits
are a working stand-in (CyboPal has not published a public control API yet).
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Mode = Literal["idle", "tracking", "follow", "preset", "agent", "estop"]

LIMITS = {
    "pan": (-55.0, 55.0),
    "tilt": (-35.0, 35.0),
    "height_mm": (80.0, 420.0),
    "reach_mm": (80.0, 700.0),
    "roll": (-18.0, 18.0),
    "elbow": (-40.0, 25.0),
}


def _clamp(name: str, value: float) -> float:
    lo, hi = LIMITS[name]
    return max(lo, min(hi, float(value)))


@dataclass
class Pose:
    pan: float = 0.0
    tilt: float = 6.0
    height_mm: float = 200.0
    reach_mm: float = 300.0
    roll: float = 0.0
    elbow: float = -8.0

    def clamped(self) -> "Pose":
        return Pose(
            pan=_clamp("pan", self.pan),
            tilt=_clamp("tilt", self.tilt),
            height_mm=_clamp("height_mm", self.height_mm),
            reach_mm=_clamp("reach_mm", self.reach_mm),
            roll=_clamp("roll", self.roll),
            elbow=_clamp("elbow", self.elbow),
        )

    def as_dict(self) -> dict[str, float]:
        return {k: round(v, 2) for k, v in asdict(self).items()}


PRESETS: dict[str, Pose] = {
    "sit": Pose(pan=0, tilt=6, height_mm=190, reach_mm=300, roll=0, elbow=-6),
    "stand": Pose(pan=0, tilt=12, height_mm=400, reach_mm=210, roll=0, elbow=4),
    "recline": Pose(pan=0, tilt=-24, height_mm=130, reach_mm=520, roll=0, elbow=-18),
    "meeting": Pose(pan=18, tilt=4, height_mm=230, reach_mm=340, roll=0, elbow=-4),
    "stow": Pose(pan=0, tilt=18, height_mm=90, reach_mm=90, roll=0, elbow=8),
    "wave_left": Pose(pan=-28, tilt=8, height_mm=240, reach_mm=360, roll=-8, elbow=-2),
    "wave_right": Pose(pan=28, tilt=8, height_mm=240, reach_mm=360, roll=8, elbow=-2),
}


@dataclass
class User:
    """Simulated person at the desk, millimetres, origin at arm base."""

    x: float = 0.0
    y: float = 420.0
    z: float = 620.0


@dataclass
class Event:
    t: float
    kind: str
    message: str
    extra: dict[str, Any] = field(default_factory=dict)


class CyboPalSim:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.pose = Pose()
        self.target = Pose()
        self.user = User()
        self.mode: Mode = "idle"
        self.display_markdown = (
            "# CyboPal ONE\n\nSimulator online. Waiting for Hermes.\n\n"
            "- 27″ 4K main display\n- 3.5″ Pauli companion\n- 6-DOF arm, 700 mm reach"
        )
        self.pauli_text = "READY"
        self.safety = {"estop": False, "collision": False, "in_bounds": True}
        self.events: deque[Event] = deque(maxlen=120)
        self.started = time.time()
        self._last_tick = self.started
        self._user_phase = 0.0
        self._wave_until = 0.0
        self._wave_flip = False
        self.speed = 3.4  # lerp gain
        self.log("boot", "CyboPal ONE simulator chassis online")

    def log(self, kind: str, message: str, **extra: Any) -> None:
        self.events.appendleft(Event(t=time.time(), kind=kind, message=message, extra=extra))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self.tick()
            u, v = self.project_user()
            return {
                "status": "ESTOP" if self.mode == "estop" else "ONLINE",
                "mode": self.mode,
                "pose": self.pose.as_dict(),
                "target": self.target.as_dict(),
                "arm_coordinates": self.cartesian(),
                "user": {"x": round(self.user.x, 1), "y": round(self.user.y, 1), "z": round(self.user.z, 1)},
                "user_in_frame": {"u": round(u, 1), "v": round(v, 1)},
                "display_markdown": self.display_markdown,
                "pauli_text": self.pauli_text,
                "safety": dict(self.safety),
                "uptime_s": round(time.time() - self.started, 1),
                "events": [
                    {
                        "t": e.t,
                        "kind": e.kind,
                        "message": e.message,
                        "extra": e.extra,
                    }
                    for e in list(self.events)[:24]
                ],
            }

    def cartesian(self) -> dict[str, float]:
        pan = math.radians(self.pose.pan)
        return {
            "x": round(math.sin(pan) * self.pose.reach_mm, 1),
            "y": round(self.pose.height_mm, 1),
            "z": round(math.cos(pan) * self.pose.reach_mm, 1),
            "yaw": round(self.pose.pan, 2),
            "pitch": round(self.pose.tilt, 2),
            "roll": round(self.pose.roll, 2),
        }

    def project_user(self) -> tuple[float, float]:
        """Pinhole project the simulated user into the bezel camera frame."""
        pan = math.radians(self.pose.pan)
        tilt = math.radians(self.pose.tilt)
        mx = math.sin(pan) * self.pose.reach_mm
        mz = math.cos(pan) * self.pose.reach_mm
        my = self.pose.height_mm + 170.0  # bezel cam, top of the 27" panel
        dx = self.user.x - mx
        dy = self.user.y - my
        dz = self.user.z - mz
        # World → camera: inverse yaw about Y, then inverse pitch about X.
        x1 = dx * math.cos(pan) - dz * math.sin(pan)
        z1 = dx * math.sin(pan) + dz * math.cos(pan)
        y1 = dy
        y2 = y1 * math.cos(tilt) + z1 * math.sin(tilt)
        z2 = -y1 * math.sin(tilt) + z1 * math.cos(tilt)
        z2 = max(z2, 40.0)
        f = (0.5 * 640.0) / math.tan(math.radians(28.0))
        u = 320.0 + f * x1 / z2
        v = 240.0 - f * y2 / z2
        return u, v

    def apply_control(
        self,
        *,
        pan: float | None = None,
        tilt: float | None = None,
        height_mm: float | None = None,
        reach_mm: float | None = None,
        roll: float | None = None,
        elbow: float | None = None,
        display_markdown: str | None = None,
        pauli_text: str | None = None,
        mode: str | None = None,
        source: str = "api",
    ) -> dict[str, Any]:
        with self._lock:
            if self.mode == "estop" and mode not in ("idle", "tracking", "follow", "preset", "agent"):
                self.log("reject", "ESTOP latched — reset mode before commanding motors")
                return self.snapshot()
            changed: list[str] = []
            t = self.target
            if pan is not None:
                t.pan = _clamp("pan", pan)
                changed.append(f"pan={t.pan:.1f}°")
            if tilt is not None:
                t.tilt = _clamp("tilt", tilt)
                changed.append(f"tilt={t.tilt:.1f}°")
            if height_mm is not None:
                t.height_mm = _clamp("height_mm", height_mm)
                changed.append(f"height={t.height_mm:.0f}mm")
            if reach_mm is not None:
                t.reach_mm = _clamp("reach_mm", reach_mm)
                changed.append(f"reach={t.reach_mm:.0f}mm")
            if roll is not None:
                t.roll = _clamp("roll", roll)
                changed.append(f"roll={t.roll:.1f}°")
            if elbow is not None:
                t.elbow = _clamp("elbow", elbow)
                changed.append(f"elbow={t.elbow:.1f}°")
            if display_markdown is not None:
                self.display_markdown = display_markdown[:8000]
                changed.append("main display")
            if pauli_text is not None:
                self.pauli_text = pauli_text[:80]
                changed.append(f"pauli={self.pauli_text}")
            if mode is not None:
                self.set_mode(mode)
                changed.append(f"mode={self.mode}")
            elif source == "agent" and self.mode not in ("estop", "tracking", "follow"):
                self.mode = "agent"
            if changed:
                self.log(source, " · ".join(changed))
            return self.snapshot()

    def set_mode(self, mode: str) -> None:
        mode = mode.lower().strip()
        if mode == "estop":
            self.mode = "estop"
            self.safety["estop"] = True
            self.target = Pose(**self.pose.as_dict())
            self.pauli_text = "E-STOP"
            self.log("safety", "Emergency stop — motors frozen")
            return
        self.safety["estop"] = False
        if mode in PRESETS:
            self.mode = "preset"
            self.target = Pose(**asdict(PRESETS[mode]))
            self.pauli_text = mode.upper()
            self.log("preset", f"Moving to {mode}")
            return
        if mode == "wave":
            self.mode = "preset"
            self._wave_until = time.time() + 4.0
            self._wave_flip = False
            self.target = Pose(**asdict(PRESETS["wave_left"]))
            self.pauli_text = "WAVE"
            self.log("preset", "Gesture: wave in / pull back")
            return
        if mode in ("tracking", "follow"):
            if self.mode != "tracking":
                self.log("firmware", "On-device tracking engaged")
            self.mode = "tracking"
            if self.pauli_text in ("READY", "IDLE", "E-STOP"):
                self.pauli_text = "FOLLOW"
            return
        if mode in ("idle", "agent", "preset"):
            self.mode = mode  # type: ignore[assignment]
            if mode == "idle":
                self.pauli_text = "IDLE"
            return
        self.log("reject", f"Unknown mode '{mode}'")

    def tick(self) -> None:
        now = time.time()
        dt = min(0.08, max(0.0, now - self._last_tick))
        self._last_tick = now
        if dt <= 0:
            return
        self._animate_user(now)
        if self.mode == "estop":
            return
        if self._wave_until > now:
            # Alternate left/right while the wave gesture is live.
            if self._near_target():
                self._wave_flip = not self._wave_flip
                key = "wave_right" if self._wave_flip else "wave_left"
                self.target = Pose(**asdict(PRESETS[key]))
        elif self.mode == "tracking":
            self._firmware_track(dt)
            self.target.roll += (0.0 - self.target.roll) * min(1.0, 1.5 * dt)
            self.target.elbow += (PRESETS["sit"].elbow - self.target.elbow) * min(1.0, 1.2 * dt)
        else:
            # Idle breathing so the chassis never looks dead.
            if self.mode == "idle":
                self.target.height_mm = _clamp(
                    "height_mm", PRESETS["sit"].height_mm + 6.0 * math.sin(now * 0.7)
                )
        self._lerp(dt)

    def _near_target(self, eps: float = 2.5) -> bool:
        a, b = self.pose, self.target
        return (
            abs(a.pan - b.pan) < eps
            and abs(a.tilt - b.tilt) < eps
            and abs(a.height_mm - b.height_mm) < 8
            and abs(a.reach_mm - b.reach_mm) < 8
        )

    def _animate_user(self, now: float) -> None:
        # Person shifts in the chair and leans — the thing tracking should chase.
        t = now - self.started
        self.user.x = 160.0 * math.sin(t * 0.28) + 28.0 * math.sin(t * 0.7)
        self.user.z = 620.0 + 70.0 * math.sin(t * 0.2)
        self.user.y = 390.0 + 24.0 * math.sin(t * 0.16)

    def _firmware_track(self, dt: float) -> None:
        u, v = self.project_user()
        err_x = (u - 320.0) / 320.0
        err_y = (v - 240.0) / 240.0
        self.target.pan = _clamp("pan", self.target.pan + err_x * 70.0 * dt)
        self.target.tilt = _clamp("tilt", self.target.tilt + err_y * 55.0 * dt)
        # Ease reach toward the user's depth so sit/lean still feels connected.
        desired_reach = _clamp("reach_mm", max(180.0, self.user.z - 280.0))
        self.target.reach_mm += (desired_reach - self.target.reach_mm) * min(1.0, 1.2 * dt)

    def _lerp(self, dt: float) -> None:
        k = min(1.0, self.speed * dt)
        for name in ("pan", "tilt", "height_mm", "reach_mm", "roll", "elbow"):
            cur = getattr(self.pose, name)
            tgt = getattr(self.target, name)
            setattr(self.pose, name, cur + (tgt - cur) * k)
        self.pose = self.pose.clamped()
        cart = self.cartesian()
        self.safety["in_bounds"] = all(
            LIMITS[n][0] <= getattr(self.pose, n) <= LIMITS[n][1] for n in LIMITS
        )
        self.safety["collision"] = cart["z"] < 40 or abs(cart["x"]) > 680

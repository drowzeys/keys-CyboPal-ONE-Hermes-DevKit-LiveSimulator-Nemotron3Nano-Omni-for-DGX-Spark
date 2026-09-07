"""Synthetic bezel + base cameras. Viewpoint follows the live pose."""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from .device import CyboPalSim


def _desk_scene(w: int, h: int) -> np.ndarray:
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    # Wall
    frame[:] = (28, 24, 22)
    # Window light
    cv2.rectangle(frame, (w - 160, 12), (w - 18, 150), (62, 52, 40), -1)
    cv2.rectangle(frame, (w - 154, 18), (w - 24, 144), (90, 78, 58), -1)
    # Desk plane
    desk_top = int(h * 0.58)
    pts = np.array(
        [[0, h], [0, desk_top + 20], [w, desk_top - 10], [w, h]], dtype=np.int32
    )
    cv2.fillConvexPoly(frame, pts, (42, 38, 48))
    wood = np.array([[40, desk_top + 8], [w - 20, desk_top - 18], [w - 8, desk_top + 36], [28, desk_top + 70]], np.int32)
    cv2.fillConvexPoly(frame, wood, (56, 78, 118))
    cv2.polylines(frame, [wood], True, (40, 56, 86), 1, cv2.LINE_AA)
    # Keyboard
    cv2.rectangle(frame, (int(w * 0.32), desk_top + 28), (int(w * 0.68), desk_top + 52), (38, 38, 42), -1)
    cv2.rectangle(frame, (int(w * 0.33), desk_top + 30), (int(w * 0.67), desk_top + 50), (70, 72, 78), 1)
    # Mug
    cv2.circle(frame, (int(w * 0.78), desk_top + 40), 14, (40, 90, 160), -1)
    cv2.circle(frame, (int(w * 0.78), desk_top + 40), 8, (28, 50, 90), -1)
    return frame


def _draw_user(frame: np.ndarray, u: float, v: float, scale: float = 1.0) -> None:
    x, y = int(u), int(v)
    h, w = frame.shape[:2]
    if not (-80 < x < w + 80 and -80 < y < h + 80):
        return
    s = max(0.45, min(1.6, scale))
    # Shoulders
    cv2.ellipse(frame, (x, y + int(52 * s)), (int(70 * s), int(38 * s)), 0, 0, 360, (48, 92, 40), -1, cv2.LINE_AA)
    # Head
    cv2.circle(frame, (x, y), int(36 * s), (96, 168, 220), -1, cv2.LINE_AA)
    cv2.circle(frame, (x, y), int(36 * s), (40, 90, 140), 2, cv2.LINE_AA)
    # Eyes
    cv2.circle(frame, (x - int(10 * s), y - int(4 * s)), max(2, int(4 * s)), (30, 30, 30), -1)
    cv2.circle(frame, (x + int(10 * s), y - int(4 * s)), max(2, int(4 * s)), (30, 30, 30), -1)


def _hud(frame: np.ndarray, sim: CyboPalSim, label: str) -> None:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 46), (0, 0, 0), -1)
    cv2.rectangle(overlay, (0, h - 36), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)
    pose = sim.pose
    cv2.putText(
        frame,
        f"CYBOPAL {label}  {sim.mode.upper()}  pan {pose.pan:+.1f}  tilt {pose.tilt:+.1f}",
        (12, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (220, 240, 255),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"SIM  {time.strftime('%H:%M:%S')}  h {pose.height_mm:.0f}mm  reach {pose.reach_mm:.0f}mm",
        (12, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (140, 210, 180),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "synthetic workspace - not a real camera",
        (12, h - 14),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (160, 160, 170),
        1,
        cv2.LINE_AA,
    )
    # Crosshair
    cv2.drawMarker(frame, (w // 2, h // 2), (90, 220, 180), cv2.MARKER_CROSS, 18, 1)


def render_bezel(sim: CyboPalSim, w: int = 640, h: int = 480) -> bytes:
    sim.tick()
    frame = _desk_scene(w, h)
    u, v = sim.project_user()
    # Apparent size from reach
    scale = max(0.5, min(1.5, 380.0 / max(120.0, sim.user.z - sim.pose.reach_mm * 0.3)))
    _draw_user(frame, u, v, scale)
    # Tracking box
    cv2.rectangle(
        frame,
        (int(u) - 50, int(v) - 50),
        (int(u) + 50, int(v) + 90),
        (80, 220, 120) if sim.mode == "tracking" else (120, 120, 130),
        1,
        cv2.LINE_AA,
    )
    _hud(frame, sim, "BEZEL CAM")
    ok, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        raise RuntimeError("jpeg encode failed")
    return jpeg.tobytes()


def render_base(sim: CyboPalSim, w: int = 640, h: int = 480) -> bytes:
    """Upward-looking desk camera: arm silhouette + user from below."""
    sim.tick()
    frame = np.full((h, w, 3), (22, 20, 26), dtype=np.uint8)
    # Ceiling wash
    cv2.circle(frame, (w // 2, 40), 220, (40, 36, 34), -1)
    desk_y = int(h * 0.78)
    cv2.rectangle(frame, (0, desk_y), (w, h), (50, 70, 105), -1)
    pan = math.radians(sim.pose.pan)
    # Arm as a line from base to screen
    base = (w // 2, desk_y - 8)
    reach_px = int(sim.pose.reach_mm * 0.28)
    height_px = int(sim.pose.height_mm * 0.42)
    tip = (
        int(base[0] + math.sin(pan) * reach_px),
        int(base[1] - height_px - math.cos(pan) * reach_px * 0.15),
    )
    cv2.line(frame, base, tip, (180, 186, 196), 7, cv2.LINE_AA)
    cv2.circle(frame, base, 16, (90, 96, 110), -1, cv2.LINE_AA)
    # Monitor slab
    tilt = math.radians(sim.pose.tilt)
    dx, dy = int(70 * math.cos(tilt)), int(40 * math.sin(tilt) + 28)
    cv2.rectangle(frame, (tip[0] - dx, tip[1] - dy), (tip[0] + dx, tip[1] + 8), (30, 32, 38), -1)
    cv2.rectangle(frame, (tip[0] - dx + 4, tip[1] - dy + 4), (tip[0] + dx - 4, tip[1] - 4), (180, 210, 90), -1)
    # User from below (top of head)
    u = int(w / 2 + sim.user.x * 0.35)
    v = int(desk_y - 90 - sim.user.z * 0.08)
    cv2.circle(frame, (u, v), 28, (96, 168, 220), -1, cv2.LINE_AA)
    _hud(frame, sim, "BASE CAM")
    ok, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        raise RuntimeError("jpeg encode failed")
    return jpeg.tobytes()

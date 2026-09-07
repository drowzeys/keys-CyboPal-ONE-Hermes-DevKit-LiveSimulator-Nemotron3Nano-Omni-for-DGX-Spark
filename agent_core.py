#!/usr/bin/env python3
"""Hermes loop: bezel camera → Nemotron Omni (vLLM) → CyboPal mock.

If vLLM is not up, runs a local tracker so the visual simulator still moves.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import time
from typing import Any

import httpx
from openai import AsyncOpenAI

MOCK = os.environ.get("CYBOPAL_URL", "http://127.0.0.1:5000").rstrip("/")
VLLM = os.environ.get("VLLM_URL", "http://127.0.0.1:8000/v1")
MODEL = os.environ.get("CYBOPAL_MODEL", "nemotron-omni")

SYSTEM = (
    "You are Hermes, the embodied operator of a CyboPal ONE desktop robotic terminal. "
    "The 27-inch 4K display sits on a 6-DOF arm (700 mm reach) with a 3.5-inch Pauli companion screen. "
    "You see a JPEG from the bezel camera of a simulated desk. "
    "Keep the person's head near frame center using pan (left/right degrees) and tilt (up/down degrees). "
    "height_mm 80-420, reach_mm 80-700. "
    "Write a short markdown briefing for the main display and a short ALL-CAPS status for Pauli. "
    "Prefer the update_cybopal_state tool. Do not narrate without calling the tool."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_cybopal_state",
            "description": "Move the CyboPal arm and push text to the main display and Pauli.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tilt": {"type": "number", "description": "Screen pitch degrees, -35..35"},
                    "pan": {"type": "number", "description": "Base yaw degrees, -55..55"},
                    "height_mm": {"type": "number"},
                    "reach_mm": {"type": "number"},
                    "display_markdown": {"type": "string"},
                    "pauli_text": {"type": "string"},
                    "mode": {
                        "type": "string",
                        "enum": ["tracking", "sit", "stand", "recline", "idle", "wave"],
                    },
                },
                "required": ["tilt", "pan", "display_markdown"],
            },
        },
    }
]


async def vllm_up(client: httpx.AsyncClient) -> bool:
    try:
        r = await client.get(VLLM.rstrip("/") + "/models", timeout=1.5)
        return r.status_code < 500
    except Exception:
        return False


async def pull_frame(client: httpx.AsyncClient) -> bytes:
    r = await client.get(f"{MOCK}/api/v1/camera/frame", timeout=5.0)
    r.raise_for_status()
    return r.content


async def pull_telem(client: httpx.AsyncClient) -> dict[str, Any]:
    r = await client.get(f"{MOCK}/api/v1/telemetry", timeout=5.0)
    r.raise_for_status()
    return r.json()["hardware_state"]


async def send_control(client: httpx.AsyncClient, payload: dict[str, Any]) -> None:
    r = await client.post(f"{MOCK}/api/v1/control", json=payload, timeout=5.0)
    r.raise_for_status()


def heuristic_action(telem: dict[str, Any]) -> dict[str, Any]:
    """Drive the displays. Firmware follow owns the joints unless vLLM says otherwise."""
    pose = telem["pose"]
    u = telem["user_in_frame"]["u"]
    v = telem["user_in_frame"]["v"]
    err_x = (u - 320.0) / 320.0
    err_y = (v - 240.0) / 240.0
    user = telem["user"]
    md = (
        f"# Hermes tracker\n\n"
        f"On-device follow is framing the simulated operator.\n\n"
        f"- pan **{pose['pan']:.1f}°** (frame err {err_x:+.2f})\n"
        f"- tilt **{pose['tilt']:.1f}°** (frame err {err_y:+.2f})\n"
        f"- height **{pose['height_mm']:.0f} mm** · reach **{pose['reach_mm']:.0f} mm**\n"
        f"- user `{user['x']:.0f}, {user['y']:.0f}, {user['z']:.0f}` mm\n"
    )
    payload = {
        "display_markdown": md,
        "pauli_text": "TRACK",
    }
    if telem.get("mode") != "tracking":
        payload["mode"] = "tracking"
    return payload


async def hermes_action(
    llm: AsyncOpenAI, frame: bytes, telem: dict[str, Any]
) -> dict[str, Any] | None:
    b64 = base64.b64encode(frame).decode("ascii")
    hint = (
        f"Telemetry JSON:\n{json.dumps({k: telem[k] for k in ('mode','pose','user','user_in_frame')})}\n"
        "Assess tracking. Call update_cybopal_state."
    )
    resp = await llm.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": hint},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            },
        ],
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.4,
        max_tokens=700,
    )
    msg = resp.choices[0].message
    if not msg.tool_calls:
        if msg.content:
            return {
                "display_markdown": msg.content[:4000],
                "pauli_text": "THINK",
            }
        return None
    args: dict[str, Any] = {}
    for tool in msg.tool_calls:
        try:
            parsed = json.loads(tool.function.arguments or "{}")
        except json.JSONDecodeError:
            continue
        args.update(parsed)
    return args or None


async def loop(mode: str, interval: float) -> None:
    print(f"CyboPal mock  {MOCK}")
    print(f"vLLM          {VLLM}  model={MODEL}")
    async with httpx.AsyncClient() as http:
        use_vllm = mode == "vllm" or (mode == "auto" and await vllm_up(http))
        if mode == "vllm" and not use_vllm:
            raise SystemExit("vLLM is not reachable at " + VLLM)
        print("loop          " + ("Nemotron Omni tool-calls" if use_vllm else "on-device tracker (no GPU)"))
        llm = AsyncOpenAI(base_url=VLLM, api_key=os.environ.get("VLLM_API_KEY", "spark-local"))
        n = 0
        while True:
            t0 = time.time()
            try:
                telem = await pull_telem(http)
                frame = await pull_frame(http)
                if use_vllm:
                    action = await hermes_action(llm, frame, telem)
                    if not action:
                        action = heuristic_action(telem)
                        action["pauli_text"] = "FALLBACK"
                else:
                    action = heuristic_action(telem)
                await send_control(http, action)
                n += 1
                pose = (await pull_telem(http))["pose"]
                print(
                    f"[{n:04d}] pan={pose['pan']:+6.1f} tilt={pose['tilt']:+5.1f} "
                    f"h={pose['height_mm']:.0f} r={pose['reach_mm']:.0f}  "
                    f"{action.get('pauli_text', '')}  {time.time()-t0:.2f}s"
                )
            except httpx.HTTPError as e:
                print(f"device/vLLM HTTP error: {e}")
                await asyncio.sleep(2)
                continue
            except KeyboardInterrupt:
                break
            delay = interval - (time.time() - t0)
            if delay > 0:
                await asyncio.sleep(delay)


def main() -> None:
    p = argparse.ArgumentParser(description="Hermes ↔ CyboPal simulator loop")
    p.add_argument("--mode", choices=("auto", "demo", "vllm"), default="auto")
    p.add_argument("--interval", type=float, default=2.0)
    args = p.parse_args()
    asyncio.run(loop(args.mode, args.interval))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Execute a CyboPal skill JSON against the live simulator (or future hardware)."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import httpx


def run_skill(url: str, skill: dict[str, Any]) -> None:
    name = skill.get("name", "unnamed")
    print(f"skill {name}: {skill.get('description', '')}")
    with httpx.Client(timeout=8.0) as http:
        for i, step in enumerate(skill.get("steps", []), 1):
            if "sleep" in step and len(step) == 1:
                print(f"  [{i}] sleep {step['sleep']}s")
                time.sleep(float(step["sleep"]))
                continue
            delay = float(step.pop("sleep", 0) or 0)
            if "mode" in step and set(step) <= {"mode", "sleep"}:
                print(f"  [{i}] mode {step['mode']}")
                http.post(f"{url}/api/v1/mode", json={"mode": step["mode"]}).raise_for_status()
            else:
                print(f"  [{i}] control { {k: step[k] for k in step if k != 'display_markdown'} }")
                http.post(f"{url}/api/v1/control", json=step).raise_for_status()
            if delay:
                time.sleep(delay)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("skill", type=Path)
    p.add_argument("--url", default="http://127.0.0.1:5000")
    args = p.parse_args()
    skill = json.loads(args.skill.read_text())
    run_skill(args.url.rstrip("/"), skill)


if __name__ == "__main__":
    main()

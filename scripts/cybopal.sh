#!/usr/bin/env bash
# Talk to a running CyboPal simulator (or, later, the same contract on hardware).
set -euo pipefail
URL="${CYBOPAL_URL:-http://127.0.0.1:5000}"
cmd="${1:-help}"
shift || true

json() { curl -fsS -H 'content-type: application/json' "$@"; }

case "$cmd" in
  health) curl -fsS "$URL/api/v1/health"; echo ;;
  telem|telemetry) curl -fsS "$URL/api/v1/telemetry" | python3 -m json.tool ;;
  mode)
    [[ $# -ge 1 ]] || { echo "usage: $0 mode sit|stand|recline|tracking|wave|meeting|stow|idle|estop"; exit 2; }
    json -X POST "$URL/api/v1/mode" -d "{\"mode\":\"$1\"}"
    echo
    ;;
  pose|control)
    # remaining args: k=v  e.g. pan=-12 tilt=8 display_markdown='hi'
    python3 - "$URL" "$@" <<'PY'
import json, sys, urllib.request
url, pairs = sys.argv[1], sys.argv[2:]
body = {}
for p in pairs:
    k, _, v = p.partition("=")
    if k in ("pan", "tilt", "height_mm", "reach_mm", "roll", "elbow"):
        body[k] = float(v)
    else:
        body[k] = v
req = urllib.request.Request(url.rstrip("/") + "/api/v1/control",
                             data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"},
                             method="POST")
print(urllib.request.urlopen(req).read().decode())
PY
    ;;
  md)
    file="${1:-/dev/stdin}"
    python3 - "$URL" "$file" <<'PY'
import json, pathlib, sys, urllib.request
url, path = sys.argv[1], sys.argv[2]
text = pathlib.Path(path).read_text() if path != "/dev/stdin" else sys.stdin.read()
body = json.dumps({"display_markdown": text}).encode()
req = urllib.request.Request(url.rstrip("/") + "/api/v1/control", data=body,
                             headers={"Content-Type": "application/json"}, method="POST")
print(urllib.request.urlopen(req).read().decode())
PY
    ;;
  skill)
    [[ $# -ge 1 ]] || { echo "usage: $0 skill skills/examples/wave-hello.json"; exit 2; }
    ROOT="$(cd "$(dirname "$0")/.." && pwd)"
    exec python3 "$ROOT/scripts/run_skill.py" --url "$URL" "$1"
    ;;
  help|-h|--help|*)
    cat <<EOF
cybopal.sh — program / test / control the live simulator

  $0 health
  $0 telemetry
  $0 mode sit|stand|recline|tracking|wave|meeting|stow|idle|estop
  $0 pose pan=12 tilt=-6 height_mm=220
  $0 md path/to/file.md
  $0 skill skills/examples/wave-hello.json

CYBOPAL_URL defaults to http://127.0.0.1:5000
EOF
    ;;
esac

#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$HERE/CorePython/LEIA_WATCHER_V3/src"
python -m pytest -q "$HERE/CorePython/LEIA_WATCHER_V3/tests" "$HERE/tests/BridgeTests"

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
    echo "Run ./scripts/venv_setup.sh before using Railway deployment commands." >&2
    exit 1
fi
exec "$ROOT/.venv/bin/python" "$ROOT/scripts/railway/deploy.py" down "$@"

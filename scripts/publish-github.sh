#!/usr/bin/env bash
# Offline preview by default. --public explicitly publishes a NEW repository.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
command -v python3 >/dev/null || { echo 'Python 3.9+ is required for publication.' >&2; exit 1; }
exec python3 "$root/scripts/publish_public.py" "$@"

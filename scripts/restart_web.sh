#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash "${ROOT_DIR}/scripts/stop_web.sh"
exec bash "${ROOT_DIR}/scripts/start_web.sh"

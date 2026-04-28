#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
FRONTEND_DIR="${ROOT_DIR}/frontend"
STATE_DIR="${START_WEB_STATE_DIR:-${ROOT_DIR}/.run}"
PID_FILE="${STATE_DIR}/web.pid"
BACKEND_URL="${START_WEB_BACKEND_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${START_WEB_FRONTEND_URL:-http://127.0.0.1:5173}"
SKIP_INSTALL="${START_WEB_SKIP_INSTALL:-0}"
BACKEND_PID=""
FRONTEND_PID=""
BACKEND_HOST=""
BACKEND_PORT=""
FRONTEND_HOST=""
FRONTEND_PORT=""

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "缺少命令: ${command_name}" >&2
    exit 1
  fi
}

url_field() {
  local url="$1"
  local field="$2"
  python3 - "$url" "$field" <<'PY'
import sys
from urllib.parse import urlparse

url = sys.argv[1]
field = sys.argv[2]
parsed = urlparse(url)

if field == "host":
    print(parsed.hostname or "")
elif field == "port":
    print(parsed.port or "")
else:
    raise SystemExit(f"unsupported field: {field}")
PY
}

cleanup() {
  trap - EXIT INT TERM
  rm -f "${PID_FILE}"

  if [[ -n "${BACKEND_PID}" ]]; then
    kill -TERM "-${BACKEND_PID}" >/dev/null 2>&1 || true
    wait "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi

  if [[ -n "${FRONTEND_PID}" ]]; then
    kill -TERM "-${FRONTEND_PID}" >/dev/null 2>&1 || true
    wait "${FRONTEND_PID}" >/dev/null 2>&1 || true
  fi
}

handle_interrupt() {
  cleanup
  exit 130
}

wait_for_url() {
  local url="$1"
  local name="$2"

  for _ in $(seq 1 60); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      echo "${name} 已就绪: ${url}"
      return 0
    fi
    sleep 1
  done

  echo "${name} 启动超时: ${url}" >&2
  return 1
}

ensure_port_available() {
  local host="$1"
  local port="$2"
  local name="$3"

  if python3 - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

with socket.socket() as sock:
    sock.settimeout(0.5)
    if sock.connect_ex((host, port)) == 0:
        raise SystemExit(1)
PY
  then
    return 0
  fi

  echo "${name} 端口已被占用: ${host}:${port}" >&2
  exit 1
}

monitor_processes() {
  while true; do
    if ! kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
      echo "后端进程已退出，正在清理..." >&2
      return 1
    fi
    if ! kill -0 "${FRONTEND_PID}" >/dev/null 2>&1; then
      echo "前端进程已退出，正在清理..." >&2
      return 1
    fi
    sleep 1
  done
}

write_pid_file() {
  mkdir -p "${STATE_DIR}"
  cat >"${PID_FILE}" <<EOF
BACKEND_PID='${BACKEND_PID}'
FRONTEND_PID='${FRONTEND_PID}'
BACKEND_URL='${BACKEND_URL}'
FRONTEND_URL='${FRONTEND_URL}'
EOF
}

start_backend() {
  local backend_command
  if [[ -n "${START_WEB_BACKEND_CMD:-}" ]]; then
    backend_command="${START_WEB_BACKEND_CMD}"
  else
    backend_command="$(cat <<EOF
exec python3 - <<'PY'
from astock.config import load_settings
from astock.webapi.app import create_app
import uvicorn

app = create_app(load_settings())
uvicorn.run(app, host="${BACKEND_HOST}", port=${BACKEND_PORT})
PY
EOF
)"
  fi

  python3 - "${backend_command}" <<'PY' &
import os
import sys

os.setsid()
os.execvp("bash", ["bash", "-lc", sys.argv[1]])
PY
  BACKEND_PID=$!
}

start_frontend() {
  local frontend_command
  if [[ -n "${START_WEB_FRONTEND_CMD:-}" ]]; then
    frontend_command="${START_WEB_FRONTEND_CMD}"
  else
    frontend_command="cd '${FRONTEND_DIR}' && export VITE_BACKEND_PROXY_TARGET='${BACKEND_URL}' && exec npm run dev -- --host '${FRONTEND_HOST}' --port '${FRONTEND_PORT}' --strictPort"
  fi

  python3 - "${frontend_command}" <<'PY' &
import os
import sys

os.setsid()
os.execvp("bash", ["bash", "-lc", sys.argv[1]])
PY
  FRONTEND_PID=$!
}

main() {
  require_command python3
  require_command npm
  require_command curl

  cd "${ROOT_DIR}"
  BACKEND_HOST="$(url_field "${BACKEND_URL}" host)"
  BACKEND_PORT="$(url_field "${BACKEND_URL}" port)"
  FRONTEND_HOST="$(url_field "${FRONTEND_URL}" host)"
  FRONTEND_PORT="$(url_field "${FRONTEND_URL}" port)"

  ensure_port_available "${BACKEND_HOST}" "${BACKEND_PORT}" "后端"
  ensure_port_available "${FRONTEND_HOST}" "${FRONTEND_PORT}" "前端"

  if [[ "${SKIP_INSTALL}" != "1" ]]; then
    if [[ ! -d "${VENV_DIR}" ]]; then
      echo "创建虚拟环境: ${VENV_DIR}"
      python3 -m venv "${VENV_DIR}"
    fi

    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"

    echo "安装 Python 依赖..."
    pip install -e ".[dev]"

    echo "安装前端依赖..."
    (
      cd "${FRONTEND_DIR}"
      npm install
    )
  elif [[ -d "${VENV_DIR}" ]]; then
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
  fi

  trap cleanup EXIT
  trap handle_interrupt INT TERM

  echo "启动后端服务..."
  start_backend

  echo "启动前端服务..."
  start_frontend

  wait_for_url "${BACKEND_URL}/docs" "后端 API"
  wait_for_url "${FRONTEND_URL}" "前端页面"
  write_pid_file

  cat <<EOF

Web 工作台已启动：
- 前端页面: ${FRONTEND_URL}
- 后端 API: ${BACKEND_URL}
- OpenAPI 文档: ${BACKEND_URL}/docs

按 Ctrl+C 可同时停止前后端服务。
EOF

  monitor_processes
}

main "$@"

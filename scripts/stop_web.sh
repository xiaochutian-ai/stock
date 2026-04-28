#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${START_WEB_STATE_DIR:-${ROOT_DIR}/.run}"
PID_FILE="${STATE_DIR}/web.pid"

kill_group_if_running() {
  local pid="$1"
  local name="$2"

  if [[ -z "${pid}" ]]; then
    return 0
  fi

  if kill -0 "${pid}" >/dev/null 2>&1; then
    echo "停止${name}进程组: ${pid}"
    kill -TERM "-${pid}" >/dev/null 2>&1 || true
    wait_for_exit "${pid}" "${name}"
  else
    echo "${name}进程不存在，跳过: ${pid}"
  fi
}

wait_for_exit() {
  local pid="$1"
  local name="$2"

  for _ in $(seq 1 20); do
    if ! kill -0 "${pid}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done

  echo "${name}进程未在预期时间内退出: ${pid}" >&2
  return 1
}

main() {
  if [[ ! -f "${PID_FILE}" ]]; then
    echo "未找到 PID 文件，无需停止: ${PID_FILE}"
    return 0
  fi

  # shellcheck disable=SC1090
  source "${PID_FILE}"

  kill_group_if_running "${BACKEND_PID:-}" "后端"
  kill_group_if_running "${FRONTEND_PID:-}" "前端"

  rm -f "${PID_FILE}"
  echo "Web 工作台已停止"
}

main "$@"

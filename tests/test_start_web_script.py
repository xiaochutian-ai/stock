from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


def _server_code(port: int, signal_file: Path) -> str:
    return f"""
import signal
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

signal_file = Path(r"{signal_file}")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        return

def on_int(signum, frame):
    signal_file.write_text("INT", encoding="utf-8")
    sys.exit(130)

def on_term(signum, frame):
    signal_file.write_text("TERM", encoding="utf-8")
    sys.exit(0)

signal.signal(signal.SIGINT, on_int)
signal.signal(signal.SIGTERM, on_term)

server = HTTPServer(("127.0.0.1", {port}), Handler)
server.serve_forever()
"""


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_start_web_script_exists_and_has_valid_bash_syntax():
    for script_name in ("start_web.sh", "stop_web.sh", "restart_web.sh"):
        script_path = Path("scripts") / script_name

        assert script_path.exists()
        assert os.access(script_path, os.X_OK)

        result = subprocess.run(
            ["bash", "-n", str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr


def test_start_web_script_manages_child_process_shutdown_via_parent_cleanup(tmp_path: Path):
    script_path = Path("scripts/start_web.sh")
    backend_signal = tmp_path / "backend.signal"
    frontend_signal = tmp_path / "frontend.signal"
    backend_port = _free_port()
    frontend_port = _free_port()

    env = os.environ.copy()
    env.update(
        {
            "START_WEB_SKIP_INSTALL": "1",
            "START_WEB_BACKEND_URL": f"http://127.0.0.1:{backend_port}",
            "START_WEB_FRONTEND_URL": f"http://127.0.0.1:{frontend_port}",
            "START_WEB_BACKEND_CMD": (
                f"{sys.executable} -c '{_server_code(backend_port, backend_signal)}'"
            ),
            "START_WEB_FRONTEND_CMD": (
                f"{sys.executable} -c '{_server_code(frontend_port, frontend_signal)}'"
            ),
        }
    )

    process = subprocess.Popen(
        ["bash", str(script_path)],
        cwd=Path.cwd(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=os.setsid,
    )
    try:
        deadline = time.time() + 20
        output = ""
        while time.time() < deadline:
            line = process.stdout.readline()
            if line:
                output += line
            if "Web 工作台已启动" in output:
                break
        else:
            raise AssertionError(f"script did not become ready, output:\n{output}")

        os.killpg(process.pid, signal.SIGINT)
        return_code = process.wait(timeout=10)

        assert return_code in (0, 130)
        assert backend_signal.read_text(encoding="utf-8") == "TERM"
        assert frontend_signal.read_text(encoding="utf-8") == "TERM"
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)


def test_stop_web_script_uses_pid_file_to_stop_services(tmp_path: Path):
    start_script_path = Path("scripts/start_web.sh")
    stop_script_path = Path("scripts/stop_web.sh")
    backend_signal = tmp_path / "backend.signal"
    frontend_signal = tmp_path / "frontend.signal"
    state_dir = tmp_path / "run"
    pid_file = state_dir / "web.pid"
    backend_port = _free_port()
    frontend_port = _free_port()

    env = os.environ.copy()
    env.update(
        {
            "START_WEB_SKIP_INSTALL": "1",
            "START_WEB_STATE_DIR": str(state_dir),
            "START_WEB_BACKEND_URL": f"http://127.0.0.1:{backend_port}",
            "START_WEB_FRONTEND_URL": f"http://127.0.0.1:{frontend_port}",
            "START_WEB_BACKEND_CMD": (
                f"{sys.executable} -c '{_server_code(backend_port, backend_signal)}'"
            ),
            "START_WEB_FRONTEND_CMD": (
                f"{sys.executable} -c '{_server_code(frontend_port, frontend_signal)}'"
            ),
        }
    )

    process = subprocess.Popen(
        ["bash", str(start_script_path)],
        cwd=Path.cwd(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=os.setsid,
    )
    try:
        deadline = time.time() + 20
        output = ""
        while time.time() < deadline:
            line = process.stdout.readline()
            if line:
                output += line
            if "Web 工作台已启动" in output and pid_file.exists():
                break
        else:
            raise AssertionError(f"script did not become ready, output:\n{output}")

        stop_result = subprocess.run(
            ["bash", str(stop_script_path)],
            cwd=Path.cwd(),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        assert stop_result.returncode == 0, stop_result.stderr
        assert not pid_file.exists()
        assert backend_signal.read_text(encoding="utf-8") == "TERM"
        assert frontend_signal.read_text(encoding="utf-8") == "TERM"
        assert process.wait(timeout=10) == 1
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)

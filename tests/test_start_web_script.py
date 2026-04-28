from __future__ import annotations

import os
import signal
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


def test_start_web_script_exists_and_has_valid_bash_syntax():
    script_path = Path("scripts/start_web.sh")

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
    backend_port = 18080
    frontend_port = 18081

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

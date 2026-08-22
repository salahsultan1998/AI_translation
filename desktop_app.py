"""Desktop launcher for LocaTool.

Runs the existing Streamlit app (app.py) as a background server on a
free local port, then opens it inside a native window via pywebview
instead of a browser tab. app.py itself is unchanged.

When run as a normal Python script, the server is started with
`python -m streamlit run app.py` in a subprocess, same as always.

When frozen into a standalone .exe (PyInstaller), there is no separate
Python interpreter to invoke `-m streamlit` on, so the frozen exe
re-launches *itself* with a hidden --run-server flag; that child
process runs the Streamlit server in-process instead.
"""
import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request

APP_TITLE = "LocaTool — AI Localization Workspace"
APP_FILE = "app.py"


def resolve_app_path() -> str:
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS  # PyInstaller's extracted bundle dir
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, APP_FILE)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def run_server_in_process(port: int) -> None:
    """Runs only inside the frozen-exe child process; blocks forever."""
    from streamlit.web import bootstrap

    flag_options = {
        "server_port": port,
        "server_address": "localhost",
        "server_headless": True,
        "browser_gatherUsageStats": False,
        "global_developmentMode": False,
    }
    bootstrap.load_config_options(flag_options=flag_options)
    bootstrap.run(resolve_app_path(), False, [], flag_options)


def start_server_process(port: int) -> subprocess.Popen:
    # agents.py loads prompts.json via a relative path, so the server
    # process must run with cwd set to the folder containing app.py.
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--run-server", "--port", str(port)]
        cwd = os.path.dirname(sys.executable)
    else:
        cmd = [
            sys.executable, "-m", "streamlit", "run", resolve_app_path(),
            "--server.port", str(port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ]
        cwd = os.path.dirname(os.path.abspath(__file__))
    return subprocess.Popen(cmd, cwd=cwd)


def main() -> None:
    import webview

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    server_process = start_server_process(port)

    try:
        if not wait_for_server(url):
            raise RuntimeError(
                "Streamlit server did not start within 30 seconds. "
                "Check the terminal output above for errors."
            )

        webview.create_window(
            APP_TITLE,
            url,
            width=1440,
            height=900,
            min_size=(1000, 700),
        )
        webview.start()
    finally:
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-server", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, help=argparse.SUPPRESS)
    known_args, _ = parser.parse_known_args()

    if known_args.run_server:
        run_server_in_process(known_args.port)
    else:
        main()

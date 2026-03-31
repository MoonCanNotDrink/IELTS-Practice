import asyncio
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from e2e_smoke import run_smoke


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class BackendSmokeTests(unittest.TestCase):
    def test_real_backend_smoke_core_flow(self):
        port = _pick_free_port()
        base_url = f"http://127.0.0.1:{port}"

        with tempfile.TemporaryDirectory(prefix="ielts-smoke-") as temp_dir:
            tmp_path = Path(temp_dir)
            db_path = tmp_path / "smoke.db"
            recordings_dir = tmp_path / "recordings"

            env = os.environ.copy()
            env.update(
                {
                    "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}",
                    "RECORDINGS_DIR": str(recordings_dir),
                    "INVITE_CODE": "IELTS2025",
                    "JWT_SECRET": "smoke-test-secret",
                    "DEBUG": "0",
                    "GEMINI_TIMEOUT_SECONDS": "1",
                    "PYTHONUNBUFFERED": "1",
                }
            )

            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=str(Path(__file__).resolve().parent),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                asyncio.run(
                    run_smoke(
                        base_url=base_url,
                        invite_code="IELTS2025",
                        skip_tts=True,
                    )
                )
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

            self.assertTrue(db_path.exists())


if __name__ == "__main__":
    unittest.main()

"""
进程管理器：启停抢票脚本，stdout/stderr 管道捕获。
"""
import asyncio
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ProcessManager:
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._mode: str = ""
        self._start_time: Optional[float] = None
        self._log_queue: asyncio.Queue = asyncio.Queue()
        self._stop_event = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def pid(self) -> Optional[int]:
        return self._process.pid if self._process else None

    @property
    def start_time(self) -> Optional[float]:
        return self._start_time

    def get_status(self) -> dict:
        return {
            "running": self.running,
            "mode": self._mode,
            "pid": self.pid,
            "startTime": self._start_time,
            "elapsed": time.time() - self._start_time if self._start_time and self.running else 0,
        }

    def start(self, mode: str) -> bool:
        if self.running:
            return False

        self._mode = mode
        self._stop_event.clear()
        self._loop = asyncio.get_event_loop()

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["PYTHONUNBUFFERED"] = "1"

        if mode == "web":
            script_dir = PROJECT_ROOT / "damai"
            script_name = "damai.py"
            env["CHROMEDRIVER_PATH"] = str(script_dir / "chromedriver.exe")
        elif mode == "mobile":
            script_dir = PROJECT_ROOT / "damai_appium"
            script_name = "damai_app_v2.py"
        else:
            return False

        try:
            self._process = subprocess.Popen(
                [sys.executable, "-u", script_name],
                cwd=str(script_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
            )
            self._start_time = time.time()

            threading.Thread(target=self._read_output, daemon=True).start()
            threading.Thread(target=self._watch_exit, daemon=True).start()

            return True
        except Exception as e:
            self._push_log("error", f"启动失败: {e}")
            return False

    def stop(self) -> bool:
        if not self.running or not self._process:
            return False

        self._stop_event.set()
        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        except Exception:
            pass

        self._process = None
        return True

    def _push_log(self, msg_type: str, text: str, code: int = None):
        if self._loop and self._loop.is_running():
            payload = {"type": msg_type, "text": text, "time": time.time()}
            if code is not None:
                payload["code"] = code
            asyncio.run_coroutine_threadsafe(
                self._log_queue.put(payload),
                self._loop,
            )

    def _read_output(self):
        if not self._process or not self._process.stdout:
            return
        try:
            for line in iter(self._process.stdout.readline, ""):
                if self._stop_event.is_set():
                    break
                line = line.strip()
                if line:
                    self._push_log("log", line)
        except (ValueError, OSError):
            pass
        except Exception:
            pass

    def _watch_exit(self):
        if not self._process:
            return
        self._process.wait()
        exit_code = self._process.returncode
        self._process = None
        self._push_log("exit", f"脚本已退出 (code={exit_code})", code=exit_code)

    async def get_logs(self):
        while True:
            msg = await self._log_queue.get()
            yield msg


process_manager = ProcessManager()

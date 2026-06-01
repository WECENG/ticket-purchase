"""
FastAPI 服务器：REST API + WebSocket + 静态文件 serve。
用法: python -m console.server [--dev]
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

from console.process_manager import process_manager
from console.config_manager import get_config, save_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
WEB_DIR = Path(__file__).resolve().parent / "web"

_parser = argparse.ArgumentParser(description="大麦抢票控制台")
_parser.add_argument("--dev", action="store_true", help="开发模式（启动 Vite HMR）")
_args, _ = _parser.parse_known_args()
DEV_MODE: bool = _args.dev

app = FastAPI(title="大麦抢票控制台", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== API Routes ==========

@app.get("/api/info")
async def api_info():
    return {
        "name": "大麦抢票控制台",
        "version": "1.0.0",
        "mode": "development" if DEV_MODE else "production",
        "port": 8765,
    }


@app.get("/api")
async def api_root():
    return {"name": "大麦抢票控制台 API", "version": "1.0.0"}


@app.get("/api/status")
async def api_status():
    return process_manager.get_status()


@app.get("/api/config")
async def api_get_config(mode: str = "web"):
    config = get_config(mode)
    return {"mode": mode, "config": config}


@app.post("/api/config")
async def api_save_config(data: dict):
    mode = data.get("mode", "web")
    config_data = data.get("config", {})
    return save_config(mode, config_data)


@app.post("/api/start")
async def api_start(data: dict):
    if process_manager.running:
        return {"success": False, "error": "已有任务在运行"}
    mode = data.get("mode", "web")
    config_data = data.get("config")
    if config_data:
        save_result = save_config(mode, config_data)
        if not save_result["success"]:
            return {"success": False, "error": f"配置保存失败: {save_result['errors']}"}
    ok = process_manager.start(mode)
    if ok:
        return {"success": True, "pid": process_manager.pid, "mode": mode}
    return {"success": False, "error": f"启动失败: {mode}"}


@app.post("/api/stop")
async def api_stop():
    if not process_manager.running:
        return {"success": False, "error": "没有运行中的任务"}
    return {"success": process_manager.stop()}


@app.post("/api/check")
async def api_check():
    script_path = PROJECT_ROOT / "damai" / "check_environment.py"
    if not script_path.exists():
        return {"success": False, "error": "check_environment.py 不存在"}
    try:
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(script_path.parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env=env,
        )
        lines = result.stdout.strip().split("\n")
        return {"success": result.returncode == 0, "exitCode": result.returncode, "output": lines}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "环境检查超时"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "status", "data": process_manager.get_status()})
    try:
        async for msg in process_manager.get_logs():
            try:
                await websocket.send_json(msg)
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ========== Frontend Serve (MUST be last) ==========

_has_static = STATIC_DIR.exists() and any(STATIC_DIR.iterdir())

if DEV_MODE:
    # Development: proxy to Vite dev server
    from httpx import AsyncClient
    _vite_client = AsyncClient(base_url="http://127.0.0.1:5173", timeout=30)
    _vite_proc: subprocess.Popen | None = None

    def _start_vite():
        global _vite_proc
        if WEB_DIR.exists() and (WEB_DIR / "node_modules").exists():
            _vite_proc = subprocess.Popen(
                ["npx", "vite", "--host", "--port", "5173"],
                cwd=str(WEB_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def _stop_vite():
        global _vite_proc
        if _vite_proc:
            _vite_proc.terminate()
            _vite_proc = None

    app.add_event_handler("startup", _start_vite)
    app.add_event_handler("shutdown", _stop_vite)

    @app.get("/{full_path:path}")
    async def vite_proxy(full_path: str):
        try:
            resp = await _vite_client.get(f"/{full_path}" if full_path else "/")
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
        except Exception:
            return Response("Vite dev server not ready. Run: cd console/web && npm run dev", status_code=503)

else:
    # Production: serve built static files as catch-all
    if _has_static:

        @app.get("/{full_path:path}")
        async def serve_frontend(request: Request, full_path: str):
            """Serve static files, fallback to index.html for SPA routing."""
            file_path = STATIC_DIR / (full_path or "index.html")
            if file_path.is_file():
                return FileResponse(file_path)
            # SPA fallback
            index_path = STATIC_DIR / "index.html"
            if index_path.is_file():
                return FileResponse(index_path)
            return Response("Frontend not built. Run: cd console/web && npm run build", status_code=404)

        @app.get("/")
        async def serve_root():
            return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    print()
    print("  \033[36m🎫  大麦抢票控制台\033[0m")
    print(f"  \033[90mmode:\033[0m {'\033[33mdevelopment (HMR)\033[0m' if DEV_MODE else '\033[32mproduction\033[0m'}")
    print(f"  \033[90mapi:\033[0m  http://127.0.0.1:8765/api")
    if DEV_MODE:
        print(f"  \033[90mweb:\033[0m  http://127.0.0.1:5173 (Vite HMR)")
    else:
        print(f"  \033[90mweb:\033[0m  http://127.0.0.1:8765")
    print(f"  \033[90mws:\033[0m   ws://127.0.0.1:8765/ws/logs")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="warning")

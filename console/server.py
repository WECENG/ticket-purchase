"""
FastAPI 服务器：REST API + WebSocket + 静态文件 serve。
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

from console.process_manager import process_manager
from console.config_manager import get_config, save_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="大麦抢票控制台", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    result = save_config(mode, config_data)
    return result


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
    else:
        return {"success": False, "error": f"启动失败，请检查模式: {mode}"}


@app.post("/api/stop")
async def api_stop():
    if not process_manager.running:
        return {"success": False, "error": "没有运行中的任务"}
    ok = process_manager.stop()
    return {"success": ok}


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
        return {
            "success": result.returncode == 0,
            "exitCode": result.returncode,
            "output": lines,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "环境检查超时（30秒）"}
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


if STATIC_DIR.exists() and any(STATIC_DIR.iterdir()):
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


@app.get("/api")
async def api_root():
    return {"name": "大麦抢票控制台 API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  大麦抢票控制台")
    print("  API: http://127.0.0.1:8765/api")
    print("  WS:  ws://127.0.0.1:8765/ws/logs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")

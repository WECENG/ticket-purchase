"""
配置管理器：表单数据 ↔ config.json / config.jsonc 读写。
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent

WEB_CONFIG_PATH = PROJECT_ROOT / "damai" / "config.json"
MOBILE_CONFIG_PATH = PROJECT_ROOT / "damai_appium" / "config.jsonc"

# 默认值
WEB_DEFAULTS = {
    "index_url": "https://www.damai.cn/",
    "login_url": "https://passport.damai.cn/login?ru=https%3A%2F%2Fwww.damai.cn%2F",
    "target_url": "",
    "users": [],
    "city": "",
    "dates": [],
    "prices": [],
    "if_listen": True,
    "if_commit_order": False,
    "max_retries": 10000,
    "fast_mode": True,
    "page_load_delay": 2,
}

MOBILE_DEFAULTS = {
    "server_url": "http://127.0.0.1:4723",
    "keyword": "",
    "users": [],
    "city": "",
    "date": "",
    "price": "",
    "price_index": 1,
    "if_commit_order": False,
    "platform_version": "12",
    "device_name": "",
}


def _read_json(path: Path) -> dict:
    """读取 JSON 文件，文件不存在时返回空 dict"""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, data: dict):
    """写入 JSON 文件（不含 BOM）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_config(mode: str) -> dict:
    """读取当前配置（mode: 'web' 或 'mobile'）"""
    if mode == "web":
        path = WEB_CONFIG_PATH
        defaults = WEB_DEFAULTS
    else:
        path = MOBILE_CONFIG_PATH
        defaults = MOBILE_DEFAULTS

    saved = _read_json(path)
    # 合并非 _comment 开头的键，默认值优先
    result = {**defaults, **{k: v for k, v in saved.items() if not k.startswith("_")}}
    return result


def save_config(mode: str, data: dict) -> dict:
    """保存配置并返回验证结果"""
    if mode == "web":
        path = WEB_CONFIG_PATH
        required = ["target_url", "users"]
    else:
        path = MOBILE_CONFIG_PATH
        required = ["keyword", "users", "city", "date", "price"]

    errors: List[str] = []

    # 基本校验
    for field in required:
        val = data.get(field)
        if not val or (isinstance(val, list) and len(val) == 0):
            errors.append(f"缺少必填字段: {field}")

    if errors:
        return {"success": False, "errors": errors}

    # 写入文件
    try:
        # 只保存非 _comment 字段
        clean = {k: v for k, v in data.items() if not k.startswith("_")}
        _write_json(path, clean)
        return {"success": True, "errors": [], "path": str(path)}
    except Exception as e:
        return {"success": False, "errors": [str(e)]}


_console_config_dir = Path(__file__).resolve().parent.parent

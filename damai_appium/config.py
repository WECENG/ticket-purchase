# -*- coding: UTF-8 -*-
"""
__Author__ = "WECENG / Codex"
__Version__ = "1.3.0"
__Description__ = "閰嶇疆绫?- 鏀寔 mode(reserved/full) + auto_buy_time + device info"
"""
import json, re, os


class Config:
    def __init__(self, server_url, keyword, users, city, date, price, price_index,
                 if_commit_order, mode="reserved", auto_buy_time=None,
                 device_name=None, platform_version=None):
        self.server_url = server_url
        self.keyword = keyword
        self.users = users
        self.city = city
        self.date = date
        self.price = price
        self.price_index = price_index
        self.if_commit_order = if_commit_order
        self.mode = mode
        self.auto_buy_time = auto_buy_time
        self.device_name = device_name
        self.platform_version = platform_version

    @staticmethod
    def load_config():
        cfg_path = os.path.join(os.path.dirname(__file__), "config.jsonc")
        with open(cfg_path, "r", encoding="utf-8-sig") as f:
            raw = f.read()
        lines = [l for l in raw.split("\n") if not l.strip().startswith("//") and "_comment" not in l]
        raw = "\n".join(lines)
        raw = re.sub(r",\s*}", "}", raw)
        raw = re.sub(r",\s*]", "]", raw)
        cfg = json.loads(raw)
        return Config(
            cfg["server_url"],
            cfg["keyword"],
            cfg.get("users", []),
            cfg.get("city", ""),
            cfg.get("date", ""),
            cfg.get("price", ""),
            cfg.get("price_index", 1),
            cfg.get("if_commit_order", False),
            cfg.get("mode", "reserved"),
            cfg.get("auto_buy_time", None),
            cfg.get("device_name", None),
            cfg.get("platform_version", None),
        )

# -*- coding: UTF-8 -*-
"""Android 抢票配置。"""

import json
from pathlib import Path


class Config:
    """Validated runtime configuration for the Appium workflow."""

    def __init__(
        self,
        server_url,
        keyword,
        users,
        city,
        date,
        price,
        price_index=None,
        if_commit_order=False,
        start_at=None,
        target_title=None,
        result_index=0,
        udid=None,
        device_name="Android",
        platform_version=None,
        app_package="cn.damai",
        app_activity=".launcher.splash.SplashMainActivity",
        max_retries=30,
        retry_interval=0.25,
        element_timeout=5,
        order_timeout=30,
        keep_session=True,
    ):
        self.server_url = server_url
        self.keyword = keyword
        self.users = users
        self.city = city
        self.date = date
        self.price = price
        self.price_index = price_index
        self.if_commit_order = if_commit_order
        self.start_at = start_at
        self.target_title = target_title or keyword
        self.result_index = result_index
        self.udid = udid
        self.device_name = device_name
        self.platform_version = platform_version
        self.app_package = app_package
        self.app_activity = app_activity
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.element_timeout = element_timeout
        self.order_timeout = order_timeout
        self.keep_session = keep_session
        self._validate()

    def _validate(self):
        required_strings = {
            "server_url": self.server_url,
            "keyword": self.keyword,
            "city": self.city,
            "date": self.date,
            "price": self.price,
        }
        missing = [name for name, value in required_strings.items() if not value]
        if missing:
            raise ValueError(f"配置项不能为空: {', '.join(missing)}")
        if not isinstance(self.users, list) or not self.users:
            raise ValueError("users 必须是至少包含一名观演人的数组")
        if any(not isinstance(user, str) or not user.strip() for user in self.users):
            raise ValueError("users 中的观演人姓名不能为空")
        if self.price_index is not None and (
            not isinstance(self.price_index, int) or self.price_index < 0
        ):
            raise ValueError("price_index 必须是非负整数或 null")
        if not isinstance(self.if_commit_order, bool):
            raise ValueError("if_commit_order 必须是布尔值")
        if not isinstance(self.result_index, int) or self.result_index < 0:
            raise ValueError("result_index 必须是非负整数")
        if not isinstance(self.max_retries, int) or self.max_retries < 1:
            raise ValueError("max_retries 必须是正整数")
        if self.retry_interval <= 0 or self.element_timeout <= 0 or self.order_timeout <= 0:
            raise ValueError("等待和超时配置必须大于 0")

    @staticmethod
    def load_config(path=None):
        config_path = Path(path) if path else Path(__file__).with_name("config.jsonc")
        with config_path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)

        return Config(
            server_url=config["server_url"],
            keyword=config["keyword"],
            users=config["users"],
            city=config["city"],
            date=config["date"],
            price=config["price"],
            price_index=config.get("price_index"),
            if_commit_order=config.get("if_commit_order", False),
            start_at=config.get("start_at"),
            target_title=config.get("target_title"),
            result_index=config.get("result_index", 0),
            udid=config.get("udid"),
            device_name=config.get("device_name", "Android"),
            platform_version=config.get("platform_version"),
            app_package=config.get("app_package", "cn.damai"),
            app_activity=config.get(
                "app_activity", ".launcher.splash.SplashMainActivity"
            ),
            max_retries=config.get("max_retries", 30),
            retry_interval=config.get("retry_interval", 0.25),
            element_timeout=config.get("element_timeout", 5),
            order_timeout=config.get("order_timeout", 30),
            keep_session=config.get("keep_session", True),
        )

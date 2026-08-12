# -*- coding: UTF-8 -*-
"""大麦 Android 自动购票流程。

流程分成两个阶段：先进入并校验目标演出详情页，再在 ``start_at`` 到达后
进入购票弹层。只有检测到订单确认页并完成观演人选择后，才允许提交订单；
``if_commit_order`` 为 false 时会停在提交按钮前。
"""

import re
import time
from datetime import datetime
from enum import Enum

from appium import webdriver
from appium.options.common.base import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

try:
    from .config import Config
except ImportError:  # 兼容在 damai_appium 目录中直接运行
    from config import Config


class RunStatus(str, Enum):
    PREPARED = "prepared"
    READY_TO_SUBMIT = "ready_to_submit"
    PAYMENT_READY = "payment_ready"
    FAILED = "failed"


def wait_until_start(start_at, now_func=None, sleep_func=time.sleep):
    """等待到本地时间；未配置或时间已到时立即返回。"""
    if not start_at:
        return

    try:
        target = datetime.fromisoformat(start_at)
    except ValueError as exc:
        raise ValueError("start_at 必须使用 YYYY-MM-DD HH:MM:SS 格式") from exc

    def current_time():
        if now_func:
            return now_func()
        return datetime.now(target.tzinfo) if target.tzinfo else datetime.now()

    last_reported = None
    while True:
        remaining = (target - current_time()).total_seconds()
        if remaining <= 0:
            break
        seconds = int(remaining)
        if seconds != last_reported and (remaining <= 10 or seconds % 30 == 0):
            print(f"等待开售时间，还剩 {seconds} 秒...")
            last_reported = seconds
        if remaining > 60:
            sleep_func(min(30, remaining - 60))
        elif remaining > 5:
            sleep_func(min(1, remaining - 5))
        else:
            sleep_func(min(0.05, remaining))

    print(f"到达设定时间 {target:%Y-%m-%d %H:%M:%S}，开始抢票")


def normalize_text(value):
    """用于日期、价格和标题的宽松匹配。"""
    value = str(value or "").lower()
    translations = str.maketrans({
        "年": ".",
        "月": ".",
        "日": "",
        "-": ".",
        "/": ".",
        "：": ":",
        "￥": "¥",
        "元": "",
        "场": "",
        "站": "",
    })
    return re.sub(r"[\s·•「」『』《》【】()（）]", "", value.translate(translations))


class DamaiBot:
    PURCHASE_CONTAINER_IDS = (
        "trade_project_detail_purchase_status_bar_container_fl",
        "cn.damai:id/trade_project_detail_purchase_status_bar_container_fl",
    )
    SEARCH_BUTTON_IDS = (
        "pioneer_homepage_header_search_btn",
        "homepage_header_search_layout",
        "homepage_header_search_btn",
    )
    SUBMIT_TEXTS = ("提交订单", "立即提交")

    def __init__(self, config=None, setup_driver=True):
        self.config = config or Config.load_config()
        self.driver = None
        self.wait = None
        self.last_status = RunStatus.FAILED
        self.last_error = ""
        if setup_driver:
            self._setup_driver()

    def _setup_driver(self):
        """创建与当前连接设备兼容的 Appium 会话。"""
        capabilities = {
            "platformName": "Android",
            "appium:automationName": "UiAutomator2",
            "appium:deviceName": self.config.device_name,
            "appium:appPackage": self.config.app_package,
            "appium:appActivity": self.config.app_activity,
            "appium:noReset": True,
            "appium:shouldTerminateApp": False,
            "appium:newCommandTimeout": 6000,
            "appium:unicodeKeyboard": True,
            "appium:resetKeyboard": False,
            "appium:disableWindowAnimation": True,
            "appium:ignoreHiddenApiPolicyError": True,
            "appium:adbExecTimeout": 30000,
        }
        if self.config.udid:
            capabilities["appium:udid"] = self.config.udid
        if self.config.platform_version:
            capabilities["appium:platformVersion"] = self.config.platform_version

        options = AppiumOptions()
        options.load_capabilities(capabilities)
        self.driver = webdriver.Remote(self.config.server_url, options=options)
        try:
            self.driver.update_settings({
                "waitForIdleTimeout": 100,
                "waitForSelectorTimeout": 500,
                "ignoreUnimportantViews": False,
                "allowInvisibleElements": False,
                "enableNotificationListener": False,
            })
        except WebDriverException as exc:
            print(f"提示：Appium 性能设置未全部应用: {exc}")
        self.wait = WebDriverWait(self.driver, self.config.element_timeout)
        print(
            "Appium 会话已连接: "
            f"{self.driver.current_package} / {self.driver.current_activity}"
        )

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def _set_error(self, message):
        self.last_error = message
        self.last_status = RunStatus.FAILED
        print(f"失败：{message}")
        return False

    def _find_all(self, by, value, context=None):
        try:
            return (context or self.driver).find_elements(by, value)
        except (StaleElementReferenceException, WebDriverException):
            return []

    def _find_first(self, selectors, timeout=None):
        deadline = time.monotonic() + (
            self.config.element_timeout if timeout is None else timeout
        )
        while time.monotonic() <= deadline:
            for by, value in selectors:
                elements = self._find_all(by, value)
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            return element
                    except WebDriverException:
                        continue
            time.sleep(0.05)
        return None

    def _tap(self, element):
        if not element:
            return False
        try:
            rect = element.rect
            self.driver.execute_script(
                "mobile: clickGesture",
                {
                    "x": rect["x"] + rect["width"] // 2,
                    "y": rect["y"] + rect["height"] // 2,
                    "duration": 40,
                },
            )
            return True
        except WebDriverException:
            try:
                element.click()
                return True
            except WebDriverException:
                return False

    def _tap_first(self, selectors, timeout=None):
        return self._tap(self._find_first(selectors, timeout=timeout))

    def _page_source(self):
        try:
            return self.driver.page_source
        except WebDriverException:
            return ""

    def _page_has_any(self, texts):
        source = self._page_source()
        return any(text in source for text in texts)

    def _dismiss_known_dialogs(self):
        """关闭不影响购票的权限提示，并确认演出购票须知。"""
        for _ in range(4):
            if self._tap_first(
                [
                    (By.ID, "damai_theme_dialog_cancel_btn"),
                    (By.XPATH, '//*[@text="下次再说"]'),
                    (By.XPATH, '//*[@text="暂不开启"]'),
                ],
                timeout=0.2,
            ):
                time.sleep(0.2)
                continue

            title = self._find_first(
                [(By.ID, "damai_theme_dialog_title")], timeout=0.1
            )
            title_text = title.text if title else ""
            if title_text in ("温馨提示", "购票须知"):
                if self._tap_first(
                    [
                        (By.ID, "damai_theme_dialog_confirm_btn"),
                        (By.XPATH, '//*[@text="确认并知悉"]'),
                    ],
                    timeout=0.2,
                ):
                    time.sleep(0.3)
                    continue
            break

    def _is_detail_page(self):
        activity = (getattr(self.driver, "current_activity", "") or "").lower()
        if "projectdetail" in activity:
            return True
        return any(
            self._find_all(By.ID, resource_id)
            for resource_id in self.PURCHASE_CONTAINER_IDS
        )

    def _detail_matches_target(self):
        if not self._is_detail_page():
            return False
        source = normalize_text(self._page_source())
        title_ok = normalize_text(self.config.keyword) in source or normalize_text(
            self.config.target_title
        ) in source
        city_ok = not self.config.city or normalize_text(self.config.city) in source
        return title_ok and city_ok

    def _open_search_page(self):
        if self._find_all(By.ID, "header_search_v2_input"):
            return True

        for _ in range(5):
            self._dismiss_known_dialogs()
            if self._find_all(By.ID, "header_search_v2_input"):
                return True
            if self._tap_first(
                [(By.ID, resource_id) for resource_id in self.SEARCH_BUTTON_IDS],
                timeout=0.5,
            ):
                time.sleep(1)
                self._dismiss_known_dialogs()
                if self._find_all(By.ID, "header_search_v2_input"):
                    return True
            try:
                self.driver.back()
            except WebDriverException:
                pass
            time.sleep(0.5)
        return False

    def _submit_search(self):
        search_input = self._find_first(
            [(By.ID, "header_search_v2_input")], timeout=2
        )
        if not search_input:
            return False
        search_input.click()
        search_input.clear()
        search_input.send_keys(self.config.keyword)
        try:
            self.driver.execute_script(
                "mobile: performEditorAction", {"action": "search"}
            )
        except WebDriverException:
            self.driver.press_keycode(66)

        deadline = time.monotonic() + self.config.element_timeout
        while time.monotonic() < deadline:
            if (
                self._find_all(By.ID, "tv_project_name")
                or self._find_all(By.ID, "tv_project_tourName")
                or self._find_all(By.ID, "tv_city")
            ):
                return True
            time.sleep(0.2)
        return False

    def _match_standard_result(self):
        candidates = []
        target_title = normalize_text(self.config.target_title)
        keyword = normalize_text(self.config.keyword)
        city = normalize_text(self.config.city)
        date = normalize_text(self.config.date)

        for title in self._find_all(By.ID, "tv_project_name"):
            try:
                item = title.find_element(
                    By.XPATH,
                    './ancestor::*[@resource-id="cn.damai:id/ll_search_item"][1]',
                )
            except WebDriverException:
                item = title
            haystack = normalize_text(getattr(item, "text", "") or title.text)
            score = 0
            if target_title and target_title in haystack:
                score += 4
            elif keyword and keyword in haystack:
                score += 3
            else:
                continue
            if city and city in haystack:
                score += 2
            if date and date in haystack:
                score += 2
            candidates.append((score, item, title.text))

        if not candidates:
            return False
        candidates.sort(key=lambda row: row[0], reverse=True)
        index = min(self.config.result_index, len(candidates) - 1)
        _, element, title_text = candidates[index]
        print(f"选择搜索结果: {title_text}")
        return self._tap(element)

    def _match_tour_city(self):
        tours = self._find_all(By.ID, "tv_project_tourName")
        if tours:
            tour_text = " ".join(tour.text for tour in tours)
            if (
                normalize_text(self.config.keyword) not in normalize_text(tour_text)
                and normalize_text(self.config.target_title)
                not in normalize_text(tour_text)
            ):
                return False

        cities = self._find_all(By.ID, "tv_city")
        dates = self._find_all(By.ID, "tv_time")
        for index, city_element in enumerate(cities):
            if normalize_text(self.config.city) != normalize_text(city_element.text):
                continue
            if index < len(dates):
                visible_date = normalize_text(dates[index].text)
                if normalize_text(self.config.date) not in visible_date:
                    continue
            print(
                f"选择巡演城市: {city_element.text} "
                f"{dates[index].text if index < len(dates) else ''}"
            )
            return self._tap(city_element)
        return False

    def _wait_for_detail_page(self):
        deadline = time.monotonic() + self.config.element_timeout * 2
        while time.monotonic() < deadline:
            self._dismiss_known_dialogs()
            if self._is_detail_page():
                return True
            time.sleep(0.2)
        return False

    def _select_detail_city(self):
        if not self.config.city:
            return True
        city_elements = self._find_all(By.ID, "tour_city_name")
        if not city_elements:
            return True
        for element in city_elements:
            if normalize_text(self.config.city) == normalize_text(element.text):
                return self._tap(element)
        return False

    def prepare_target(self):
        """进入并校验目标详情页；本阶段不会点击购票按钮。"""
        print("准备目标演出页面...")
        self._dismiss_known_dialogs()
        if self._detail_matches_target():
            if not self._select_detail_city():
                return self._set_error(f"详情页未找到城市 {self.config.city}")
            self.last_status = RunStatus.PREPARED
            print("目标详情页已就绪")
            return True

        if not self._open_search_page():
            return self._set_error("无法进入大麦搜索页")
        if not self._submit_search():
            return self._set_error(f"搜索 {self.config.keyword} 后未出现演出结果")
        if not (self._match_tour_city() or self._match_standard_result()):
            return self._set_error(
                f"未找到同时匹配 {self.config.keyword} / {self.config.city} / "
                f"{self.config.date} 的演出"
            )
        if not self._wait_for_detail_page():
            return self._set_error("点击搜索结果后没有进入演出详情页")
        if not self._select_detail_city():
            return self._set_error(f"详情页未找到城市 {self.config.city}")

        source = normalize_text(self._page_source())
        if normalize_text(self.config.city) not in source:
            return self._set_error("详情页城市校验失败")
        if normalize_text(self.config.date) not in source:
            return self._set_error("详情页日期校验失败")

        self.last_status = RunStatus.PREPARED
        print(
            f"目标详情页已就绪: {self.config.target_title} / "
            f"{self.config.city} / {self.config.date}"
        )
        return True

    def _selected_city_status(self):
        cities = self._find_all(By.ID, "tour_city_name")
        statuses = self._find_all(By.ID, "tour_city_name_state_desc")
        for index, city in enumerate(cities):
            if normalize_text(self.config.city) == normalize_text(city.text):
                return statuses[index].text if index < len(statuses) else ""
        return ""

    def _refresh_detail(self):
        try:
            size = self.driver.get_window_size()
            x = size["width"] // 2
            self.driver.swipe(x, int(size["height"] * 0.3), x, int(size["height"] * 0.75), 250)
        except WebDriverException:
            pass

    def _purchase_panel_open(self):
        return bool(
            self._find_all(By.ID, "project_detail_perform_price_flowlayout")
            or self._find_all(By.ID, "btn_buy_view")
            or self._find_all(By.ID, "btn_buy")
            or self._find_all(By.ID, "preform_scrollview")
            or "ncovsku" in (
                getattr(self.driver, "current_activity", "") or ""
            ).lower()
        )

    def _is_reservation_panel(self):
        """识别开售前的预约页，防止把预约成功误判为已进入购票页。"""
        return self._page_has_any(("预约想看场次", "提交抢票预约"))

    def _open_purchase_panel(self):
        blocked_statuses = ("缺货", "登记", "预约", "未开售", "即将开售")
        for attempt in range(1, self.config.max_retries + 1):
            self._dismiss_known_dialogs()
            status = self._selected_city_status()
            if status and any(word in status for word in blocked_statuses):
                if attempt == 1 or attempt % 10 == 0:
                    print(f"当前状态: {status}，第 {attempt} 次刷新等待")
                self._refresh_detail()
                time.sleep(self.config.retry_interval)
                continue

            container = self._find_first(
                [(By.ID, resource_id) for resource_id in self.PURCHASE_CONTAINER_IDS],
                timeout=0.3,
            )
            if container and self._tap(container):
                deadline = time.monotonic() + self.config.element_timeout
                while time.monotonic() < deadline:
                    if self._purchase_panel_open():
                        if self._is_reservation_panel():
                            if attempt == 1 or attempt % 10 == 0:
                                print("大麦仍返回开售前预约页，返回详情页继续等待")
                            try:
                                self.driver.back()
                            except WebDriverException:
                                pass
                            time.sleep(self.config.retry_interval)
                            break
                        return True
                    if self._is_order_confirmation_page():
                        return True
                    time.sleep(0.1)
            self._refresh_detail()
            time.sleep(self.config.retry_interval)
        return self._set_error("重试结束后仍未进入购票弹层")

    def _click_matching_text(self, target, context=None, skip_words=()):
        target_normalized = normalize_text(target)
        if not target_normalized:
            return False
        elements = self._find_all(By.XPATH, ".//*" if context else "//*", context)
        matches = []
        for element in elements:
            try:
                text = element.text.strip()
                if not text or any(word in text for word in skip_words):
                    continue
                normalized = normalize_text(text)
                if target_normalized in normalized or normalized in target_normalized:
                    matches.append((len(normalized), element, text))
            except WebDriverException:
                continue
        for _, element, text in sorted(matches, key=lambda row: row[0]):
            if self._tap(element):
                print(f"已选择: {text}")
                return True
        return False

    def _select_date(self):
        # 新版麒麟页会同时保留旧容器 ID，但日期文字不再暴露给
        # UiAutomator。票档区出现即表示从目标详情页进入后场次已选中。
        if self._find_all(By.ID, "preform_scrollview") and self._find_all(
            By.ID, "tv_price_name"
        ):
            print(f"新版购票页已选中目标场次: {self.config.date}")
            return True

        date_containers = self._find_all(By.ID, "project_detail_perform_flowlayout")
        if not date_containers:
            if not self._find_all(By.ID, "preform_scrollview"):
                return True  # 单一场次时通常不显示场次选择器

            scroll_views = self._find_all(By.ID, "preform_scrollview")
            headers = self._find_all(By.ID, "tv_perform_name")
            if not scroll_views or not headers:
                return self._set_error("新版购票页未找到场次区域")
            try:
                header_bottom = headers[0].rect["y"] + headers[0].rect["height"]
            except WebDriverException:
                header_bottom = 0

            candidates = []
            for class_name in ("android.view.ViewGroup", "android.widget.FrameLayout"):
                selector = (
                    f'new UiSelector().className("{class_name}").clickable(true)'
                )
                for element in self._find_all(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    selector,
                    context=scroll_views[0],
                ):
                    try:
                        rect = element.rect
                        if element.is_displayed() and rect["y"] >= header_bottom:
                            candidates.append((rect["y"], rect["x"], element))
                    except WebDriverException:
                        continue
            if not candidates:
                return self._set_error("新版购票页未找到可点击场次")
            candidates.sort(key=lambda row: (row[0], row[1]))
            if not self._tap(candidates[0][2]):
                return self._set_error("新版购票页选择场次失败")

            deadline = time.monotonic() + self.config.element_timeout
            while time.monotonic() < deadline:
                if self._find_all(By.ID, "tv_price_name"):
                    print(f"已选择唯一演出场次: {self.config.date}")
                    return True
                time.sleep(0.05)
            return self._set_error("选择场次后票档区域未出现")
        for container in date_containers:
            if self._click_matching_text(
                self.config.date,
                context=container,
                skip_words=("无票", "售罄", "缺货"),
            ):
                return True
        return self._set_error(f"购票弹层未找到可售场次 {self.config.date}")

    def _select_price(self):
        # 大麦的抢票预约会在新版页面自动选中票档。必须先检查底部
        # 实际价格；该页面也保留旧票档容器，但容器内文字不可访问。
        if self._find_all(By.ID, "preform_scrollview"):
            selected_prices = self._find_all(By.ID, "tv_price")
            if any(
                (
                    normalize_text(self.config.price) in normalize_text(element.text)
                    or normalize_text(element.text) in normalize_text(self.config.price)
                )
                for element in selected_prices
                if getattr(element, "text", "")
            ):
                print(f"预约信息已自动选中票档: {self.config.price}")
                return True

        containers = self._find_all(By.ID, "project_detail_perform_price_flowlayout")
        if not containers:
            scroll_views = self._find_all(By.ID, "preform_scrollview")
            price_headers = self._find_all(By.ID, "tv_price_name")
            if not scroll_views or not price_headers:
                return self._set_error("购票弹层未找到票档区域")

            if self.config.price_index is None:
                return self._set_error(
                    "新版票档文字不可访问，必须配置 price_index 才能安全选择"
                )

            try:
                header_bottom = (
                    price_headers[0].rect["y"] + price_headers[0].rect["height"]
                )
            except WebDriverException:
                header_bottom = 0
            candidates = []
            seen_bounds = set()
            for class_name in ("android.widget.FrameLayout", "android.view.ViewGroup"):
                selector = (
                    f'new UiSelector().className("{class_name}").clickable(true)'
                )
                for element in self._find_all(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    selector,
                    context=scroll_views[0],
                ):
                    try:
                        rect = element.rect
                        bounds = (rect["x"], rect["y"], rect["width"], rect["height"])
                        if (
                            not element.is_displayed()
                            or rect["y"] < header_bottom
                            or bounds in seen_bounds
                        ):
                            continue
                        text = element.text or ""
                        if any(word in text for word in ("无票", "售罄", "缺货")):
                            continue
                        seen_bounds.add(bounds)
                        candidates.append((rect["y"], rect["x"], element))
                    except WebDriverException:
                        continue
            candidates.sort(key=lambda row: (row[0], row[1]))
            if self.config.price_index >= len(candidates):
                return self._set_error(
                    f"price_index={self.config.price_index} 越界，新版购票页仅找到 "
                    f"{len(candidates)} 个可售票档"
                )
            if not self._tap(candidates[self.config.price_index][2]):
                return self._set_error("新版购票页按索引选择票档失败")
            print(
                f"新版购票页已按索引 {self.config.price_index} "
                f"选择 {self.config.price}"
            )
            return True
        container = containers[0]

        if self._click_matching_text(
            self.config.price,
            context=container,
            skip_words=("无票", "售罄", "缺货"),
        ):
            return True

        if self.config.price_index is None:
            return self._set_error(
                f"票档文字不可见，且未配置 price_index，无法安全选择 {self.config.price}"
            )

        candidates = []
        for element in self._find_all(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().className("android.widget.FrameLayout").clickable(true)',
            context=container,
        ):
            try:
                if element.is_displayed() and element.is_enabled():
                    candidates.append(element)
            except WebDriverException:
                continue
        if self.config.price_index >= len(candidates):
            return self._set_error(
                f"price_index={self.config.price_index} 越界，当前仅找到 "
                f"{len(candidates)} 个可点击票档"
            )
        if not self._tap(candidates[self.config.price_index]):
            return self._set_error("按 price_index 点击票档失败")
        print(
            f"票档文字不可见，已使用备用索引 {self.config.price_index} "
            f"选择 {self.config.price}"
        )
        return True

    def _select_quantity(self):
        target_count = len(self.config.users)
        if target_count == 1:
            return True
        if not self._find_all(By.ID, "layout_num"):
            return self._set_error("需要多张票，但购票弹层没有数量选择器")
        plus = self._find_first(
            [
                (By.ID, "img_jia"),
                (By.XPATH, '//*[@resource-id="cn.damai:id/img_jia"]'),
                (By.XPATH, '//*[@text="+"]'),
            ],
            timeout=1,
        )
        if not plus:
            return self._set_error("未找到购票数量加号")
        for _ in range(target_count - 1):
            if not self._tap(plus):
                return self._set_error("增加购票数量失败")
            time.sleep(0.05)
        print(f"已选择 {target_count} 张票")
        return True

    def _confirm_purchase(self):
        if self._tap_first(
            [
                (By.ID, "btn_buy_view"),
                (By.ID, "btn_buy"),
                (By.XPATH, '//*[@text="确定"]'),
                (By.XPATH, '//*[@text="确认购买"]'),
            ],
            timeout=self.config.element_timeout,
        ):
            return True
        return self._set_error("未找到购票弹层的确认按钮")

    def _find_submit_button(self, timeout=0):
        selectors = []
        for text in self.SUBMIT_TEXTS:
            selectors.extend(
                [
                    (By.XPATH, f'//*[@text="{text}"]'),
                    (
                        AppiumBy.ANDROID_UIAUTOMATOR,
                        f'new UiSelector().text("{text}")',
                    ),
                ]
            )
        selectors.extend(
            [
                (By.ID, "btn_submit"),
                (By.ID, "submit_order"),
            ]
        )
        return self._find_first(selectors, timeout=timeout)

    def _is_order_confirmation_page(self):
        activity = (getattr(self.driver, "current_activity", "") or "").lower()
        if any(
            name in activity
            for name in ("dmorderactivity", "orderconfirm", "ordercreate")
        ):
            return True
        if self._find_submit_button(timeout=0):
            return True
        return self._page_has_any(
            ("确认订单", "确认购买", "选择观演人", "实名观演人")
        )

    def _wait_for_order_confirmation(self):
        deadline = time.monotonic() + self.config.order_timeout
        while time.monotonic() < deadline:
            self._dismiss_known_dialogs()
            if self._is_order_confirmation_page():
                return True
            if self._page_has_any(("验证码", "安全验证", "滑动验证", "访问被拒绝")):
                return self._set_error("遇到验证码或风控验证，需要人工处理")
            if self._page_has_any(("排队中", "正在排队")):
                print("正在排队，继续等待...")
            time.sleep(0.25)
        return self._set_error("确认购买后未在超时时间内进入订单确认页")

    def _select_users(self):
        for user_index, user in enumerate(self.config.users):
            element = self._find_first(
                [
                    (
                        AppiumBy.ANDROID_UIAUTOMATOR,
                        f'new UiSelector().text("{user}")',
                    ),
                    (By.XPATH, f'//*[@text="{user}"]'),
                    (By.XPATH, f'//*[contains(@text,"{user}")]'),
                ],
                timeout=self.config.element_timeout,
            )
            if not element:
                return self._set_error(f"订单页未找到观演人 {user}")

            # 新版订单页的姓名是普通 TextView，选中状态位于同一行的
            # cn.damai:id/checkbox；不能再点击姓名并假设已经选中。
            checkbox = None
            try:
                row = element.find_element(
                    By.XPATH,
                    './ancestor::*[@resource-id="cn.damai:id/layout_main"][1]',
                )
                row_checkboxes = self._find_all(By.ID, "checkbox", context=row)
                if row_checkboxes:
                    checkbox = row_checkboxes[0]
            except WebDriverException:
                pass

            if checkbox is None:
                checkboxes = self._find_all(By.ID, "checkbox")
                if user_index < len(checkboxes):
                    checkbox = checkboxes[user_index]

            control = checkbox or element
            try:
                already_selected = (
                    control.get_attribute("checked") == "true"
                    or control.get_attribute("selected") == "true"
                )
            except WebDriverException:
                already_selected = False

            if already_selected:
                print(f"观演人已选择并验证: {user}")
                continue

            if checkbox is None:
                return self._set_error(
                    f"找到观演人 {user}，但无法定位对应复选框，已停止以防错选"
                )
            if not self._tap(checkbox):
                return self._set_error(f"无法选择观演人 {user}")

            deadline = time.monotonic() + self.config.element_timeout
            while time.monotonic() < deadline:
                try:
                    if checkbox.get_attribute("checked") == "true":
                        print(f"已选择并验证观演人: {user}")
                        break
                except (StaleElementReferenceException, WebDriverException):
                    pass
                time.sleep(0.05)
            else:
                return self._set_error(f"点击后未能验证观演人已选中: {user}")
        return True

    def _is_payment_page(self):
        package = (getattr(self.driver, "current_package", "") or "").lower()
        activity = (getattr(self.driver, "current_activity", "") or "").lower()
        # 确认订单页本身展示“支付方式”，不能仅凭该文字判定已提交。
        if any(
            name in activity
            for name in ("dmorderactivity", "orderconfirm", "ordercreate")
        ):
            return False
        if any(
            name in package
            for name in ("com.eg.android.alipaygphone", "com.tencent.mm")
        ):
            return True
        if any(name in activity for name in ("cashier", "payment", "payactivity")):
            return True
        return self._page_has_any(("立即支付", "确认支付", "收银台"))

    def _submit_and_wait_for_payment(self, submit_button):
        if not self._tap(submit_button):
            return self._set_error("点击提交订单失败")
        deadline = time.monotonic() + self.config.order_timeout
        while time.monotonic() < deadline:
            if self._is_payment_page():
                self.last_status = RunStatus.PAYMENT_READY
                print("订单已创建，已进入支付界面；脚本不会自动支付")
                return True
            if self._page_has_any(("提交失败", "库存不足", "已售罄", "人数不匹配")):
                return self._set_error("订单提交后页面返回失败状态")
            time.sleep(0.25)
        return self._set_error("提交订单后未在超时时间内检测到支付界面")

    def run_ticket_grabbing(self):
        """从已准备的详情页执行到提交前或支付页。"""
        started_at = time.monotonic()
        self.last_error = ""
        if self._is_order_confirmation_page():
            print("当前已在订单确认页，从观演人校验继续执行")
        else:
            if not self._is_detail_page() and not self.prepare_target():
                return False
            if not self._open_purchase_panel():
                return False
            if not self._select_date():
                return False
            if not self._select_price():
                return False
            if not self._select_quantity():
                return False
            if not self._confirm_purchase():
                return False
            if not self._wait_for_order_confirmation():
                return False

        if not self._select_users():
            return False
        submit_button = self._find_submit_button(timeout=self.config.element_timeout)
        if not submit_button:
            return self._set_error("观演人选择完成，但订单页没有提交按钮")

        if not self.config.if_commit_order:
            self.last_status = RunStatus.READY_TO_SUBMIT
            print(
                "安全停止：已到达订单提交按钮前，if_commit_order=false，"
                "没有创建订单"
            )
            print(f"本次耗时: {time.monotonic() - started_at:.2f} 秒")
            return True

        result = self._submit_and_wait_for_payment(submit_button)
        if result:
            print(f"本次耗时: {time.monotonic() - started_at:.2f} 秒")
        return result

    def _recover_to_detail(self):
        for _ in range(4):
            if self._is_detail_page():
                return True
            try:
                self.driver.back()
            except WebDriverException:
                return False
            time.sleep(0.5)
        return self._is_detail_page()

    def run_with_retry(self, max_retries=None):
        attempts = max_retries or self.config.max_retries
        for attempt in range(1, attempts + 1):
            print(f"执行购票流程，第 {attempt}/{attempts} 次")
            if self.run_ticket_grabbing():
                if self.last_status == RunStatus.READY_TO_SUBMIT:
                    print("演练成功：订单信息已准备完成，未提交")
                elif self.last_status == RunStatus.PAYMENT_READY:
                    print("下单成功：支付界面已拉起")
                return True
            if attempt < attempts:
                print(f"本次失败：{self.last_error}，准备重试")
                self._recover_to_detail()
                time.sleep(self.config.retry_interval)
        print(f"流程失败：{self.last_error}")
        return False


def main():
    bot = DamaiBot()
    try:
        if bot._is_order_confirmation_page():
            print("检测到未完成的确认订单页，将直接继续")
        else:
            if not bot.prepare_target():
                return 1
            print("目标页面准备完成，请保持手机解锁和网络稳定")
        wait_until_start(bot.config.start_at)
        return 0 if bot.run_with_retry() else 1
    finally:
        if bot.driver and (
            not bot.config.keep_session or bot.last_status == RunStatus.FAILED
        ):
            bot.close()
        elif bot.driver:
            print("Appium 会话保持中，手机页面不会被关闭")


if __name__ == "__main__":
    raise SystemExit(main())

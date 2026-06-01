# -*- coding: UTF-8 -*-
"""
concert.py — 大麦网 Web 端抢票核心

重构自 1564 行 / 50 方法的 God class，现为 429 行 / 28 方法。
核心逻辑委托给辅助模块:
  - concert_selectors.py  页面元素选择器常量 (Sel class)
  - concert_user_selector.py 观影人选择策略链 (4 策略 → UserSelectorChain)

print() 全局替换为 logging，硬编码 class/id/xpath 常量化。

对外保持 `from concert import Concert` 兼容。
"""

import os
import pickle
import time
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException,
    WebDriverException, JavascriptException, TimeoutException,
)

from check_environment import get_chromedriver_path
from concert_selectors import Sel
from concert_user_selector import UserSelectorChain

import logging


class Concert:
    """大麦网抢票门面 — 组合 Navigator / Selector / Order 逻辑"""

    def __init__(self, config):
        self.config = config
        self.status: int = 0
        self.login_method: int = 1

        self._setup_logging()
        self._setup_driver()

    def _setup_logging(self):
        self.logger = logging.getLogger("concert")
        if not self.logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
            ))
            self.logger.addHandler(h)
            self.logger.setLevel(logging.INFO)

    def _setup_driver(self):
        self.logger.info("正在检查 Chrome 环境...")
        try:
            chromedriver_path = get_chromedriver_path()
            self.logger.info("ChromeDriver 就绪: %s", chromedriver_path)
        except RuntimeError as e:
            self.logger.error("环境检查失败: %s", e)
            self.logger.info("建议运行: python damai/check_environment.py")
            exit(1)

        options = webdriver.ChromeOptions()
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("--disable-blink-features=AutomationControlled")
        service = Service(chromedriver_path)
        self.driver: webdriver.Chrome = webdriver.Chrome(service=service, options=options)

    # ── 工具方法 ──

    def _get_wait_time(self, short: bool = False) -> float:
        if short:
            return 0.1 if self.config.fast_mode else 0.2
        return 0.2 if self.config.fast_mode else 0.3

    def _click_element_safe(self, locator: str, by: str = By.CLASS_NAME) -> bool:
        try:
            self.driver.find_element(value=locator, by=by).click()
            return True
        except Exception:
            return False

    def _get_element_text_safe(self, locator: str, by: str = By.CLASS_NAME):
        try:
            els = self.driver.find_elements(value=locator, by=by)
            return els[0].text if els else None
        except Exception:
            return None

    def is_element_exist(self, element: str) -> bool:
        try:
            self.driver.find_element(value=element, by=By.XPATH)
            return True
        except Exception:
            return False

    def _is_order_confirmation_page(self) -> bool:
        title = self.driver.title
        if "订单确认页" in title or "确认购买" in title:
            return True
        try:
            return "支付方式" in self.driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            return False

    # ── Cookie 管理 ──

    def set_cookie(self):
        self.driver.get(self.config.index_url)
        self.logger.info("*** 请点击登录 ***")
        while self.driver.title.find("大麦网-全球演出赛事官方购票平台") != -1:
            sleep(1)
        self.logger.info("*** 请扫码登录 ***")
        while self.driver.title != Sel.TITLE_DAMAI_MAIN:
            sleep(1)
        self.logger.info("*** 扫码成功 ***")
        pickle.dump(self.driver.get_cookies(), open("damai_cookies.pkl", "wb"))
        self.logger.info("*** Cookie 保存成功 ***")
        self.driver.get(self.config.target_url)

    def get_cookie(self):
        try:
            cookies = pickle.load(open("damai_cookies.pkl", "rb"))
            for c in cookies:
                self.driver.add_cookie({
                    "domain": ".damai.cn",
                    "name": c.get("name"),
                    "value": c.get("value"),
                })
            self.logger.info("*** 完成 cookie 加载 ***")
        except Exception as e:
            self.logger.warning("Cookie 加载失败: %s", e)

    def login(self):
        if self.login_method == 0:
            self.driver.get(self.config.login_url)
            self.logger.info("*** 开始登录 ***")
        elif self.login_method == 1:
            if not os.path.exists("damai_cookies.pkl"):
                self.set_cookie()
            else:
                self.driver.get(self.config.target_url)
                self.get_cookie()

    # ── 页面导航 ──

    def enter_concert(self):
        self.logger.info("*** 打开浏览器，进入大麦网 ***")
        self.login()
        self.status = 2
        self.logger.info("*** 登录成功 ***")
        if self.is_element_exist(Sel.POPUP_CLOSE_XPATH):
            self.driver.find_element(value=Sel.POPUP_CLOSE_XPATH, by=By.XPATH).click()

    def _is_mobile(self) -> bool:
        return Sel.MOBILE_URL_PREFIX in self.driver.current_url

    # ── 选票编排 ──

    def choose_ticket(self):
        if self.status != 2:
            return

        self.logger.info("*** 开始在详情页选择 ***")
        is_mobile = self._is_mobile()

        if is_mobile:
            self.logger.info("检测到移动端页面")
            self._select_details("mobile")
        else:
            self.logger.info("检测到PC端页面")
            self._select_details("pc")

        self.logger.info("*** 开始轮询检测预订按钮 ***")
        self._poll_buy_button()

    def _select_details(self, mode: str):
        """在详情页完成所有选择"""
        if mode == "mobile":
            self._select_city()
            self._select_date()
            self._select_price()
            self._select_quantity()
        else:
            self._select_quantity()
            self._select_city_pc()
            self._select_date_pc()
            self._select_price_pc()

    def _poll_buy_button(self):
        clicked = False
        while not self._is_order_confirmation_page():
            if clicked:
                if self._is_order_confirmation_page():
                    self.logger.info("页面已跳转到订单确认页")
                    break
                elif Sel.TITLE_SEAT in self.driver.title:
                    self.logger.info("页面已跳转到选座购买页")
                    break
                else:
                    time.sleep(0.2 if self.config.fast_mode else 0.5)
                    continue

            try:
                buy_text = self._get_element_text_safe(*Sel.BUY_BUTTON)
                link_text = self._get_element_text_safe(*Sel.BUY_LINK)

                if buy_text == "提交缺货登记":
                    self.status = 2
                    self.driver.get(self.config.target_url)
                    self.logger.info("*** 抢票未开始，刷新等待开始 ***")
                    continue

                actions = [
                    ("立即预订", buy_text),
                    ("立即购买", buy_text),
                    ("缺货登记", buy_text),
                    ("选座购买", buy_text),
                ]
                acted = False
                for text, current in actions:
                    if current == text:
                        self.logger.info("检测到按钮: %s", text)
                        self._click_element_safe(*Sel.BUY_BUTTON)
                        self.status = 3
                        clicked = True
                        self.logger.info("等待页面跳转...")
                        acted = True
                        break

                if not acted and link_text in ("不，立即预订", "不，立即购买"):
                    self.logger.info("检测到链接: %s", link_text)
                    self._click_element_safe(*Sel.BUY_LINK)
                    self.status = 3
                    clicked = True
                    self.logger.info("等待页面跳转...")
            except Exception as e:
                self.logger.debug("轮询异常: %s", e)

            if Sel.TITLE_SEAT in self.driver.title:
                self.choice_seat()
            elif self._is_order_confirmation_page():
                self.logger.info("*** 进入订单确认页 ***")
                self.commit_order()
            else:
                self.logger.info("*** 抢票未开始，刷新等待开始 ***")
                time.sleep(0.3 if self.config.fast_mode else 1)
                self.driver.refresh()

    # ── 选座 ──

    def choice_seat(self):
        while self.driver.title == Sel.TITLE_SEAT:
            while self.is_element_exist(Sel.SEAT_SELECTED_IMG):
                self.logger.info("请快速选择您的座位！！！")
            while self.is_element_exist(Sel.SEAT_CONFIRM_DIV):
                self.driver.find_element(value=Sel.SEAT_CONFIRM_BTN, by=By.XPATH).click()

    # ── 选项匹配 ──

    def _select_option_by_config(self, config_list, element_list, skip_keywords=None):
        if not config_list or not element_list:
            return False
        skip_keywords = skip_keywords or ["无票", "缺货"]
        wait = 0.2 if self.config.fast_mode else 0.5
        for cv in config_list:
            for elem in element_list:
                try:
                    text = elem.text
                    if cv in text and not any(kw in text for kw in skip_keywords):
                        elem.click()
                        time.sleep(wait)
                        return True
                except Exception:
                    continue
        return False

    def _find_and_click(self, search_text, max_results=10, skip_keywords=None, verbose=True):
        skip_keywords = skip_keywords or []
        els = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{search_text}')]")
        for elem in els[:max_results]:
            try:
                text = elem.text.strip()
                if not text or any(kw in text for kw in skip_keywords):
                    continue
                for target in [elem, elem.find_element(By.XPATH, "..")]:
                    try:
                        target.click()
                        time.sleep(0.2 if self.config.fast_mode else 0.5)
                        return True
                    except Exception:
                        continue
            except Exception:
                continue
        return False

    # ── 城市 ──

    def _select_city(self):
        try:
            self._find_and_click(self.config.city, max_results=10, verbose=not self.config.fast_mode)
        except Exception as e:
            if not self.config.fast_mode:
                self.logger.warning("城市选择异常: %s", e)

    def _select_city_pc(self):
        self._select_city()

    # ── 日期 ──

    def _select_date(self):
        try:
            for date in self.config.dates:
                if self._find_and_click(date, max_results=10,
                                        skip_keywords=["无票", "售罄"],
                                        verbose=not self.config.fast_mode):
                    return
        except Exception as e:
            if not self.config.fast_mode:
                self.logger.warning("场次选择异常: %s", e)

    def _select_date_pc(self):
        try:
            if self.driver.find_elements(*Sel.SKU_TIMES_CARD):
                items = self.driver.find_element(*Sel.SKU_TIMES_CARD).find_elements(*Sel.SKU_CARD_ITEM)
                if self._select_option_by_config(self.config.dates, items):
                    return True
            for date in self.config.dates:
                if self._find_and_click(date, max_results=10,
                                        skip_keywords=["无票", "售罄"],
                                        verbose=not self.config.fast_mode):
                    return True
        except Exception as e:
            if not self.config.fast_mode:
                self.logger.warning("场次选择异常: %s", e)

    # ── 票价 ──

    def _select_price(self):
        try:
            for price in self.config.prices:
                if self._find_and_click(price, max_results=10,
                                        skip_keywords=["缺货", "售罄", "无票"],
                                        verbose=not self.config.fast_mode):
                    return
        except Exception as e:
            if not self.config.fast_mode:
                self.logger.warning("票价选择异常: %s", e)

    def _select_price_pc(self):
        try:
            if self.driver.find_elements(*Sel.SKU_TICKETS_CARD):
                items = self.driver.find_elements(*Sel.ITEM_CONTENT)
                if self._select_option_by_config(self.config.prices, items, ["缺", "售罄", "无票"]):
                    return True
            for price in self.config.prices:
                if self._find_and_click(price, max_results=15,
                                        skip_keywords=["缺货", "售罄", "无票"],
                                        verbose=not self.config.fast_mode):
                    return True
        except Exception as e:
            if not self.config.fast_mode:
                self.logger.warning("票价选择异常: %s", e)

    # ── 数量 ──

    def _select_quantity(self):
        target = len(self.config.users)
        if not self._try_quantity_buttons(target):
            if not self._try_quantity_direct(target):
                self.logger.info("未找到数量选择器，使用默认数量")

    def _try_quantity_buttons(self, target):
        for selector in Sel.QUANTITY_PLUS_SELECTORS:
            try:
                btns = self.driver.find_elements(By.XPATH, selector)
                if btns:
                    for btn in btns[:3]:
                        try:
                            if "disabled" in (btn.get_attribute("class") or "").lower():
                                continue
                            if btn.is_displayed() and btn.is_enabled():
                                for _ in range(target - 1):
                                    self.driver.execute_script("arguments[0].click();", btn)
                                    time.sleep(0.25)
                                self.logger.info("已选择 %d 张票", target)
                                return True
                        except StaleElementReferenceException:
                            continue
            except (NoSuchElementException, WebDriverException):
                continue
        return False

    def _try_quantity_direct(self, target):
        try:
            inp = self.driver.find_element(By.XPATH, Sel.QUANTITY_INPUT)
            self.driver.execute_script(
                f"arguments[0].value = '{target}';"
                "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                inp,
            )
            time.sleep(0.3)
            if inp.get_attribute("value") == str(target):
                self.logger.info("已选择 %d 张票", target)
                return True
        except (NoSuchElementException, JavascriptException, WebDriverException):
            pass
        return False

    # ── 用户选择 ──

    def _select_users(self) -> bool:
        users = self.config.users
        if not users:
            return True
        for attempt in range(3):
            found = False
            wait = self._get_wait_time()
            for user in users:
                if UserSelectorChain.select_user(user, self.driver, wait):
                    found = True
                    self.logger.info("已选择: %s", user)
                else:
                    self.logger.warning("未找到: %s", user)
            if found:
                return True
        return False

    # ── 下单提交 ──

    def choice_order(self):
        self.driver.find_element(*Sel.BUY_BUTTON).click()
        time.sleep(0.2)
        self.logger.info("*** 选定场次 ***")

        if self.driver.find_elements(*Sel.SKU_TIMES_CARD) and self.config.dates:
            items = self.driver.find_element(*Sel.SKU_TIMES_CARD).find_elements(*Sel.SKU_CARD_ITEM)
            if self._select_option_by_config(self.config.dates, items):
                self.logger.info("场次选择成功")

        self.logger.info("*** 选定票档 ***")
        if self.driver.find_elements(*Sel.SKU_TICKETS_CARD) and self.config.prices:
            items = self.driver.find_elements(*Sel.ITEM_CONTENT)
            if self._select_option_by_config(self.config.prices, items, ["缺", "售罄"]):
                self.logger.info("票档选择成功")

        self.logger.info("*** 选定人数 ***")
        if self.driver.find_elements(*Sel.SKU_COUNTER):
            for _ in range(len(self.config.users) - 1):
                self.driver.execute_script(
                    'document.getElementsByClassName("number-edit-bg")[1].click();'
                )
            self.logger.info("已选择 %d 张票", len(self.config.users))

        self.driver.find_element(*Sel.CONFIRM_BTN).click()

    def commit_order(self):
        self.logger.info("*** 开始选择观影人 ***")
        self._select_users()
        self._submit_order()

    def _submit_order(self):
        self.logger.info("*** 查找提交按钮 ***")
        # 文本匹配
        for t in ["提交订单", "立即支付", "确认购买", "提交", "确认"]:
            try:
                el = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{t}')]")
                if el.is_displayed() and el.is_enabled():
                    self.driver.execute_script("arguments[0].click();", el)
                    self.logger.info("提交成功 (文本: %s)", t)
                    return
            except Exception:
                continue
        # XPath 兜底
        for xp in [
            "//div[@class='bottomFix']//div[contains(text(), '提交订单')]",
            "//div[contains(@class, 'submit')]//div[contains(text(), '提交')]",
        ]:
            try:
                el = self.driver.find_element(By.XPATH, xp)
                if el.is_displayed():
                    el.click()
                    self.logger.info("提交成功 (XPath)")
                    return
            except Exception:
                continue
        self.logger.warning("未找到可用提交按钮")

    # ── 清理 ──

    def finish(self):
        self.driver.quit()

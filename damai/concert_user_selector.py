# -*- coding: UTF-8 -*-
"""
concert_user_selector.py — 用户选择策略链

将原来 _try_select_user_method1~4 提取为独立策略类，
UserSelectorChain 按序执行，任一成功即返回。
"""

import time
from abc import ABC, abstractmethod
from typing import List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver


class UserSelectStrategy(ABC):
    """用户选择策略抽象基类"""

    @abstractmethod
    def try_select(self, user: str, driver: WebDriver, wait_time: float) -> bool:
        """尝试选择指定用户，返回是否成功"""
        ...


# ── 策略 1: 查找并点击包含用户名的 div 附近的复选框 ──

class DivCheckboxStrategy(UserSelectStrategy):
    """方法1: 查找包含用户名的 div，点击其附近的复选框/icon"""

    CHECKBOX_SELECTORS = [
        "following-sibling::*//i[contains(@class, 'iconfont')]",
        "following-sibling::*[1]//i",
        "following-sibling::i",
        "..//following-sibling::*//i[contains(@class, 'iconfont')]",
        "..//following-sibling::i",
        "..//i[contains(@class, 'iconfont')]",
        "..//i[contains(@class, 'icon')]",
        "..//i[contains(@class, 'check')]",
        "following-sibling::*[1]//input",
        "following-sibling::*[1]//span",
        "..//following-sibling::*//input",
        "../..//input[@type='checkbox']",
        "..//label",
    ]

    def try_select(self, user: str, driver: WebDriver, wait_time: float) -> bool:
        xpath = f"//div[contains(text(), '{user}')]"
        elements = driver.find_elements(By.XPATH, xpath)
        if not elements:
            return False

        # 找最佳匹配
        best_match = None
        for elem in elements:
            try:
                text = elem.text.strip()
                if text == user:
                    best_match = elem
                    break
                elif len(text) < 30 and user in text and best_match is None:
                    best_match = elem
            except Exception:
                continue

        if not best_match:
            return False

        # 尝试点击附近复选框
        for selector in self.CHECKBOX_SELECTORS:
            try:
                checkbox = best_match.find_element(By.XPATH, selector)
                driver.execute_script("arguments[0].click();", checkbox)
                time.sleep(wait_time)
                return True
            except Exception:
                continue

        # 兜底：直接点击 div
        try:
            driver.execute_script("arguments[0].click();", best_match)
            time.sleep(wait_time)
            return True
        except Exception:
            return False


# ── 策略 2: 通过复选框和 label 选择 ──

class CheckboxLabelStrategy(UserSelectStrategy):
    """方法2: 查找所有复选框，通过 label 文本或附近文本匹配"""

    def try_select(self, user: str, driver: WebDriver, wait_time: float) -> bool:
        try:
            labels = driver.find_elements(By.TAG_NAME, "label")
            for label in labels:
                try:
                    label_text = label.text.strip()
                    if user not in label_text:
                        continue
                    label_for = label.get_attribute("for")
                    if label_for:
                        checkbox = driver.find_element(By.ID, label_for)
                        if not checkbox.is_selected():
                            checkbox.click()
                            time.sleep(wait_time)
                            return True
                except Exception:
                    continue

            # 通过复选框附近文本
            checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            for cb in checkboxes:
                try:
                    parent = cb.find_element(By.XPATH, "..")
                    nearby = parent.text.strip()
                    if user in nearby and not cb.is_selected():
                        cb.click()
                        time.sleep(wait_time)
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False


# ── 策略 3: 点击包含用户名的任意元素 ──

class TextClickStrategy(UserSelectStrategy):
    """方法3: 点击页面中文本精确匹配用户名的元素"""

    def try_select(self, user: str, driver: WebDriver, wait_time: float) -> bool:
        try:
            xpath = f"//*[contains(text(), '{user}')]"
            elements = driver.find_elements(By.XPATH, xpath)
            for elem in elements[:10]:
                try:
                    text = elem.text.strip()
                    if text == user or (len(text) < 30 and user in text):
                        elem.click()
                        time.sleep(wait_time)
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False


# ── 策略 4: JavaScript 查找并点击 ──

class JSClickStrategy(UserSelectStrategy):
    """方法4: 使用 JavaScript 查找所有可见文本并尝试点击匹配项"""

    def try_select(self, user: str, driver: WebDriver, wait_time: float) -> bool:
        try:
            # 扫描页面上所有可见文本节点
            script = """
            var results = [];
            var walker = document.createTreeWalker(
                document.body, NodeFilter.SHOW_TEXT, null, false
            );
            var node;
            while (node = walker.nextNode()) {
                var text = node.textContent.trim();
                if (text.indexOf(arguments[0]) !== -1 && text.length < 50) {
                    var parent = node.parentElement;
                    if (parent && parent.offsetParent !== null) {
                        results.push(parent);
                    }
                }
            }
            return results.slice(0, 15);
            """
            parents = driver.execute_script(script, user)
            if not parents:
                return False

            for parent in parents:
                try:
                    # 尝试找复选框
                    for sel in ["input[@type='checkbox']", ".//i", ".//span"]:
                        try:
                            child = parent.find_element(By.XPATH, sel)
                            driver.execute_script("arguments[0].click();", child)
                            time.sleep(wait_time)
                            return True
                        except Exception:
                            continue
                    # 直接点击父元素
                    driver.execute_script("arguments[0].click();", parent)
                    time.sleep(wait_time)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False


# ── 策略链编排 ──

class UserSelectorChain:
    """按序执行用户选择策略，任一成功后提前返回"""

    STRATEGIES: List[UserSelectStrategy] = [
        DivCheckboxStrategy(),
        CheckboxLabelStrategy(),
        TextClickStrategy(),
        JSClickStrategy(),
    ]

    @classmethod
    def select_user(cls, user: str, driver: WebDriver, wait_time: float = 0.2) -> bool:
        """尝试选择指定用户，返回是否成功"""
        for strategy in cls.STRATEGIES:
            try:
                if strategy.try_select(user, driver, wait_time):
                    return True
            except Exception:
                continue
        return False

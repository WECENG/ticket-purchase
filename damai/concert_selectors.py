# -*- coding: UTF-8 -*-
"""
concert_selectors.py — 大麦网 Web 端页面元素选择器常量。

提取所有硬编码的 class name / ID / XPath，方便大麦页面更新时统一修改。
选择器格式: (By 类型, 值) 元组，或纯字符串（用于 XPath）。
"""

from selenium.webdriver.common.by import By


class Sel:
    """选择器命名空间"""

    # ── 购买相关按钮 ──
    BUY_BUTTON = ("CLASS_NAME", "buy__button__text")
    BUY_LINK = ("CLASS_NAME", "buy-link")

    # ── 场次/票档选择 ──
    SKU_TIMES_CARD = ("CLASS_NAME", "sku-times-card")       # 场次卡片容器
    SKU_TICKETS_CARD = ("CLASS_NAME", "sku-tickets-card")   # 票档卡片容器
    SKU_CARD_ITEM = ("CLASS_NAME", "bui-dm-sku-card-item")  # 场次/票档单项
    ITEM_CONTENT = ("CLASS_NAME", "item-content")           # 票价内容
    SKU_COUNTER = ("CLASS_NAME", "bui-dm-sku-counter")      # 数量选择器

    # ── 订单确认按钮 ──
    CONFIRM_BTN = ("CLASS_NAME", "bui-btn-contained")

    # ── 城市选择 ──
    CITY_TOUR = ("CLASS_NAME", "bui-dm-tour")
    CITY_LIST = ("CLASS_NAME", "tour-list")
    CITY_SKU_TOUR = ("CLASS_NAME", "sku-tour")

    # ── 详情页弹窗 ──
    POPUP_CLOSE_XPATH = "/html/body/div[2]/div[2]/div/div/div[3]/div[2]"

    # ── 数量选择器 ──
    QUANTITY_INPUT = "//input[contains(@class, 'cafe-c-input-number-input')]"
    QUANTITY_PLUS_SELECTORS = [
        "//div[contains(@class, 'cafe-c-input-number')]//a[contains(@class, 'handler-up')]",
        "//a[contains(@class, 'cafe-c-input-number-handler-up')]",
        "//div[contains(@class, 'number_right_info')]//a[last()]",
        "//*[contains(@class, 'cafe-c-input-number')]//a[contains(text(), '+')]",
        "//a[contains(@class, 'handler-up')]",
    ]

    # ── 选座页面 ──
    SEAT_SELECTED_IMG = '//*[@id="app"]/div[2]/div[2]/div[1]/div[2]/img'
    SEAT_CONFIRM_DIV = '//*[@id="app"]/div[2]/div[2]/div[2]/div'
    SEAT_CONFIRM_BTN = '//*[@id="app"]/div[2]/div[2]/div[2]/button'

    # ── 页面扫描（调试用） ──
    SCAN_CITY_SELECTORS = ["bui-dm-tour", "tour-list", "city-list", "sku-tour"]
    SCAN_DATE_SELECTORS = ["sku-times-card", "sku-times", "date-list", "tour-list"]
    SCAN_PRICE_SELECTORS = ["sku-tickets-card", "sku-ticket", "price-list", "ticket-list"]

    # ── URL 常量 ──
    MOBILE_URL_PREFIX = "m.damai.cn"
    TITLE_DAMAI_MAIN = "大麦网-全球演出赛事官方购票平台-100%正品、先付先抢、在线选座！"
    TITLE_SEAT = "选座购买"

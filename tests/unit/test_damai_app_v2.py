from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from damai_appium.config import Config
from damai_appium.damai_app_v2 import (
    DamaiBot,
    RunStatus,
    normalize_text,
    wait_until_start,
)


def make_config(**overrides):
    values = {
        "server_url": "http://127.0.0.1:4723",
        "keyword": "孙燕姿",
        "target_title": "孙燕姿巡回演唱会",
        "users": ["测试用户"],
        "city": "杭州",
        "date": "10.11",
        "price": "看台980元",
        "price_index": 2,
        "if_commit_order": False,
        "start_at": None,
        "result_index": 0,
        "udid": None,
        "device_name": "Android",
        "platform_version": None,
        "app_package": "cn.damai",
        "app_activity": ".launcher.splash.SplashMainActivity",
        "max_retries": 3,
        "retry_interval": 0.01,
        "element_timeout": 1,
        "order_timeout": 1,
        "keep_session": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def patch_successful_pre_submit_flow(monkeypatch, bot):
    monkeypatch.setattr(bot, "_is_detail_page", lambda: True)
    monkeypatch.setattr(bot, "_open_purchase_panel", lambda: True)
    monkeypatch.setattr(bot, "_is_order_confirmation_page", lambda: False)
    monkeypatch.setattr(bot, "_select_date", lambda: True)
    monkeypatch.setattr(bot, "_select_price", lambda: True)
    monkeypatch.setattr(bot, "_select_quantity", lambda: True)
    monkeypatch.setattr(bot, "_confirm_purchase", lambda: True)
    monkeypatch.setattr(bot, "_wait_for_order_confirmation", lambda: True)
    monkeypatch.setattr(bot, "_select_users", lambda: True)
    monkeypatch.setattr(bot, "_find_submit_button", lambda timeout=0: object())


class FakeElement:
    def __init__(
        self,
        text="",
        x=0,
        y=0,
        width=100,
        height=100,
        attributes=None,
        ancestor=None,
    ):
        self.text = text
        self.rect = {"x": x, "y": y, "width": width, "height": height}
        self.attributes = attributes or {}
        self.ancestor = ancestor or self

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def get_attribute(self, name):
        return self.attributes.get(name, "false")

    def find_element(self, by, value):
        return self.ancestor


def test_normalize_text_matches_date_and_price_variants():
    assert normalize_text("2026年10月11日") == "2026.10.11"
    assert normalize_text("看台 980元") == "看台980"
    assert normalize_text("杭州站") == "杭州"


def test_wait_until_start_returns_when_clock_reaches_target():
    target = datetime(2026, 8, 12, 15, 0, 0)
    times = iter([target - timedelta(milliseconds=50), target])
    sleeps = []

    wait_until_start(
        target.isoformat(sep=" "),
        now_func=lambda: next(times),
        sleep_func=sleeps.append,
    )

    assert sleeps == [pytest.approx(0.05)]


def test_invalid_config_rejects_empty_users():
    with pytest.raises(ValueError, match="users"):
        Config(
            "http://127.0.0.1:4723",
            "演出",
            [],
            "杭州",
            "10.11",
            "980",
        )


def test_dry_run_stops_before_submit(monkeypatch):
    bot = DamaiBot(config=make_config(if_commit_order=False), setup_driver=False)
    patch_successful_pre_submit_flow(monkeypatch, bot)
    submit = []
    monkeypatch.setattr(
        bot,
        "_submit_and_wait_for_payment",
        lambda button: submit.append(button) or True,
    )

    assert bot.run_ticket_grabbing() is True
    assert bot.last_status == RunStatus.READY_TO_SUBMIT
    assert submit == []


def test_commit_mode_only_succeeds_after_payment_is_verified(monkeypatch):
    bot = DamaiBot(config=make_config(if_commit_order=True), setup_driver=False)
    patch_successful_pre_submit_flow(monkeypatch, bot)

    def fail_payment(_button):
        return bot._set_error("没有检测到支付界面")

    monkeypatch.setattr(bot, "_submit_and_wait_for_payment", fail_payment)

    assert bot.run_ticket_grabbing() is False
    assert bot.last_status == RunStatus.FAILED
    assert "支付界面" in bot.last_error


def test_qilin_purchase_panel_is_recognized_from_activity():
    bot = DamaiBot(config=make_config(), setup_driver=False)
    bot.driver = SimpleNamespace(
        current_activity=".commonbusiness.seatbiz.sku.qilin.ui.NcovSkuActivity"
    )
    bot._find_all = lambda *args, **kwargs: []

    assert bot._purchase_panel_open() is True


def test_reservation_panel_is_not_treated_as_live_purchase(monkeypatch):
    bot = DamaiBot(config=make_config(), setup_driver=False)
    monkeypatch.setattr(bot, "_page_source", lambda: "预约想看场次 提交抢票预约")

    assert bot._is_reservation_panel() is True


def test_qilin_selects_single_performance_then_first_available_price(monkeypatch):
    bot = DamaiBot(
        config=make_config(date="09.12", price="普通票388元", price_index=0),
        setup_driver=False,
    )
    scroll = FakeElement()
    performance_header = FakeElement(y=100, height=20)
    price_header = FakeElement(y=300, height=20)
    performance = FakeElement(y=150)
    normal = FakeElement(text="可预约", x=0, y=350)
    vip = FakeElement(text="可预约", x=110, y=350)
    svip = FakeElement(text="缺货登记", x=0, y=460)
    state = {"date_selected": False}

    def fake_find_all(by, value, context=None):
        if value == "project_detail_perform_flowlayout":
            return []
        if value == "project_detail_perform_price_flowlayout":
            return []
        if value == "preform_scrollview":
            return [scroll]
        if value == "tv_perform_name":
            return [performance_header]
        if value == "tv_price_name":
            return [price_header] if state["date_selected"] else []
        if value == "tv_price":
            return []
        if "android.view.ViewGroup" in value:
            return [performance] if not state["date_selected"] else []
        if "android.widget.FrameLayout" in value:
            return [normal, vip, svip] if state["date_selected"] else []
        return []

    selected = []

    def fake_tap(element):
        if element is performance:
            state["date_selected"] = True
        else:
            selected.append(element)
        return True

    monkeypatch.setattr(bot, "_find_all", fake_find_all)
    monkeypatch.setattr(bot, "_tap", fake_tap)

    assert bot._select_date() is True
    assert bot._select_price() is True
    assert selected == [normal]


def test_qilin_keeps_price_already_selected_by_reservation(monkeypatch):
    bot = DamaiBot(
        config=make_config(price="普通票388元", price_index=0),
        setup_driver=False,
    )
    scroll = FakeElement()
    price_header = FakeElement(y=300, height=20)
    selected_price = FakeElement(text="388")

    def fake_find_all(by, value, context=None):
        if value == "project_detail_perform_price_flowlayout":
            return [FakeElement()]  # 真机新版页面仍暴露旧容器 ID
        if value == "preform_scrollview":
            return [scroll]
        if value == "tv_price_name":
            return [price_header]
        if value == "tv_price":
            return [selected_price]
        return []

    monkeypatch.setattr(bot, "_find_all", fake_find_all)

    assert bot._select_price() is True


def test_qilin_accepts_selected_date_even_when_legacy_container_exists(monkeypatch):
    bot = DamaiBot(config=make_config(date="09.12"), setup_driver=False)
    scroll = FakeElement()
    old_container = FakeElement()
    price_header = FakeElement(text="票档")

    def fake_find_all(by, value, context=None):
        if value == "preform_scrollview":
            return [scroll]
        if value == "tv_price_name":
            return [price_header]
        if value == "project_detail_perform_flowlayout":
            return [old_container]  # 日期文字在真机上不可访问
        return []

    monkeypatch.setattr(bot, "_find_all", fake_find_all)

    assert bot._select_date() is True


def test_dm_order_activity_is_confirmation_not_payment(monkeypatch):
    bot = DamaiBot(config=make_config(), setup_driver=False)
    bot.driver = SimpleNamespace(
        current_activity=".ultron.view.activity.DmOrderActivity",
        current_package="cn.damai",
    )
    monkeypatch.setattr(bot, "_page_source", lambda: "支付方式 支付宝 立即提交")

    assert bot._is_order_confirmation_page() is True
    assert bot._is_payment_page() is False


def test_select_users_keeps_verified_checked_checkbox(monkeypatch):
    bot = DamaiBot(config=make_config(users=["测试用户"]), setup_driver=False)
    row = FakeElement()
    name = FakeElement(text="测试用户", ancestor=row)
    checkbox = FakeElement(attributes={"checked": "true"})
    tapped = []

    monkeypatch.setattr(bot, "_find_first", lambda *args, **kwargs: name)
    monkeypatch.setattr(
        bot,
        "_find_all",
        lambda by, value, context=None: [checkbox] if value == "checkbox" else [],
    )
    monkeypatch.setattr(bot, "_tap", lambda element: tapped.append(element) or True)

    assert bot._select_users() is True
    assert tapped == []


def test_select_users_taps_checkbox_and_verifies_selection(monkeypatch):
    bot = DamaiBot(config=make_config(users=["测试用户"]), setup_driver=False)
    row = FakeElement()
    name = FakeElement(text="测试用户", ancestor=row)
    checkbox = FakeElement(attributes={"checked": "false"})

    monkeypatch.setattr(bot, "_find_first", lambda *args, **kwargs: name)
    monkeypatch.setattr(
        bot,
        "_find_all",
        lambda by, value, context=None: [checkbox] if value == "checkbox" else [],
    )

    def tap(element):
        element.attributes["checked"] = "true"
        return True

    monkeypatch.setattr(bot, "_tap", tap)

    assert bot._select_users() is True
    assert checkbox.get_attribute("checked") == "true"


def test_run_resumes_existing_order_page_without_reopening_purchase(monkeypatch):
    bot = DamaiBot(
        config=make_config(if_commit_order=False),
        setup_driver=False,
    )
    opened = []
    monkeypatch.setattr(bot, "_is_order_confirmation_page", lambda: True)
    monkeypatch.setattr(bot, "_open_purchase_panel", lambda: opened.append(True))
    monkeypatch.setattr(bot, "_select_users", lambda: True)
    monkeypatch.setattr(bot, "_find_submit_button", lambda timeout=0: object())

    assert bot.run_ticket_grabbing() is True
    assert bot.last_status == RunStatus.READY_TO_SUBMIT
    assert opened == []

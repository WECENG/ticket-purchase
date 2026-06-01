# -*- coding: UTF-8 -*-
"""smoke tests for concert core logic."""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "damai"))


def make_mock_config(**overrides):
    cfg = Mock()
    defaults = {
        "index_url": "https://www.damai.cn/",
        "login_url": "https://passport.damai.cn/login",
        "target_url": "https://detail.damai.cn/item.htm?id=123456",
        "users": ["ZhangSan", "LiSi"],
        "city": "Beijing",
        "dates": ["2026-06-15"],
        "prices": ["680"],
        "if_listen": True,
        "if_commit_order": False,
        "max_retries": 100,
        "fast_mode": True,
        "page_load_delay": 2,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(cfg, k, v)
    return cfg


def make_mock_element(text="", tag="div", attrs=None, displayed=True, enabled=True):
    el = Mock()
    el.text = text
    el.tag_name = tag
    el.is_displayed.return_value = displayed
    el.is_enabled.return_value = enabled
    el.is_selected.return_value = False
    el.get_attribute = Mock(side_effect=lambda a: (attrs or {}).get(a, ""))
    el.find_element = Mock(side_effect=lambda *a, **kw: make_mock_element())
    el.find_elements = Mock(return_value=[])
    el.click = Mock()
    el.rect = {"x": 0, "y": 0, "width": 100, "height": 40}
    return el


class TestConcertToolMethods:

    @pytest.fixture
    def concert(self):
        with patch("check_environment.get_chromedriver_path", return_value="/fake/chromedriver"):
            with patch("concert.webdriver.Chrome") as mock_chrome:
                mock_driver = Mock()
                mock_driver.title = "damai"
                mock_driver.current_url = "https://m.damai.cn/detail?itemId=123"
                mock_driver.find_element = Mock()
                mock_driver.find_elements = Mock(return_value=[])
                mock_driver.get = Mock()
                mock_driver.quit = Mock()
                mock_chrome.return_value = mock_driver
                from concert import Concert
                return Concert(make_mock_config())

    def test_init(self, concert):
        assert concert.config is not None
        assert concert.status == 0

    def test_get_wait_time(self, concert):
        assert concert._get_wait_time() == 0.2
        assert concert._get_wait_time(short=True) == 0.1
        concert.config.fast_mode = False
        assert concert._get_wait_time() == 0.3

    def test_is_order_page(self, concert):
        concert.driver.title = "订单确认页"
        assert concert._is_order_confirmation_page() is True
        concert.driver.title = "商品详情"
        body = Mock()
        body.text = "选座购买"
        concert.driver.find_element.return_value = body
        assert concert._is_order_confirmation_page() is False

    def test_is_mobile(self, concert):
        assert concert._is_mobile() is True
        concert.driver.current_url = "https://www.damai.cn/"
        assert concert._is_mobile() is False

    def test_finish(self, concert):
        concert.finish()
        concert.driver.quit.assert_called_once()

    def test_element_exist(self, concert):
        concert.driver.find_element.return_value = Mock()
        assert concert.is_element_exist("//div") is True
        concert.driver.find_element.side_effect = Exception("nope")
        assert concert.is_element_exist("//div") is False

    def test_click_safe(self, concert):
        assert concert._click_element_safe("btn", "class_name") is True
        concert.driver.find_element.side_effect = Exception("gone")
        assert concert._click_element_safe("btn", "class_name") is False

    def test_get_text_safe(self, concert):
        el = Mock()
        el.text = "Buy"
        concert.driver.find_elements.return_value = [el]
        assert concert._get_element_text_safe("btn", "class_name") == "Buy"
        concert.driver.find_elements.return_value = []
        assert concert._get_element_text_safe("btn", "class_name") is None

    def test_select_option(self, concert):
        el = make_mock_element(text="680 yuan")
        assert concert._select_option_by_config(["680"], [el]) is True
        el = make_mock_element(text="680 无票")
        assert concert._select_option_by_config(["680"], [el]) is False

    def test_select_option_empty(self, concert):
        assert concert._select_option_by_config([], [make_mock_element()]) is False
        assert concert._select_option_by_config(["680"], []) is False

    def test_find_and_click(self, concert):
        el = make_mock_element(text="Beijing", tag="span")
        concert.driver.find_elements.return_value = [el]
        assert concert._find_and_click("Beijing") is True
        concert.driver.find_elements.return_value = []
        assert concert._find_and_click("nope") is False

    def test_choose_ticket_bad_status(self, concert):
        concert.status = 0
        concert.choose_ticket()

    def test_quantity_buttons(self, concert):
        btn = make_mock_element(tag="a", attrs={"class": "handler-up"})
        concert.driver.find_elements.return_value = [btn]
        assert concert._try_quantity_buttons(2) is True

    def test_quantity_direct(self, concert):
        inp = make_mock_element(tag="input")
        inp.get_attribute = Mock(return_value="2")
        concert.driver.find_element.return_value = inp
        assert concert._try_quantity_direct(2) is True


class TestSelectors:

    def test_import(self):
        from concert_selectors import Sel
        assert Sel is not None

    def test_buy_button(self):
        from concert_selectors import Sel
        assert isinstance(Sel.BUY_BUTTON, tuple)
        assert len(Sel.BUY_BUTTON) == 2

    def test_sku(self):
        from concert_selectors import Sel
        assert Sel.SKU_TIMES_CARD
        assert Sel.SKU_TICKETS_CARD
        assert Sel.SKU_COUNTER

    def test_quantity(self):
        from concert_selectors import Sel
        assert len(Sel.QUANTITY_PLUS_SELECTORS) >= 3

    def test_seat(self):
        from concert_selectors import Sel
        assert Sel.SEAT_SELECTED_IMG
        assert Sel.SEAT_CONFIRM_BTN


class TestUserSelectorChain:

    @pytest.fixture
    def mock_driver(self):
        d = Mock()
        d.find_elements = Mock(return_value=[])
        d.find_element = Mock(side_effect=Exception("nope"))
        d.execute_script = Mock()
        return d

    def test_div_finds(self, mock_driver):
        from concert_user_selector import DivCheckboxStrategy
        el = make_mock_element(text="ZhangSan", tag="div")
        inner = make_mock_element(tag="i", attrs={"class": "iconfont"})
        el.find_element.return_value = inner
        mock_driver.find_elements.return_value = [el]
        s = DivCheckboxStrategy()
        assert s.try_select("ZhangSan", mock_driver, 0.01) is True

    def test_div_no_match(self, mock_driver):
        from concert_user_selector import DivCheckboxStrategy
        mock_driver.find_elements.return_value = []
        assert DivCheckboxStrategy().try_select("Nope", mock_driver, 0.01) is False

    def test_label_selects(self, mock_driver):
        from concert_user_selector import CheckboxLabelStrategy
        label = make_mock_element(text="ZhangSan 138****", tag="label")
        label.get_attribute = Mock(return_value="cb_1")
        cb = make_mock_element(tag="input", attrs={"type": "checkbox"})
        cb.is_selected.return_value = False
        mock_driver.find_elements.return_value = [label]
        # Override fixture default: find_element with ID="cb_1" must return the checkbox
        mock_driver.find_element = Mock(return_value=cb)
        mock_driver.find_element.side_effect = None
        assert CheckboxLabelStrategy().try_select("ZhangSan", mock_driver, 0.01) is True

    def test_text_click(self, mock_driver):
        from concert_user_selector import TextClickStrategy
        el = make_mock_element(text="ZhangSan", tag="span")
        mock_driver.find_elements.return_value = [el]
        assert TextClickStrategy().try_select("ZhangSan", mock_driver, 0.01) is True

    def test_text_no_match(self, mock_driver):
        from concert_user_selector import TextClickStrategy
        mock_driver.find_elements.return_value = []
        assert TextClickStrategy().try_select("Nope", mock_driver, 0.01) is False

    def test_chain_ok(self, mock_driver):
        from concert_user_selector import UserSelectorChain
        el = make_mock_element(text="ZhangSan", tag="span")
        mock_driver.find_elements.return_value = [el]
        assert UserSelectorChain.select_user("ZhangSan", mock_driver, 0.01) is True

    def test_chain_fail(self, mock_driver):
        from concert_user_selector import UserSelectorChain
        mock_driver.find_elements.return_value = []
        mock_driver.execute_script.side_effect = Exception("no")
        assert UserSelectorChain.select_user("Nope", mock_driver, 0.01) is False


class TestDamaiConfig:

    def test_all_fields(self):
        from damai.config import Config
        cfg = Config(
            "https://a.com", "https://b.com", "https://c.com",
            ["u1", "u2"], "Shanghai", ["2026-07-01"], ["380", "580"],
            False, True, 50, False, 5,
        )
        assert cfg.users == ["u1", "u2"]
        assert cfg.max_retries == 50
        assert cfg.fast_mode is False

    def test_commit_false(self):
        from damai.config import Config
        cfg = Config("", "", "", ["u1"], "", [], [], True, False, 10, True, 2)
        assert cfg.if_commit_order is False

    def test_missing_users_exits(self):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", create=True) as mo:
                mo.return_value.__enter__.return_value.read.return_value = json.dumps({
                    "index_url": "a", "login_url": "b", "target_url": "c",
                    "users": [], "if_listen": True, "if_commit_order": False,
                })
                import damai.damai
                with pytest.raises(SystemExit):
                    damai.damai.check_config_file()
"""
Shared test helper functions for building mock objects.
"""
from unittest.mock import Mock


def make_mock_config(**overrides):
    """Create a mock Config object for concert tests."""
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


def make_mock_element(text="", tag="div", attrs=None, displayed=True,
                      enabled=True):
    """Create a mock Selenium WebElement for tests."""
    el = Mock()
    el.text = text
    el.tag_name = tag
    el.is_displayed.return_value = displayed
    el.is_enabled.return_value = enabled
    el.is_selected.return_value = False
    el.get_attribute = Mock(
        side_effect=lambda a: (attrs or {}).get(a, "")
    )
    el.find_element = Mock(
        side_effect=lambda *a, **kw: make_mock_element()
    )
    el.find_elements = Mock(return_value=[])
    el.click = Mock()
    el.rect = {"x": 0, "y": 0, "width": 100, "height": 40}
    return el

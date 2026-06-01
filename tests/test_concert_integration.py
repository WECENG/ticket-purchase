# -*- coding: UTF-8 -*-
"""Selenium integration tests — verify selectors actually hit DOM elements.

Requires Chrome + ChromeDriver.  Run with:  pytest --run-integration
These tests use a minimal local HTML fixture that mimics Damai's DOM.
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from concert_selectors import Sel
from tests.helpers import make_mock_config

# --run-integration is required; the conftest marker handles skipping

FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "damai_minimal.html"
)
FIXTURE_URL = FIXTURE_PATH.as_uri()


@pytest.mark.integration
class TestMinimalHTMLIntegration:
    """Verify Concert methods against a real browser + fixture HTML."""

    @pytest.fixture
    def concert(self):
        """Concert with real ChromeDriver (no mock), pointing at fixture."""
        with patch("check_environment.get_chromedriver_path",
                   return_value=_get_chromedriver()):
            from concert import Concert
            c = Concert(make_mock_config())
            c.driver.get(FIXTURE_URL)
            yield c
            c.finish()

    def test_click_safe_hits_buy_button(self, concert):
        """_click_element_safe finds and clicks the buy__button__text."""
        assert concert._click_element_safe(*Sel.BUY_BUTTON) is True

    def test_get_text_safe_reads_buy_button(self, concert):
        """_get_element_text_safe returns '立即购买' from the fixture."""
        text = concert._get_element_text_safe(*Sel.BUY_BUTTON)
        assert text == "立即购买"

    def test_find_and_click_by_text(self, concert):
        """_find_and_click locates the button by visible text."""
        assert concert._find_and_click("立即购买", max_results=5) is True

    def test_is_order_page_after_click(self, concert):
        """After clicking buy, title changes → _is_order_confirmation_page."""
        concert._click_element_safe(*Sel.BUY_BUTTON)
        # The fixture's JS updates title to '订单确认页' on button click
        assert concert._is_order_confirmation_page() is True


def _get_chromedriver():
    """Resolve ChromeDriver path; prefer the project's check_environment."""
    try:
        from check_environment import get_chromedriver_path
        return get_chromedriver_path()
    except Exception:
        # Fallback: try common paths
        import shutil
        for p in [
            "/opt/homebrew/bin/chromedriver",
            "/usr/local/bin/chromedriver",
            shutil.which("chromedriver"),
        ]:
            if p and (os.path.exists(p) or os.path.islink(p)):
                return p
    raise RuntimeError(
        "ChromeDriver not found. Install with: brew install --cask chromedriver"
    )

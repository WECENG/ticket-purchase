# -*- coding: UTF-8 -*-
"""State-machine tests for _poll_buy_button — the core ticket-grabbing loop."""

from unittest.mock import Mock, patch

import pytest

from concert_selectors import Sel
from tests.helpers import make_mock_config


def _build_sequence_mock(return_values):
    """Return a callable that yields successive values from ``return_values``.

    Each call advances an internal index; once exhausted the last value is
    repeated.  If a value is an Exception instance it is *raised* instead of
    returned, matching `Mock(side_effect=[...])` semantics.
    """
    idx = [0]

    def _next(*args, **kwargs):
        result = return_values[min(idx[0], len(return_values) - 1)]
        idx[0] += 1
        if isinstance(result, Exception):
            raise result
        return result

    return _next


class TestPollBuyButton:
    """Unit tests for the _poll_buy_button state machine."""

    # ── helpers ──

    def _mock_confirm(self, concert, sequence):
        concert._is_order_confirmation_page = _build_sequence_mock(sequence)

    def _patch_click_safe(self, concert, side_effect=None):
        concert._click_element_safe = Mock(side_effect=side_effect)

    def _patch_get_text(self, concert, buy_vals, link_vals=None):
        """Mock _get_element_text_safe to distinguish BUY_BUTTON / BUY_LINK."""
        buy_seq = _build_sequence_mock(buy_vals)
        link_seq = _build_sequence_mock(link_vals or [None])

        def mock_get_text(locator, by):
            if by == Sel.BUY_LINK[1]:
                return link_seq()
            return buy_seq()

        concert._get_element_text_safe = mock_get_text

    # ── Scenario 1: direct "立即购买" on first poll ──

    @patch("time.sleep")
    def test_direct_buy_on_first_poll(self, mock_sleep, concert):
        """First poll finds 立即购买 → click → confirm page → commit_order."""
        self._mock_confirm(concert, [False, True])
        self._patch_get_text(concert, ["立即购买"])
        self._patch_click_safe(concert, side_effect=[True])
        concert.commit_order = Mock()
        concert.choice_seat = Mock()
        concert.status = 2

        concert._poll_buy_button()

        concert._click_element_safe.assert_called_once_with(
            *Sel.BUY_BUTTON
        )
        assert concert.status == 3
        concert.commit_order.assert_called_once()

    # ── Scenario 2: "提交缺货登记" → refresh → then ticket opens ──

    @patch("time.sleep")
    def test_out_of_stock_then_opens(self, mock_sleep, concert):
        """缺货登记 → refresh → 立即购买 → confirm page."""
        self._mock_confirm(concert, [False, False, True])
        self._patch_get_text(concert, ["提交缺货登记", "立即购买"])
        self._patch_click_safe(concert, side_effect=[True])
        concert.commit_order = Mock()
        concert.choice_seat = Mock()
        concert.status = 2

        concert._poll_buy_button()

        # After 缺货登记: driver.get(target_url) should be called
        concert.driver.get.assert_called_with(concert.config.target_url)
        assert concert.status == 3
        concert.commit_order.assert_called_once()

    # ── Scenario 3: "选座购买" path ──

    @patch("time.sleep")
    def test_seat_selection_path(self, mock_sleep, concert):
        """选座购买 → click → title becomes 选座购买 → choice_seat."""
        self._mock_confirm(concert, [False, False])
        self._patch_get_text(concert, ["选座购买"])
        self._patch_click_safe(concert, side_effect=[True])
        concert.driver.title = Sel.TITLE_SEAT
        concert.commit_order = Mock()
        concert.choice_seat = Mock()
        concert.status = 2

        concert._poll_buy_button()

        concert._click_element_safe.assert_called_once_with(
            *Sel.BUY_BUTTON
        )
        concert.choice_seat.assert_called_once()
        concert.commit_order.assert_not_called()

    # ── Scenario 4: link-button mode ("不，立即预订") ──

    @patch("time.sleep")
    def test_link_button_mode(self, mock_sleep, concert):
        """Button text not matched but link says 不，立即预订 → click link."""
        self._mock_confirm(concert, [False, True])
        self._patch_get_text(concert, ["其他文本"], ["不，立即预订"])
        self._patch_click_safe(concert, side_effect=[True])

        concert.commit_order = Mock()
        concert.choice_seat = Mock()
        concert.status = 2

        concert._poll_buy_button()

        concert._click_element_safe.assert_called_once_with(
            *Sel.BUY_LINK
        )
        assert concert.status == 3
        concert.commit_order.assert_called_once()

    # ── Scenario 5: _get_element_text_safe raises → loop survives ──

    @patch("time.sleep")
    def test_exception_recovery(self, mock_sleep, concert):
        """Exception in _get_element_text_safe → loop retries → succeeds.

        Uses _patch_get_text so that BUY_LINK is also controlled (returns
        None rather than raising StopIteration from an exhausted list).
        """
        self._mock_confirm(concert, [False, False, False, True])
        self._patch_get_text(
            concert,
            [Exception("element gone"), "立即购买"],
            [None, None],
        )
        self._patch_click_safe(concert, side_effect=[True])
        concert.commit_order = Mock()
        concert.choice_seat = Mock()
        concert.status = 2

        concert._poll_buy_button()

        concert.commit_order.assert_called_once()

    # ── Scenario 6: repeat-click guard ──

    @patch("time.sleep")
    def test_repeat_click_guard(self, mock_sleep, concert):
        """After first click, loop polls but never re-clicks.

        The clicked=True branch uses ``continue``, so after clicking
        the loop only checks ``_is_order_confirmation_page`` and
        ``driver.title`` until either a confirm or seat page appears.
        """
        self._mock_confirm(concert, [False, False, False, True])
        self._patch_get_text(concert, ["立即购买"])
        self._patch_click_safe(concert, side_effect=[True])
        concert.driver.title = "大麦网-商品详情"
        concert.commit_order = Mock()
        concert.choice_seat = Mock()
        concert.status = 2

        concert._poll_buy_button()

        # Only one click despite the polling
        click_calls = concert._click_element_safe.call_count
        assert click_calls == 1, (
            f"Expected 1 click, got {click_calls}"
        )

    # ── Scenario 7: already on confirmation page ──

    @patch("time.sleep")
    def test_already_on_confirm_page(self, mock_sleep, concert):
        """_is_order_confirmation_page returns True immediately → exit."""
        self._mock_confirm(concert, [True])
        concert._get_element_text_safe = Mock()
        self._patch_click_safe(concert)

        concert._poll_buy_button()

        # No clicks, no text checks
        concert._get_element_text_safe.assert_not_called()
        concert._click_element_safe.assert_not_called()

    # ── Scenario 8: after click, page not transitioned → sleep and refresh ──

    @patch("time.sleep")
    def test_post_click_polling_waits(self, mock_sleep, concert):
        """After click but before confirm page loads, loop sleeps + refreshes.

        The bottom ``else`` branch logs "抢票未开始" and calls refresh.
        """
        self._mock_confirm(concert, [False, False, False, False, True])
        self._patch_get_text(concert, ["立即购买"])
        self._patch_click_safe(concert, side_effect=[True])
        concert.driver.title = "not-seat-page"
        concert.commit_order = Mock()
        concert.choice_seat = Mock()
        concert.status = 2

        concert._poll_buy_button()

        # sleep was called (at least once for polling)
        assert mock_sleep.call_count >= 1
        # driver.refresh was called (the else branch)
        concert.driver.refresh.assert_called()
        # Only one click
        assert concert._click_element_safe.call_count == 1

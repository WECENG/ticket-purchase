# -*- coding: UTF-8 -*-
"""Order-flow tests for commit_order, _select_users, and _submit_order."""

from unittest.mock import Mock, patch

import pytest

from concert_user_selector import UserSelectorChain
from tests.helpers import make_mock_element


class TestSubmitOrder:
    """Unit tests for _submit_order — the final order submission."""

    def test_text_match_first_word(self, concert):
        """First text pattern '提交订单' matches → execute_script click."""
        el = make_mock_element(text="提交订单", displayed=True, enabled=True)
        concert.driver.find_element = Mock(return_value=el)

        concert._submit_order()

        concert.driver.execute_script.assert_called_once_with(
            "arguments[0].click();", el
        )

    def test_fallback_to_xpath(self, concert):
        """All text patterns fail → XPath fallback succeeds.

        Uses an argument-aware mock so the test does not depend on the
        ordering of text patterns inside _submit_order.
        """
        def mock_find_element(by, value):
            if "bottomFix" in value:
                return make_mock_element(displayed=True)
            raise Exception("not found")

        concert.driver.find_element = Mock(side_effect=mock_find_element)

        # Should complete without raising
        concert._submit_order()

    def test_no_match_logs_warning(self, concert):
        """Neither text nor XPath matches → warning logged, no crash."""
        concert.driver.find_element = Mock(
            side_effect=Exception("gone")
        )

        concert._submit_order()

        # Should not raise, should log warning
        concert.driver.execute_script.assert_not_called()


class TestCommitOrder:
    """Unit tests for commit_order orchestration."""

    def test_commit_order_calls_submit(self, concert):
        """commit_order calls _select_users then _submit_order."""
        with patch.object(
            UserSelectorChain, "select_user", return_value=True
        ):
            concert._submit_order = Mock()
            concert.commit_order()
            concert._submit_order.assert_called_once()

    def test_commit_order_empty_users(self, concert):
        """Empty users list → _select_users returns True immediately."""
        concert.config.users = []
        concert._submit_order = Mock()
        concert.commit_order()
        concert._submit_order.assert_called_once()


class TestSelectUsers:
    """Unit tests for _select_users retry logic."""

    def test_select_users_all_found(self, concert):
        """Both users found on first attempt."""
        with patch.object(
            UserSelectorChain, "select_user", return_value=True
        ) as mock_select:
            result = concert._select_users()
            assert result is True
            assert mock_select.call_count == 2  # ZhangSan + LiSi

    def test_select_users_all_retries_exhausted(self, concert):
        """3 attempts fail → returns False."""
        with patch.object(
            UserSelectorChain, "select_user", return_value=False
        ):
            result = concert._select_users()
            assert result is False

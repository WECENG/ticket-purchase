"""
Shared pytest fixtures and configuration.
"""
import os
import sys
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch

import pytest

from tests.helpers import make_mock_config

# Ensure damai/ is importable for concert fixtures
_damai_path = Path(__file__).resolve().parent.parent / "damai"
if str(_damai_path) not in sys.path:
    sys.path.insert(0, str(_damai_path))


# ── Integration test toggle ──
def pytest_addoption(parser):
    parser.addoption(
        "--run-integration", action="store_true", default=False,
        help="Run integration tests that require Chrome/ChromeDriver",
    )


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_config() -> dict:
    """Provide a mock configuration for tests."""
    return {
        "username": "test_user",
        "password": "test_password",
        "target_url": "https://example.com",
        "ticket_count": 1,
        "seat_type": "VIP",
        "price_levels": ["580", "380"],
        "dates": ["2024-01-01"],
        "retry_times": 3,
        "timeout": 30,
    }


@pytest.fixture
def mock_selenium_driver():
    """Mock Selenium WebDriver for unit tests."""
    with patch("selenium.webdriver.Chrome") as mock_driver_class:
        mock_driver = Mock()
        mock_driver_class.return_value = mock_driver

        mock_driver.get = Mock()
        mock_driver.find_element = Mock()
        mock_driver.find_elements = Mock()
        mock_driver.quit = Mock()
        mock_driver.current_url = "https://example.com"
        mock_driver.title = "Test Page"

        yield mock_driver


@pytest.fixture
def mock_appium_driver():
    """Mock Appium driver for mobile tests."""
    mock_driver = Mock()
    mock_driver.find_element = Mock()
    mock_driver.find_elements = Mock()
    mock_driver.tap = Mock()
    mock_driver.swipe = Mock()
    mock_driver.quit = Mock()
    yield mock_driver


@pytest.fixture
def sample_html_response() -> str:
    """Provide sample HTML response for parsing tests."""
    return """
    <html>
        <body>
            <div class="ticket-info">
                <span class="price">¥380</span>
                <span class="seat-type">VIP座位</span>
                <button class="buy-btn">立即购买</button>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def mock_time(monkeypatch):
    """Mock time-related functions for deterministic tests."""
    import time

    current_time = 1704067200.0  # 2024-01-01 00:00:00 UTC

    def mock_time_func():
        return current_time

    def mock_sleep(seconds):
        nonlocal current_time
        current_time += seconds

    monkeypatch.setattr(time, "time", mock_time_func)
    monkeypatch.setattr(time, "sleep", mock_sleep)

    return mock_time_func


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch):
    """Reset environment variables for each test."""
    env_vars_to_clear = [
        "DAMAI_USERNAME",
        "DAMAI_PASSWORD",
        "SELENIUM_DRIVER_PATH",
        "APPIUM_SERVER_URL",
    ]
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def mock_file_operations(tmp_path):
    """Provide mocked file operations for tests."""
    def create_test_file(filename: str, content: str = "") -> Path:
        file_path = tmp_path / filename
        file_path.write_text(content)
        return file_path

    return create_test_file


# ── Shared concert fixture ──
@pytest.fixture
def concert():
    """Create a Concert instance with a fully mocked Selenium driver."""
    with patch("check_environment.get_chromedriver_path",
               return_value="/fake/chromedriver"):
        with patch("concert.webdriver.Chrome") as mock_chrome:
            mock_driver = Mock()
            mock_driver.title = "大麦网-商品详情"
            mock_driver.current_url = (
                "https://detail.damai.cn/item.htm?id=123"
            )
            mock_driver.find_element = Mock()
            mock_driver.find_elements = Mock(return_value=[])
            mock_driver.get = Mock()
            mock_driver.quit = Mock()
            mock_driver.refresh = Mock()
            mock_driver.execute_script = Mock()
            mock_chrome.return_value = mock_driver
            from concert import Concert
            return Concert(make_mock_config())


# Pytest configuration hooks
def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

    # Skip integration tests unless --run-integration is set
    if not config.getoption("--run-integration"):
        skip_int = pytest.mark.skip(reason="need --run-integration to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_int)

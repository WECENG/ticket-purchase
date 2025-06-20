"""
Shared pytest fixtures and configuration.
"""
import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch

import pytest


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
        
        # Common WebDriver methods
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
    # Create a mock driver without importing appium
    mock_driver = Mock()
    
    # Common Appium methods
    mock_driver.find_element = Mock()
    mock_driver.find_elements = Mock()
    mock_driver.tap = Mock()
    mock_driver.swipe = Mock()
    mock_driver.quit = Mock()
    
    # Mock the Remote class
    with patch.object(mock_driver, "__class__.__name__", "Remote"):
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
    # Clear any environment variables that might affect tests
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


# Pytest configuration hooks
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers description
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
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
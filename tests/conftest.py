"""Pytest configuration and shared fixtures for Innomight Labs CLI tests."""

import pytest
from typing import Generator
from unittest.mock import Mock, patch


@pytest.fixture
def mock_planner_agent() -> Generator[Mock, None, None]:
    """Mock the planner agent to prevent AWS Bedrock calls."""
    with patch('main.planner_agent') as mock_agent:
        mock_agent.send_message.return_value = "Mocked agent response"
        mock_agent.usage_totals = {'input_tokens': 0, 'output_tokens': 0}
        mock_agent.last_usage = {'input_tokens': 0, 'output_tokens': 0}
        yield mock_agent


@pytest.fixture
def mock_console_print() -> Generator[Mock, None, None]:
    """Mock Rich console.print to capture output."""
    with patch('main.console.print') as mock_print:
        yield mock_print


@pytest.fixture
def mock_prompt() -> Generator[Mock, None, None]:
    """Mock prompt-toolkit prompt function."""
    with patch('main.prompt') as mock_prompt_func:
        yield mock_prompt_func


@pytest.fixture
def mock_display_banner() -> Generator[Mock, None, None]:
    """Mock the display_banner function."""
    with patch('main.display_banner') as mock_banner:
        yield mock_banner


@pytest.fixture
def mock_build_toolbar() -> Generator[Mock, None, None]:
    """Mock the build_bottom_toolbar function."""
    with patch('main.build_bottom_toolbar') as mock_toolbar:
        mock_toolbar.return_value = []
        yield mock_toolbar


@pytest.fixture
def mock_clipboard_manager() -> Generator[Mock, None, None]:
    """Mock ClipboardManager to avoid system clipboard interactions."""
    with patch('main.ClipboardManager') as mock_cm:
        mock_instance = Mock()
        mock_cm.return_value = mock_instance
        yield mock_instance

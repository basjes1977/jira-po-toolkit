"""Shared pytest fixtures for Jira testing."""
import pytest
import os
from pathlib import Path

@pytest.fixture
def mock_jira_env(tmp_path, monkeypatch):
    """Create a temporary .jira_environment file for testing."""
    env_file = tmp_path / ".jira_environment"
    env_file.write_text("""
export JT_JIRA_URL="https://test.atlassian.net"
export JT_JIRA_USERNAME="test@example.com"
export JT_JIRA_PASSWORD="test-api-token-123"
export JT_JIRA_BOARD="42"
export JT_JIRA_FIELD_STORY_POINTS="customfield_10024"
export JT_JIRA_FIELD_EPIC_LINK="customfield_10031"
export JT_JIRA_FIELD_ACCEPTANCE_CRITERIA="customfield_10140"
""")

    # Point jira_config to use this test file
    import jira_config
    monkeypatch.setattr(jira_config, "DEFAULT_ENV_PATH", env_file)

    # Clear cache to force reload with test config
    jira_config.load_jira_env.cache_clear()
    jira_config.get_jira_session.cache_clear()

    return env_file

@pytest.fixture(autouse=True)
def reset_session_cache():
    """Reset session cache between tests to ensure isolation."""
    import jira_config
    if hasattr(jira_config, 'get_jira_session'):
        jira_config.get_jira_session.cache_clear()
    yield
    if hasattr(jira_config, 'get_jira_session'):
        jira_config.get_jira_session.cache_clear()

@pytest.fixture
def mock_responses():
    """Enable responses library for HTTP mocking."""
    import responses as resp_lib
    with resp_lib.RequestsMock() as rsps:
        yield rsps

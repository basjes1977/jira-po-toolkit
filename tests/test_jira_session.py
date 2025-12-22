"""Test session creation and configuration."""
import pytest
from jira_config import get_jira_session, load_jira_env
from requests import Session
from requests.adapters import HTTPAdapter

def test_session_is_singleton(mock_jira_env):
    """Verify get_jira_session returns same instance (connection pooling)."""
    session1 = get_jira_session()
    session2 = get_jira_session()
    assert session1 is session2, "Session should be singleton"

def test_session_is_requests_session(mock_jira_env):
    """Verify returned object is a requests.Session."""
    session = get_jira_session()
    assert isinstance(session, Session)

def test_session_has_auth(mock_jira_env):
    """Verify session has authentication configured from .jira_environment."""
    session = get_jira_session()
    assert session.auth is not None
    assert session.auth == ("test@example.com", "test-api-token-123")

def test_session_has_retry_adapter(mock_jira_env):
    """Verify session has HTTPAdapter with retry logic mounted."""
    session = get_jira_session()
    adapter = session.get_adapter("https://test.atlassian.net")

    assert isinstance(adapter, HTTPAdapter)
    assert adapter.max_retries is not None
    assert adapter.max_retries.total == 4
    assert adapter.max_retries.backoff_factor == 1.0
    assert 500 in adapter.max_retries.status_forcelist
    assert 429 in adapter.max_retries.status_forcelist

def test_session_connection_pooling(mock_jira_env):
    """Verify connection pooling parameters are set."""
    session = get_jira_session()
    adapter = session.get_adapter("https://test.atlassian.net")
    assert adapter._pool_connections == 10
    assert adapter._pool_maxsize == 20

def test_session_verify_ssl_default(mock_jira_env, monkeypatch):
    """Verify SSL verification defaults to True when not configured."""
    # Remove SSL config from environment
    monkeypatch.delenv("JT_SSL_VERIFY", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)

    # Clear cache and recreate session
    import jira_config
    jira_config.get_jira_session.cache_clear()

    session = get_jira_session()
    assert session.verify is True

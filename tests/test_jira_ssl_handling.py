"""Test SSL verification configuration modes."""
import pytest
from pathlib import Path
from jira_config import get_jira_session, get_ssl_verify

def test_ssl_verify_true(mock_jira_env, monkeypatch):
    """Test SSL verification enabled explicitly."""
    monkeypatch.setenv("JT_SSL_VERIFY", "true")

    # Clear cache
    import jira_config
    jira_config.get_jira_session.cache_clear()

    assert get_ssl_verify() is True
    session = get_jira_session()
    assert session.verify is True

def test_ssl_verify_false(mock_jira_env, monkeypatch):
    """Test SSL verification disabled (not recommended)."""
    monkeypatch.setenv("JT_SSL_VERIFY", "false")

    import jira_config
    jira_config.get_jira_session.cache_clear()

    assert get_ssl_verify() is False
    session = get_jira_session()
    assert session.verify is False

def test_ssl_verify_custom_cert(mock_jira_env, tmp_path, monkeypatch):
    """Test SSL verification with custom certificate (e.g., Zscaler)."""
    cert_file = tmp_path / "Zscaler.pem"
    cert_file.write_text("-----BEGIN CERTIFICATE-----\nFAKE CERT FOR TESTING\n-----END CERTIFICATE-----")

    monkeypatch.setenv("JT_SSL_VERIFY", str(cert_file))

    import jira_config
    # Note: get_ssl_verify() doesn't have cache, only get_jira_session() does
    jira_config.get_jira_session.cache_clear()

    ssl_verify = get_ssl_verify()
    assert ssl_verify == str(cert_file.resolve())

    session = get_jira_session()
    assert session.verify == str(cert_file.resolve())

def test_ssl_verify_nonexistent_cert_fallback(mock_jira_env, monkeypatch, capsys):
    """Test fallback to True when cert path doesn't exist."""
    monkeypatch.setenv("JT_SSL_VERIFY", "/nonexistent/Zscaler.pem")

    # Note: get_ssl_verify() doesn't have cache, it reads from environment each time
    # Should print warning and return True
    result = get_ssl_verify()
    assert result is True

    captured = capsys.readouterr()
    assert "Warning" in captured.out
    assert "does not exist" in captured.out

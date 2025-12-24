"""
Tests for jira_security module - JQL sanitization and log redaction.
"""

import pytest
import logging
from jira_security import (
    sanitize_jql_value,
    sanitize_jql_list,
    SensitiveDataFilter,
    get_safe_jql_logger
)


class TestSanitizeJQLValue:
    """Test JQL value sanitization."""

    def test_valid_issue_key(self):
        """Valid issue keys should pass through unchanged."""
        assert sanitize_jql_value("PROJ-123", "key") == "PROJ-123"
        assert sanitize_jql_value("ABC-1", "key") == "ABC-1"
        assert sanitize_jql_value("EMSS-999", "key") == "EMSS-999"

    def test_invalid_issue_key_format(self):
        """Invalid issue key formats should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid issue key format"):
            sanitize_jql_value("proj-123", "key")  # lowercase

        with pytest.raises(ValueError, match="Invalid issue key format"):
            sanitize_jql_value("PROJ123", "key")  # no hyphen

        with pytest.raises(ValueError, match="Invalid issue key format"):
            sanitize_jql_value("PROJ-", "key")  # no number

    def test_sql_injection_attempt(self):
        """SQL-style injection attempts should be blocked."""
        with pytest.raises(ValueError, match="SQL comment markers"):
            sanitize_jql_value("PROJ-123--", "key")

        with pytest.raises(ValueError, match="SQL comment markers"):
            sanitize_jql_value("PROJ-123/*comment*/", "key")

    def test_quote_injection_attempt(self):
        """Excessive quotes should be blocked."""
        with pytest.raises(ValueError, match="excessive quotes"):
            sanitize_jql_value('PROJ-123"""', "key")

        with pytest.raises(ValueError, match="excessive quotes"):
            sanitize_jql_value("PROJ-123'''", "key")

    def test_valid_labels(self):
        """Valid labels should pass through."""
        assert sanitize_jql_value("NLMS", "label") == "NLMS"
        assert sanitize_jql_value("S&A-MPC", "label") == "S&A-MPC"
        assert sanitize_jql_value("my_label", "label") == "my_label"
        assert sanitize_jql_value("label-123", "label") == "label-123"

    def test_invalid_label_characters(self):
        """Labels with invalid characters should be rejected."""
        with pytest.raises(ValueError, match="Invalid label format"):
            sanitize_jql_value("label with spaces", "label")

        with pytest.raises(ValueError, match="Invalid label format"):
            sanitize_jql_value("label@special", "label")

        with pytest.raises(ValueError, match="Invalid label format"):
            sanitize_jql_value("label;drop", "label")

    def test_empty_value(self):
        """Empty values should raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            sanitize_jql_value("", "key")

        with pytest.raises(ValueError, match="empty"):
            sanitize_jql_value("   ", "key")

    def test_none_value(self):
        """None values should raise ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            sanitize_jql_value(None, "key")


class TestSanitizeJQLList:
    """Test JQL list sanitization."""

    def test_valid_key_list(self):
        """Valid key lists should pass through."""
        result = sanitize_jql_list(["PROJ-1", "PROJ-2", "ABC-123"], "key")
        assert result == ["PROJ-1", "PROJ-2", "ABC-123"]

    def test_empty_list(self):
        """Empty lists should return empty."""
        assert sanitize_jql_list([], "key") == []

    def test_invalid_item_in_list(self):
        """Lists with invalid items should raise ValueError."""
        with pytest.raises(ValueError, match="Failed to sanitize"):
            sanitize_jql_list(["PROJ-1", "invalid--key"], "key")

    def test_label_list(self):
        """Label lists should be sanitized."""
        result = sanitize_jql_list(["NLMS", "IEMS", "S&A-MPC"], "label")
        assert result == ["NLMS", "IEMS", "S&A-MPC"]


class TestSensitiveDataFilter:
    """Test sensitive data redaction in logs."""

    def test_api_token_redaction(self):
        """API tokens should be redacted."""
        filter_obj = SensitiveDataFilter()

        text = "Using token ATATT3xFfGF0LxNqJVbpSOQ4OkdCWkFY to authenticate"
        redacted = filter_obj._redact(text)

        assert "ATATT" not in redacted
        assert "[REDACTED-TOKEN]" in redacted
        assert "to authenticate" in redacted  # Other text preserved

    def test_email_redaction(self):
        """Email addresses should be redacted."""
        filter_obj = SensitiveDataFilter()

        text = "User user@example.com made a request"
        redacted = filter_obj._redact(text)

        assert "user@example.com" not in redacted
        assert "[REDACTED-EMAIL]" in redacted
        assert "made a request" in redacted

    def test_issue_key_preservation(self):
        """Issue keys should NOT be redacted."""
        filter_obj = SensitiveDataFilter()

        text = "Processing issue PROJ-123"
        redacted = filter_obj._redact(text)

        # Issue key should remain
        assert "PROJ-123" in redacted

    def test_long_alphanumeric_redaction(self):
        """Long alphanumeric strings should be redacted (potential credentials)."""
        filter_obj = SensitiveDataFilter()

        text = "Secret: abc123def456ghi789jkl012mno345pqr678"
        redacted = filter_obj._redact(text)

        # Long string should be redacted
        assert "abc123def456ghi789jkl012mno345pqr678" not in redacted
        assert "[REDACTED]" in redacted

    def test_log_record_filtering(self):
        """LogRecord messages should be filtered."""
        filter_obj = SensitiveDataFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=1,
            msg="API token ATATT123xyz456 used",
            args=(),
            exc_info=None
        )

        # Filter should return True (don't suppress)
        assert filter_obj.filter(record) is True

        # Message should be redacted
        assert "ATATT123xyz456" not in record.msg
        assert "[REDACTED-TOKEN]" in record.msg

    def test_integer_args_preserved(self):
        """Integer arguments should not be converted to strings (for %d formatting)."""
        filter_obj = SensitiveDataFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=1,
            msg="Fetching %d items with %s status",
            args=(42, "active"),
            exc_info=None
        )

        # Filter should return True
        assert filter_obj.filter(record) is True

        # Integer should remain an integer (not converted to string)
        assert isinstance(record.args[0], int)
        assert record.args[0] == 42

        # String should still be redacted if needed
        assert isinstance(record.args[1], str)
        assert record.args[1] == "active"

        # The formatted message should work with %d
        formatted = record.msg % record.args
        assert formatted == "Fetching 42 items with active status"


class TestGetSafeJQLLogger:
    """Test logger creation with sensitive data filtering."""

    def test_logger_has_filter(self):
        """Logger should have SensitiveDataFilter attached."""
        logger = get_safe_jql_logger("test_logger")

        # Check filter is attached
        filters = [f for f in logger.filters if isinstance(f, SensitiveDataFilter)]
        assert len(filters) == 1

    def test_logger_no_duplicate_filters(self):
        """Calling get_safe_jql_logger twice shouldn't add duplicate filters."""
        logger1 = get_safe_jql_logger("test_logger2")
        logger2 = get_safe_jql_logger("test_logger2")

        # Should still only have one filter
        filters = [f for f in logger2.filters if isinstance(f, SensitiveDataFilter)]
        assert len(filters) == 1

    def test_logger_redacts_in_practice(self, caplog):
        """Logger should actually redact sensitive data when logging."""
        logger = get_safe_jql_logger("test_logger3")
        logger.setLevel(logging.INFO)

        with caplog.at_level(logging.INFO, logger="test_logger3"):
            logger.info("API token: ATATT123456789abc")

        # Check log output
        assert len(caplog.records) == 1
        assert "ATATT123456789abc" not in caplog.text
        assert "[REDACTED-TOKEN]" in caplog.text


class TestTextValueSanitization:
    """Test text value sanitization (free-form text)."""

    def test_valid_text(self):
        """Simple text should pass through."""
        result = sanitize_jql_value("simple text", "text")
        assert "simple text" in result

    def test_text_with_jql_operators(self):
        """Text with JQL operators should be blocked."""
        with pytest.raises(ValueError, match="JQL operator"):
            sanitize_jql_value("text AND malicious", "text")

        with pytest.raises(ValueError, match="JQL operator"):
            sanitize_jql_value("text OR attack", "text")

        with pytest.raises(ValueError, match="JQL operator"):
            sanitize_jql_value("text (parentheses)", "text")

    def test_quote_escaping(self):
        """Quotes in text should be escaped."""
        result = sanitize_jql_value("text with 'quotes'", "text")
        assert "\\'" in result

    def test_unknown_value_type(self):
        """Unknown value types should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown value_type"):
            sanitize_jql_value("test", "unknown_type")

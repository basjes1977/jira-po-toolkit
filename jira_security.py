"""
Security utilities for Jira API interactions.

Provides JQL injection prevention and sensitive data redaction for logging.
"""

import re
import logging
from typing import List


def sanitize_jql_value(value: str, value_type: str = 'key') -> str:
    """Validate and sanitize JQL input to prevent injection attacks.

    Args:
        value: Raw input value (e.g., epic key, label, issue key)
        value_type: Type of value being sanitized:
            - 'key': Jira issue key (e.g., PROJ-123)
            - 'label': Label/tag name
            - 'text': Free-form text (most restrictive)

    Returns:
        Sanitized value safe for JQL interpolation

    Raises:
        ValueError: If value contains malicious patterns or doesn't match expected format

    Examples:
        >>> sanitize_jql_value("PROJ-123", "key")
        'PROJ-123'
        >>> sanitize_jql_value("my-label", "label")
        'my-label'
        >>> sanitize_jql_value("PROJ-123'; DROP TABLE", "key")
        Traceback (most recent call last):
        ValueError: Invalid issue key format...
    """
    if not value or not isinstance(value, str):
        raise ValueError(f"Value must be a non-empty string, got: {type(value)}")

    value = value.strip()

    if not value:
        raise ValueError("Value cannot be empty or whitespace only")

    # Check for SQL-style comments (common injection technique)
    if '--' in value or '/*' in value or '*/' in value:
        raise ValueError(f"Invalid value '{value}': contains SQL comment markers")

    # Check for multiple quotes (common injection technique)
    if value.count('"') > 2 or value.count("'") > 2:
        raise ValueError(f"Invalid value '{value}': excessive quotes detected")

    # Validate based on value type
    if value_type == 'key':
        # Jira issue keys: PROJECT-123
        pattern = r'^[A-Z][A-Z0-9]*-\d+$'
        if not re.match(pattern, value):
            raise ValueError(
                f"Invalid issue key format: '{value}'. "
                f"Expected format: UPPERCASE-NUMBER (e.g., PROJ-123)"
            )
        return value

    elif value_type == 'label':
        # Labels: alphanumeric, hyphen, underscore, ampersand (for S&A_MGT, S&A-MPC)
        pattern = r'^[a-zA-Z0-9\-_&]+$'
        if not re.match(pattern, value):
            raise ValueError(
                f"Invalid label format: '{value}'. "
                f"Labels can only contain letters, numbers, hyphens, underscores, and ampersands"
            )
        return value

    elif value_type == 'text':
        # Free-form text: block special JQL operators and dangerous chars
        dangerous_patterns = [
            r'\bAND\b', r'\bOR\b', r'\bNOT\b', r'\bIN\b', r'\bIS\b',
            r'\bWAS\b', r'\bWAS\s+IN\b', r'\bIS\s+NOT\b',
            r'[<>=!~]', r'[()]', r'[\[\]]'
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(
                    f"Invalid text value '{value}': contains JQL operator or special character"
                )
        # Escape quotes
        value = value.replace('"', '\\"').replace("'", "\\'")
        return value

    else:
        raise ValueError(f"Unknown value_type: '{value_type}'. Use 'key', 'label', or 'text'")


def sanitize_jql_list(values: List[str], value_type: str = 'key') -> List[str]:
    """Sanitize a list of values for JQL IN clauses.

    Args:
        values: List of raw input values
        value_type: Type of values (same as sanitize_jql_value)

    Returns:
        List of sanitized values

    Raises:
        ValueError: If any value fails sanitization

    Example:
        >>> sanitize_jql_list(["PROJ-1", "PROJ-2"], "key")
        ['PROJ-1', 'PROJ-2']
        >>> sanitize_jql_list(["PROJ-1", "malicious'; --"], "key")
        Traceback (most recent call last):
        ValueError: Invalid issue key format...
    """
    if not values:
        return []

    sanitized = []
    for value in values:
        try:
            sanitized.append(sanitize_jql_value(value, value_type))
        except ValueError as e:
            # Re-raise with context about which value failed
            raise ValueError(f"Failed to sanitize value in list: {e}") from e

    return sanitized


class SensitiveDataFilter(logging.Filter):
    """Logging filter to redact sensitive data from log messages.

    Automatically redacts:
    - API tokens (pattern: ATATT followed by alphanumeric/special chars)
    - Email addresses
    - Long alphanumeric strings that might be credentials
    - Authorization headers

    Usage:
        >>> logger = logging.getLogger('myapp')
        >>> logger.addFilter(SensitiveDataFilter())
    """

    # Regex patterns for sensitive data
    API_TOKEN_PATTERN = re.compile(r'ATATT[a-zA-Z0-9_\-]+')
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    LONG_ALPHANUM_PATTERN = re.compile(r'\b[a-zA-Z0-9]{24,}\b')

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive data from the log record.

        Args:
            record: Log record to filter

        Returns:
            True (always - we modify but don't suppress)
        """
        # Redact message
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)

        # Redact args (if any)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact(str(arg)) for arg in record.args)

        return True

    def _redact(self, text: str) -> str:
        """Redact sensitive patterns from text.

        Args:
            text: Text to redact

        Returns:
            Text with sensitive data replaced
        """
        if not isinstance(text, str):
            return text

        # Redact API tokens
        text = self.API_TOKEN_PATTERN.sub('[REDACTED-TOKEN]', text)

        # Redact email addresses
        text = self.EMAIL_PATTERN.sub('[REDACTED-EMAIL]', text)

        # Redact long alphanumeric strings (potential credentials/tokens)
        # But preserve issue keys (format: PROJ-123)
        def replace_if_not_issue_key(match):
            value = match.group(0)
            # Don't redact if it looks like an issue key
            if re.match(r'^[A-Z]+-\d+$', value):
                return value
            return '[REDACTED]'

        text = self.LONG_ALPHANUM_PATTERN.sub(replace_if_not_issue_key, text)

        return text


def get_safe_jql_logger(name: str) -> logging.Logger:
    """Return a logger with sensitive data filtering enabled.

    The logger will automatically redact API tokens, emails, and other
    sensitive data from all log messages.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance with SensitiveDataFilter attached

    Example:
        >>> logger = get_safe_jql_logger(__name__)
        >>> logger.info("API token: ATATT123abc")  # Logs: "API token: [REDACTED-TOKEN]"
    """
    logger = logging.getLogger(name)

    # Check if filter already added (avoid duplicates)
    has_filter = any(isinstance(f, SensitiveDataFilter) for f in logger.filters)
    if not has_filter:
        logger.addFilter(SensitiveDataFilter())

    return logger

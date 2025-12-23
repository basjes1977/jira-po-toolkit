"""
Shared helpers for loading Jira configuration from .jira_environment.
Centralizes the parsing logic that multiple scripts previously duplicated.
"""

from __future__ import annotations

import os
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_PATH = BASE_DIR / ".jira_environment"


def _parse_line(line: str, data: Dict[str, str]) -> None:
    """Parse a single export-style line into the provided dict."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()
    if "=" not in stripped:
        return
    key, value = stripped.split("=", 1)
    data[key.strip()] = value.strip().strip('"').strip("'")


@lru_cache(maxsize=4)
def load_jira_env(env_path: Optional[Path] = None) -> Dict[str, str]:
    """Return the parsed Jira environment variables from .jira_environment."""
    path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    env: Dict[str, str] = {}
    if path.exists():
        with path.open() as fh:
            for line in fh:
                _parse_line(line, env)
    return env


def get_jira_setting(key: str, default: Optional[str] = None, env_path: Optional[Path] = None) -> Optional[str]:
    """Convenience accessor for a single config value."""
    env = load_jira_env(env_path=env_path)
    return env.get(key, default)


def get_ssl_verify() -> Union[bool, str]:
    """Return the SSL verification setting for requests.

    Returns:
        - True: Use standard SSL verification (default)
        - str: Path to custom CA bundle (e.g., Zscaler certificate)

    Raises:
        ValueError: If SSL verification is disabled (no longer supported for security)

    Checks in order:
        1. JT_SSL_VERIFY environment variable (set by jpt_menu.py) - HIGHEST PRIORITY
        2. JT_SSL_VERIFY from .jira_environment file
        3. REQUESTS_CA_BUNDLE environment variable (standard requests library var) - LOWEST PRIORITY
        4. Default to True (standard SSL verification)
    """
    # PRIORITY 1: Check JT_SSL_VERIFY environment variable (set by menu or user)
    ssl_verify = os.environ.get('JT_SSL_VERIFY')

    # PRIORITY 2: Fall back to .jira_environment file
    if not ssl_verify:
        ssl_verify = get_jira_setting('JT_SSL_VERIFY')

    # PRIORITY 3: Fall back to REQUESTS_CA_BUNDLE (shell environment)
    # Note: Only use this if nothing else is set, since shell settings can be stale
    if not ssl_verify:
        ssl_verify = os.environ.get('REQUESTS_CA_BUNDLE')

    # Default to True if nothing is set
    if not ssl_verify:
        return True

    # Parse the value
    ssl_verify_lower = ssl_verify.strip().lower()

    # Check for boolean false - NO LONGER SUPPORTED
    if ssl_verify_lower in ('false', '0', 'no', 'off', 'disabled'):
        raise ValueError(
            "SSL verification cannot be disabled for security reasons.\n"
            "\n"
            "Options:\n"
            "  1. Set JT_SSL_VERIFY=true for standard verification\n"
            "  2. Set JT_SSL_VERIFY=/path/to/cert.pem for custom CA bundle (e.g., Zscaler)\n"
            "  3. Remove JT_SSL_VERIFY to use default verification\n"
            "\n"
            "Update your .jira_environment file or environment variable accordingly."
        )

    # Check for boolean true
    if ssl_verify_lower in ('true', '1', 'yes', 'on', 'enabled'):
        return True

    # Otherwise treat as file path - expand ~ and make absolute
    cert_path = Path(ssl_verify).expanduser()
    if not cert_path.is_absolute():
        # If it's a relative path, try to resolve it from the script directory
        cert_path = BASE_DIR / cert_path

    if cert_path.exists():
        return str(cert_path.resolve())

    # If path doesn't exist, log warning and default to True
    print(f"Warning: SSL certificate path does not exist: {cert_path}")
    print("Falling back to standard SSL verification.")
    return True


@lru_cache(maxsize=1)
def get_jira_session() -> requests.Session:
    """Return a configured requests.Session for Jira API calls.

    Features:
    - Automatic retry logic for 5xx errors, network failures, rate limits
    - Pre-configured authentication from .jira_environment
    - SSL verification based on get_ssl_verify()
    - Connection pooling for performance (10 connections, 20 max)
    - Exponential backoff: 1s, 2s, 4s, 8s (4 retries)

    Returns:
        Configured requests.Session instance (singleton per process)

    Example:
        >>> session = get_jira_session()
        >>> resp = session.get(url, timeout=15)
    """
    session = requests.Session()

    # Configure retry logic with urllib3
    retry_strategy = Retry(
        total=4,                      # Max retry attempts (matches current jira_get)
        backoff_factor=1.0,           # Exponential: 1s, 2s, 4s, 8s
        status_forcelist=[500, 502, 503, 504, 429],  # Server errors + rate limit
        allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        raise_on_status=False,        # Let caller handle HTTP errors
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,    # Number of connection pools
        pool_maxsize=20         # Connections per pool
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Configure authentication
    env = load_jira_env()
    username = env.get("JT_JIRA_USERNAME")
    api_token = env.get("JT_JIRA_PASSWORD")
    if username and api_token:
        session.auth = (username, api_token)

    # Configure SSL verification
    session.verify = get_ssl_verify()

    import logging
    logger = logging.getLogger(__name__)
    logger.debug("Initialized Jira session with retry logic and connection pooling")

    return session

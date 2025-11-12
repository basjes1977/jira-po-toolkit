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
        - False: Disable SSL verification (not recommended)
        - str: Path to custom CA bundle (e.g., Zscaler certificate)

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

    # Check for boolean false
    if ssl_verify_lower in ('false', '0', 'no', 'off', 'disabled'):
        # Suppress InsecureRequestWarning when SSL verification is disabled
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass
        return False

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

"""
Shared helpers for loading Jira configuration from .jira_environment.
Centralizes the parsing logic that multiple scripts previously duplicated.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

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

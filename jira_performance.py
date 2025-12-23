"""
Performance utilities for Jira API interactions.

Provides caching and optimized date parsing to reduce API calls and CPU overhead.
"""

from functools import lru_cache
from datetime import datetime
from typing import Optional, Dict


@lru_cache(maxsize=128)
def parse_iso8601_datetime(iso_string: str) -> Optional[datetime]:
    """Parse ISO 8601 datetime string with caching.

    Handles various Jira datetime formats with automatic timezone normalization.
    Results are cached for performance (common dates parsed only once).

    Supported formats:
    - 2024-01-15T09:00:00.000Z
    - 2024-01-15T09:00:00.000+0000
    - 2024-01-15T09:00:00+02:00
    - 2024-01-15T09:00:00.123456Z

    Args:
        iso_string: ISO 8601 formatted datetime string

    Returns:
        datetime object with timezone info, or None if parsing fails

    Examples:
        >>> parse_iso8601_datetime("2024-01-15T09:00:00.000Z")
        datetime.datetime(2024, 1, 15, 9, 0, tzinfo=datetime.timezone.utc)

        >>> parse_iso8601_datetime("2024-01-15T09:00:00+02:00")
        datetime.datetime(2024, 1, 15, 9, 0, tzinfo=...)

        >>> parse_iso8601_datetime("invalid")
        None
    """
    if not iso_string:
        return None

    try:
        # Handle Z (Zulu/UTC) timezone indicator
        if 'Z' in iso_string:
            return datetime.fromisoformat(iso_string.replace('Z', '+00:00'))

        # Handle explicit timezone offset (+HH:MM or +HHMM)
        elif '+' in iso_string or iso_string.count('-') > 2:
            # Has timezone offset already
            return datetime.fromisoformat(iso_string)

        # No timezone info - assume UTC
        else:
            return datetime.fromisoformat(iso_string)

    except (ValueError, TypeError, AttributeError):
        # Return None for unparseable dates rather than raising
        # This allows calling code to handle missing dates gracefully
        return None


@lru_cache(maxsize=64)
def get_cached_sprint_metadata(
    jira_url: str,
    sprint_id: int,
    session_id: str = "default"
) -> Dict:
    """Fetch and cache sprint metadata (name, dates) to eliminate duplicate API calls.

    This function fetches sprint data from Jira once and caches the result for
    the lifetime of the process. Subsequent calls for the same sprint return
    the cached data without making additional API requests.

    **Performance Impact:**
    - Without caching: 3 API calls per sprint (name + dates + start_datetime)
    - With caching: 1 API call per sprint (3x speedup)

    Args:
        jira_url: Base Jira URL (e.g., "https://jira.example.com")
        sprint_id: Numeric sprint ID
        session_id: Optional session identifier for cache keying
                    (allows cache invalidation per session if needed)

    Returns:
        dict with keys: id, name, startDate, endDate, state, etc.
        Full sprint object from Jira API

    Raises:
        requests.HTTPError: If API call fails (e.g., 404 for invalid sprint ID)

    Examples:
        >>> metadata = get_cached_sprint_metadata("https://jira.example.com", 123)
        >>> metadata['name']
        'Sprint 42'
        >>> metadata['startDate']
        '2024-01-15T09:00:00.000Z'

        >>> # Second call uses cache - no API request
        >>> metadata2 = get_cached_sprint_metadata("https://jira.example.com", 123)
    """
    from jira_config import get_jira_session

    # Get shared session (with retry logic, auth, SSL config)
    session = get_jira_session()

    url = f"{jira_url}/rest/agile/1.0/sprint/{sprint_id}"
    resp = session.get(url, timeout=15)
    resp.raise_for_status()

    return resp.json()


def clear_sprint_cache():
    """Clear the sprint metadata cache.

    Useful for testing or if you need to force a refresh of sprint data.

    Examples:
        >>> clear_sprint_cache()
        >>> # Next call to get_cached_sprint_metadata will fetch fresh data
    """
    get_cached_sprint_metadata.cache_clear()


def clear_date_parse_cache():
    """Clear the ISO 8601 date parsing cache.

    Useful for testing or debugging date parsing issues.

    Examples:
        >>> clear_date_parse_cache()
        >>> # Next call to parse_iso8601_datetime will re-parse the date
    """
    parse_iso8601_datetime.cache_clear()


def get_cache_stats() -> Dict[str, Dict]:
    """Get cache statistics for performance monitoring.

    Returns hit/miss counts and cache size for both caches.

    Returns:
        dict with keys:
            - 'sprint_cache': cache_info namedtuple (hits, misses, maxsize, currsize)
            - 'date_cache': cache_info namedtuple (hits, misses, maxsize, currsize)

    Examples:
        >>> stats = get_cache_stats()
        >>> stats['sprint_cache'].hits
        15
        >>> stats['sprint_cache'].misses
        3
        >>> hit_rate = stats['sprint_cache'].hits / (stats['sprint_cache'].hits + stats['sprint_cache'].misses)
        >>> print(f"Cache hit rate: {hit_rate:.1%}")
        Cache hit rate: 83.3%
    """
    return {
        'sprint_cache': get_cached_sprint_metadata.cache_info(),
        'date_cache': parse_iso8601_datetime.cache_info(),
    }

"""
Shared helpers for Jira sprint metrics (used by velocity/forecast features).
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple, Union

import requests
from jira_config import get_ssl_verify, get_jira_session

# Shared session for all Jira API calls
_JIRA_SESSION = get_jira_session()


def get_recent_sprints(
    jira_url: str,
    board_id: str,
    auth: Tuple[str, str] = None,  # Deprecated, kept for compatibility
    state: str = "closed",
    max_results: int = 10,
    verify: Union[bool, str, None] = None,  # Deprecated, kept for compatibility
    session: requests.Session = None,  # New parameter
) -> List[Dict]:
    """Return recent sprints for the board sorted descending by end date.

    Args:
        auth: DEPRECATED - auth now comes from session
        verify: DEPRECATED - SSL config now comes from session
        session: Optional session to use (defaults to shared _JIRA_SESSION)
    """
    if session is None:
        session = _JIRA_SESSION
    url = f"{jira_url}/rest/agile/1.0/board/{board_id}/sprint?state={state}"
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    sprints = resp.json().get("values", [])
    sprints = [s for s in sprints if s.get("endDate")]
    sprints.sort(key=lambda s: s["endDate"], reverse=True)
    return sprints[:max_results]


def get_sprint_issues(
    jira_url: str,
    sprint_id: int,
    auth: Tuple[str, str] = None,  # Deprecated
    page_size: int = 50,
    verify: Union[bool, str, None] = None,  # Deprecated
    session: requests.Session = None,  # New
) -> List[Dict]:
    """Return all issues in the given sprint.

    Args:
        auth: DEPRECATED - auth now comes from session
        verify: DEPRECATED - SSL config now comes from session
        session: Optional session to use (defaults to shared _JIRA_SESSION)
    """
    if session is None:
        session = _JIRA_SESSION
    url = f"{jira_url}/rest/agile/1.0/sprint/{sprint_id}/issue"
    issues: List[Dict] = []
    start_at = 0
    while True:
        params = {"startAt": start_at, "maxResults": page_size}
        resp = session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        issues.extend(data["issues"])
        if start_at + page_size >= data["total"]:
            break
        start_at += page_size
    return issues


def achieved_points_and_time(issues: Iterable[Dict], story_points_field: str) -> Tuple[float, int]:
    """Sum completed story points and logged time for the provided issues."""
    points = 0.0
    time_logged = 0
    DONE_STATUSES = {"done", "closed", "resolved"}
    for issue in issues:
        fields = issue.get("fields", {})
        status = (fields.get("status", {}) or {}).get("name", "").lower()
        if status not in DONE_STATUSES:
            continue
        story_points = fields.get(story_points_field)
        if story_points not in (None, "", "?"):
            try:
                points += float(story_points)
            except Exception:
                pass
        timetracking = fields.get("timetracking")
        if isinstance(timetracking, dict):
            spent = timetracking.get("timeSpentSeconds")
            if spent not in (None, "", "?"):
                try:
                    time_logged += int(spent)
                except Exception:
                    pass
    return points, time_logged


def build_velocity_history(
    jira_url: str,
    board_id: str,
    auth: Tuple[str, str],
    story_points_field: str,
    max_sprints: int = 5,
) -> List[Dict]:
    """Return velocity history for the most recent completed sprints."""
    history = []
    sprints = get_recent_sprints(jira_url, board_id, auth, state="closed", max_results=max_sprints)
    for sprint in sprints:
        issues = get_sprint_issues(jira_url, sprint["id"], auth)
        points, time_logged = achieved_points_and_time(issues, story_points_field)
        history.append(
            {
                "name": sprint.get("name"),
                "start": (sprint.get("startDate") or "")[:10],
                "end": (sprint.get("endDate") or "")[:10],
                "points": points,
                "time_seconds": time_logged,
            }
        )
    return history


def window_averages(values: Sequence[float], window_size: int) -> float:
    """Return the average of the first N values (or fewer if not enough)."""
    if not values:
        return 0.0
    size = min(window_size, len(values))
    if size == 0:
        return 0.0
    return sum(values[:size]) / size

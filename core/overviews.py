"""
Core overview logic for JiraPresentationTool.

This module provides the business logic for fetching blocked and on-hold stories.
It can be used by both the CLI and Flask web UI.
"""

import logging
from typing import Dict, List, Any, Optional, Callable

from jira_config import load_jira_env, get_jira_session

# Set up logging
logger = logging.getLogger(__name__)

# Load Jira environment at module level for performance
JIRA_ENV = load_jira_env()
JIRA_URL = JIRA_ENV.get("JT_JIRA_URL", "https://equinixjira.atlassian.net/").rstrip("/")
BOARD_ID = JIRA_ENV.get("JT_JIRA_BOARD")

# Shared session for all Jira API calls
_JIRA_SESSION = get_jira_session()


def get_blocked_stories(
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """Fetch stories that are blocked by another work item.

    Args:
        progress_callback: Optional callback for progress updates

    Returns:
        dict: {
            'success': bool,
            'stories': List of blocked story dicts with blocker info,
            'count': int,
            'error': str or None
        }
    """
    def update_progress(msg: str):
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

    try:
        update_progress("Fetching blocked stories...")

        url = f"{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/issue"
        issues = []
        start_at = 0

        while True:
            params = {
                "jql": "issuetype = Story AND issueLinkType = 'is blocked by'",
                "startAt": start_at,
                "maxResults": 50,
                "fields": "summary,labels,assignee,issuelinks"
            }
            resp = _JIRA_SESSION.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            issues.extend(data["issues"])
            if start_at + 50 >= data["total"]:
                break
            start_at += 50

        # Process issues to extract blocker information
        blocked_stories = []
        for issue in issues:
            fields = issue["fields"]

            # Find all 'is blocked by' links
            blockers = []
            for link in fields.get("issuelinks", []):
                if link.get("type", {}).get("inward", "").lower() == "is blocked by":
                    blocker = link.get("inwardIssue", {}).get("key")
                    if blocker:
                        blockers.append(blocker)

            # Only include stories that actually have blockers
            if blockers:
                assignee = fields.get("assignee")
                blocked_stories.append({
                    'key': issue['key'],
                    'summary': fields.get("summary", ""),
                    'labels': fields.get("labels", []),
                    'assignee': assignee.get("displayName") if assignee and isinstance(assignee, dict) else "Unassigned",
                    'blockers': blockers,
                    'url': f"{JIRA_URL}/browse/{issue['key']}"
                })

        update_progress(f"Found {len(blocked_stories)} blocked stories")

        return {
            'success': True,
            'stories': blocked_stories,
            'count': len(blocked_stories),
            'error': None
        }

    except Exception as e:
        logger.exception("Error fetching blocked stories")
        return {
            'success': False,
            'stories': [],
            'count': 0,
            'error': str(e)
        }


def get_on_hold_stories(
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """Fetch stories with status 'On hold'.

    Args:
        progress_callback: Optional callback for progress updates

    Returns:
        dict: {
            'success': bool,
            'stories': List of on-hold story dicts,
            'count': int,
            'error': str or None
        }
    """
    def update_progress(msg: str):
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

    try:
        update_progress("Fetching on-hold stories...")

        url = f"{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/issue"
        issues = []
        start_at = 0

        while True:
            params = {
                "jql": "issuetype = Story AND status = 'On hold'",
                "startAt": start_at,
                "maxResults": 50,
                "fields": "summary,labels,assignee"
            }
            resp = _JIRA_SESSION.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            issues.extend(data["issues"])
            if start_at + 50 >= data["total"]:
                break
            start_at += 50

        # Process issues
        on_hold_stories = []
        for issue in issues:
            fields = issue["fields"]
            assignee = fields.get("assignee")
            on_hold_stories.append({
                'key': issue['key'],
                'summary': fields.get("summary", ""),
                'labels': fields.get("labels", []),
                'assignee': assignee.get("displayName") if assignee and isinstance(assignee, dict) else "Unassigned",
                'url': f"{JIRA_URL}/browse/{issue['key']}"
            })

        update_progress(f"Found {len(on_hold_stories)} on-hold stories")

        return {
            'success': True,
            'stories': on_hold_stories,
            'count': len(on_hold_stories),
            'error': None
        }

    except Exception as e:
        logger.exception("Error fetching on-hold stories")
        return {
            'success': False,
            'stories': [],
            'count': 0,
            'error': str(e)
        }

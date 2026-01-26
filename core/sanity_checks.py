"""
Core sanity check logic for JiraPresentationTool.

This module provides the business logic for checking 'To Refine' and 'Ready' stories
for missing labels and acceptance criteria. It can be used by both the CLI and Flask web UI.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Any, Optional, Callable

from jira_config import load_jira_env, get_jira_session

# Set up logging
logger = logging.getLogger(__name__)

# Load Jira environment at module level for performance
JIRA_ENV = load_jira_env()
JIRA_URL = JIRA_ENV.get("JT_JIRA_URL", "https://equinixjira.atlassian.net/").rstrip("/")
BOARD_ID = JIRA_ENV.get("JT_JIRA_BOARD")
FIELD_EPIC_LINK = JIRA_ENV.get("JT_JIRA_FIELD_EPIC_LINK", "customfield_10031")
FIELD_ACCEPTANCE_CRITERIA = JIRA_ENV.get("JT_JIRA_FIELD_ACCEPTANCE_CRITERIA", "customfield_10140")

# Shared session for all Jira API calls
_JIRA_SESSION = get_jira_session()


def check_missing(issue):
    """Check if an issue is missing labels or acceptance criteria.

    Args:
        issue: Jira issue dict

    Returns:
        List of strings describing what's missing
    """
    fields = issue["fields"]
    missing = []

    # Check labels
    labels = [lbl for lbl in fields.get("labels", []) if lbl]
    if not labels:
        missing.append("No Label")

    # Check acceptance criteria
    ac = fields.get(FIELD_ACCEPTANCE_CRITERIA)

    def has_bullet_with_text(val):
        if not isinstance(val, str):
            return False
        for line in val.splitlines():
            line = line.strip()
            if (line.startswith('*') or line.startswith('-')) and len(line.lstrip('*-').strip()) > 0:
                return True
        return False

    is_empty = False
    if ac is None:
        is_empty = True
    elif isinstance(ac, str):
        is_empty = not has_bullet_with_text(ac)
    elif isinstance(ac, (list, dict)):
        is_empty = len(ac) == 0
    else:
        is_empty = False  # treat other types as filled

    if is_empty:
        missing.append("No Acceptance Criteria")

    return missing


def get_to_refine_stories(
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """Check 'To Refine' stories for missing labels and acceptance criteria.

    Args:
        progress_callback: Optional callback for progress updates

    Returns:
        dict: {
            'success': bool,
            'total_stories': int,
            'total_epics': int,
            'issues_with_problems': List of issue dicts with 'missing' field,
            'error': str or None
        }
    """
    def update_progress(msg: str):
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

    try:
        update_progress("Fetching 'To Refine' stories...")

        # Fetch stories via the agile board issue endpoint
        url = f"{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/issue"
        issues = []
        start_at = 0

        while True:
            params = {
                "jql": "issuetype = Story AND status = 'To Refine'",
                "startAt": start_at,
                "maxResults": 50,
                "fields": f"summary,description,issuetype,labels,{FIELD_EPIC_LINK},epic,acceptanceCriteria,{FIELD_ACCEPTANCE_CRITERIA},parent"
            }
            resp = _JIRA_SESSION.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            issues.extend(data["issues"])
            if start_at + 50 >= data["total"]:
                break
            start_at += 50

        update_progress(f"Fetched {len(issues)} stories, checking for issues...")

        # Check each issue for problems
        issues_with_problems = []
        for issue in issues:
            missing = check_missing(issue)
            if missing:
                issues_with_problems.append({
                    'key': issue['key'],
                    'summary': issue['fields'].get('summary', ''),
                    'issuetype': issue['fields']['issuetype']['name'],
                    'labels': issue['fields'].get('labels', []),
                    'missing': missing,
                    'url': f"{JIRA_URL}/browse/{issue['key']}"
                })

        update_progress(f"Found {len(issues_with_problems)} issues with problems")

        return {
            'success': True,
            'total_stories': len(issues),
            'total_epics': 0,  # Not fetching epics in simplified version
            'issues_with_problems': issues_with_problems,
            'error': None
        }

    except Exception as e:
        logger.exception("Error checking 'To Refine' stories")
        return {
            'success': False,
            'total_stories': 0,
            'total_epics': 0,
            'issues_with_problems': [],
            'error': str(e)
        }


def get_ready_stories(
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """Check 'Ready' stories for missing labels and acceptance criteria.

    Args:
        progress_callback: Optional callback for progress updates

    Returns:
        dict: {
            'success': bool,
            'total_stories': int,
            'issues_with_problems': List of issue dicts with 'missing' field,
            'error': str or None
        }
    """
    def update_progress(msg: str):
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

    try:
        update_progress("Fetching 'Ready' stories...")

        # Fetch stories via the agile board issue endpoint
        url = f"{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/issue"
        issues = []
        start_at = 0

        while True:
            params = {
                "jql": "issuetype = Story AND status = 'Ready'",
                "startAt": start_at,
                "maxResults": 50,
                "fields": f"summary,description,issuetype,labels,{FIELD_EPIC_LINK},epic,acceptanceCriteria,{FIELD_ACCEPTANCE_CRITERIA},parent"
            }
            resp = _JIRA_SESSION.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            issues.extend(data["issues"])
            if start_at + 50 >= data["total"]:
                break
            start_at += 50

        update_progress(f"Fetched {len(issues)} stories, checking for issues...")

        # Check each issue for problems
        issues_with_problems = []
        for issue in issues:
            missing = check_missing(issue)
            if missing:
                issues_with_problems.append({
                    'key': issue['key'],
                    'summary': issue['fields'].get('summary', ''),
                    'issuetype': issue['fields']['issuetype']['name'],
                    'labels': issue['fields'].get('labels', []),
                    'missing': missing,
                    'url': f"{JIRA_URL}/browse/{issue['key']}"
                })

        update_progress(f"Found {len(issues_with_problems)} issues with problems")

        return {
            'success': True,
            'total_stories': len(issues),
            'issues_with_problems': issues_with_problems,
            'error': None
        }

    except Exception as e:
        logger.exception("Error checking 'Ready' stories")
        return {
            'success': False,
            'total_stories': 0,
            'issues_with_problems': [],
            'error': str(e)
        }

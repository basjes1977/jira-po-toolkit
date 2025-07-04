
"""
Show 'On Hold' Stories Overview
------------------------------
Displays all stories with status 'On hold', including summary, labels, assignee, and a direct Jira link.

Usage:
    python jira_on_hold_overview.py

Requirements:
    - Jira API credentials in `.jira_environment` in the script directory.
    - Python 3.7+
    - `requests` package

Jira API Reference: https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/
"""

import os
import sys
from pathlib import Path
import requests

def load_jira_env():
    """Load Jira credentials from .jira_environment file."""
    env_path = Path(__file__).parent / ".jira_environment"
    env = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "):
                    line = line[len("export ") :]
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"')
    return env

JIRA_ENV = load_jira_env()
JIRA_URL = JIRA_ENV.get("JT_JIRA_URL", "https://equinixjira.atlassian.net/").rstrip("/")
JIRA_EMAIL = JIRA_ENV.get("JT_JIRA_USERNAME")
JIRA_API_TOKEN = JIRA_ENV.get("JT_JIRA_PASSWORD")
BOARD_ID = JIRA_ENV.get("JT_JIRA_BOARD")

def get_on_hold_stories():
    """Fetch all stories with status 'On hold' from the configured Jira board."""
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
        resp = requests.get(url, params=params, auth=(JIRA_EMAIL, JIRA_API_TOKEN))
        resp.raise_for_status()
        data = resp.json()
        issues.extend(data["issues"])
        if start_at + 50 >= data["total"]:
            break
        start_at += 50
    return issues

def print_results(issues):
    """Print a summary of all 'On hold' stories with key details and Jira links."""
    print("\nStories with status 'On hold':\n")
    if not issues:
        print("No stories with status 'On hold' found.")
        return
    for issue in issues:
        fields = issue["fields"]
        summary = fields.get("summary", "")
        labels = ", ".join(fields.get("labels", []))
        assignee = fields.get("assignee")
        assignee_name = assignee.get("displayName") if assignee and isinstance(assignee, dict) else "Unassigned"
        url = f"{JIRA_URL}/browse/{issue['key']}"
        print(f"STORY: {issue['key']}: {summary}\n  Labels: {labels}\n  Assignee: {assignee_name}\n  {url}\n")

if __name__ == "__main__":
    issues = get_on_hold_stories()
    print_results(issues)

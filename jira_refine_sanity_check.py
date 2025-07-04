import os
import sys
from pathlib import Path
import requests
from collections import defaultdict

# --- Load Jira credentials from .jira_environment ---
def load_jira_env():
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

# --- Fetch all Epics and Stories in 'To Refine' state ---
def get_to_refine_issues():
    # Only check issues on the configured board
    # 1. Get all sprints for the board (to get board context)
    # 2. Get all issues for the board (backlog + sprints)
    # 3. Filter for Epics/Stories in 'To Refine'
    url = f"{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/issue"
    issues = []
    start_at = 0
    while True:
        params = {
            "jql": "(issuetype = Epic OR issuetype = Story) AND status = 'To Refine'",
            "startAt": start_at,
            "maxResults": 50,
            "fields": "summary,issuetype,labels,customfield_10031,epic,acceptanceCriteria,customfield_10140,parent"
        }
        resp = requests.get(url, params=params, auth=(JIRA_EMAIL, JIRA_API_TOKEN))
        resp.raise_for_status()
        data = resp.json()
        issues.extend(data["issues"])
        if start_at + 50 >= data["total"]:
            break
        start_at += 50
    return issues

# --- Group and sort issues ---
def group_and_sort_issues(issues):
    grouped = defaultdict(lambda: {"epic": None, "stories": []})
    for issue in issues:
        fields = issue["fields"]
        issuetype = fields["issuetype"]["name"]
        epic_link = None
        if issuetype == "Epic":
            grouped[issue["key"]]["epic"] = issue
        else:
            # Try to get epic link from customfield_10031 (Jira default Epic Link field)
            epic_link = fields.get("customfield_10031")
            grouped[epic_link]["stories"].append(issue)
    return grouped

# --- Check for missing label or acceptance criteria ---
def check_missing(issue):
    fields = issue["fields"]
    missing = []
    if not fields.get("labels"):
        missing.append("No Label")
    # Only check customfield_10140 for acceptance criteria
    ac = fields.get("customfield_10140")
    # Debug: print the value seen for customfield_10140
    # print(f"DEBUG: customfield_10140 for {issue.get('key')}: {repr(ac)}")
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

# --- Print results ---
def print_results(grouped):
    print("\nEpics and Stories in 'To Refine' missing Label and/or Acceptance Criteria:\n")
    for epic_key, group in grouped.items():
        epic = group["epic"]
        if epic:
            epic_url = f"{JIRA_URL}/browse/{epic['key']}"
            epic_missing = check_missing(epic)
            if epic_missing:
                print(f"EPIC: {epic['key']}: {epic['fields'].get('summary','')} [ {'; '.join(epic_missing)} ]\n  {epic_url}")
        for story in group["stories"]:
            story_url = f"{JIRA_URL}/browse/{story['key']}"
            story_missing = check_missing(story)
            if story_missing:
                print(f"  STORY: {story['key']}: {story['fields'].get('summary','')} [ {'; '.join(story_missing)} ]\n    {story_url}")

if __name__ == "__main__":
    issues = get_to_refine_issues()
    grouped = group_and_sort_issues(issues)
    print_results(grouped)

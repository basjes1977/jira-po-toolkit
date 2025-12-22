import requests

from jira_config import load_jira_env, get_ssl_verify, get_jira_session

JIRA_ENV = load_jira_env()
JIRA_URL = JIRA_ENV.get("JT_JIRA_URL", "https://equinixjira.atlassian.net/").rstrip("/")
JIRA_EMAIL = JIRA_ENV.get("JT_JIRA_USERNAME")
JIRA_API_TOKEN = JIRA_ENV.get("JT_JIRA_PASSWORD")
BOARD_ID = JIRA_ENV.get("JT_JIRA_BOARD")
SSL_VERIFY = get_ssl_verify()

# Shared session for all Jira API calls
_JIRA_SESSION = get_jira_session()

def get_blocked_stories():
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
    return issues

def print_results(issues):
    print("\nStories that are blocked by another work item:\n")
    found = False
    for issue in issues:
        fields = issue["fields"]
        summary = fields.get("summary", "")
        labels = ", ".join(fields.get("labels", []))
        assignee = fields.get("assignee")
        assignee_name = assignee.get("displayName") if assignee and isinstance(assignee, dict) else "Unassigned"
        url = f"{JIRA_URL}/browse/{issue['key']}"
        # Find all 'is blocked by' links
        blockers = []
        for link in fields.get("issuelinks", []):
            if link.get("type", {}).get("inward", "").lower() == "is blocked by":
                blocker = link.get("inwardIssue", {}).get("key")
                if blocker:
                    blockers.append(blocker)
        if blockers:  # Only print if there are blockers
            found = True
            blockers_str = ", ".join(blockers)
            print(f"STORY: {issue['key']}: {summary}\n  Labels: {labels}\n  Assignee: {assignee_name}\n  Blocked by: {blockers_str}\n  {url}\n")
    if not found:
        print("No blocked stories found.")

if __name__ == "__main__":
    issues = get_blocked_stories()
    print_results(issues)

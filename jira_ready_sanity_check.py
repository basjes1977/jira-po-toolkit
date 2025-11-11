import requests
from jira_config import load_jira_env

JIRA_ENV = load_jira_env()
JIRA_URL = JIRA_ENV.get("JT_JIRA_URL", "https://equinixjira.atlassian.net/").rstrip("/")
JIRA_EMAIL = JIRA_ENV.get("JT_JIRA_USERNAME")
JIRA_API_TOKEN = JIRA_ENV.get("JT_JIRA_PASSWORD")
BOARD_ID = JIRA_ENV.get("JT_JIRA_BOARD")
FIELD_ACCEPTANCE_CRITERIA = JIRA_ENV.get("JT_JIRA_FIELD_ACCEPTANCE_CRITERIA", "customfield_10140")

# --- Label order from jpt.py ---
LABEL_ORDER = [
    "NLMS",
    "IEMS",
    "ESMS",
    "UKMS",
    "S&A-MPC",
    "S&A_MGT",
    "FIMS",
]
label_order_lower = [l.lower() for l in LABEL_ORDER]

def get_ready_stories():
    url = f"{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/issue"
    issues = []
    start_at = 0
    while True:
        params = {
            "jql": "issuetype = Story AND status = 'Ready'",
            "startAt": start_at,
            "maxResults": 50,
            "fields": f"summary,issuetype,labels,{FIELD_ACCEPTANCE_CRITERIA}"
        }
        resp = requests.get(url, params=params, auth=(JIRA_EMAIL, JIRA_API_TOKEN))
        resp.raise_for_status()
        data = resp.json()
        issues.extend(data["issues"])
        if start_at + 50 >= data["total"]:
            break
        start_at += 50
    return issues

def has_acceptance_criteria(fields):
    ac = fields.get(FIELD_ACCEPTANCE_CRITERIA)
    if not isinstance(ac, str):
        return False
    for line in ac.splitlines():
        line = line.strip()
        if (line.startswith('*') or line.startswith('-')) and len(line.lstrip('*-').strip()) > 0:
            return True
    return False

def has_valid_label(fields):
    labels = [l.lower() for l in fields.get("labels", [])]
    for label in label_order_lower:
        if label in labels:
            return True
    return False

def print_results(issues):
    print("\nStories in 'Ready' state missing Acceptance Criteria and/or valid Label:\n")
    for issue in issues:
        fields = issue["fields"]
        missing = []
        if not has_acceptance_criteria(fields):
            missing.append("No Acceptance Criteria")
        if not has_valid_label(fields):
            missing.append("No Valid Label")
        if missing:
            url = f"{JIRA_URL}/browse/{issue['key']}"
            print(f"STORY: {issue['key']}: {fields.get('summary','')} [ {'; '.join(missing)} ]\n  {url}")

if __name__ == "__main__":
    issues = get_ready_stories()
    print_results(issues)

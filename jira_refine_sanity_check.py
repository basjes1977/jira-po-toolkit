import argparse
from collections import Counter, defaultdict

import requests
from jira_config import load_jira_env, get_ssl_verify

JIRA_ENV = load_jira_env()
JIRA_URL = JIRA_ENV.get("JT_JIRA_URL", "https://equinixjira.atlassian.net/").rstrip("/")
JIRA_EMAIL = JIRA_ENV.get("JT_JIRA_USERNAME")
JIRA_API_TOKEN = JIRA_ENV.get("JT_JIRA_PASSWORD")
BOARD_ID = JIRA_ENV.get("JT_JIRA_BOARD")
FIELD_EPIC_LINK = JIRA_ENV.get("JT_JIRA_FIELD_EPIC_LINK", "customfield_10031")
FIELD_ACCEPTANCE_CRITERIA = JIRA_ENV.get("JT_JIRA_FIELD_ACCEPTANCE_CRITERIA", "customfield_10140")
SSL_VERIFY = get_ssl_verify()

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
            "fields": f"summary,description,issuetype,labels,{FIELD_EPIC_LINK},epic,acceptanceCriteria,{FIELD_ACCEPTANCE_CRITERIA},parent"
        }
        resp = requests.get(url, params=params, auth=(JIRA_EMAIL, JIRA_API_TOKEN), verify=SSL_VERIFY)
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
            epic_link = fields.get(FIELD_EPIC_LINK)
            grouped[epic_link]["stories"].append(issue)
    return grouped

# --- Check for missing label or acceptance criteria ---
def check_missing(issue):
    fields = issue["fields"]
    missing = []
    labels = [lbl for lbl in fields.get("labels", []) if lbl]
    if not labels:
        missing.append("No Label")
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

def suggest_labels(story, grouped, max_suggestions=3):
    fields = story["fields"]
    epic_key = fields.get(FIELD_EPIC_LINK)
    group = grouped.get(epic_key) if epic_key in grouped else None
    candidates = []
    if group:
        # Other stories in same epic
        for peer in group["stories"]:
            if peer["key"] == story["key"]:
                continue
            candidates.extend([lbl for lbl in peer["fields"].get("labels", []) if lbl])
        # Labels on the epic itself
        epic = group.get("epic")
        if epic:
            candidates.extend([lbl for lbl in epic["fields"].get("labels", []) if lbl])
    if not candidates:
        return None
    counter = Counter([c.strip() for c in candidates if c.strip()])
    if not counter:
        return []
    return [label for label, _ in counter.most_common(max_suggestions)]

def set_story_labels(issue_key, labels):
    unique_labels = []
    for lbl in labels:
        clean = lbl.strip()
        if clean and clean not in unique_labels:
            unique_labels.append(clean)
    if not unique_labels:
        raise ValueError("No valid labels provided")
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"
    payload = {"fields": {"labels": unique_labels}}
    headers = {"Content-Type": "application/json"}
    resp = requests.put(url, json=payload, auth=(JIRA_EMAIL, JIRA_API_TOKEN), headers=headers, verify=SSL_VERIFY)
    resp.raise_for_status()

def collect_stories_missing_labels(grouped):
    missing = []
    for epic_key, group in grouped.items():
        for story in group["stories"]:
            fields = story["fields"]
            labels = [lbl for lbl in fields.get("labels", []) if lbl]
            if not labels:
                missing.append((epic_key, story))
    return missing

def interactive_label_fix(grouped, stories_missing_label=None):
    if stories_missing_label is None:
        stories_missing_label = collect_stories_missing_labels(grouped)
    if not stories_missing_label:
        print("\nAll stories already have labels. Nothing to fix.")
        return
    print(f"\nFound {len(stories_missing_label)} stories without labels. You can now add them.")
    for _, story in stories_missing_label:
        key = story["key"]
        summary = story["fields"].get("summary", "")
        suggestions = suggest_labels(story, grouped)
        default_hint = ""
        if suggestions:
            default_hint = f" [suggestions: {', '.join(suggestions)}]"
        print(f"\nStory {key}: {summary}{default_hint}")
        print("Enter comma-separated labels, 'skip' to skip, or press Enter to accept the first suggestion.")
        while True:
            user_input = input("Labels: ").strip()
            if not user_input:
                if suggestions:
                    chosen_labels = [suggestions[0]]
                    break
                confirm_skip = input("No suggestions available. Skip this story? [Y/n]: ").strip().lower()
                if confirm_skip in ("", "y", "yes"):
                    chosen_labels = []
                    break
                continue
            if user_input.lower() in ("skip", "s"):
                chosen_labels = []
                break
            labels = [lbl.strip() for lbl in user_input.split(",") if lbl.strip()]
            if labels:
                chosen_labels = labels
                break
            print("Please enter at least one label or type 'skip'.")
        if not chosen_labels:
            print(f"Skipped {key}")
            continue
        try:
            set_story_labels(key, chosen_labels)
            print(f"Set labels {chosen_labels} on {key}")
        except requests.HTTPError as err:
            print(f"Failed to update {key}: {err}")
        except Exception as exc:
            print(f"Unexpected error while updating {key}: {exc}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check 'To Refine' Epics/Stories and optionally fix missing labels.")
    parser.add_argument("--fix-labels", action="store_true", help="Interactively add labels to stories missing them.")
    args = parser.parse_args()

    issues = get_to_refine_issues()
    grouped = group_and_sort_issues(issues)
    print_results(grouped)

    missing_label_stories = collect_stories_missing_labels(grouped)

    if args.fix_labels:
        interactive_label_fix(grouped, missing_label_stories)
    elif missing_label_stories:
        resp = input("\nOne or more stories are missing labels. Add them now? [y/N]: ").strip().lower()
        if resp in ("y", "yes"):
            interactive_label_fix(grouped, missing_label_stories)

import argparse

import requests
from jira_config import load_jira_env, get_ssl_verify

JIRA_ENV = load_jira_env()
JIRA_URL = JIRA_ENV.get("JT_JIRA_URL", "https://equinixjira.atlassian.net/").rstrip("/")
JIRA_EMAIL = JIRA_ENV.get("JT_JIRA_USERNAME")
JIRA_API_TOKEN = JIRA_ENV.get("JT_JIRA_PASSWORD")
BOARD_ID = JIRA_ENV.get("JT_JIRA_BOARD")
FIELD_ACCEPTANCE_CRITERIA = JIRA_ENV.get("JT_JIRA_FIELD_ACCEPTANCE_CRITERIA", "customfield_10140")
SSL_VERIFY = get_ssl_verify()

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

def get_board_filter_id():
    """Return the board filter id so JQL searches match board scope (backlog + sprints)."""
    url = f"{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/configuration"
    try:
        resp = requests.get(url, auth=(JIRA_EMAIL, JIRA_API_TOKEN), verify=SSL_VERIFY)
        resp.raise_for_status()
        data = resp.json()
        return data.get("filter", {}).get("id")
    except requests.RequestException as err:
        print(f"Warning: could not load board config for filter scoping: {err}")
    return None

def jira_search(jql, fields, start_at=0, max_results=50):
    """Execute a JQL search using the preferred /search/jql endpoint with fallback shapes."""
    headers = {"Content-Type": "application/json"}
    payloads = [
        {"jql": jql, "fields": fields, "startAt": start_at, "maxResults": max_results},
        {"jql": jql, "fields": fields},  # some tenants reject pagination hints in the body
        {"query": {"jql": jql, "startAt": start_at, "maxResults": max_results}, "fields": fields},
    ]
    endpoints = [
        f"{JIRA_URL}/rest/api/3/search/jql",
        f"{JIRA_URL}/rest/api/3/search",
    ]
    last_error = None
    for endpoint in endpoints:
        for payload in payloads:
            try:
                resp = requests.post(endpoint, json=payload, auth=(JIRA_EMAIL, JIRA_API_TOKEN), headers=headers, verify=SSL_VERIFY)
                if resp.status_code == 200:
                    return resp.json()
                last_error = f"{resp.status_code}: {resp.text}"
                if resp.status_code == 410:
                    continue
            except requests.RequestException as err:
                last_error = err
                continue
    raise RuntimeError(f"Jira search failed for '{jql}': {last_error}")

def get_ready_items():
    url = f"{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/issue"
    issues = []
    start_at = 0
    while True:
        params = {
            "jql": "issuetype = Story AND status = 'Ready'",
            "startAt": start_at,
            "maxResults": 50,
            "fields": f"summary,description,issuetype,labels,{FIELD_ACCEPTANCE_CRITERIA}"
        }
        resp = requests.get(url, params=params, auth=(JIRA_EMAIL, JIRA_API_TOKEN), verify=SSL_VERIFY)
        resp.raise_for_status()
        data = resp.json()
        issues.extend(data["issues"])
        if start_at + 50 >= data["total"]:
            break
        start_at += 50
    # Epics are not returned by the Agile issue endpoint; fetch via JQL scoped to the board filter
    filter_id = get_board_filter_id()
    epic_jql_parts = ["issuetype = Epic", "status = 'Ready'"]
    if filter_id:
        epic_jql_parts.append(f"filter = {filter_id}")
    epic_jql = " AND ".join(epic_jql_parts)
    epic_fields = ["summary", "description", "issuetype", "labels", FIELD_ACCEPTANCE_CRITERIA]
    start_at = 0
    while True:
        data = jira_search(epic_jql, epic_fields, start_at=start_at, max_results=50)
        epics_batch = data.get("issues", [])
        issues.extend(epics_batch)
        total = data.get("total", 0)
        if start_at + len(epics_batch) >= total:
            break
        start_at += len(epics_batch)
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

def has_description(fields):
    desc = fields.get("description")
    if desc is None:
        return False
    if isinstance(desc, str):
        return bool(desc.strip())
    if isinstance(desc, dict):
        def has_text(node):
            if node is None:
                return False
            if isinstance(node, str):
                return bool(node.strip())
            if isinstance(node, dict):
                node_type = node.get("type")
                if node_type == "text":
                    return bool((node.get("text") or "").strip())
                for key in ("text", "content", "paragraphs", "items"):
                    child = node.get(key)
                    if isinstance(child, list):
                        if any(has_text(item) for item in child):
                            return True
                    elif isinstance(child, (dict, str)):
                        if has_text(child):
                            return True
                return False
            if isinstance(node, list):
                return any(has_text(item) for item in node)
            return False
        return has_text(desc)
    return True

def has_valid_label(fields):
    labels = [l.lower() for l in fields.get("labels", [])]
    for label in label_order_lower:
        if label in labels:
            return True
    return False

def is_severely_invalid(fields):
    return (not has_acceptance_criteria(fields)) and (not has_valid_label(fields)) and (not has_description(fields))

def normalize_label(label_input):
    if not label_input:
        return None
    stripped = label_input.strip()
    if not stripped:
        return None
    lower = stripped.lower()
    for label in LABEL_ORDER:
        if label.lower() == lower:
            return label
    return stripped

def update_story_labels(issue_key, labels):
    sanitized = []
    for lbl in labels:
        if lbl and lbl not in sanitized:
            sanitized.append(lbl)
    if not sanitized:
        raise ValueError("No labels provided")
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"
    payload = {"fields": {"labels": sanitized}}
    headers = {"Content-Type": "application/json"}
    resp = requests.put(url, json=payload, auth=(JIRA_EMAIL, JIRA_API_TOKEN), headers=headers, verify=SSL_VERIFY)
    resp.raise_for_status()

def collect_missing_label_stories(issues):
    return [issue for issue in issues if not has_valid_label(issue["fields"])]

def collect_missing_label_epics(issues):
    return [issue for issue in issues if issue["fields"]["issuetype"]["name"].lower() == "epic" and not has_valid_label(issue["fields"])]

def collect_severely_invalid_stories(issues):
    return [issue for issue in issues if is_severely_invalid(issue["fields"])]

def interactive_label_fix(stories):
    if not stories:
        print("\nAll 'Ready' stories already have valid labels.")
        return
    print("\nValid label options (comma-separated input allowed):")
    print(", ".join(LABEL_ORDER))
    for issue in stories:
        fields = issue["fields"]
        key = issue["key"]
        summary = fields.get("summary", "")
        existing = [lbl for lbl in fields.get("labels", []) if lbl]
        suggestion = existing if existing else None
        print(f"\nStory {key}: {summary}")
        if existing:
            print(f"Existing labels: {', '.join(existing)}")
        while True:
            prompt = "Enter one or more valid labels (comma-separated)"
            if suggestion:
                prompt += f" [default: {', '.join(suggestion)}]"
            prompt += " (or type 'skip'): "
            user_input = input(prompt).strip()
            if not user_input and suggestion:
                normalized = []
                for lbl in suggestion:
                    canonical = normalize_label(lbl)
                    if canonical and canonical not in normalized:
                        normalized.append(canonical)
                if normalized:
                    chosen = normalized
                    break
            if not user_input:
                confirm_skip = input("No label entered. Skip this story? [Y/n]: ").strip().lower()
                if confirm_skip in ("", "y", "yes"):
                    chosen = None
                    break
                continue
            if user_input.lower() in ("skip", "s"):
                chosen = None
                break
            entered = []
            for part in user_input.split(","):
                canonical = normalize_label(part)
                if canonical and canonical not in entered:
                    entered.append(canonical)
            if not entered:
                print("Please enter at least one label (comma-separated).")
                continue
            chosen = entered
            break
        if not chosen:
            print(f"Skipped {key}")
            continue
        try:
            update_story_labels(key, chosen)
            print(f"Set labels {chosen} on {key}")
        except requests.HTTPError as err:
            print(f"Failed to update {key}: {err}")
        except Exception as exc:
            print(f"Unexpected error while updating {key}: {exc}")

def interactive_epic_label_fix(epics):
    if not epics:
        print("\nAll 'Ready' epics already have valid labels.")
        return
    print("\nValid label options (comma-separated input allowed):")
    print(", ".join(LABEL_ORDER))
    for issue in epics:
        fields = issue["fields"]
        key = issue["key"]
        summary = fields.get("summary", "")
        existing = [lbl for lbl in fields.get("labels", []) if lbl]
        suggestion = existing if existing else None
        print(f"\nEpic {key}: {summary}")
        if existing:
            print(f"Existing labels: {', '.join(existing)}")
        while True:
            prompt = "Enter one or more valid labels (comma-separated)"
            if suggestion:
                prompt += f" [default: {', '.join(suggestion)}]"
            prompt += " (or type 'skip'): "
            user_input = input(prompt).strip()
            if not user_input and suggestion:
                normalized = []
                for lbl in suggestion:
                    canonical = normalize_label(lbl)
                    if canonical and canonical not in normalized:
                        normalized.append(canonical)
                if normalized:
                    chosen = normalized
                    break
            if not user_input:
                confirm_skip = input("No label entered. Skip this epic? [Y/n]: ").strip().lower()
                if confirm_skip in ("", "y", "yes"):
                    chosen = None
                    break
                continue
            if user_input.lower() in ("skip", "s"):
                chosen = None
                break
            entered = []
            for part in user_input.split(","):
                canonical = normalize_label(part)
                if canonical and canonical not in entered:
                    entered.append(canonical)
            if not entered:
                print("Please enter at least one label (comma-separated).")
                continue
            chosen = entered
            break
        if not chosen:
            print(f"Skipped {key}")
            continue
        try:
            update_story_labels(key, chosen)
            print(f"Set labels {chosen} on {key}")
        except requests.HTTPError as err:
            print(f"Failed to update {key}: {err}")
        except Exception as exc:
            print(f"Unexpected error while updating {key}: {exc}")

def transition_issue_to_refine(issue_key):
    transitions_url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions"
    resp = requests.get(transitions_url, auth=(JIRA_EMAIL, JIRA_API_TOKEN), verify=SSL_VERIFY)
    resp.raise_for_status()
    data = resp.json()
    transitions = data.get("transitions", [])
    target = None
    for tr in transitions:
        name = (tr.get("name") or "").lower()
        to_name = (tr.get("to", {}).get("name") or "").lower()
        if "to refine" in name or "to refine" in to_name:
            target = tr.get("id")
            break
    if not target and transitions:
        for tr in transitions:
            if tr.get("to", {}).get("name", "").lower() == "to refine":
                target = tr.get("id")
                break
    if not target:
        raise RuntimeError(f"No 'To Refine' transition available for {issue_key}")
    payload = {"transition": {"id": target}}
    resp = requests.post(transitions_url, json=payload, auth=(JIRA_EMAIL, JIRA_API_TOKEN), verify=SSL_VERIFY)
    resp.raise_for_status()

def prompt_move_to_refine(stories):
    if not stories:
        return
    print("\nThe following 'Ready' stories have no description, no acceptance criteria, and no valid label.")
    print("These items cannot be executed safely. You can move them back to 'To Refine'.")
    for issue in stories:
        key = issue["key"]
        summary = issue["fields"].get("summary", "")
        url = f"{JIRA_URL}/browse/{key}"
        print(f"\n{key}: {summary}\n  {url}")
        resp = input("Move this story back to 'To Refine'? [y/N]: ").strip().lower()
        if resp not in ("y", "yes"):
            continue
        try:
            transition_issue_to_refine(key)
            print(f"{key} moved to 'To Refine'.")
        except requests.HTTPError as err:
            print(f"Failed to transition {key}: {err}")
        except Exception as exc:
            print(f"Unexpected error while transitioning {key}: {exc}")

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
            itype = fields.get("issuetype", {}).get("name", "Story").upper()
            print(f"{itype}: {issue['key']}: {fields.get('summary','')} [ {'; '.join(missing)} ]\n  {url}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check 'Ready' stories for missing acceptance criteria and valid labels.")
    parser.add_argument("--fix-labels", action="store_true", help="Interactively add a valid label to stories that are missing one.")
    args = parser.parse_args()

    issues = get_ready_items()
    print_results(issues)
    severe_stories = collect_severely_invalid_stories([i for i in issues if i["fields"]["issuetype"]["name"].lower() == "story"])
    prompt_move_to_refine(severe_stories)
    skip_keys = {issue["key"] for issue in severe_stories}
    filtered_issues = [issue for issue in issues if issue["key"] not in skip_keys]
    missing_label_stories = collect_missing_label_stories(filtered_issues)
    missing_label_epics = collect_missing_label_epics(filtered_issues)
    if args.fix_labels:
        interactive_label_fix(missing_label_stories)
        interactive_epic_label_fix(missing_label_epics)
    elif missing_label_stories:
        resp = input("\nOne or more 'Ready' stories are missing a valid label. Add them now? [y/N]: ").strip().lower()
        if resp in ("y", "yes"):
            interactive_label_fix(missing_label_stories)
    if missing_label_epics:
        resp = input("\nOne or more 'Ready' epics are missing a valid label. Add them now? [y/N]: ").strip().lower()
        if resp in ("y", "yes"):
            interactive_epic_label_fix(missing_label_epics)
    prompt_move_to_refine(severe_stories)

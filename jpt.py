import sys
import time
"""
Jira Sprint PowerPoint Generator
--------------------------------
This script fetches Jira sprint data and generates a PowerPoint presentation using a template.
It groups issues by label, displays issue details (with assignee avatars), and includes summary and upcoming slides.
All text is placed using template placeholders for consistent formatting.
Split: presentation logic moved to jpt_presentation.py
"""

def get_upcoming_sprint_id():
    url = f"{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/sprint?state=future"
    resp = requests.get(url, auth=(JIRA_EMAIL, JIRA_API_TOKEN))
    resp.raise_for_status()
    sprints = resp.json().get("values", [])
    if not sprints:
        return None
    return sprints[0]["id"]
import requests
from jpt_presentation import create_presentation
from collections import defaultdict
import os
import logging

# Load Jira credentials from .jira_environment
from jira_config import load_jira_env
from jira_metrics import build_velocity_history

JIRA_ENV = load_jira_env()
JIRA_URL = JIRA_ENV.get("JT_JIRA_URL", "https://equinixjira.atlassian.net/").rstrip("/")
JIRA_EMAIL = JIRA_ENV.get("JT_JIRA_USERNAME")
JIRA_API_TOKEN = JIRA_ENV.get("JT_JIRA_PASSWORD")
BOARD_ID = JIRA_ENV.get("JT_JIRA_BOARD")
FIELD_STORY_POINTS = JIRA_ENV.get("JT_JIRA_FIELD_STORY_POINTS", "customfield_10024")

# Configure logging
logger = logging.getLogger("jpt")
_log_level = os.environ.get("JPT_VERBOSE")
if _log_level and _log_level not in ("", "0", "False", "false"):
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    logger.setLevel(logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger.setLevel(logging.INFO)

# HTTP helper that retries on transient server/network errors.
def jira_get(url, params=None, max_retries=4, backoff=1.0, timeout=15, **kwargs):
    """GET with retries for Jira endpoints. Returns requests.Response or raises.

    Accepts arbitrary kwargs but will always use basic auth from env.
    """
    sess = requests.Session()
    for attempt in range(1, max_retries + 1):
        try:
            logger.debug("GET %s params=%s (attempt %d)", url, params, attempt)
            resp = sess.get(url, params=params, auth=(JIRA_EMAIL, JIRA_API_TOKEN), timeout=timeout)
            # Treat 5xx as retryable
            if 500 <= resp.status_code < 600:
                logger.warning("Server error %s for %s (attempt %d)", resp.status_code, url, attempt)
                if attempt == max_retries:
                    resp.raise_for_status()
                time.sleep(backoff * attempt)
                continue
            return resp
        except requests.exceptions.RequestException as e:
            logger.warning("Request error for %s: %s (attempt %d)", url, e, attempt)
            if attempt == max_retries:
                raise
            time.sleep(backoff * attempt)
    raise RuntimeError("Failed to GET %s after retries" % url)

# Monkey-patch requests.get to use jira_get so existing calls use retries.
requests.get = jira_get


def jql_search(payload, max_retries=2):
    """Run a JQL search using the newer API. Try /rest/api/3/search/jql then fallback to /rest/api/3/search.

    Returns the parsed JSON on success, or None on failure.
    """
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    endpoints = [
        f"{JIRA_URL}/rest/api/3/search/jql",
        f"{JIRA_URL}/rest/api/3/search",
    ]
    # Try a few payload shapes because different Jira Cloud instances accept slightly different shapes
    jql = payload.get("jql") or payload.get("query") or ''
    field_list = payload.get("fields")
    if isinstance(field_list, str):
        field_list = [field_list]
    candidate_payloads = [
        {"jql": jql, "fields": field_list or [], "maxResults": payload.get("maxResults", 50)},
        {"query": {"jql": jql}, "fields": field_list or [], "maxResults": payload.get("maxResults", 50)},
        {"query": {"jql": jql, "startAt": 0, "maxResults": payload.get("maxResults", 50)}, "fields": field_list or []},
        {"jql": jql},
    ]
    for endpoint in endpoints:
        for attempt in range(1, max_retries + 1):
            for try_payload in candidate_payloads:
                try:
                    logger.debug("POST %s payload=%s (attempt %d)", endpoint, try_payload, attempt)
                    resp = requests.Session().post(endpoint, json=try_payload, auth=(JIRA_EMAIL, JIRA_API_TOKEN), headers=headers, timeout=15)
                    text = None
                    try:
                        text = resp.text
                    except Exception:
                        text = '<no-body>'
                    logger.debug("Response %s %s", resp.status_code, (text[:200] + '...') if text and len(text) > 200 else text)
                    if resp.status_code == 200:
                        try:
                            return resp.json()
                        except Exception:
                            return None
                    # client error: try next payload shape immediately
                    if 400 <= resp.status_code < 500:
                        logger.debug("Client error %s from %s for payload %s: %s", resp.status_code, endpoint, try_payload, text)
                        continue
                    # server error: wait and retry payload/endpoint
                    time.sleep(0.5 * attempt)
                except requests.exceptions.RequestException as e:
                    logger.warning("JQL search request exception to %s: %s", endpoint, e)
                    time.sleep(0.5 * attempt)
        logger.debug("Falling back from endpoint %s to next", endpoint)
    logger.warning("JQL search failed for payload: %s", payload)
    return None

def get_current_sprint_id():
    """
    Get the ID of the current active sprint from Jira.
    """
    url = f"{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/sprint?state=active"
    resp = requests.get(url, auth=(JIRA_EMAIL, JIRA_API_TOKEN))
    resp.raise_for_status()
    sprints = resp.json().get("values", [])
    if not sprints:
        raise Exception("No active sprint found.")
    return sprints[0]["id"]

def get_issues(sprint_id):
    """
    Fetch all issues for a given sprint ID from Jira.
    Returns a list of issue dicts.
    """
    url = f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue"
    issues = []
    start_at = 0
    while True:
        params = {"startAt": start_at, "maxResults": 50}
        resp = requests.get(url, params=params, auth=(JIRA_EMAIL, JIRA_API_TOKEN))
        resp.raise_for_status()
        data = resp.json()
        issues.extend(data["issues"])
        if start_at + 50 >= data["total"]:
            break
        start_at += 50
    return issues

def get_sprint_name(sprint_id):
    """
    Fetch the name of a sprint given its ID.
    """
    url = f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}"
    resp = requests.get(url, auth=(JIRA_EMAIL, JIRA_API_TOKEN))
    resp.raise_for_status()
    data = resp.json()
    return data.get("name", f"Sprint_{sprint_id}")

def get_sprint_dates(sprint_id):
    """
    Fetch the start and end date of a sprint given its ID.
    Returns (start_date, end_date) as strings (YYYY-MM-DD) or (None, None) if not available.
    """
    url = f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}"
    resp = requests.get(url, auth=(JIRA_EMAIL, JIRA_API_TOKEN))
    resp.raise_for_status()
    data = resp.json()
    start = data.get("startDate")
    end = data.get("endDate")
    # Format as YYYY-MM-DD if present
    def fmt(dt):
        if not dt:
            return None
        return dt[:10]
    return (fmt(start), fmt(end))


def get_next_sprint_id():
    """Return the first future sprint id on the board, or None if none planned."""
    url = f"{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/sprint?state=future"
    resp = requests.get(url, auth=(JIRA_EMAIL, JIRA_API_TOKEN))
    resp.raise_for_status()
    sprints = resp.json().get("values", [])
    if not sprints:
        return None
    return sprints[0].get("id")


def issue_in_sprint(issue, sprint_id):
    """Return True if the given issue is part of the sprint with id sprint_id.

    This function checks several common Jira fields that may contain sprint information:
    - known custom fields like 'customfield_10007' (Sprint), 'sprint'
    - string representations that include 'id=<sprint_id>'
    It intentionally performs broad checks because Jira servers may store sprint info in different fields.
    """
    try:
        fields = issue.get('fields', {})
    except Exception:
        return False
    # Check a few likely field keys first
    possible_keys = ['sprint', 'customfield_10007', 'customfield_10020', 'customfield_10100']
    sid = str(sprint_id)
    for key in possible_keys:
        if key in fields:
            val = fields.get(key)
            if not val:
                continue
            # If it's a list of sprint descriptors
            if isinstance(val, list):
                for v in val:
                    if isinstance(v, dict) and str(v.get('id')) == sid:
                        return True
                    if isinstance(v, str) and f"id={sid}" in v:
                        return True
            else:
                if isinstance(val, dict) and str(val.get('id')) == sid:
                    return True
                if isinstance(val, str) and f"id={sid}" in val:
                    return True
    # Fallback: search any string field for 'id=<sprint_id>' (covers odd storage)
    for k, v in fields.items():
        if isinstance(v, str) and f"id={sid}" in v:
            return True
    return False

def group_issues_by_label(issues, sprint_id=None):
    """
    Group issues by the first matching label from a predefined list (case-insensitive).
    Only includes issues of type 'story' or 'task'.
    Returns a dict: label -> list of issues, in the order of the label list, with 'Other' for unmatched.
    """
    LABEL_MAP = {
        "nlms": "Dutch Platform(s)",
        "iems": "Irish Platform(s)",
        "esms": "Spanish Platform(s)",
        "ukms": "UK Platform(s)",
        "s&a-mpc": "MPC",
        "s&a_mgt": "Management tasks",
        "fims": "Finnish Platform(s)",
    }
    LABEL_ORDER = list(LABEL_MAP.keys())
    grouped = {LABEL_MAP[label]: [] for label in LABEL_ORDER}
    grouped["Other"] = []
    CANCELLED_STATUSES = {"cancelled", "canceled", "removed", "declined"}
    for issue in issues:
        # If a sprint_id is provided, filter out issues that are not part of that sprint.
        if sprint_id is not None and not issue_in_sprint(issue, sprint_id):
            try:
                logger.debug("Excluding %s: not in sprint %s", issue.get('key'), sprint_id)
            except Exception:
                pass
            continue
        fields = issue["fields"]
        status_name = fields.get("status", {}).get("name", "").lower()
        if status_name in CANCELLED_STATUSES:
            try:
                logger.debug("Excluding %s: status '%s'", issue.get('key'), status_name)
            except Exception:
                pass
            continue
        issuetype = fields["issuetype"]["name"].lower()
        if issuetype not in ["story", "task"]:
            continue
        labels = [l.lower() for l in fields.get("labels", [])]
        found = False
        for label_key in LABEL_ORDER:
            if label_key in labels:
                grouped[LABEL_MAP[label_key]].append(issue)
                found = True
                break
        if not found:
            grouped["Other"].append(issue)
    # Remove empty groups for cleaner output
    return {k: v for k, v in grouped.items() if v}

# ...existing code...

if __name__ == "__main__":
    # CLI: allow dumping issue JSON for debugging
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Jira Presentation Tool")
    parser.add_argument("--dump-issue", "-d", nargs="+", help="Issue key(s) to fetch and print full JSON (fields=*all) and exit")
    parser.add_argument("--dump-epic-map", action="store_true", help="Print the built epic->initiative mapping (includes captured descriptions) before creating the presentation")
    args, unknown = parser.parse_known_args()
    if args.dump_issue:
        for ik in args.dump_issue:
            try:
                spinner_running = False
            except Exception:
                pass
            url = f"{JIRA_URL}/rest/api/2/issue/{ik}"
            params = {"fields": "*all", "expand": "names,renderedFields"}
            try:
                resp = requests.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"Failed to fetch {ik}: {e}")
        sys.exit(0)

    # Emoji spinner for progress indicator
    import threading
    import itertools
    import time

    spinner_running = True
    spinner_message = ["Starting..."]
    def spinner_func():
        emojis = ["⏳", "🕐", "🕑", "🕒", "🕓", "🕔", "⌛", "🕐", "🕑", "🕒", "🕓", "🕔"]
        for idx in itertools.cycle(range(len(emojis))):
            if not spinner_running:
                break
            sys.stdout.write(f"\r{emojis[idx]} {spinner_message[0]}   ")
            sys.stdout.flush()
            time.sleep(0.15)
        sys.stdout.write("\r" + " " * 40 + "\r")

    spinner_thread = threading.Thread(target=spinner_func)
    spinner_thread.start()

    try:
        spinner_message[0] = "Fetching current sprint ID..."
        sprint_id = get_current_sprint_id()
        spinner_message[0] = "Fetching sprint name..."
        sprint_name = get_sprint_name(sprint_id)
        spinner_message[0] = "Fetching sprint dates..."
        sprint_start, sprint_end = get_sprint_dates(sprint_id)
        spinner_message[0] = "Fetching issues for current sprint..."
        issues = get_issues(sprint_id)
        spinner_message[0] = "Grouping issues by label..."
        grouped = group_issues_by_label(issues, sprint_id=sprint_id)
        spinner_message[0] = "Creating PowerPoint presentation..."
        import re
        # Replace any character not valid in filenames (non-ASCII, special chars) with underscore
        safe_sprint_name = re.sub(r'[^\w\-.]', '_', sprint_name, flags=re.ASCII)
        safe_sprint_name = re.sub(r'_+', '_', safe_sprint_name).strip('_')
        filename = f"{safe_sprint_name or 'Sprint'}.pptx"
        # Resolve epic display names (attempt to fetch epic summaries by key)
        def detect_epic_name_local(fields):
            candidates = ['customfield_10008', 'customfield_10006', 'epic', 'Epic Link', 'epic_link']
            for key in candidates:
                if key in fields and fields.get(key):
                    val = fields.get(key)
                    if isinstance(val, dict):
                        return val.get('key') or val.get('name') or str(val)
                    if isinstance(val, list) and val:
                        first = val[0]
                        if isinstance(first, dict):
                            return first.get('key') or first.get('name') or str(first)
                        return str(first)
                    return str(val)
            for k, v in fields.items():
                if 'epic' in k.lower() and v:
                    if isinstance(v, dict):
                        return v.get('key') or v.get('name') or str(v)
                    return str(v)
            return None

        epic_candidates = set()
        for issues_in_label in grouped.values():
            for issue in issues_in_label:
                epic_id = detect_epic_name_local(issue.get('fields', {}))
                if epic_id and epic_id != 'None':
                    epic_candidates.add(str(epic_id))

        epic_map = {}
        # Batch lookup epic summaries using JQL search to avoid many single-issue requests
        import re as _re
        epic_keys = [e for e in epic_candidates if _re.match(r'^[A-Z]+-\d+$', str(e))]
        non_keys = [e for e in epic_candidates if e not in epic_keys]
        # Fetch keys in chunks (Jira may limit URL length; 50 is a safe chunk)
        def chunks(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i+n]

        # We'll also try to detect the epic's parent (initiative) via the epic's 'parent' field.
        parent_keys_to_fetch = set()
        epic_parent_map = {}  # epic_key -> parent_key (if present)
        # parent_key -> dict with 'display' and 'description' when parent object is embedded in issue JSON
        embedded_parent_map = {}
        def detect_parent_from_issue(issue_obj):
            """Try multiple heuristics to find a parent/initiative key from an issue JSON.

            Returns the parent key (e.g., 'EMSS-81') or None.
            """
            try:
                fields_resp = issue_obj.get('fields', {})
            except Exception:
                return None
            # 1) direct 'parent' field (common in Portfolio setups)
            parent = fields_resp.get('parent')
            if parent and isinstance(parent, dict):
                pkey = parent.get('key')
                if pkey:
                    return pkey
            # 2) some instances put initiative/parent in custom fields or differently named fields
            for k, v in fields_resp.items():
                if not k:
                    continue
                kl = k.lower()
                if ('parent' in kl or 'initiative' in kl) and v:
                    if isinstance(v, dict) and v.get('key'):
                        return v.get('key')
                    if isinstance(v, list) and v:
                        first = v[0]
                        if isinstance(first, dict) and first.get('key'):
                            return first.get('key')
            # 3) inspect issue links for a parent-like relation
            for link in fields_resp.get('issuelinks', []) or []:
                # Link types vary; try common patterns
                t = link.get('type', {})
                tname = (t.get('name') or '').lower()
                # inwardIssue / outwardIssue may contain the related issue
                for side in ('outwardIssue', 'inwardIssue'):
                    rel = link.get(side)
                    if not rel:
                        continue
                    rkey = rel.get('key')
                    if not rkey:
                        continue
                    # If the link type name suggests a parent/child or initiative relation, accept it
                    if any(x in tname for x in ('parent', 'child', 'initiative', 'is parent', 'is child', 'parent/child')):
                        return rkey
                    # Some instances store direction text in 'outward'/'inward' fields
                    outward = (t.get('outward') or '').lower()
                    inward = (t.get('inward') or '').lower()
                    if any(x in outward for x in ('is parent', 'parent of', 'initiates', 'relates to')) or any(x in inward for x in ('is parent', 'parent of', 'initiates', 'relates to')):
                        return rkey
            # If we didn't already return, try a more permissive approach on linked issues:
            # - accept any linked issue that looks like an EMSS initiative key (EMSS-\d+)
            import re as _re
            token_re = _re.compile(r"\bEMSS-\d+\b")
            for link in fields_resp.get('issuelinks', []) or []:
                for side in ('outwardIssue', 'inwardIssue'):
                    rel = link.get(side)
                    if not rel:
                        continue
                    rkey = rel.get('key')
                    if not rkey:
                        continue
                    # If the linked key appears to be an EMSS initiative, accept it
                    if token_re.match(rkey):
                        logger.debug("Found EMSS-linked parent key %s in issuelinks", rkey)
                        return rkey

            # 4) as a last resort, scan any string field for an EMSS-xxxx token (initiative in other project)
            def _search_for_token(obj):
                if isinstance(obj, str):
                    m = token_re.search(obj)
                    if m:
                        return m.group(0)
                    return None
                if isinstance(obj, dict):
                    for vv in obj.values():
                        found = _search_for_token(vv)
                        if found:
                            return found
                if isinstance(obj, list):
                    for vv in obj:
                        found = _search_for_token(vv)
                        if found:
                            return found
                return None

            found = _search_for_token(fields_resp)
            if found:
                logger.debug("Heuristically found parent token %s inside issue fields", found)
                return found
            return None
        for chunk in chunks(epic_keys, 50):
            q = ",".join(chunk)
            jql = f"key in ({q})"
            payload = {"jql": jql, "fields": "summary,parent", "maxResults": 100}
            try:
                data = jql_search(payload)
                if data:
                    for issue in data.get('issues', []):
                        key = issue.get('key')
                        fields_resp = issue.get('fields', {})
                        logger.debug("Batch JQL returned issue %s with fields: %s", key, list(fields_resp.keys()))
                        summary = fields_resp.get('summary')
                        display = f"{key}: {summary}" if summary else key
                        if key:
                            epic_map[key] = display
                        # Try to find a parent (initiative) reference using heuristics
                        pkey = detect_parent_from_issue(issue)
                        if pkey:
                            logger.debug("Detected parent %s for epic %s (batch)", pkey, key)
                            epic_parent_map[key] = pkey
                            # attempt to find parent object in fields_resp if present
                            pfield = fields_resp.get('parent')
                            if pfield and isinstance(pfield, dict) and pfield.get('key') == pkey and pfield.get('fields') and pfield['fields'].get('summary'):
                                # parent embedded with summary — record it so we can use it later without fetching
                                ps = pfield['fields'].get('summary')

                                def _extract_description_from_fields(field_dict, prefer_summary=None):
                                    d = field_dict.get('description')
                                    if d:
                                        return d
                                    # look for long string fields that look like descriptions
                                    for kk, vv in field_dict.items():
                                        if kk in ('summary', 'issuetype', 'status', 'priority'):
                                            continue
                                        if isinstance(vv, str) and len(vv.strip()) > 40:
                                            if prefer_summary and vv.strip() == (prefer_summary or '').strip():
                                                continue
                                            return vv
                                        if isinstance(vv, dict):
                                            if 'value' in vv and isinstance(vv['value'], str) and len(vv['value'].strip()) > 40:
                                                return vv['value']
                                    return ""

                                pdesc_raw = _extract_description_from_fields(pfield['fields'], prefer_summary=ps)
                                desc_excerpt = ""
                                if pdesc_raw:
                                    if isinstance(pdesc_raw, dict):
                                        desc_excerpt = str(pdesc_raw)
                                    else:
                                        desc_excerpt = str(pdesc_raw).splitlines()[0][:120]
                                display = f"{pkey}: {ps}" if ps else pkey
                                if desc_excerpt:
                                    display = f"{display} — {desc_excerpt}"
                                embedded_parent_map[pkey] = {"key": pkey, "display": display, "description": pdesc_raw}
                                logger.debug("Parent %s embedded; recorded display: %s", pkey, display)
                            else:
                                parent_keys_to_fetch.add(pkey)
                else:
                    # fallback to per-issue attempt if search fails
                    for key in chunk:
                        try:
                            url2 = f"{JIRA_URL}/rest/api/2/issue/{key}"
                            r2 = requests.get(url2, auth=(JIRA_EMAIL, JIRA_API_TOKEN))
                            if r2.status_code == 200:
                                    d2 = r2.json()
                                    logger.debug("Per-issue fetch for %s returned fields: %s", key, list(d2.get('fields', {}).keys()))
                                    s2 = d2.get('fields', {}).get('summary')
                                    epic_map[key] = f"{key}: {s2}" if s2 else key
                                    # detect parent via heuristics on the full issue JSON
                                    pkey = detect_parent_from_issue(d2)
                                    if pkey:
                                        logger.debug("Detected parent %s for epic %s (per-issue)", pkey, key)
                                        epic_parent_map[key] = pkey
                                        parent_obj = d2.get('fields', {}).get('parent')
                                        if parent_obj and isinstance(parent_obj, dict) and parent_obj.get('key') == pkey and parent_obj.get('fields') and parent_obj['fields'].get('summary'):
                                            # record embedded parent display
                                            ps = parent_obj['fields'].get('summary')
                                            pdesc = parent_obj['fields'].get('description') or ""
                                            desc_excerpt = ""
                                            if pdesc:
                                                if isinstance(pdesc, dict):
                                                    desc_excerpt = str(pdesc)
                                                else:
                                                    desc_excerpt = str(pdesc).splitlines()[0][:120]
                                            display = f"{pkey}: {ps}" if ps else pkey
                                            if desc_excerpt:
                                                display = f"{display} — {desc_excerpt}"
                                            embedded_parent_map[pkey] = display
                                            logger.debug("Parent %s embedded; recorded display: %s (per-issue)", pkey, display)
                                        else:
                                            parent_keys_to_fetch.add(pkey)
                            else:
                                epic_map[key] = key
                        except Exception:
                            epic_map[key] = key
            except Exception:
                for key in chunk:
                    epic_map[key] = key

        # For any epics where we still don't have a parent detected, try linkedIssues search
        missing_parents = [k for k in epic_keys if k not in epic_parent_map]
        # First, try a per-issue GET for any epics where the batch JQL didn't expose parent info
        if missing_parents:
            for ek in list(missing_parents):
                try:
                    url_issue = f"{JIRA_URL}/rest/api/2/issue/{ek}"
                    r = requests.get(url_issue, params={"fields": "*all", "expand": "names,renderedFields"})
                    if r.status_code == 200:
                        d = r.json()
                        logger.debug("Per-issue GET returned for %s fields: %s", ek, list(d.get('fields', {}).keys()))
                        pkey = detect_parent_from_issue(d)
                        if pkey:
                            epic_parent_map[ek] = pkey
                            parent_obj = d.get('fields', {}).get('parent')
                            if parent_obj and isinstance(parent_obj, dict) and parent_obj.get('key') == pkey and parent_obj.get('fields') and parent_obj['fields'].get('summary'):
                                ps = parent_obj['fields'].get('summary')
                                # try to extract description from fields
                                def _extract_description_from_fields(field_dict, prefer_summary=None):
                                    dsc = field_dict.get('description')
                                    if dsc:
                                        return dsc
                                    for kk, vv in field_dict.items():
                                        if kk in ('summary', 'issuetype', 'status', 'priority'):
                                            continue
                                        if isinstance(vv, str) and len(vv.strip()) > 40:
                                            if prefer_summary and vv.strip() == (prefer_summary or '').strip():
                                                continue
                                            return vv
                                        if isinstance(vv, dict):
                                            if 'value' in vv and isinstance(vv['value'], str) and len(vv['value'].strip()) > 40:
                                                return vv['value']
                                    return ""

                                pdesc_raw = _extract_description_from_fields(parent_obj['fields'], prefer_summary=ps)
                                desc_excerpt = ""
                                if pdesc_raw:
                                    if isinstance(pdesc_raw, dict):
                                        desc_excerpt = str(pdesc_raw)
                                    else:
                                        desc_excerpt = str(pdesc_raw).splitlines()[0][:120]
                                display = f"{pkey}: {ps}" if ps else pkey
                                if desc_excerpt:
                                    display = f"{display} — {desc_excerpt}"
                                embedded_parent_map[pkey] = {"key": pkey, "display": display, "description": pdesc_raw}
                                logger.debug("Per-issue parent %s embedded; recorded display: %s", pkey, display)
                            else:
                                parent_keys_to_fetch.add(pkey)
                            # remove from missing_parents list since we found something
                            if ek in missing_parents:
                                missing_parents.remove(ek)
                except Exception:
                    logger.debug("Per-issue GET failed for %s", ek, exc_info=True)

        if missing_parents:
            for ek in missing_parents:
                # First try: look for Initiative in EMSS project linked to this epic
                jql1 = f'project = EMSS AND issue in linkedIssues("{ek}") AND issuetype = Initiative'
                search_url = f"{JIRA_URL}/rest/api/3/search/jql"
                payload1 = {"jql": jql1, "fields": "summary", "maxResults": 5}
                try:
                    data1 = jql_search(payload1)
                    if data1:
                        issues1 = data1.get('issues', [])
                        if issues1:
                            pk = issues1[0].get('key')
                            epic_parent_map[ek] = pk
                            parent_keys_to_fetch.add(pk)
                            continue
                except Exception:
                    pass
                # Fallback: any linked issue (take first), across projects
                jql2 = f'issue in linkedIssues("{ek}")'
                payload2 = {"jql": jql2, "fields": "summary", "maxResults": 5}
                try:
                    data2 = jql_search(payload2)
                    if data2:
                        issues2 = data2.get('issues', [])
                        if issues2:
                            pk = issues2[0].get('key')
                            epic_parent_map[ek] = pk
                            parent_keys_to_fetch.add(pk)
                except Exception:
                    pass

        # Now fetch parent (initiative) details for any parents we need (summary/description)
        initiative_map = {}  # parent_key -> display string (key: summary - short description)
        if parent_keys_to_fetch:
            parent_keys = list(parent_keys_to_fetch)
            for pchunk in chunks(parent_keys, 50):
                pq = ",".join(pchunk)
                pjql = f"key in ({pq})"
                # Use the API v3 JQL search endpoint
                purl = f"{JIRA_URL}/rest/api/3/search/jql"
                ppayload = {"jql": pjql, "fields": "summary,description", "maxResults": 100}
                try:
                    pdata = jql_search(ppayload)
                    if pdata:
                        for pitem in pdata.get('issues', []):
                            pkey = pitem.get('key')
                            pfields = pitem.get('fields', {})
                            psummary = pfields.get('summary')

                            def _extract_description_from_fields(field_dict, prefer_summary=None):
                                d = field_dict.get('description')
                                if d:
                                    return d
                                for kk, vv in field_dict.items():
                                    if kk in ('summary', 'issuetype', 'status', 'priority'):
                                        continue
                                    if isinstance(vv, str) and len(vv.strip()) > 40:
                                        if prefer_summary and vv.strip() == (prefer_summary or '').strip():
                                            continue
                                        return vv
                                    if isinstance(vv, dict):
                                        if 'value' in vv and isinstance(vv['value'], str) and len(vv['value'].strip()) > 40:
                                            return vv['value']
                                return ""

                            pdescription_raw = _extract_description_from_fields(pfields, prefer_summary=psummary)
                            # Use first line or short excerpt of description to keep slides tidy
                            desc_excerpt = ""
                            if pdescription_raw:
                                if isinstance(pdescription_raw, dict):
                                    desc_excerpt = str(pdescription_raw)
                                else:
                                    desc_excerpt = str(pdescription_raw).splitlines()[0][:120]
                            display = f"{pkey}: {psummary}" if psummary else pkey
                            if desc_excerpt:
                                display = f"{display} — {desc_excerpt}"
                            initiative_map[pkey] = {"key": pkey, "display": display, "description": pdescription_raw}
                    else:
                        # On failure, at least seed with keys
                        for pk in pchunk:
                            initiative_map[pk] = pk
                except Exception:
                    for pk in pchunk:
                        initiative_map[pk] = pk

        # Merge any embedded parent displays we discovered earlier so we don't need to fetch them
        # (embedded_parent_map is populated when per-issue JSON contained a parent object with summary).
        if embedded_parent_map:
            for pk, info in embedded_parent_map.items():
                if pk not in initiative_map:
                    # info is a dict {display, description}
                    # ensure embedded info has the key present
                    if isinstance(info, dict) and 'key' not in info:
                        info['key'] = pk
                    initiative_map[pk] = info
                    logger.debug("Seeded initiative_map from embedded_parent_map for %s -> %s", pk, info.get('display'))

        # Build epic -> initiative display mapping to pass into presentation (epic_goals param)
        epic_initiative_map = {}
        for epic_key, parent_key in epic_parent_map.items():
            # Prefer a fetched initiative info (dict), then an embedded parent info dict, then fall back to showing the raw parent key.
            if parent_key in initiative_map:
                epic_initiative_map[epic_key] = initiative_map[parent_key]
            elif parent_key in embedded_parent_map:
                epic_initiative_map[epic_key] = embedded_parent_map[parent_key]
            elif parent_key:
                # We couldn't fetch summary/description due to permissions or API errors. Show the raw key so the slide isn't blank.
                epic_initiative_map[epic_key] = {"key": parent_key, "display": parent_key, "description": ""}
            else:
                epic_initiative_map[epic_key] = None

        # Non-key epics: use the value itself as display
        for nk in non_keys:
            epic_map[nk] = nk

        # Prepare planned items for next sprint: stories from next planned sprint + in-progress stories from this sprint
        def _is_story_or_task(issue):
            try:
                itype = issue.get('fields', {}).get('issuetype', {}).get('name', '')
            except Exception:
                itype = ''
            return itype and itype.lower() in ('story', 'task')

        DONE_STATUSES = {"done", "closed", "resolved"}
        CANCELLED_STATUSES = {"cancelled", "canceled", "removed", "declined"}

        # In-progress stories from current sprint
        in_progress = []
        for issues_in_label in grouped.values():
            for issue in issues_in_label:
                if not _is_story_or_task(issue):
                    continue
                status_name = (issue.get('fields', {}).get('status', {}).get('name') or '').lower()
                if status_name and status_name not in DONE_STATUSES and status_name not in CANCELLED_STATUSES:
                    in_progress.append(issue)

        # Stories from the next planned sprint (if present)
        planned_next = []
        try:
            next_id = get_next_sprint_id()
            if next_id:
                next_issues = get_issues(next_id)
                for ni in next_issues:
                    if _is_story_or_task(ni):
                        planned_next.append(ni)
        except Exception as e:
            logger.debug("Could not fetch next sprint issues: %s", e)

        # Merge planned items (dedupe by key)
        planned_by_key = {}
        for it in planned_next + in_progress:
            k = it.get('key')
            if not k:
                continue
            planned_by_key[k] = it
        planned_items = list(planned_by_key.values())

        # If requested, dump the epic -> initiative mapping so the user can inspect what was discovered
        if args and getattr(args, 'dump_epic_map', False):
            try:
                import json as _json
                print("\n--- epic_initiative_map (epic_key -> initiative info) ---\n")
                print(_json.dumps(epic_initiative_map, indent=2, ensure_ascii=False))
                print("\n--- end epic_initiative_map ---\n")
            except Exception:
                logger.exception("Failed to dump epic_initiative_map")

        velocity_history = []
        try:
            velocity_history = build_velocity_history(
                JIRA_URL,
                BOARD_ID,
                (JIRA_EMAIL, JIRA_API_TOKEN),
                FIELD_STORY_POINTS,
                max_sprints=10,
            )
        except Exception as exc:
            logger.debug("Unable to build velocity history: %s", exc)

        create_presentation(
            grouped,
            sprint_name,
            sprint_start,
            sprint_end,
            filename=filename,
            epic_map=epic_map,
            epic_goals=epic_initiative_map,
            planned_items=planned_items,
            velocity_history=velocity_history,
        )
        spinner_message[0] = "Done!"
    finally:
        spinner_running = False
        spinner_thread.join()

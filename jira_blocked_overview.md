# Show Blocked Stories Overview

Displays all stories that are blocked by another work item, including summary, labels, assignee, blockers, and a direct Jira link.

## Usage

```sh
python jira_blocked_overview.py
```

## What it does
- Fetches all Jira issues of type 'Story' that have an 'is blocked by' issue link from the configured board.
- Prints a list with:
  - Issue key and summary
  - Labels
  - Assignee (or 'Unassigned')
  - Blocked by (list of blocking issue keys)
  - Direct link to the issue in Jira

## Requirements
- Jira API credentials in `.jira_environment` in the script directory.
- Python 3.7+
- `requests` package

## Example Output
```
Stories that are blocked by another work item:

STORY: MSEU-456: Example summary
  Labels: infra, urgent
  Assignee: John Smith
  Blocked by: MSEU-123, MSEU-789
  https://yourdomain.atlassian.net/browse/MSEU-456
```

---
MIT License

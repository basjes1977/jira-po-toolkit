# Show 'On Hold' Stories Overview

Displays all stories with status 'On hold', including summary, labels, assignee, and a direct Jira link.

## Usage

```sh
python jira_on_hold_overview.py
```

## What it does
- Fetches all Jira issues of type 'Story' with status 'On hold' from the configured board.
- Prints a list with:
  - Issue key and summary
  - Labels
  - Assignee (or 'Unassigned')
  - Direct link to the issue in Jira

## Requirements
- Jira API credentials in `.jira_environment` in the script directory.
- Python 3.7+
- `requests` package

## Example Output
```
Stories with status 'On hold':

STORY: MSEU-123: Example summary
  Labels: infra, urgent
  Assignee: Jane Doe
  https://yourdomain.atlassian.net/browse/MSEU-123
```

---
MIT License

# Check 'Ready' Stories (Sanity Check)

Checks all Stories in 'Ready' state for missing acceptance criteria and for a valid label.

## Usage

```sh
python jira_ready_sanity_check.py
```

## What it does
- Fetches all Stories in 'Ready' state from the configured board.
- Checks for:
  - Missing acceptance criteria (must be a markdown list in the custom field)
  - Missing valid label (from the PowerPoint generator's list)
- Prints a list with direct Jira links.

## Requirements
- Jira API credentials in `.jira_environment` in the script directory.
- Python 3.7+
- `requests` package

## Example Output
```
Stories in 'Ready' state missing Acceptance Criteria and/or valid Label:

STORY: MSEU-102: Example Story [ No Acceptance Criteria; No Valid Label ]
  https://yourdomain.atlassian.net/browse/MSEU-102
```

---
MIT License

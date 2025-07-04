# Check 'To Refine' Stories & Epics (Sanity Check)

Checks all Epics and Stories in 'To Refine' state for missing labels and acceptance criteria.

## Usage

```sh
python jira_refine_sanity_check.py
```

## What it does
- Fetches all Epics and Stories in 'To Refine' state from the configured board.
- Checks for:
  - Missing labels
  - Missing acceptance criteria (must be a markdown list in the custom field)
- Results are grouped by Epic and printed with direct Jira links.

## Requirements
- Jira API credentials in `.jira_environment` in the script directory.
- Python 3.7+
- `requests` package

## Example Output
```
Epics and Stories in 'To Refine' missing Label and/or Acceptance Criteria:

EPIC: MSEU-100: Example Epic [ No Label ]
  https://yourdomain.atlassian.net/browse/MSEU-100
  STORY: MSEU-101: Example Story [ No Acceptance Criteria ]
    https://yourdomain.atlassian.net/browse/MSEU-101
```

---
MIT License

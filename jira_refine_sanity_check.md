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

```text
Epics and Stories in 'To Refine' missing Label and/or Acceptance Criteria:

EPIC: MSEU-100: Example Epic [ No Label ]
  https://yourdomain.atlassian.net/browse/MSEU-100
  STORY: MSEU-101: Example Story [ No Acceptance Criteria ]
    https://yourdomain.atlassian.net/browse/MSEU-101
```

## Setup: .jira_environment

Before running any scripts, create a file named `.jira_environment` in the script directory with the following content:

```sh
# Jira connection settings
export JT_JIRA_URL="https://<your-domain>.atlassian.net/"
export JT_JIRA_USERNAME="your-email@domain.com"
export JT_JIRA_PASSWORD="your-jira-api-token"
export JT_JIRA_BOARD="<board-id>"  # Use the board *number*, not the board name!

# Custom field IDs (update these to match your Jira instance)
export JT_JIRA_FIELD_STORY_POINTS="customfield_10024"
export JT_JIRA_FIELD_EPIC_LINK="customfield_10031"
export JT_JIRA_FIELD_ACCEPTANCE_CRITERIA="customfield_10140"

# (Optional) SMTP settings for notification scripts
export SMTP_SERVER="smtp.yourdomain.com"
export SMTP_PORT="587"
export SMTP_USERNAME="your-smtp-user"
export SMTP_PASSWORD="your-smtp-password"
export SMTP_FROM="your-email@domain.com"
```

- **Jira Board:** The board ID is a number, not the board name.
- **Custom Fields:** If your Jira uses different custom field IDs, update them here.
- **SMTP:** Only needed for scripts that send email notifications.

After editing, restart your terminal or reload your environment to apply the changes.

---

MIT License

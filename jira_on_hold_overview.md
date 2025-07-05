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

```text
Stories with status 'On hold':

STORY: MSEU-123: Example summary
  Labels: infra, urgent
  Assignee: Jane Doe
  https://yourdomain.atlassian.net/browse/MSEU-123
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

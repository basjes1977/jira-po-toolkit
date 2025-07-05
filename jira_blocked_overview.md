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

```text
Stories that are blocked by another work item:

STORY: MSEU-456: Example summary
  Labels: infra, urgent
  Assignee: John Smith
  Blocked by: MSEU-123, MSEU-789
  https://yourdomain.atlassian.net/browse/MSEU-456
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

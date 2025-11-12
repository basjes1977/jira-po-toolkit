# Check 'Ready' Stories (Sanity Check)

Checks all Stories in 'Ready' state for missing acceptance criteria and for a valid label.

## Usage

```sh
python jira_ready_sanity_check.py
```

### Optional Flags

- `--fix-labels`: interactively assign one of the approved labels (comma-separated input is not needed here). When run via `jpt_menu.py` or without the flag, the script automatically prompts you to launch the helper if any 'Ready' stories lack a valid label.

## What it does

- Fetches all Stories in 'Ready' state from the configured board.
- Checks for:
  - Missing acceptance criteria (must be a markdown list in the custom field)
  - Missing valid label (from the PowerPoint generator's list)
- If a story lacks description *and* acceptance criteria *and* a valid label, the script can transition it back to the `To Refine` state.
- Prints a list with direct Jira links.

## Requirements

- Jira API credentials in `.jira_environment` in the script directory.
- Python 3.7+
- `requests` package

## Example Output

```text
Stories in 'Ready' state missing Acceptance Criteria and/or valid Label:

STORY: MSEU-102: Example Story [ No Acceptance Criteria; No Valid Label ]
  https://yourdomain.atlassian.net/browse/MSEU-102
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

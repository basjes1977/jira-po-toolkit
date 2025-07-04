# Jira To Do Notifier (`jira_todo_notify.py`)

This script checks your Jira backlog for stories in the "To Do" state, prints a summary with clickable links, and notifies assignees of their stories via email.

## Features

- Fetches all stories in the "To Do" state for the board configured in `.jira_environment`.
- Prints each story with a clickable Jira link.
- Groups stories by assignee and sends each assignee a single email listing their "To Do" stories.
- Supports a `--test` mode to send all notifications only to a test address.
- Email method (SMTP or local Outlook) and platform (Mac/Windows) are configurable via `smtp_settings.env` or command line.

## Usage

```sh
python jira_todo_notify.py
```

### Email Method Options

You can choose how emails are sent:

- **Default**: Uses the method and platform set in `smtp_settings.env` (`EMAIL_METHOD` and `OUTLOOK_PLATFORM`).
- **Override via CLI:**
    - `--email-method smtp` (default)
    - `--email-method outlook --outlook-platform mac`
    - `--email-method outlook --outlook-platform windows`


### Test Mode

You can enable test mode to send all notifications to a single test address (default: `bas.rutjes@eu.equinix.com`).

- Enable in `smtp_settings.env`:
  ```sh
  TEST_MODE=true
  TEST_EMAIL=your_test_email@domain.com
  ```
- Or override on the command line:
  ```sh
  python jira_todo_notify.py --test --test-email your_test_email@domain.com
  ```

When test mode is enabled, all notifications are sent to the configured test email address with all "To Do" stories.

## Quick Start

1. Clone or download this repository.
2. Install requirements:

   ```sh
   pip install -r requirements.txt
   ```
3. Configure `.jira_environment` and `smtp_settings.env` as described below.
4. Run the script:

   ```sh
   python jira_todo_notify.py
   ```

---

## Confirmation Prompt (Safety Feature)

To prevent accidental mass notifications, the script will prompt for confirmation before sending real emails when test mode is OFF.

- You must type `yes` to proceed. Any other input will abort the script.

**Example:**

```sh
[CONFIRMATION] Test mode is OFF. This will send real emails to all assignees.
Are you sure you want to continue? Type 'yes' to proceed:
```

If you do not type `yes`, the script will exit without sending any emails.

---

## Configuration

### Jira Environment

The script uses `.jira_environment` in the same directory for Jira credentials and board info. Example:

```sh
export JT_JIRA_URL="https://yourcompany.atlassian.net/"
export JT_JIRA_USERNAME="your.email@company.com"
export JT_JIRA_PASSWORD="your_api_token"
export JT_JIRA_BOARD="123"
```


### SMTP/Outlook & Test Settings

Edit `smtp_settings.env` to configure the SMTP server, Outlook defaults, and test mode. Example:

```sh
# For SMTP
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your_email@domain.com
SMTP_PASSWORD=your_password
FROM_EMAIL=your_email@domain.com
FROM_NAME=Jira Bot

# For local SMTP
# SMTP_SERVER=localhost
# SMTP_PORT=25
# FROM_NAME=Jira Bot

# Default email method: smtp or outlook
EMAIL_METHOD=smtp
# If using outlook, set platform: mac or windows
OUTLOOK_PLATFORM=mac

# Test mode options
TEST_MODE=false
TEST_EMAIL=your_test_email@domain.com
```


## Requirements

- Python 3.7+
- `requests` (install with `pip install requests`)
- If you want to use Outlook on Windows, you must also install `pywin32`:
  - Uncomment the `pywin32` line in `requirements.txt` and run `pip install -r requirements.txt`

## Notes

- The script uses only standard library modules and `requests` (and optionally `pywin32` for Windows Outlook).
- `smtplib` is part of the Python standard library and does not need to be installed.
- Only stories with an assignee and a valid email address will be notified. Unassigned stories are sent to `bas.rutjes@eu.equinix.com`.
- The email body includes a message for the assignee about updating and refining their stories.

## Troubleshooting

- If emails are not sent, check your SMTP/Outlook settings and firewall.
- If you get authentication errors, verify your SMTP credentials in `smtp_settings.env`.
- For Jira API errors, check your `.jira_environment` values and Jira permissions.
- For Outlook on Windows, ensure `pywin32` is installed and Outlook is running.

---

## Known Limitations: Outlook for Mac (AppleScript)

**Outlook for Mac (AppleScript) Limitation:**

- When using `EMAIL_METHOD=outlook` and `OUTLOOK_PLATFORM=mac`, the script sends emails via AppleScript to Microsoft Outlook for Mac.
- Due to a long-standing limitation/bug in Outlook for Mac's AppleScript interface, **all line breaks and paragraph breaks in the plain text body are ignored or collapsed** when the email is sent. This means the recipient will see the entire message as a single paragraph, regardless of how the text is formatted in the script.
- This affects all programmatic mail sent via AppleScript, not just this script. There is currently no reliable workaround.
- **Workarounds:**
  - Use `EMAIL_METHOD=smtp` for correct formatting (recommended).
  - Use Outlook on Windows (which supports HTML and respects line breaks).
  - If you need to send via Outlook for Mac, consider opening a draft manually and sending it yourself (contact your admin or see script for possible options).

**Summary:**

- This is a limitation of Outlook for Mac, not the script. The script generates correct plain text, but Outlook for Mac will not respect line breaks when sending via AppleScript.

---

## License

(Add your license here if you plan to share or distribute this script.)

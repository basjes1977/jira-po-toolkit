# JiraPresentationTool - Unified Menu & Scripts

![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

This project was inspired by a script a colleague had created, but that solution did not completely suit my wishes. I started by building the presentation functionality, and from there the toolkit evolved into a unified terminal menu (`jpt_menu.py`) to run a suite of Jira automation and reporting scripts for sprint management, notifications, sanity checks, and forecasting.

---

## Table of Contents

- [Contributor Notes](#contributor-notes)
- [Getting Started](#getting-started)
- [Menu Options & Scripts](#menu-options--scripts)
- [Troubleshooting](#troubleshooting)
- [Setup](#setup)
- [How to Acquire a Jira API Token](#how-to-acquire-a-jira-api-token)
- [Environment Configuration](#environment-configuration)
- [See Also](#see-also)
- [Support](#support)
- [Changelog](#changelog)
- [How to Find Custom Field IDs in Jira](#how-to-find-custom-field-ids-in-jira)
- [License](#license)

---

## Getting Started

1. **Clone the repository and install dependencies** (see [Setup](#setup)).
2. **Configure your Jira credentials** in `.jira_environment`.
3. **Activate the virtual environment:**

   **Option A: Manual activation** (required each time you open a new terminal):
   ```sh
   source .venv/bin/activate  # On macOS/Linux
   # .venv\Scripts\activate   # On Windows
   ```

   **Option B: Automatic activation** (recommended - set up once, see [Automatic Virtual Environment Activation](#automatic-virtual-environment-activation-optional-but-recommended)):
   - Install and configure `direnv`
   - Run `direnv allow` in the project directory
   - The venv will auto-activate when you `cd` into the directory

4. **Run the menu:**

   ```sh
   python jpt_menu.py
   ```

---

## Menu Options & Scripts

### 1. Generate Sprint PowerPoint Presentation (`jpt.py`)

- **Purpose:** Generates a PowerPoint presentation for the current sprint, grouped by label, with summary and upcoming slides.
- **Features:**
  - Emoji spinner for progress indication during data fetch and presentation creation.
  - Handles file locking: prompts you to close the PowerPoint file if it is open before saving.
  - Output file name is sanitized to remove problematic characters.
  - Only issues of type 'story' or 'task' are included.
  - Adds summary, velocity (last 10 sprints with line chart), upcoming, and "thanks" slides using the template.
- **Instructions:**
  - Ensure `sprint-template.pptx` is present in the script directory.
  - Output file is named after the sprint (e.g., `Sprint 42.pptx`).
- [See detailed README](./jpt.md)

### 2. Send Jira TODO Notification Email (`jira_todo_notify.py`)

- **Purpose:** Sends notification emails for Jira TODOs.
- **Instructions:**
  - Supports SMTP/Outlook, test mode, and HTML/plain text.
  - Configure credentials in `.env` or as prompted.
- [See detailed README](./jira_todo_notify.md)

### 3. Check 'To Refine' Stories & Epics (Sanity Check) (`jira_refine_sanity_check.py`)

- **Purpose:** Checks all Epics and Stories in 'To Refine' state for missing labels and acceptance criteria.
- **Instructions:**
  - Acceptance criteria must be a markdown list in the custom field.
  - Results are grouped by Epic.
  - Run with `python jira_refine_sanity_check.py --fix-labels` to interactively add one or more labels (comma-separated) to unlabeled stories; defaults come from sibling stories/epics. When launched without flags (via the menu) you’ll be prompted to add labels automatically if any are missing.
- [See detailed README](./jira_refine_sanity_check.md)

### 4. Check 'Ready' Stories (Sanity Check) (`jira_ready_sanity_check.py`)

- **Purpose:** Checks all Stories in 'Ready' state for missing acceptance criteria and for a valid label.
- **Instructions:**
  - A story is only 'Ready' if it has acceptance criteria (markdown list) and a label from the PowerPoint generator's list.
  - Run with `python jira_ready_sanity_check.py --fix-labels` to assign one or more labels interactively (comma-separated); when launched from the menu you'll be prompted automatically if any labels are missing.
  - Stories lacking description, acceptance criteria, and a valid label trigger an early prompt so you can move them back to `To Refine` before spending time labeling.
- [See detailed README](./jira_ready_sanity_check.md)

### 5. Show 'On Hold' Stories Overview (`jira_on_hold_overview.py`)

- **Purpose:** Displays all stories with status 'On hold', including summary, labels, assignee, and a direct Jira link.
- [See detailed README](./jira_on_hold_overview.md)

### 6. Show Blocked Stories Overview (`jira_blocked_overview.py`)

- **Purpose:** Displays all stories that are blocked by another work item, including summary, labels, assignee, blockers, and a direct Jira link.
- [See detailed README](./jira_blocked_overview.md)

### 7. Forecast Next Sprint Capacity (Excel Export) (`jpt_forecast.py`)

- **Purpose:** Fetches last 10 sprints, calculates achieved points/time, prompts for team availability, and forecasts next sprint's capacity.
- **Instructions:**
  - Exports results and forecast to Excel, appending new sprints only, with trend charts.
  - Close the Excel file before running.
- [See detailed README](./jpt_forecast.md)

---

## Troubleshooting

- **Virtual Environment Issues:**
  - If you see errors like "bad interpreter" or "no such file or directory" when running Python/pip, your virtual environment may be corrupted
  - Solution: Remove and recreate the virtual environment:
    ```sh
    rm -rf .venv
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

- **SSL/Certificate Issues (e.g., Zscaler):**
  - When you run `jpt_menu.py`, you'll be prompted to choose SSL verification mode:
    - **Option 1**: Use Zscaler certificate (if you're behind Zscaler proxy)
    - **Option 2**: Use standard SSL verification (no proxy)
    - **Option 3**: Disable SSL verification (bypasses security, use for testing only)
  - If you get "certificate verify failed" errors with option 2, you're likely behind Zscaler and should use option 1
  - This configuration is set once per session when you start the menu

- **PowerPoint File Lock:**
  - If the script cannot save the presentation, close the PowerPoint file and press Enter when prompted.

---

## Setup

**Prerequisites:** Python 3.7 or higher

1. **Create and activate a virtual environment (recommended):**

   ```sh
   python3 -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # .venv\Scripts\activate   # On Windows
   ```

   Your prompt should now show `(.venv)` at the beginning.

2. **Install dependencies:**

   With the virtual environment activated, run:

   ```sh
   pip install -r requirements.txt
   ```

   This will install: `requests`, `python-pptx`, `openpyxl`, `python-dotenv`, and dependencies.

3. **Configure Jira credentials:**
   - Create `.jira_environment` in the script directory:

     ```sh
     export JT_JIRA_URL="https://<your-domain>.atlassian.net/"
     export JT_JIRA_USERNAME="your-email@domain.com"
     export JT_JIRA_PASSWORD="your-jira-api-token"
     export JT_JIRA_BOARD="<board-id>"  # Use the board *number*, not the board name!
     ```

4. **Templates:**
   - For PowerPoint export, place `sprint-template.pptx` in the script directory.

5. **Verify installation:**

   Test that all modules import correctly:

   ```sh
   python -c "import jira_config, jpt, jira_metrics; print('✓ Installation successful')"
   ```

---

## Automatic Virtual Environment Activation (Optional but Recommended)

To automatically activate the virtual environment when you enter the project directory, you can use `direnv`:

### Installing direnv

**macOS (using Homebrew):**
```sh
brew install direnv
```

**Linux (Ubuntu/Debian):**
```sh
sudo apt install direnv
```

**Linux (other distributions):**
See [direnv installation guide](https://direnv.net/docs/installation.html)

### Configuring direnv

After installing direnv, add the following to your shell configuration file:

**For Bash** (`~/.bashrc` or `~/.bash_profile`):
```sh
eval "$(direnv hook bash)"
```

**For Zsh** (`~/.zshrc`):
```sh
eval "$(direnv hook zsh)"
```

**For Fish** (`~/.config/fish/config.fish`):
```sh
direnv hook fish | source
```

Then **reload your shell** for the changes to take effect:
```sh
source ~/.bashrc  # For Bash
source ~/.zshrc   # For Zsh
```

Or simply open a new terminal window/tab.

### Allowing direnv

The first time you enter the project directory after installing direnv, run:
```sh
direnv allow
```

This authorizes direnv to automatically load the `.envrc` file in this directory.

**Done!** Now whenever you `cd` into the project directory, the virtual environment will activate automatically, and it will deactivate when you leave.

---

## How to Acquire a Jira API Token

To use these scripts, you need a Jira API token for authentication. Follow these steps:

1. **Go to Atlassian API tokens:**
   [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

2. **Click "Create API token".**

3. **Enter a label** (e.g., "JiraPresentationTool") and click **Create**.

4. **Copy the generated token** and save it somewhere safe.
   **You will not be able to see it again!**

5. **Use this token as `JT_JIRA_PASSWORD`** in your `.jira_environment` file:

   ```sh
   export JT_JIRA_PASSWORD="your-jira-api-token"
   ```

6. **Use your Atlassian email address** as `JT_JIRA_USERNAME`.

**More info:**
See Atlassian’s documentation: [Manage API tokens for your Atlassian account](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)

---

## Environment Configuration

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

All scripts import credentials via `jira_config.py`, so updating this single file keeps every CLI in sync.

After editing, restart your terminal or reload your environment to apply the changes.

---

**Tip:**
You can find your custom field IDs using the Jira REST API. See [How to Find Custom Field IDs in Jira](#how-to-find-custom-field-ids-in-jira) for step-by-step instructions.

---

## See Also

See each script's README for more details and usage examples.

---

## Support

This project is free to use, including for commercial purposes, under the MIT License.
If you find it useful and would like to support its development, consider buying me a coffee or making a donation:

☕ [Buy Me a Coffee](https://coff.ee/basjes)
💸 [Donate via PayPal](https://paypal.me/basjes1977)

---

## Changelog

- **2025-07-04**: Added per-script README files, improved menu, and enhanced documentation structure.
- **2025-07-03**: Added blocked/on-hold story overviews, improved Excel/PowerPoint export, and unified menu.
- **2025-07-01**: Initial release with PowerPoint generator, notification, and sanity check scripts.

---

## How to Find Custom Field IDs in Jira

To work with custom fields (such as acceptance criteria) in scripts or API calls, you often need the custom field's internal ID (e.g., `customfield_12345`). You can find these IDs using the Jira REST API:

1. **Get issue JSON via API:**
   - Open an issue in your browser and add `?expand=names` to the URL, or use `curl`:

     ```sh
     curl -u your-email@domain.com:your-jira-api-token \
       -H "Accept: application/json" \
       "https://<your-domain>.atlassian.net/rest/api/3/issue/<ISSUE-KEY>?expand=names"
     ```

2. **Inspect the JSON output:**
   - Look for the `fields` section. Custom fields will appear as keys like `customfield_XXXXX`.
   - The `names` section maps these IDs to their human-readable names.

3. **More info:**
   - See the [Jira Cloud REST API Reference](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/#version) for details.

---

## License

MIT License

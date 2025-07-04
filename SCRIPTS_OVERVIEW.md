# JiraPresentationTool Scripts Overview

This repository contains a set of scripts to automate and support Jira sprint reporting, notifications, sanity checks, and forecasting. All scripts can be run from a unified terminal menu (`jpt_menu.py`).

## Main Menu (jpt_menu.py)
Run the menu to access all tools:

```
python jpt_menu.py
```

## Available Tools

- **Generate Sprint PowerPoint Presentation (`jpt.py`)**
  - Generates a PowerPoint presentation for the current sprint, grouped by label, with summary and upcoming slides.
  - Requires `sprint-template.pptx` in the script directory.

- **Send Jira TODO Notification Email (`jira_todo_notify.py`)**
  - Sends notification emails for Jira TODOs. Supports SMTP/Outlook, test mode, and HTML/plain text.

- **Check 'To Refine' Stories & Epics (Sanity Check) (`jira_refine_sanity_check.py`)**
  - Checks all Epics and Stories in 'To Refine' state for missing labels and acceptance criteria (markdown list in custom field).

- **Check 'Ready' Stories (Sanity Check) (`jira_ready_sanity_check.py`)**
  - Checks all Stories in 'Ready' state for missing acceptance criteria and for a valid label (from the PowerPoint generator's list).

- **Show 'On Hold' Stories Overview (`jira_on_hold_overview.py`)**
  - Displays all stories with status 'On hold', including summary, labels, assignee, and a direct Jira link.

- **Show Blocked Stories Overview (`jira_blocked_overview.py`)**
  - Displays all stories that are blocked by another work item, including summary, labels, assignee, blockers, and a direct Jira link.

- **Forecast Next Sprint Capacity (Excel Export) (`jpt_forecast.py`)**
  - Fetches last 10 sprints, calculates achieved points/time, prompts for team availability, and forecasts next sprint's capacity.
  - Exports results and forecast to Excel, appending new sprints only, with trend charts.

## Setup
- See the main `README.md` for setup instructions, including `.jira_environment` and dependencies.

## Notes
- All scripts require valid Jira API credentials in `.jira_environment`.
- For PowerPoint/Excel export, close the output file before running the script to avoid file lock errors.
- For best results, run all scripts from the main menu (`jpt_menu.py`).

---
For more details on each script, see the comments at the top of each file or run the menu for descriptions.

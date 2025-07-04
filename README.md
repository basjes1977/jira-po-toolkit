# JiraPresentationTool - Unified Menu & Scripts

![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## Table of Contents

- [Getting Started](#getting-started)
- [Menu Options & Scripts](#menu-options--scripts)
- [Setup](#setup)
- [Changelog](#changelog)
- [Jira API Documentation](#jira-api-documentation)
- [License](#license)

## Jira API Documentation

- [Jira Cloud REST API Reference](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)

---

## Changelog

- **2025-07-04**: Added per-script README files, improved menu, and enhanced documentation structure.
- **2025-07-03**: Added blocked/on-hold story overviews, improved Excel/PowerPoint export, and unified menu.
- **2025-07-01**: Initial release with PowerPoint generator, notification, and sanity check scripts.

git clone <repo-url>
cd JiraPresentationTool
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export JT_JIRA_URL="https://<your-domain>.atlassian.net/"
export JT_JIRA_USERNAME="your-email@domain.com"
export JT_JIRA_PASSWORD="your-jira-api-token"
export JT_JIRA_BOARD="<board-id>"
python jpt.py

# JiraPresentationTool - Unified Menu & Scripts

This project provides a unified terminal menu (`jpt_menu.py`) to run a suite of Jira automation and reporting scripts for sprint management, notifications, sanity checks, and forecasting.

## Getting Started

1. **Clone the repository and install dependencies** (see below).
2. **Configure your Jira credentials** in `.jira_environment` (see below).
3. **Run the menu:**

```sh
python jpt_menu.py
```

You will see a menu with the following options:

---

## Menu Options & Scripts

### 1. Generate Sprint PowerPoint Presentation (`jpt.py`)
- **Purpose:** Generates a PowerPoint presentation for the current sprint, grouped by label, with summary and upcoming slides.
- **Instructions:**
  - Ensure `sprint-template.pptx` is present in the script directory.
  - Output file is named after the sprint (e.g., `Sprint 42.pptx`).
  - Only issues of type 'story' or 'task' are included.
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
- [See detailed README](./jira_refine_sanity_check.md)

### 4. Check 'Ready' Stories (Sanity Check) (`jira_ready_sanity_check.py`)
- **Purpose:** Checks all Stories in 'Ready' state for missing acceptance criteria and for a valid label.
- **Instructions:**
  - A story is only 'Ready' if it has acceptance criteria (markdown list) and a label from the PowerPoint generator's list.
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

## Setup

1. **Install dependencies:**
   - Python 3.7+
   - `pip install -r requirements.txt`
2. **Configure Jira credentials:**
   - Create `.jira_environment` in the script directory:
     ```
     export JT_JIRA_URL="https://<your-domain>.atlassian.net/"
     export JT_JIRA_USERNAME="your-email@domain.com"
     export JT_JIRA_PASSWORD="your-jira-api-token"
     export JT_JIRA_BOARD="<board-id>"
     ```
3. **Templates:**
   - For PowerPoint export, place `sprint-template.pptx` in the script directory.

---

## See each script's README for more details and usage examples.

---
MIT License

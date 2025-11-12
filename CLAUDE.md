# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JiraPresentationTool is a Python-based suite of Jira automation and reporting scripts for sprint management. The project provides a unified terminal menu (`jpt_menu.py`) to run various operations including PowerPoint generation, sanity checks, notifications, and capacity forecasting.

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Launch the main menu (recommended entry point)
python jpt_menu.py

# Run individual scripts directly
python jpt.py                          # Generate sprint PowerPoint
python jira_refine_sanity_check.py     # Check 'To Refine' stories
python jira_ready_sanity_check.py      # Check 'Ready' stories
python jpt_forecast.py                 # Forecast next sprint capacity
python jira_todo_notify.py             # Send TODO notifications
python jira_blocked_overview.py        # Show blocked stories
python jira_on_hold_overview.py        # Show on-hold stories
```

### Testing Imports
```bash
# Verify all modules import correctly
python - <<'PY'
import jira_config,jpt,jpt_forecast,jira_refine_sanity_check,jira_ready_sanity_check,jira_todo_notify,jira_blocked_overview,jira_on_hold_overview
print('import ok')
PY
```

## Architecture

### Configuration Management
- **All Jira credentials and settings** are loaded from `.jira_environment` file (not committed to git)
- The `jira_config.py` module provides centralized configuration loading via `load_jira_env()` and `get_jira_setting()`
- **Never duplicate parsing logic** - always import from `jira_config.py`
- Custom field IDs (story points, epic link, acceptance criteria) are configured in `.jira_environment`

### Core Components

**Menu System (`jpt_menu.py`)**
- Single entry point for all scripts
- Displays explanations before running each option
- Uses `subprocess.run()` with `sys.executable` to ensure same Python environment

**PowerPoint Generation (`jpt.py` + `jpt_presentation.py`)**
- `jpt.py`: Main script for data fetching with retry logic and JQL search fallbacks
- `jpt_presentation.py`: Isolated PowerPoint rendering logic
- Uses `sprint-template.pptx` as template
- Includes velocity slide with 10-sprint history (line chart of points vs. hours)
- HTTP helper `jira_get()` implements retry logic for transient failures
- Monkey-patches `requests.get` to use retry logic throughout

**Metrics and Forecasting (`jira_metrics.py`)**
- Shared helpers for sprint velocity calculations
- Functions: `get_recent_sprints()`, `get_sprint_issues()`, `achieved_points_and_time()`, `build_velocity_history()`
- Used by both PowerPoint generation (velocity slide) and forecast script

**Sanity Check Scripts**
- `jira_refine_sanity_check.py`: Checks Epics/Stories in 'To Refine' for missing labels and acceptance criteria
  - Auto-prompts to launch label helper if unlabeled stories exist
  - `--fix-labels` flag forces interactive label assignment
  - Accepts comma-separated labels, normalizes case-insensitively
- `jira_ready_sanity_check.py`: Checks Stories in 'Ready' state
  - Detects "severely invalid" stories (no description + no AC + no label)
  - Offers to transition invalid stories back to 'To Refine' before labeling
  - `--fix-labels` flag available for interactive label assignment

**Forecast Script (`jpt_forecast.py`)**
- Fetches last 10 sprints, calculates velocity metrics
- Prompts for team availability
- Exports to Excel (`sprint_forecast_history.xlsx`) with trend charts
- **Important**: Users must close Excel file before running to avoid file locks

### Data Flow
1. All scripts load credentials via `jira_config.load_jira_env()`
2. Scripts make authenticated requests to Jira REST API (v1.0 agile and v3 core APIs)
3. PowerPoint/Excel scripts use templates and write to local files
4. Sanity check scripts can interactively update Jira via API

### File Organization
- All Python scripts live at repository root
- Each major script has a companion `.md` file with detailed documentation
- Template file: `sprint-template.pptx` (required for PowerPoint generation)
- Generated files: `Sprint_Review.pptx` (or `Sprint {name}.pptx`), `sprint_forecast_history.xlsx`

## Important Implementation Details

### Jira API Interactions
- **Story points field**: Configured as `JT_JIRA_FIELD_STORY_POINTS` (typically `customfield_10024`)
- **Epic link field**: Configured as `JT_JIRA_FIELD_EPIC_LINK` (typically `customfield_10031`)
- **Acceptance criteria field**: Configured as `JT_JIRA_FIELD_ACCEPTANCE_CRITERIA` (typically `customfield_10140`)
- **Board ID**: Must be numeric, not board name (`JT_JIRA_BOARD`)
- Only 'story' and 'task' issue types are included in presentations
- "Done" statuses: `done`, `closed`, `resolved`

### JQL Search Strategy
- `jpt.py` implements fallback logic trying multiple API endpoints and payload formats
- First tries `/rest/api/3/search/jql`, then falls back to `/rest/api/3/search`
- Tries multiple payload shapes because different Jira Cloud instances accept different formats

### Error Handling
- HTTP retry logic in `jira_get()` handles 5xx errors and network issues
- PowerPoint file lock handling: prompts user to close file if save fails
- Velocity fetch failures log at DEBUG level but don't block presentation generation
- SSL/Certificate issues: Interactive prompt in `jpt_menu.py` offers three SSL verification modes:
  - Option 1: Use Zscaler certificate (for Zscaler proxy environments)
  - Option 2: Use standard SSL verification (default, no proxy)
  - Option 3: Disable SSL verification (bypasses security, for testing only)
  - Uses `get_ssl_verify()` from `jira_config.py` to determine SSL verification setting
  - All requests across all scripts automatically use the correct SSL configuration

### Label Management
- Both sanity check scripts normalize labels case-insensitively against existing tags
- Scripts accept comma-separated label input for multiple labels at once
- Label updates replace entire label list (after deduplication)
- Custom platform tags are preserved during updates

## Workflow Guidelines

### When Adding New Scripts
1. Add script to `MENU` list in `jpt_menu.py` with description
2. Add explanation to `EXPLANATIONS` dict in `jpt_menu.py`
3. Create companion `.md` file with detailed documentation
4. Update `README.md` menu section
5. Keep `AGENTS.md` synchronized with new workflows
6. Use `jira_config.load_jira_env()` for credentials - never duplicate parsing

### When Adding New Data to Presentations
- Pass new data via parameters to `create_presentation()` in `jpt_presentation.py`
- Keep rendering logic isolated inside `jpt_presentation.py`
- Keep data fetching logic in `jpt.py`
- Use shared helpers from `jira_metrics.py` for sprint calculations

### When Modifying Configuration
- Update `.jira_environment` file (create from README example if needed)
- Never hardcode credentials or custom field IDs
- Use `jira_config.get_jira_setting()` for accessing individual settings

## Environment Variables

```bash
# Required Jira connection settings
JT_JIRA_URL              # Jira instance URL (e.g., https://example.atlassian.net/)
JT_JIRA_USERNAME         # Atlassian email
JT_JIRA_PASSWORD         # Jira API token
JT_JIRA_BOARD            # Board ID (numeric)

# Required custom field IDs
JT_JIRA_FIELD_STORY_POINTS
JT_JIRA_FIELD_EPIC_LINK
JT_JIRA_FIELD_ACCEPTANCE_CRITERIA

# Optional debugging
JPT_VERBOSE              # Set to 1/true/True for DEBUG logging

# Optional SMTP settings (for notification scripts)
SMTP_SERVER
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
SMTP_FROM

# Optional SSL certificate handling
JT_SSL_VERIFY            # Set by jpt_menu.py based on user prompt; can also be set manually
                         # - "true"/"1": Standard SSL verification (default)
                         # - "false"/"0": Disable SSL verification (not recommended)
                         # - Path to certificate file (e.g., "/path/to/Zscaler.pem")
REQUESTS_CA_BUNDLE       # Alternative SSL cert path (falls back to this if JT_SSL_VERIFY not set)
```

## Dependencies

- `requests`: HTTP library for Jira API calls
- `python-pptx`: PowerPoint generation
- `openpyxl`: Excel export functionality
- `dotenv`: Environment variable loading (optional)
- `pywin32`: Windows-only, for Outlook integration (commented in requirements.txt)

Python 3.7+ required.

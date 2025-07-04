# Forecast Next Sprint Capacity (Excel Export)

Fetches last 10 sprints, calculates achieved points/time, prompts for team availability, and forecasts next sprint's capacity. Exports results and forecast to Excel, appending new sprints only, with trend charts.

## Usage

```sh
python jpt_forecast.py
```

## What it does
- Fetches last 10 completed sprints from the configured board.
- Calculates achieved story points and time.
- Prompts for team member availability for the next sprint.
- Forecasts next sprint's capacity (1, 3, 5, 10 sprint averages).
- Exports results and forecast to Excel, appending new sprints only, with trend charts.
- Checks for Excel file lock before saving.

## Requirements
- Jira API credentials in `.jira_environment` in the script directory.
- Python 3.7+
- `requests`, `openpyxl`

## Example Output
```
Excel file with sprint history and forecast saved as: sprint_forecast_history.xlsx
```

---
MIT License

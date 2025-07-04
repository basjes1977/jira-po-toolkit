# Generate Sprint PowerPoint Presentation

Generates a PowerPoint presentation for the current sprint, grouped by label, with summary and upcoming slides.

## Usage

```sh
python jpt.py
```

## What it does
- Fetches Jira sprint data and generates a PowerPoint presentation using a template.
- Groups issues by label, displays issue details, and includes summary and upcoming slides.
- Output file is named after the sprint (e.g., `Sprint 42.pptx`).
- Only issues of type 'story' or 'task' are included.

## Requirements
- Jira API credentials in `.jira_environment` in the script directory.
- Python 3.7+
- `requests`, `python-pptx`, `dotenv`
- `sprint-template.pptx` in the script directory

## Example Output
```
Presentation saved as Sprint_42.pptx
```

---
MIT License

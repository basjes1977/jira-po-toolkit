# Jira Refine Sanity Check (`jira_refine_sanity_check.py`)

This script helps you ensure that all Epics and User Stories in the "To Refine" state are ready for refinement by checking for missing labels and/or missing acceptance criteria.

## What It Does

- Fetches all Epics and Stories in the "To Refine" state from your Jira board.
- Checks each Epic and Story for:
  - Missing labels
  - Missing acceptance criteria (in the `acceptanceCriteria` or `customfield_10032` field)
- Groups and sorts results by Epic and Story.
- Prints a clear, clickable summary to the terminal, showing which items are missing required information.

## Usage

1. Ensure your `.jira_environment` file is configured with your Jira URL, username, API token, and board ID (see below).
2. Install requirements:

   ```sh
   pip install requests
   ```

3. Run the script:

   ```sh
   python jira_refine_sanity_check.py
   ```

## Output Example

```
Epics and Stories in 'To Refine' missing Label and/or Acceptance Criteria:

EPIC: MSEU-100: Improve Dashboard [ No Label; No Acceptance Criteria ]
  https://equinixjira.atlassian.net/browse/MSEU-100
  STORY: MSEU-101: Add filter [ No Acceptance Criteria ]
    https://equinixjira.atlassian.net/browse/MSEU-101
  STORY: MSEU-102: Add export [ No Label ]
    https://equinixjira.atlassian.net/browse/MSEU-102
```

## Configuration

Your `.jira_environment` file should look like this:

```sh
export JT_JIRA_URL="https://yourcompany.atlassian.net/"
export JT_JIRA_USERNAME="your.email@company.com"
export JT_JIRA_PASSWORD="your_api_token"
export JT_JIRA_BOARD="123"
```

- The script uses the Jira REST API and requires an API token for authentication.
- The script assumes the default Jira field for Epic Link is `customfield_10031` and for Acceptance Criteria is `acceptanceCriteria` or `customfield_10032`. Adjust the script if your Jira instance uses different custom field IDs.

## Notes

- Only Epics and Stories in the "To Refine" state **on the board configured in your `.jira_environment`** are checked.
- The script prints clickable links for easy access to each Epic or Story in Jira.
- No emails are sent; this is a reporting/sanity check tool.

## License

(Add your license here if you plan to share or distribute this script.)

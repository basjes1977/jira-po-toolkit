import subprocess
import sys
import os
from pathlib import Path

MENU = [
    ("Generate Sprint PowerPoint Presentation", "jpt.py"),
    ("Send Jira TODO Notification Email", "jira_todo_notify.py"),
    ("Check 'To Refine' Stories & Epics (Sanity Check)", "jira_refine_sanity_check.py"),
    ("Check 'Ready' Stories (Sanity Check)", "jira_ready_sanity_check.py"),
    ("Show 'On Hold' Stories Overview", "jira_on_hold_overview.py"),
    ("Show Blocked Stories Overview", "jira_blocked_overview.py"),
    ("Forecast Next Sprint Capacity (Excel Export)", "jpt_forecast.py"),
    ("Exit", None)
]

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def prompt_zscaler_usage():
    """Prompt user once about SSL configuration and set environment variable."""
    clear()
    print("SSL Configuration")
    print("-" * 50)
    print("\nHow should SSL certificates be verified?")
    print()
    print("  1. Use Zscaler certificate (for Zscaler proxy)")
    print("  2. Use standard SSL verification (no proxy)")
    print("  3. Disable SSL verification (not recommended, bypasses security)")
    print()
    print("If you get 'certificate verify failed' errors, you're likely behind")
    print("Zscaler and should choose option 1.")
    print()

    while True:
        response = input("Your choice (1/2/3): ").strip()
        if response == '1':
            # Check if Zscaler.pem exists
            cert_path = Path(__file__).parent / "Zscaler.pem"
            if cert_path.exists():
                os.environ['JT_SSL_VERIFY'] = str(cert_path)
                print(f"\n✓ Using Zscaler certificate: {cert_path}")
            else:
                print(f"\n⚠ Warning: Zscaler.pem not found at {cert_path}")
                print("  You may encounter SSL errors. Consider option 3 to bypass.")
                os.environ['JT_SSL_VERIFY'] = 'true'
            break
        elif response == '2':
            os.environ['JT_SSL_VERIFY'] = 'true'
            print("\n✓ Using standard SSL verification")
            print("  (If you get SSL errors, try option 1 or 3)")
            break
        elif response == '3':
            os.environ['JT_SSL_VERIFY'] = 'false'
            print("\n⚠ SSL verification DISABLED")
            print("  Warning: This bypasses certificate security checks!")
            break
        else:
            print("Invalid input. Please enter '1', '2', or '3'.")

    print("\nPress Enter to continue to main menu...")
    input()

def main():
    # Prompt for Zscaler usage once at startup
    prompt_zscaler_usage()

    # Explanations for each script
    EXPLANATIONS = {
        "jira_blocked_overview.py": (
            "Show Blocked Stories Overview\n"
            "-----------------------------\n"
            "Displays all stories that are blocked by another work item, including summary, labels, assignee, blockers, and a direct Jira link.\n"
        ),
        "jpt.py": (
            "Generate Sprint PowerPoint presentation\n"
            "--------------------------------------\n"
            "Fetches Jira sprint data and generates a PowerPoint presentation using a template.\n"
            "Groups issues by label, displays issue details, and includes summary and upcoming slides.\n"
            "Ensure 'sprint-template.pptx' is present in the script directory."
        ),
        "jira_todo_notify.py": (
            "Send Jira TODO notification email\n"
            "-------------------------------\n"
            "Sends a notification email for Jira TODOs.\n"
            "Supports SMTP/Outlook, test mode, and HTML/plain text. Configure credentials in .env or as prompted."
        ),
        "jira_refine_sanity_check.py": (
            "Run Jira refine sanity check\n"
            "----------------------------\n"
            "Checks all Epics and Stories in 'To Refine' state for missing labels and acceptance criteria.\n"
            "Acceptance criteria must be a markdown list in the custom field. Results are grouped by Epic."
        ),
        "jira_ready_sanity_check.py": (
            "Run Jira 'Ready' sanity check\n"
            "-----------------------------\n"
            "Checks all Stories in 'Ready' state for missing acceptance criteria and for a valid label.\n"
            "A story is only 'Ready' if it has acceptance criteria (markdown list) and a label from the PowerPoint generator's list."
        ),
        "jira_on_hold_overview.py": (
            "Show 'On Hold' Stories Overview\n"
            "-------------------------------\n"
            "Displays all stories with status 'On hold', including summary, labels, assignee, and a direct Jira link.\n"
        ),
        "jpt_forecast.py": (
            "Forecast Next Sprint Capacity (Excel Export)\n"
            "-------------------------------------------\n"
            "Fetches last 10 sprints, calculates achieved points/time, prompts for team availability, and forecasts next sprint's capacity.\n"
            "Exports results and forecast to Excel, appending new sprints only, with trend charts. Close the Excel file before running."
        ),
    }
    while True:
        clear()
        print("Jira Presentation Tool - Main Menu\n")
        for i, (desc, _) in enumerate(MENU, 1):
            print(f"  {i}. {desc}")
        try:
            choice = int(input("\nSelect an option: "))
        except Exception:
            print("Invalid input. Press Enter to continue...")
            input()
            continue
        if choice < 1 or choice > len(MENU):
            print("Invalid choice. Press Enter to continue...")
            input()
            continue
        desc, script = MENU[choice-1]
        if script is None:
            print("Goodbye!")
            break
        # Show explanation if available
        print(f"\n--- {desc} ---\n")
        if script in EXPLANATIONS:
            print(EXPLANATIONS[script] + "\n")
        # Use sys.executable to ensure the same Python environment
        try:
            subprocess.run([sys.executable, script], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\nScript '{script}' exited with error code {e.returncode}.")
        except FileNotFoundError:
            print(f"\nScript '{script}' not found.")
        print("\nPress Enter to return to the menu...")
        input()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Interactive setup wizard for JiraPresentationTool.

This script helps users configure their Jira environment by asking questions
and creating the .jira_environment file.
"""

import os
import sys
from pathlib import Path
import requests


def print_banner():
    """Print welcome banner."""
    print("=" * 60)
    print("Jira Presentation Tool - Setup Wizard")
    print("=" * 60)
    print()


def test_jira_connection(url, email, api_token):
    """Test if Jira credentials work.

    Returns:
        (success: bool, message: str)
    """
    try:
        url = url.rstrip('/')
        test_url = f"{url}/rest/api/3/myself"
        response = requests.get(
            test_url,
            auth=(email, api_token),
            timeout=10
        )

        if response.status_code == 200:
            user_data = response.json()
            display_name = user_data.get('displayName', 'Unknown')
            return True, f"✓ Successfully connected as: {display_name}"
        else:
            return False, f"✗ Connection failed: HTTP {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"✗ Connection error: {str(e)}"


def get_board_id(url, email, api_token):
    """Fetch available boards and let user select one.

    Returns:
        board_id: str or None
    """
    try:
        url = url.rstrip('/')
        boards_url = f"{url}/rest/agile/1.0/board"
        response = requests.get(
            boards_url,
            auth=(email, api_token),
            params={"maxResults": 50},
            timeout=10
        )

        if response.status_code != 200:
            print(f"Warning: Could not fetch boards (HTTP {response.status_code})")
            return None

        boards = response.json().get('values', [])
        if not boards:
            print("Warning: No boards found")
            return None

        print("\nAvailable Jira Boards:")
        for idx, board in enumerate(boards, 1):
            print(f"  {idx}. {board['name']} (ID: {board['id']}) - {board.get('type', 'Unknown')}")

        while True:
            try:
                choice = input(f"\nSelect board (1-{len(boards)}) or enter board ID directly: ").strip()

                # Try as index
                if choice.isdigit() and 1 <= int(choice) <= len(boards):
                    return str(boards[int(choice) - 1]['id'])

                # Try as direct board ID
                if choice.isdigit():
                    return choice

                print("Invalid choice. Please try again.")
            except (ValueError, KeyboardInterrupt):
                return None

    except Exception as e:
        print(f"Warning: Error fetching boards: {e}")
        return None


def main():
    """Run the setup wizard."""
    print_banner()

    env_path = Path.cwd() / '.jira_environment'

    if env_path.exists():
        print(f"⚠️  Configuration file already exists: {env_path}")
        overwrite = input("Do you want to overwrite it? [y/N]: ").strip().lower()
        if overwrite not in ('y', 'yes'):
            print("Setup cancelled.")
            sys.exit(0)
        print()

    print("Let's configure your Jira environment.\n")

    # Step 1: Jira URL
    print("Step 1: Jira Instance URL")
    print("Example: https://yourcompany.atlassian.net")
    while True:
        jira_url = input("Jira URL: ").strip()
        if jira_url.startswith('http'):
            break
        print("Please enter a valid URL starting with http:// or https://")

    # Step 2: Credentials
    print("\nStep 2: Jira Credentials")
    print("You'll need your Atlassian email and an API token.")
    print("Create an API token at: https://id.atlassian.com/manage-profile/security/api-tokens")

    email = input("\nJira Email: ").strip()
    api_token = input("Jira API Token: ").strip()

    # Test connection
    print("\nTesting connection...")
    success, message = test_jira_connection(jira_url, email, api_token)
    print(message)

    if not success:
        print("\n⚠️  Connection test failed. You can continue, but the tool may not work.")
        continue_anyway = input("Continue anyway? [y/N]: ").strip().lower()
        if continue_anyway not in ('y', 'yes'):
            print("Setup cancelled.")
            sys.exit(1)

    # Step 3: Board ID
    print("\nStep 3: Jira Board")
    board_id = get_board_id(jira_url, email, api_token)

    if not board_id:
        print("Could not automatically fetch boards.")
        board_id = input("Enter your Jira Board ID manually: ").strip()

    # Step 4: Custom Fields (with defaults)
    print("\nStep 4: Custom Field IDs (Optional)")
    print("Press Enter to use common defaults, or enter custom field IDs.")

    story_points = input("Story Points Field [customfield_10024]: ").strip() or "customfield_10024"
    epic_link = input("Epic Link Field [customfield_10031]: ").strip() or "customfield_10031"
    acceptance_criteria = input("Acceptance Criteria Field [customfield_10140]: ").strip() or "customfield_10140"

    # Step 5: SSL Verification
    print("\nStep 5: SSL Certificate Verification")
    print("1. Standard SSL verification (recommended)")
    print("2. Custom certificate file (for corporate proxies)")
    print("3. Disable SSL verification (not recommended)")

    while True:
        ssl_choice = input("Choose option [1]: ").strip() or "1"
        if ssl_choice in ('1', '2', '3'):
            break
        print("Invalid choice. Please enter 1, 2, or 3.")

    if ssl_choice == '1':
        ssl_verify = "true"
    elif ssl_choice == '2':
        cert_path = input("Enter path to certificate file: ").strip()
        ssl_verify = cert_path
    else:
        ssl_verify = "false"
        print("⚠️  WARNING: SSL verification disabled. This is not recommended for production use.")

    # Create .jira_environment file
    print("\nCreating configuration file...")

    config_content = f"""# Jira Presentation Tool Configuration
# Generated by setup wizard

# Jira Connection
JT_JIRA_URL={jira_url}
JT_JIRA_USERNAME={email}
JT_JIRA_PASSWORD={api_token}
JT_JIRA_BOARD={board_id}

# Custom Field IDs
JT_JIRA_FIELD_STORY_POINTS={story_points}
JT_JIRA_FIELD_EPIC_LINK={epic_link}
JT_JIRA_FIELD_ACCEPTANCE_CRITERIA={acceptance_criteria}

# SSL Verification
JT_SSL_VERIFY={ssl_verify}

# Optional: Enable debug logging (set to 1 for verbose output)
# JPT_VERBOSE=0
"""

    try:
        with open(env_path, 'w') as f:
            f.write(config_content)

        # Set file permissions to 600 (owner read/write only) for security
        os.chmod(env_path, 0o600)

        print(f"\n✓ Configuration saved to: {env_path}")
        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print("\nYou can now run:")
        print("  • Flask Web UI:  python webapp/app.py")
        print("  • CLI scripts:   python cli/powerpoint_cli.py")
        print("\nTo modify settings later, edit: .jira_environment")
        print()

    except Exception as e:
        print(f"\n✗ Error creating configuration file: {e}")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(130)

import argparse
import os
import smtplib
import subprocess
import sys
import webbrowser
from collections import defaultdict
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

import requests

from jira_config import load_jira_env

JIRA_ENV = load_jira_env()
JIRA_URL = JIRA_ENV.get("JT_JIRA_URL", "https://equinixjira.atlassian.net/").rstrip("/")
JIRA_EMAIL = JIRA_ENV.get("JT_JIRA_USERNAME")
JIRA_API_TOKEN = JIRA_ENV.get("JT_JIRA_PASSWORD")
BOARD_ID = JIRA_ENV.get("JT_JIRA_BOARD")

# --- Load SMTP settings from settings file ---
def load_smtp_settings():
    settings_path = Path(__file__).parent / "smtp_settings.env"
    smtp = {
        "SMTP_SERVER": "localhost",
        "SMTP_PORT": "25",
        "SMTP_USER": None,
        "SMTP_PASSWORD": None,
        "FROM_EMAIL": JIRA_EMAIL or "jira-bot@localhost",
        "FROM_NAME": "Jira Bot"
    }
    if settings_path.exists():
        with open(settings_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    smtp[k.strip()] = v.strip().strip('"')
    return smtp

SMTP = load_smtp_settings()

# Read default email method, platform, and test mode from SMTP settings
DEFAULT_EMAIL_METHOD = SMTP.get("EMAIL_METHOD", "smtp").lower()
DEFAULT_OUTLOOK_PLATFORM = SMTP.get("OUTLOOK_PLATFORM", None)
DEFAULT_TEST_MODE = SMTP.get("TEST_MODE", "false").lower() == "true"
DEFAULT_TEST_EMAIL = SMTP.get("TEST_EMAIL", "bas.rutjes@eu.equinix.com")

# --- Fetch all backlog stories in 'To Do' state ---
def get_todo_stories():
    url = f"{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/issue?jql=issuetype=Story AND status='To Do'"
    issues = []
    start_at = 0
    while True:
        params = {"startAt": start_at, "maxResults": 50}
        resp = requests.get(url, params=params, auth=(JIRA_EMAIL, JIRA_API_TOKEN))
        resp.raise_for_status()
        data = resp.json()
        issues.extend(data["issues"])
        if start_at + 50 >= data["total"]:
            break
        start_at += 50
    return issues

# --- Print summary and links ---
def print_todo_stories(issues):
    print("\nStories in 'To Do':\n-------------------")
    for issue in issues:
        key = issue["key"]
        summary = issue["fields"].get("summary", "")
        url = f"{JIRA_URL}/browse/{key}"
        print(f"{key}: {summary}\n  {url}\n")

# --- Group by assignee ---
def group_by_assignee(issues):
    grouped = defaultdict(list)
    for issue in issues:
        assignee = issue["fields"].get("assignee")
        if assignee and assignee.get("emailAddress"):
            grouped[assignee["emailAddress"]].append(issue)
        else:
            # No assignee, send to Bas
            grouped["bas.rutjes@eu.equinix.com"].append(issue)
    return grouped

# --- Send notification emails ---
def send_email(to_email, to_name, issues, method="smtp", platform=None):
    from_email = SMTP["FROM_EMAIL"]
    from_name = SMTP["FROM_NAME"]
    subject = f"Jira: Your 'To Do' Stories"

    # Build HTML body
    html_body = f"""
    <html>
    <body style='font-family: Arial, sans-serif; font-size: 14px;'>
    <p>Dear {to_name},</p><br>
    <p>You have the following story/stories that are in the <b>To Do</b> state.<br>
    Please see to it they get updated. Once done, set them to the <b>To Refine</b> state so we can refine the story further.</p><br>
    <ul>
    """
    for issue in issues:
        key = issue["key"]
        summary = issue["fields"].get("summary", "")
        url = f"{JIRA_URL}/browse/{key}"
        html_body += f'<li><a href="{url}"><b>{key}</b></a>: {summary}</li>'
    html_body += """
    </ul>
    <p>With kind regards,<br>Your Product Owner</p>
    </body>
    </html>
    """

    # Improved plain text body for non-HTML clients
    # Use Unicode line separator (U+2028) and paragraph separator (U+2029)
    LS = '\u2028'  # Line Separator
    PS = '\u2029'  # Paragraph Separator
    body = (
        f"Dear {to_name},{PS}"
        f"You have the following story/stories in the 'To Do' state:{PS}"
        f"--------------------------------------------------------{PS}"
    )
    for issue in issues:
        key = issue["key"]
        summary = issue["fields"].get("summary", "")
        url = f"{JIRA_URL}/browse/{key}"
        body += (
            f"{key}:{LS}"
            f"    {summary}{LS}"
            f"    Link: {url}{PS}"
        )
    body += (
        f"--------------------------------------------------------{PS}"
        f"Please update these stories as needed. Once done, set them to the 'To Refine' state so we can refine them further.{PS}"
        f"With kind regards,{PS}Your Product Owner"
    )
    if method == "smtp":
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((from_name, from_email))
        msg["To"] = to_email
        part1 = MIMEText(body, "plain")
        part2 = MIMEText(html_body, "html")
        msg.attach(part1)
        msg.attach(part2)
        print(f"[LOG] Sending email to {to_email} using SMTP with HTML and plain text parts.")
        try:
            smtp_server = SMTP["SMTP_SERVER"]
            smtp_port = int(SMTP["SMTP_PORT"])
            if smtp_port == 465:
                import smtplib
                with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                    if SMTP["SMTP_USER"] and SMTP["SMTP_PASSWORD"]:
                        server.login(SMTP["SMTP_USER"], SMTP["SMTP_PASSWORD"])
                    server.sendmail(from_email, [to_email], msg.as_string())
            else:
                import smtplib
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.ehlo()
                    if smtp_port == 587:
                        server.starttls()
                        server.ehlo()
                    if SMTP["SMTP_USER"] and SMTP["SMTP_PASSWORD"]:
                        server.login(SMTP["SMTP_USER"], SMTP["SMTP_PASSWORD"])
                    server.sendmail(from_email, [to_email], msg.as_string())
            print(f"Email sent to {to_email}")
        except Exception as e:
            print(f"Failed to send email to {to_email}: {e}")
    elif method == "outlook":
        if platform == "mac":
            # Use AppleScript to send mail via Outlook on Mac (plain text only)
            print(f"[LOG] Sending email to {to_email} using Outlook (Mac) in plain text mode.")
            applescript = f'''
            tell application "Microsoft Outlook"
                set newMessage to make new outgoing message with properties {{subject:"{subject}", plain text content:"{body}"}}
                tell newMessage
                    make new recipient at end of to recipients with properties {{email address:{{address:"{to_email}"}}}}
                    send
                end tell
            end tell
            '''
            try:
                subprocess.run(["osascript", "-e", applescript], check=True)
                print(f"Outlook (Mac): Email sent to {to_email}")
            except Exception as e:
                print(f"Failed to send email via Outlook (Mac) to {to_email}: {e}")
        elif platform == "windows":
            print(f"[LOG] Sending email to {to_email} using Outlook (Windows) with HTML body.")
            try:
                import win32com.client
                outlook = win32com.client.Dispatch('Outlook.Application')
                mail = outlook.CreateItem(0)
                mail.To = to_email
                mail.Subject = subject
                mail.BodyFormat = 2  # 2 = HTML format
                mail.HTMLBody = html_body
                mail.Send()
                print(f"Outlook (Windows): Email sent to {to_email}")
            except Exception as e:
                print(f"Failed to send email via Outlook (Windows) to {to_email}: {e}")
        else:
            print("Unknown platform for Outlook. Use 'mac' or 'windows'.")
    else:
        print("Unknown email method. Use 'smtp' or 'outlook'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Notify Jira assignees of their 'To Do' stories.")
    parser.add_argument('--test', action='store_true', help='Test mode: only send email to the configured test address (overrides smtp_settings.env)')
    parser.add_argument('--test-email', type=str, help='Override the test email address (overrides smtp_settings.env)')
    parser.add_argument('--email-method', choices=['smtp', 'outlook'], help='Choose email method: smtp or outlook (overrides smtp_settings.env)')
    parser.add_argument('--outlook-platform', choices=['mac', 'windows'], help='If using --email-method outlook, specify platform (overrides smtp_settings.env)')
    args = parser.parse_args()

    # Use CLI args if provided, else fall back to smtp_settings.env
    email_method = args.email_method if args.email_method else DEFAULT_EMAIL_METHOD
    outlook_platform = args.outlook_platform if args.outlook_platform else DEFAULT_OUTLOOK_PLATFORM

    test_mode = args.test if args.test else DEFAULT_TEST_MODE
    test_email = args.test_email if args.test_email else DEFAULT_TEST_EMAIL

    issues = get_todo_stories()
    print_todo_stories(issues)
    grouped = group_by_assignee(issues)

    if test_mode:
        # Combine all issues into one list for the test email
        all_issues = [issue for user_issues in grouped.values() for issue in user_issues]
        if all_issues:
            send_email(test_email, f"{test_email} (TEST)", all_issues, method=email_method, platform=outlook_platform)
        else:
            print(f"No 'To Do' stories found for test email {test_email}.")
    else:
        print("[CONFIRMATION] Test mode is OFF. This will send real emails to all assignees.")
        confirm = input("Are you sure you want to continue? Type 'yes' to proceed: ").strip().lower()
        if confirm != 'yes':
            print("Aborted by user.")
            sys.exit(0)
        for email, user_issues in grouped.items():
            # If this is the fallback group, use a generic name
            if email == "bas.rutjes@eu.equinix.com":
                name = "Bas Rutjes (Unassigned Stories)"
            else:
                assignee = user_issues[0]["fields"].get("assignee", {})
                name = assignee.get("displayName", email)
            send_email(email, name, user_issues, method=email_method, platform=outlook_platform)

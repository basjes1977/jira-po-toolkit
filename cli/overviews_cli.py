#!/usr/bin/env python3
"""
CLI wrapper for blocked and on-hold story overviews.

This script provides a command-line interface to view blocked and on-hold stories.
"""

import sys
import argparse

from core.overviews import get_blocked_stories, get_on_hold_stories


def print_blocked_stories(stories):
    """Print blocked stories in a formatted way.

    Args:
        stories: List of blocked story dicts
    """
    print("\nStories that are blocked by another work item:\n")
    if not stories:
        print("No blocked stories found.")
        return

    for story in stories:
        labels_str = ", ".join(story['labels']) if story['labels'] else "None"
        blockers_str = ", ".join(story['blockers'])
        print(f"STORY: {story['key']}: {story['summary']}")
        print(f"  Labels: {labels_str}")
        print(f"  Assignee: {story['assignee']}")
        print(f"  Blocked by: {blockers_str}")
        print(f"  {story['url']}\n")


def print_on_hold_stories(stories):
    """Print on-hold stories in a formatted way.

    Args:
        stories: List of on-hold story dicts
    """
    print("\nStories with status 'On hold':\n")
    if not stories:
        print("No stories with status 'On hold' found.")
        return

    for story in stories:
        labels_str = ", ".join(story['labels']) if story['labels'] else "None"
        print(f"STORY: {story['key']}: {story['summary']}")
        print(f"  Labels: {labels_str}")
        print(f"  Assignee: {story['assignee']}")
        print(f"  {story['url']}\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="View Blocked and On-Hold Stories"
    )
    parser.add_argument(
        "--type", "-t",
        choices=["blocked", "on-hold", "both"],
        default="both",
        help="Type of overview to display (default: both)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    args = parser.parse_args()

    # Set up logging level
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

    try:
        # Fetch and display blocked stories
        if args.type in ("blocked", "both"):
            result = get_blocked_stories()
            if not result['success']:
                print(f"\n✗ Error fetching blocked stories: {result['error']}", file=sys.stderr)
                sys.exit(1)
            print_blocked_stories(result['stories'])

        # Fetch and display on-hold stories
        if args.type in ("on-hold", "both"):
            result = get_on_hold_stories()
            if not result['success']:
                print(f"\n✗ Error fetching on-hold stories: {result['error']}", file=sys.stderr)
                sys.exit(1)
            print_on_hold_stories(result['stories'])

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nCancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

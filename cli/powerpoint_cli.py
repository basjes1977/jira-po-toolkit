#!/usr/bin/env python3
"""
CLI wrapper for PowerPoint generation.

This script provides a command-line interface to the core PowerPoint generation logic.
"""

import sys
import argparse
import threading
import itertools
import time
from pathlib import Path

from core.powerpoint import generate_sprint_presentation


def show_spinner(message_container):
    """Show animated spinner with progress message."""
    emojis = ["⏳", "🕐", "🕑", "🕒", "🕓", "🕔", "⌛", "🕐", "🕑", "🕒", "🕓", "🕔"]
    for idx in itertools.cycle(range(len(emojis))):
        if not message_container.get('running', True):
            break
        msg = message_container.get('message', '')
        sys.stdout.write(f"\r{emojis[idx]} {msg}   ")
        sys.stdout.flush()
        time.sleep(0.15)
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Jira Sprint Review PowerPoint Presentation"
    )
    parser.add_argument(
        "--sprint-id", "-s",
        type=int,
        help="Sprint ID to generate presentation for (default: active sprint)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        help="Output directory for the presentation file (default: current directory)"
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

    # Spinner state
    spinner_state = {
        'running': True,
        'message': 'Starting...'
    }

    # Progress callback to update spinner message
    def progress_callback(message: str):
        spinner_state['message'] = message

    # Start spinner thread
    spinner_thread = threading.Thread(target=show_spinner, args=(spinner_state,))
    spinner_thread.daemon = True
    spinner_thread.start()

    try:
        # Generate presentation
        result = generate_sprint_presentation(
            sprint_id=args.sprint_id,
            output_dir=Path(args.output_dir) if args.output_dir else None,
            progress_callback=progress_callback
        )

        # Stop spinner
        spinner_state['running'] = False
        spinner_thread.join(timeout=1)

        # Check result
        if result['success']:
            print(f"\n✓ Success! Generated presentation for {result['sprint_name']}")
            print(f"  File: {result['file_path']}")
            print(f"  Issues: {result['issue_count']}")
            print(f"  Epics: {result['epic_count']}")
            sys.exit(0)
        else:
            print(f"\n✗ Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

    except KeyboardInterrupt:
        spinner_state['running'] = False
        spinner_thread.join(timeout=1)
        print("\n\nCancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        spinner_state['running'] = False
        spinner_thread.join(timeout=1)
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

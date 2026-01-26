#!/usr/bin/env python3
"""
CLI wrapper for sprint forecast generation.

This script provides a command-line interface to the core forecast logic.
"""

import sys
import argparse
import threading
import itertools
import time as _time
from pathlib import Path

from core.forecast import generate_sprint_forecast, get_sprint_history


def prompt_availability(members):
    """Interactively prompt for team member availability.

    Args:
        members: List of team member names

    Returns:
        Dict mapping member names to available days
    """
    print("\nEnter the number of days each team member is available in the coming sprint:")
    avail = {}
    for m in members:
        while True:
            try:
                days = float(input(f"  {m}: "))
                avail[m] = days
                break
            except (ValueError, EOFError):
                print("  Please enter a number.")
    return avail


def show_spinner(message_container):
    """Show animated spinner with progress message."""
    emojis = ["⏳", "🕐", "🕑", "🕒", "🕓", "🕔", "⌛", "🕐", "🕑", "🕒", "🕓", "🕔"]
    for idx in itertools.cycle(range(len(emojis))):
        if not message_container.get('running', True):
            break
        msg = message_container.get('message', '')
        sys.stdout.write(f"\r{emojis[idx]} {msg}   ")
        sys.stdout.flush()
        _time.sleep(0.15)
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()


def print_forecast_table(forecast_windows):
    """Print forecast results in a formatted table.

    Args:
        forecast_windows: Dict containing forecast data
    """
    print("\n--- Sprint Forecast ---")
    print(f"Team total available days (next sprint): {forecast_windows['total_availability']}")
    print("\n| Window   | Avg Points | Forecast Points| Avg Time | Forecast Time |")
    print("|----------|------------|----------------|----------|---------------|")

    for window_key, window_label in [
        ('last_1', 'Last 1'),
        ('last_3', 'Last 3'),
        ('last_5', 'Last 5'),
        ('last_10', 'Last 10')
    ]:
        w = forecast_windows[window_key]
        print(f"| {window_label:8} | {w['avg_points']:10.1f} | {w['forecast_points']:14.1f} | "
              f"{w['avg_time_formatted']:8} | {w['forecast_time_formatted']:13} |")

    print("\nNotes:")
    print("- Forecast is scaled by the ratio of available days (next sprint vs. past sprints).")
    print("- Past sprint availability is estimated as 10 days per team member per sprint.")
    print("- Forecast is based on achieved (Done/Closed/Resolved) issues only.")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Sprint Forecast Based on Historical Data"
    )
    parser.add_argument(
        "--max-sprints", "-n",
        type=int,
        default=10,
        help="Maximum number of completed sprints to analyze (default: 10)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        help="Output directory for the Excel file (default: current directory)"
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
        # First, fetch sprint history to get team members
        results, all_members = get_sprint_history(
            max_sprints=args.max_sprints,
            progress_callback=progress_callback
        )

        # Stop spinner for interactive input
        spinner_state['running'] = False
        spinner_thread.join(timeout=1)

        if not results:
            print("\n✗ Error: No completed sprints found", file=sys.stderr)
            sys.exit(1)

        # Show sprint information
        print("\nSprints analyzed:")
        for r in results:
            s = r['sprint']
            print(f"  {s['name']} ({s.get('startDate', '')[:10]} to {s.get('endDate', '')[:10]})")

        # Interactively prompt for team availability
        team_availability = prompt_availability(all_members)

        # Restart spinner for forecast generation
        spinner_state['running'] = True
        spinner_thread = threading.Thread(target=show_spinner, args=(spinner_state,))
        spinner_thread.daemon = True
        spinner_thread.start()

        # Generate forecast
        result = generate_sprint_forecast(
            team_availability=team_availability,
            output_dir=Path(args.output_dir) if args.output_dir else None,
            max_sprints=args.max_sprints,
            progress_callback=progress_callback
        )

        # Stop spinner
        spinner_state['running'] = False
        spinner_thread.join(timeout=1)

        # Check result
        if result['success']:
            print_forecast_table(result['forecast_windows'])
            print(f"\n✓ Excel file with sprint history and forecast saved as: {result['file_path']}")
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
        import traceback
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

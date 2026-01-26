"""
Simple Flask web UI for Jira Presentation Tool.

This provides a web interface for all CLI operations:
- PowerPoint generation
- Sprint forecasting
- Sanity checks
- Overviews (blocked, on-hold)

To run: python webapp/app.py
Access: http://localhost:5000
"""

from flask import Flask, render_template
from pathlib import Path
import os
import sys


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['OUTPUT_DIR'] = Path.cwd()  # Save to current directory (same as CLI)

    # Add parent directory to path so we can import webapp.routes
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    from webapp.routes import powerpoint, forecast, overviews, sanity_checks, setup
    app.register_blueprint(powerpoint.bp)
    app.register_blueprint(forecast.bp)
    app.register_blueprint(overviews.bp)
    app.register_blueprint(sanity_checks.bp)
    app.register_blueprint(setup.bp)

    def check_config():
        """Check if .jira_environment exists."""
        from flask import request, redirect, url_for
        env_path = Path.cwd() / '.jira_environment'

        # Skip check for setup routes and static files
        if request.path.startswith('/setup') or request.path.startswith('/static') or request.path == '/health':
            return None

        if not env_path.exists():
            return redirect(url_for('setup.index'))

    app.before_request(check_config)

    @app.route('/')
    def index():
        """Home page."""
        return render_template('index.html')

    @app.route('/health')
    def health():
        """Health check endpoint."""
        return {'status': 'ok'}, 200

    return app


if __name__ == '__main__':
    app = create_app()
    print("=" * 60)
    print("Jira Presentation Tool - Web UI")
    print("=" * 60)
    print("\nStarting Flask server at http://localhost:5000")
    print("\nPress Ctrl+C to stop\n")
    app.run(debug=True, port=5000, host='127.0.0.1')
